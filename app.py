from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from summarizer import extract_text_from_file, generate_summary, simplify_jargon
import os
import logging
import torch

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=32 * 1024 * 1024  # 32MB limit
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'bmp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'file' not in request.files:
        logger.error("No file in request")
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        logger.error("Invalid file type")
        return jsonify({"error": "File type not supported"}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logger.info(f"Processing: {filename}")

        text = extract_text_from_file(filepath)
        logger.info(f"Text extracted ({len(text)} chars)")

        summary = generate_summary(text)
        simplified = simplify_jargon(text)
        
        return jsonify({
            'summary': summary,
            'jargon': simplified,
            'device': 'gpu' if torch.cuda.is_available() else 'cpu',
            'text': text[:500] + "..." if len(text) > 500 else text  # Return first 500 chars for preview
        })

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)