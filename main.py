from datetime import datetime
from flask import Flask, flash, render_template, request, redirect, send_file
from google.cloud import storage
import os
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Part

load_dotenv()
google_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

app = Flask(__name__)
app.secret_key = 'sreeja'

project_id = 'assignment1-436717'
bucket_name = "srija_1503"
storage_client = storage.Client()
ALLOWED_EXTENSIONS = {'wav', 'txt', 'mp3'}

vertexai.init(project=project_id, location="us-central1")
model = GenerativeModel("gemini-1.5-flash-001")
prompt = """
Please provide an exact transcript for the audio, followed by sentiment analysis.

Your response should follow the format:

Text: USERS SPEECH TRANSCRIPTION

Sentiment Analysis: positive|neutral|negative
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_cloud_files(bucket_name):
    bucket = storage_client.bucket(bucket_name)
    return [blob.name for blob in bucket.list_blobs()]

def upload_blob(file_data, destination_blob_name):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(file_data, content_type=file_data.content_type)
    except Exception as e:
        print(f"Error uploading file: {e}")

def transcribe_gcs(gcs_uri):
    audio_file = Part.from_uri(gcs_uri, mime_type="audio/wav")
    contents = [audio_file, prompt]
    response = model.generate_content(contents)
    return response.text

def get_latest_files_from_gcs():
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs())
    audio_files = [blob for blob in blobs if blob.name.endswith(('.wav', '.mp3'))]
    text_files = [blob for blob in blobs if blob.name.endswith('.txt')]
    audio_files.sort(key=lambda x: x.updated, reverse=True)
    text_files.sort(key=lambda x: x.updated, reverse=True)
    latest_audio = audio_files[0].name if audio_files else None
    latest_text = text_files[0].name if text_files else None
    signed_url = None
    if latest_audio:
        blob = bucket.blob(latest_audio)
        signed_url = blob.generate_signed_url(version="v4", expiration=3600)
    transcription = ""
    if latest_text:
        blob = bucket.blob(latest_text)
        transcription = blob.download_as_text()
    return signed_url, transcription

@app.route('/')
def index():
    files = get_cloud_files(bucket_name)
    latest_audio, transcription = get_latest_files_from_gcs()
    return render_template('index.html', files=files, latest_audio=latest_audio, transcription=transcription)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data uploaded')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = f"audio_{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
        upload_blob(file, filename)
        gcs_uri = f"gs://{bucket_name}/{filename}"
        result = transcribe_gcs(gcs_uri)
        text_filename = f"{filename}.txt"
        bucket = storage_client.bucket(bucket_name)
        text_blob = bucket.blob(text_filename)
        text_blob.upload_from_string(result, content_type="text/plain")
        files = get_cloud_files(bucket_name)
        flash('File uploaded and processed successfully')
        return render_template('index.html', transcription=result, files=files)
    else:
        flash('Invalid file format')
        return redirect(request.url)

@app.route('/gcs/<filename>')
def serve_gcs_file(filename):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        signed_url = blob.generate_signed_url(version="v4", expiration=3600)
        return signed_url
    except Exception as e:
        return str(e), 500

@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_file('./script.js')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
