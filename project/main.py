from datetime import datetime
from flask import Flask, flash, render_template, request, redirect, url_for, send_file, send_from_directory
from google.cloud import texttospeech
from google.cloud import speech
import os


tts_client = texttospeech.TextToSpeechClient()
speech_client = speech.SpeechClient()

app = Flask(__name__)
app.secret_key = 'sreeja'

UPLOAD_FOLDER = 'speechtotext'
AUDIO_FOLDER = 'texttospeech'
ALLOWED_EXTENSIONS = {'wav', 'txt', 'mp3'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files(loc):
    files = []
    for filename in os.listdir(loc):
        if allowed_file(filename):
            files.append(filename)
    files.sort(reverse=True)
    return files

@app.route('/tts/<filename>')
def get_audio(filename):
    return send_from_directory(app.config['AUDIO_FOLDER'], filename, mimetype='audio/mpeg')

@app.route('/')
def index():
    files = get_files(UPLOAD_FOLDER)
    audios = get_files(AUDIO_FOLDER)
    return render_template('index.html', files=files, audios=audios)

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
        filename = "audio_" + datetime.now().strftime("%Y%m%d-%I%M%S") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash('File uploaded successfully')

        def transcribe_file(audio_file: str) -> str:
            with open(audio_file, "rb") as f:
                audio_content = f.read()

            audio = speech.RecognitionAudio(content=audio_content)

            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                sample_rate_hertz=24000,
                language_code="en-US",
            )

            response = speech_client.recognize(config=config, audio=audio)

            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                print(f"Transcript: {transcript}")
                return transcript
            else:
                return "No transcription available"

        result = transcribe_file(file_path)
        flash(result)

        text_file = os.path.splitext(file_path)[0] + ".txt"
        with open(text_file, "w") as file:
            file.write(result)

    return render_template('index.html', transcription=result)

@app.route('/speechtotext/<filename>')
def view_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    output_filename = "output_" + datetime.now().strftime("%Y%m%d-%I%M%S") + ".mp3"
    output_path = os.path.join(AUDIO_FOLDER, output_filename)

    with open(output_path, "wb") as out:
        out.write(response.audio_content)
        flash(f'Audio content written to file "{output_filename}"')

    return redirect('/')

@app.route('/script.js', methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/speechtotext/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
