# hjCAD

![image](https://github.com/user-attachments/assets/ecd31614-153f-48e0-8e02-c5b776e08d91)

hjCAD is a free, open-source alternative to GrabCAD - a 3D/2D design file sharing platform.

## About

hjCAD allows engineers and designers to upload, share, and collaborate on CAD files. It supports various file formats commonly used in CAD software.

## Features

- Google OAuth integration for secure user authentication
- File upload with support for multiple CAD file formats
- File metadata including descriptions and tags
- Like and comment functionality for shared files
- Search capability to find relevant CAD files
- Rate limiting to prevent abuse

## Tech Stack

- Backend: Python with Flask framework
- Frontend: HTML with Tailwind CSS
- Authentication: Google OAuth 2.0
- Database: JSON file-based storage (can be extended to other databases)

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Run the application: `python app.py`

## Usage

After setting up the project, users can:
1. Log in using their Google account
2. Upload CAD files
3. View and download shared CAD files
4. Like and comment on files
5. Search for specific files using keywords

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Contact

Project maintained by [hemangjoshi37a](https://github.com/hemangjoshi37a).
