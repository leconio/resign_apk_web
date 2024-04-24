import os
import json
import shutil
from flask import Flask, request, render_template, send_file, stream_with_context, Response
from datetime import datetime, timedelta
import subprocess

jarsigner_exec = os.getenv('APKSIGNER_PATH', '')

app = Flask(__name__)

# Path to the configuration file
CONFIG_FILE = 'config.json'

# Directory for saving uploaded files
UPLOAD_FOLDER = 'uploads'

# Read the configuration file
with open(CONFIG_FILE) as f:
    config = json.load(f)

@app.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Retrieve the uploaded file and selected car model
        file = request.files['file']
        car_type = request.form['car_type']

        # Check if the file type is an APK
        if file and file.filename.endswith('.apk'):
            # Save the uploaded file
            filename = datetime.now().strftime('%Y%m%d_%H%M%S') + '.apk'
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

            # Redirect to the signing page
            return render_template('sign.html', file_path=file_path, car_type=car_type)

    # Render the upload page
    return render_template('upload.html', car_types=config.keys())

@app.route('/sign', methods=['POST'])
def sign():
    # Retrieve all necessary data before entering the generator
    file_path = request.form['file_path']
    car_type = request.form['car_type']

    # Get the certificate path for the selected car model
    keystore_path = config[car_type]['keystore']
    alias = config[car_type]['alias']
    password = config[car_type]['password']
    keypass = config[car_type]['keypass']

    # Generator function using previously retrieved local variables
    def sign_and_respond():
        # Check for jarsigner environment
        check_jarsigner_command = jarsigner_exec
        try:
            subprocess.check_output(check_jarsigner_command, shell=True, stderr=subprocess.STDOUT)
            yield 'Jarsigner environment check passed\n'
        except subprocess.CalledProcessError:
            yield 'Jarsigner environment check failed, please ensure the Java Development Kit (JDK) is correctly installed and configured\n'
            return

        # Sign the APK file
        signed_filename = f'signed_{os.path.basename(file_path)}'
        signed_file_path = os.path.join(UPLOAD_FOLDER, signed_filename)
        sign_command = f'{check_jarsigner_command} sign --ks {keystore_path} -ks-type pkcs12 --ks-pass pass:{password} --ks-key-alias {alias} --key-pass pass:{keypass} --v1-signing-enabled true --v2-signing-enabled true --out {signed_file_path} {file_path}'

        try:
            output = subprocess.check_output(sign_command, shell=True, stderr=subprocess.STDOUT)
            yield output.decode('utf-8')
            yield f'APK signing successful, signed file: {signed_filename}\n'
        except subprocess.CalledProcessError as e:
            yield f'APK signing failed: {str(e)}\n'
            return

        # Return download link
        download_url = f'<a href="/download/{signed_filename}">{signed_filename}</a>'
        yield f'Download link: {download_url}\n'

    return Response(stream_with_context(sign_and_respond()))

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)