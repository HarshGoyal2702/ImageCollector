from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file
import os
from rembg import remove
import cv2
import numpy as np
from datetime import datetime
import zipfile
import io

from config import SECRET_KEY, UPLOAD_FOLDER, RESULT_FOLDER, ZIP_FOLDER, ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Set folders
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['ZIP_FOLDER'] = ZIP_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)
os.makedirs(app.config['ZIP_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        username = request.form['username']
        file = request.files['file']

        if file and username and allowed_file(file.filename):
            filename = f"{username}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process image
            input_image = cv2.imread(filepath)
            input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
            result = remove(input_image)

            output_filename = f"{username}_transparent.png"
            output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename)
            cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGRA))

            flash("✅ Image uploaded and background removed successfully!", "success")
            return redirect(url_for('upload_file'))
        else:
            flash("❌ Please provide valid username and image file.", "danger")
            return redirect(url_for('upload_file'))

    return render_template('upload.html')


# Admin password
ADMIN_PASSWORD = "admin123"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect password.', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    image_data = []
    result_files = sorted(os.listdir(app.config['RESULT_FOLDER']), reverse=True)

    for processed_filename in result_files:
        if processed_filename.endswith('_transparent.png'):
            username = processed_filename.replace('_transparent.png', '')
            original_filename = f"{username}.jpg"  # or png, adjust if needed
            original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            image_data.append({
                "username": username,
                "processed_filename": processed_filename,
                "original_filename": original_filename,
                "original_exists": os.path.exists(original_path)
            })

    if request.method == 'POST':
        selected_images = request.form.getlist('selected_images')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for filename in selected_images:
                result_path = os.path.join(app.config['RESULT_FOLDER'], filename)
                if os.path.exists(result_path):
                    zip_file.write(result_path, arcname=filename)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name="selected_images.zip",
            mimetype='application/zip'
        )

    return render_template('admin_dashboard.html', images=image_data)

@app.route('/admin/delete/<filename>')
def delete_image(filename):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        os.remove(os.path.join(app.config['RESULT_FOLDER'], filename))
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename.replace("_transparent.png", "")))
    except Exception as e:
        print(f"Error deleting files: {e}")

    flash('Image deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=5000)
