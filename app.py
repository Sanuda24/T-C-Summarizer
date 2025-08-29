from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from summarizer import extract_text_from_file, generate_summary, simplify_jargon
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from datetime import datetime
from datetime import timedelta
from bson import ObjectId
import os
import logging
import re
import torch
import time, concurrent.futures
import numpy as np
import requests
import io, csv
from rouge_score import rouge_scorer
import textstat

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config.update(
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=32 * 1024 * 1024,  
    MONGO_URI="mongodb+srv://Users:1234@cluster0.smh0yjv.mongodb.net/TCproject?retryWrites=true&w=majority&appName=Cluster0",   
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

@app.route('/home')
def home():
    return render_template('homepage.html', user=session.get('user'), guest=session.get('guest'))


@app.route('/')
def root():
    if 'user' not in session and 'guest' not in session:
        return redirect(url_for('home'))
    return render_template('index.html', user=session.get('user'), guest=session.get('guest'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user' in session or 'guest' in session or 'admin' in session:
            if 'admin' in session:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('root'))
        return render_template('login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    
    admin = mongo.db.admins.find_one({"email": email})
    if admin and bcrypt.check_password_hash(admin['password'], password):
        session.clear()
        session.permanent = True
        session['admin'] = email
        return redirect(url_for('admin_dashboard'))

    
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
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        except PermissionError:
            logger.warning(f"Could not delete file {filepath}, will try again later.")


@app.route('/save_summary', methods=['POST'])
def save_summary():
    if 'user' not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        data = request.get_json()
        summary_data = {
            "user_email": session['user'],
            "title": data.get('title', 'Untitled Summary'),
            "filename": data.get('filename', ''),
            "content": data.get('content', ''),
            "summary": data.get('summary', []),
            "jargon": data.get('jargon', {}),
            "created_at": datetime.utcnow()
        }
        
        result = mongo.db.summaries.insert_one(summary_data)
        return jsonify({"success": True, "id": str(result.inserted_id)})
    except Exception as e:
        logger.error(f"Failed to save summary: {str(e)}")
        return jsonify({"error": "Failed to save summary"}), 500
    
@app.route('/delete_summary/<summary_id>', methods=['DELETE'])
def delete_summary(summary_id):
    if 'user' not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        result = mongo.db.summaries.delete_one({
            "_id": ObjectId(summary_id),
            "user_email": session['user']
        })
        
        if result.deleted_count == 0:
            return jsonify({"error": "Summary not found"}), 404
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Failed to delete summary: {str(e)}")
        return jsonify({"error": "Failed to delete summary"}), 500

@app.route('/get_summaries', methods=['GET'])
def get_summaries():
    if 'user' not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        summaries = list(mongo.db.summaries.find(
            {"user_email": session['user']},
            {"title": 1, "filename": 1, "created_at": 1}
        ).sort("created_at", -1))
        
        for summary in summaries:
            summary['_id'] = str(summary['_id'])
            summary['created_at'] = summary['created_at'].strftime("%Y-%m-%d %H:%M")
        
        return jsonify(summaries)
    except Exception as e:
        logger.error(f"Failed to fetch summaries: {str(e)}")
        return jsonify({"error": "Failed to fetch summaries"}), 500

@app.route('/get_summary/<summary_id>', methods=['GET'])
def get_summary(summary_id):
    if 'user' not in session:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        summary = mongo.db.summaries.find_one({
            "_id": ObjectId(summary_id),
            "user_email": session['user']
        })
        
        if not summary:
            return jsonify({"error": "Summary not found"}), 404
        
        summary['_id'] = str(summary['_id'])
        summary['created_at'] = summary['created_at'].strftime("%Y-%m-%d %H:%M")
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Failed to fetch summary: {str(e)}")
        return jsonify({"error": "Failed to fetch summary"}), 500


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', admin=session['admin'])

@app.route('/admin/api/loadtests')
def api_loadtests():
    if 'admin' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    tests = list(mongo.db.loadtests.find().sort("created_at", -1))
    for t in tests:
        t['_id'] = str(t['_id'])
        t['created_at'] = t['created_at'].strftime("%Y-%m-%d %H:%M")
    return jsonify(tests)

@app.route('/admin/api/experiments')
def api_experiments():
    if 'admin' not in session:
        return jsonify({"error": "Unauthorized"}), 403
    experiments = list(mongo.db.experiments.find().sort("created_at", -1))
    for e in experiments:
        e['_id'] = str(e['_id'])
        e['created_at'] = e['created_at'].strftime("%Y-%m-%d %H:%M")
    return jsonify(experiments)

@app.route('/admin/run-loadtest', methods=['POST'])
def run_loadtest():
    if 'admin' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    concurrency_levels = [1, 5, 10, 20]
    results = []
    for c in concurrency_levels:
        durations = []
        errors = 0
        start_time = time.time()

        def simulate_request(_):
            try:
                t0 = time.time()
                
                r = requests.post("http://127.0.0.1:5000/summarize",
                                  files={"file": ("test.txt", b"Test load")})
                dt = time.time() - t0
                if r.status_code != 200:
                    raise Exception("Bad response")
                return dt
            except:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as executor:
            futures = [executor.submit(simulate_request, i) for i in range(20)]
            for f in concurrent.futures.as_completed(futures):
                dt = f.result()
                if dt is None:
                    errors += 1
                else:
                    durations.append(dt)

        total_time = time.time() - start_time
        p95 = float(np.percentile(durations, 95)) if durations else None

        result = {
            "concurrency": c,
            "rps": len(durations) / total_time if total_time > 0 else 0,
            "p95_ms": p95 * 1000 if p95 else None,
            "error_rate": errors / 20,
            "created_at": datetime.utcnow()
        }
        mongo.db.loadtests.insert_one(result)
        results.append(result)

    return jsonify(results)

@app.route('/admin/run-eval', methods=['POST'])
def run_eval():
    if 'admin' not in session:
        return jsonify({"error": "Unauthorized"}), 403



    files = [f for f in os.listdir("eval_data") if f.endswith(".txt")]
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

    results = []
    for f in files:
        path = os.path.join("eval_data", f)
        with open(path, "r", encoding="utf-8") as fp:
            doc = fp.read()

        # Ensure doc is a string
        if isinstance(doc, list):
            doc = " ".join(doc)

        t0 = time.time()
        r = requests.post("http://127.0.0.1:5000/summarize",
                          files={"file": (f, doc.encode("utf-8"))})
        latency = time.time() - t0

        summary = ""
        if r.status_code == 200:
            summary = r.json().get("summary", "")
        
        
        if isinstance(summary, list):
            summary = " ".join(summary)

        rougeL = scorer.score(doc, summary)["rougeL"].fmeasure if summary else 0
        fk_grade = textstat.flesch_kincaid_grade(summary) if summary else None

        record = {
            "file": f,
            "rougeL": rougeL,
            "fk_grade": fk_grade,
            "latency_s": latency,
            "created_at": datetime.utcnow()
        }
        mongo.db.experiments.insert_one(record)
        results.append(record)
        

    return jsonify(results)



@app.route('/admin/export/experiments.csv')
def export_experiments():
    if 'admin' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    docs = list(mongo.db.experiments.find().sort("created_at", -1))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["file", "rougeL", "fk_grade", "latency_s", "created_at"])
    for d in docs:
        cw.writerow([d.get("file"), d.get("rougeL"), d.get("fk_grade"), d.get("latency_s"),
                     d.get("created_at").strftime("%Y-%m-%d %H:%M")])
    output = io.BytesIO()
    output.write(si.getvalue().encode())
    output.seek(0)
    return send_file(output, mimetype="text/csv", download_name="experiments.csv", as_attachment=True)


if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
