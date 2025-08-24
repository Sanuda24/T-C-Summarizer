from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
from summarizer import extract_text_from_file, generate_summary, simplify_jargon
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from datetime import timedelta
import os
import logging
import re
import torch

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=32 * 1024 * 1024,  
    MONGO_URI="mongodb://localhost:27017/TCproject",   
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
app.secret_key = "123"  

mongo = PyMongo(app)
bcrypt = Bcrypt(app)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'bmp'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#password validation
def is_valid_password(pw: str) -> bool:
    return (
        isinstance(pw, str)
        and len(pw) >= 6
        and re.search(r"[A-Za-z]", pw) is not None
        and re.search(r"\d", pw) is not None
    )


@app.route('/')
def root():
    if 'user' not in session and 'guest' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session.get('user'), guest=session.get('guest'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user' in session or 'guest' in session:
            return redirect(url_for('root'))
        return render_template('login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    user = mongo.db.users.find_one({"email": email})
    if user and bcrypt.check_password_hash(user['password'], password):
        session.clear()
        session.permanent = True
        session['user'] = email
        return redirect(url_for('root'))
    return render_template('login.html', error="Invalid email or password")

@app.route('/guest')
def guest():
    session.clear()
    session.permanent = True
    session['guest'] = True
    return redirect(url_for('root'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    if not is_valid_password(password):
        return render_template('signup.html',
                               error="Password must be at least 6 characters and include letters & numbers.")

    if mongo.db.users.find_one({"email": email}):
        return render_template('signup.html', error="Email already exists")

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    mongo.db.users.insert_one({"email": email, "password": hashed_pw})
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    next_page = request.args.get('next')
    session.clear()
    if next_page == 'login':
        return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('settings.html', user=session['user'])

    action = request.form.get('action')

    if action == 'change_email':
        new_email = request.form.get('new_email', '').strip().lower()
        if not new_email:
            return render_template('settings.html', user=session['user'], error="Email cannot be empty.")
        if mongo.db.users.find_one({"email": new_email}):
            return render_template('settings.html', user=session['user'], error="Email already in use.")
        mongo.db.users.update_one({"email": session['user']}, {"$set": {"email": new_email}})
        session['user'] = new_email
        return render_template('settings.html', user=session['user'], success="Email updated.")

    if action == 'change_password':
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        if not is_valid_password(new_pw):
            return render_template('settings.html', user=session['user'],
                                   error="New password must be at least 6 characters and include letters & numbers.")
        user = mongo.db.users.find_one({"email": session['user']})
        if not user or not bcrypt.check_password_hash(user['password'], old_pw):
            return render_template('settings.html', user=session['user'], error="Incorrect old password.")
        new_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        mongo.db.users.update_one({"email": session['user']}, {"$set": {"password": new_hash}})
        return render_template('settings.html', user=session['user'], success="Password changed.")

    return render_template('settings.html', user=session['user'])


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

    filepath = None
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
        })

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
