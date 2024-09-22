import os
from dotenv import load_dotenv

load_dotenv()

YOUR_SECRET_KEY = os.getenv('SECRET_KEY')
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# Directory to save uploaded files
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')

# Set of allowed file extensions
ALLOWED_EXTENSIONS = {'stp', 'step', 'igs', 'iges', 'dxf', 'dwg', 'sldprt', 'sldasm'}

# Define the allowed extensions function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
