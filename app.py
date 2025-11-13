import os
import tempfile
import zipfile
import json
import uuid
from flask import Flask, request, send_from_directory, jsonify, render_template, redirect, url_for
import numpy as np
import pydicom
from skimage import measure

BASE_DIR = os.path.dirname(__file__)
UPLOADS = os.path.join(BASE_DIR, "uploads")
DATA = os.path.join(BASE_DIR, "data")  # store volumes as .npz
MESH_DIR = os.path.join(BASE_DIR, "mesh")
for d in (UPLOADS, DATA, MESH_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')

def read_dicom_series_from_files(file_paths):
    slices = []
    for p in file_paths:
        try:
            ds = pydicom.dcmread(p)
            if hasattr(ds, 'PixelData'):
                slices.append(ds)
        except Exception as e:
            print("skip", p, e)
    if not slices:
        raise RuntimeError("No valid DICOM slices found.")
    def sort_key(x):
        if hasattr(x, 'InstanceNumber'):
            return int(x.InstanceNumber)
        if hasattr(x, 'SliceLocation'):
            return float(x.SliceLocation)
        return 0
    slices.sort(key=sort_key)
    arrs = [s.pixel_array.astype(np.int16) for s in slices]
    volume = np.stack(arrs, axis=0)
    try:
        spacing = (float(slices[0].SliceThickness), float(slices[0].PixelSpacing[0]), float(slices[0].PixelSpacing[1]))
    except Exception:
        spacing = (1.0,1.0,1.0)
    return volume, spacing

def generate_mesh_from_volume(volume, spacing, threshold):
    v = volume.astype(float)
    v = (v - v.min()) / (v.max() - v.min() + 1e-9)
    verts, faces, normals, values = measure.marching_cubes(v, level=threshold, spacing=spacing)
    return {"vertices": verts.tolist(), "faces": faces.tolist()}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # Accept zip or multiple files
    if 'zipfile' in request.files and request.files['zipfile'].filename != '':
        z = request.files['zipfile']
        tempdir = tempfile.mkdtemp(dir=UPLOADS)
        zpath = os.path.join(tempdir, "upload.zip")
        z.save(zpath)
        with zipfile.ZipFile(zpath, 'r') as zf:
            zf.extractall(tempdir)
        file_paths = []
        for root, _, filenames in os.walk(tempdir):
            for fn in filenames:
                file_paths.append(os.path.join(root, fn))
    else:
        files = request.files.getlist('files')
        if not files:
            return "No files uploaded", 400
        tempdir = tempfile.mkdtemp(dir=UPLOADS)
        file_paths = []
        for f in files:
            outp = os.path.join(tempdir, f.filename)
            f.save(outp)
            file_paths.append(outp)
    try:
        volume, spacing = read_dicom_series_from_files(file_paths)
    except Exception as e:
        return f"Failed to read DICOM series: {e}", 400
    case_id = str(uuid.uuid4())
    np.savez_compressed(os.path.join(DATA, f"{case_id}.npz"), volume=volume, spacing=spacing)
    # generate initial mesh with default threshold 0.5
    mesh = generate_mesh_from_volume(volume, spacing, threshold=0.5)
    mesh_path = os.path.join(MESH_DIR, f"{case_id}.json")
    with open(mesh_path, 'w') as fh:
        json.dump(mesh, fh)
    return redirect(url_for('viewer', case_id=case_id))

@app.route('/viewer/<case_id>')
def viewer(case_id):
    return render_template('viewer.html', case_id=case_id)

@app.route('/mesh/<case_id>.json')
def mesh_json(case_id):
    # optional threshold param
    threshold = float(request.args.get('threshold', 0.5))
    mesh_path = os.path.join(MESH_DIR, f"{case_id}.json")
    data_path = os.path.join(DATA, f"{case_id}.npz")
    if os.path.exists(mesh_path):
        # If threshold is default and mesh exists, serve it
        if abs(threshold - 0.5) < 1e-6:
            return send_from_directory(MESH_DIR, f"{case_id}.json")
    if not os.path.exists(data_path):
        return jsonify({"error": "case not found"}), 404
    # regenerate mesh from saved volume
    with np.load(data_path, allow_pickle=True) as dd:
        volume = dd['volume']
        spacing = tuple(dd['spacing'].tolist()) if hasattr(dd['spacing'], 'tolist') else tuple(dd['spacing'])
    mesh = generate_mesh_from_volume(volume, spacing, threshold)
    # save mesh for future default use
    with open(mesh_path, 'w') as fh:
        json.dump(mesh, fh)
    return jsonify(mesh)

@app.route('/cases')
def list_cases():
    # list available cases
    cases = []
    for fn in os.listdir(DATA):
        if fn.endswith('.npz'):
            cid = fn.replace('.npz','')
            cases.append(cid)
    return jsonify({"cases": cases})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
