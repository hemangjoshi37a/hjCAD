import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, jsonify, session, send_file
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError, InvalidScopeError
import config
from werkzeug.utils import secure_filename
import json
import uuid
from datetime import datetime
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

app.secret_key = config.YOUR_SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = config.ALLOWED_EXTENSIONS
app.config['CAD_DATA_FILE'] = 'cad_data.json'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size

# Setup for Google OAuth2
blueprint = make_google_blueprint(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    scope=["https://www.googleapis.com/auth/userinfo.email", "openid", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_url="/"
)
app.register_blueprint(blueprint, url_prefix="/login")


# Setup rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_cad_data():
    if not os.path.exists(app.config['CAD_DATA_FILE']):
        return {}
    with open(app.config['CAD_DATA_FILE'], 'r') as f:
        return json.load(f)

def save_cad_data(data):
    with open(app.config['CAD_DATA_FILE'], 'w') as f:
        json.dump(data, f, indent=4)

@app.route("/")
@login_required
def index():
    try:
        resp = google.get("/oauth2/v2/userinfo")
        assert resp.ok, resp.text
        user_info = resp.json()
        session['user_id'] = user_info['id']
        session['user_email'] = user_info['email']
    except (TokenExpiredError, InvalidScopeError):
        del blueprint.token
        return redirect(url_for("google.login"))

    return render_template("index.html", user_info=user_info)

@app.route('/upload', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def upload_file():
    if 'cad_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400

    file = request.files['cad_file']
    description = request.form.get('description', '').strip()
    tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        cad_data = get_cad_data()
        cad_data[unique_filename] = {
            'original_filename': filename,
            'description': description,
            'tags': tags,
            'likes': 0,
            'comments': [],
            'upload_date': datetime.now().isoformat(),
            'uploader': session.get('user_email', 'anonymous'),
            'file_size': os.path.getsize(file_path)
        }
        save_cad_data(cad_data)

        return jsonify({'success': True, 'message': 'File uploaded successfully'})

    return jsonify({'success': False, 'message': 'Invalid file extension'}), 400

@app.route('/get_cad_files')
@login_required
def get_cad_files_route():
    cad_files = get_cad_files()
    return jsonify(cad_files)

@app.route('/download/<filename>', methods=['GET'])
@login_required
@limiter.limit("30/minute")
def download_file(filename):
    cad_data = get_cad_data()
    if filename in cad_data:
        original_filename = cad_data[filename]['original_filename']
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True, download_name=original_filename)
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/like/<filename>', methods=['POST'])
@login_required
@limiter.limit("30/minute")
def like_file(filename):
    cad_data = get_cad_data()
    if filename in cad_data:
        cad_data[filename]['likes'] += 1
        save_cad_data(cad_data)
        return jsonify({'success': True, 'likes': cad_data[filename]['likes']})
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
@login_required
def delete_file(filename):
    cad_data = get_cad_data()
    if filename in cad_data:
        if cad_data[filename]['uploader'] != session.get('user_email'):
            return jsonify({'success': False, 'message': 'You are not authorized to delete this file'}), 403

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            del cad_data[filename]
            save_cad_data(cad_data)
            return jsonify({'success': True, 'message': 'File deleted successfully'})

    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/comment/<filename>', methods=['POST'])
@login_required
@limiter.limit("10/minute")
def add_comment(filename):
    comment = request.json.get('comment', '').strip()
    if not comment:
        return jsonify({'success': False, 'message': 'Comment cannot be empty'}), 400

    user_email = session.get('user_email', 'anonymous')

    cad_data = get_cad_data()
    if filename in cad_data:
        cad_data[filename]['comments'].append({
            'user': user_email,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        })
        save_cad_data(cad_data)
        return jsonify({'success': True, 'message': 'Comment added successfully'})
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route('/search', methods=['GET'])
@login_required
def search_files():
    query = request.args.get('q', '').lower()
    cad_files = get_cad_files()
    results = [file for file in cad_files if query in file['original_filename'].lower() or
               query in file['description'].lower() or
               any(query in tag.lower() for tag in file['tags'])]
    return jsonify(results)

def get_cad_files():
    cad_data = get_cad_data()
    files = [
        {
            'filename': filename,
            'original_filename': file_data['original_filename'],
            'description': file_data['description'],
            'tags': file_data['tags'],
            'likes': file_data['likes'],
            'comments': file_data['comments'],
            'upload_date': file_data['upload_date'],
            'uploader': file_data['uploader'],
            'file_size': file_data['file_size']
        }
        for filename, file_data in cad_data.items()
    ]
    return sorted(files, key=lambda x: x['likes'], reverse=True)

@app.route('/get_file_content/<filename>')
@login_required
def get_file_content(filename):
    cad_data = get_cad_data()
    if filename in cad_data:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        return send_file(file_path)
    return jsonify({'success': False, 'message': 'File not found'}), 404

@app.route("/logout")
def logout():
    if google.authorized:
        token = blueprint.token["access_token"]
        resp = google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert resp.ok, resp.text
        del blueprint.token
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(ssl_context="adhoc", port=5001, debug=False)
