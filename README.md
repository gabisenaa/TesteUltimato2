# RADIORUM — DICOM 3D Viewer (Render-ready prototype)

**What this is**
- A Render-ready prototype for RADIORUM: accepts multi-file or ZIP DICOM uploads, stores a reconstructed volume per case, and serves an interactive 3D mesh viewer with a real-time threshold slider (requests server to regenerate mesh without reupload).
- Intended as a demo/proof-of-concept. Not production-ready for PHI handling.

**How to deploy on Render**
1. Push this repository to GitHub.
2. Create a new Web Service on Render and connect your GitHub repo.
3. For the build command use: `pip install -r requirements.txt`
   For the start command use: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Render will provide an URL like `https://your-app.onrender.com`.

**Local testing**
- Create a virtualenv and install requirements:
  ```bash
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
- Run locally with gunicorn (recommended) or python:
  ```bash
  gunicorn app:app --bind 0.0.0.0:5000
  # or
  python app.py
  ```
