import os
import re
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash  # pyre-ignore
from flask_sqlalchemy import SQLAlchemy  # pyre-ignore
import groq  # pyre-ignore
from dotenv import load_dotenv  # pyre-ignore
from werkzeug.security import generate_password_hash, check_password_hash  # pyre-ignore
from functools import wraps

import joblib  # pyre-ignore
import pandas as pd  # pyre-ignore
import numpy as np  # pyre-ignore

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'healthpilot_super_secret_key_123')
# Configure Database
# On Vercel, the filesystem is read-only except for /tmp. 
# Render or local environments can use the instance folder.
if os.environ.get('VERCEL'):
    db_path = '/tmp/healthcare.db'
else:
    # Use absolute path for local/Render to avoid issues
    basedir = os.path.abspath(os.path.dirname(__name__))
    db_path = os.path.join(basedir, 'instance', 'healthcare.db')
    os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize Groq client
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is not set.")
client = groq.Groq(api_key=api_key)

# Load machine learning model
ml_model = None
mlb = None
try:
    ml_model = joblib.load('symptom_model.pkl')
    mlb = joblib.load('symptom_binarizer.pkl')
except Exception as e:
    print("Warning: ML model not loaded.", e)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    prescriptions = db.relationship('Prescription', backref='user', lazy=True)

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    image_base64 = db.Column(db.Text, nullable=True)
    prescription_text = db.Column(db.Text, nullable=True)
    extracted_data = db.Column(db.Text, nullable=False) # JSON representation of medicines

with app.app_context():
    db.create_all()

SYSTEM_PROMPT = """You are an AI Prescription Interpretation System (APIS) — a medical assistant specialized in reading and explaining medical prescriptions.

When given a prescription image or text, you MUST respond ONLY with a valid JSON array. No markdown, no explanation, no preamble.

Each element in the array represents one medicine found in the prescription.

JSON format:
[
  {
    "medicine_name": "Full medicine name",
    "dosage": "Exact dosage (e.g., 500 mg)",
    "frequency": "How often to take (e.g., Twice daily)",
    "duration": "How long to take (e.g., 5 days)"
  }
]

Rules:
- Always return a JSON array, even for a single medicine.
- If the prescription is unclear or unreadable, return: [{"error": "Prescription could not be read clearly. Please upload a clearer image."}]
- Expand all abbreviations: BD=Twice daily, TDS=Three times daily, OD=Once daily, Tab=Tablet, Cap=Capsule, etc.
- Be thorough and accurate. Patient safety depends on this.
"""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password")
    
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")
        
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash("Username already exists.")
        elif email_exists:
            flash("Email already registered.")
        else:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_pw)  # pyre-ignore
            db.session.add(new_user)
            db.session.commit()
            
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            return redirect(url_for('index'))
            
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    return render_template("index.html", username=session.get('username'))

@app.route("/api/scan", methods=["POST"])
def scan_prescription():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    prescription_text = data.get("text", "").strip()
    image_data = data.get("image", None)
    image_type = data.get("image_type", "image/jpeg")

    if not prescription_text and not image_data:
        return jsonify({"error": "Please provide prescription text or an image."}), 400

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if image_data:
        if "," in image_data:
            image_data = image_data.split(",")[1]
        messages.append({  # pyre-ignore
            "role": "user",
            "content": [
                {"type": "text", "text": "Please analyze this prescription image and extract all medicine details."},
                {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{image_data}"}}
            ]
        })
    else:
        messages.append({
            "role": "user",
            "content": f"Please analyze this prescription and extract all medicine details:\n\n{prescription_text}"
        })

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            max_tokens=2048,
        )
        raw_text = response.choices[0].message.content.strip()
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        
        parsed = json.loads(raw_text)
        
        # Save to database
        new_prescription = Prescription(user_id=session.get('user_id'), image_base64=data.get("image", None), prescription_text=prescription_text, extracted_data=json.dumps(parsed))  # pyre-ignore
        db.session.add(new_prescription)
        db.session.commit()

        return jsonify({"medicines": parsed, "id": new_prescription.id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to interpret prescription: {str(e)}"}), 500

@app.route("/api/prescriptions", methods=["GET"])
@login_required
def get_prescriptions():
    user_id = session.get('user_id')
    prescriptions = Prescription.query.filter_by(user_id=user_id).order_by(Prescription.date.desc()).all()
    result = []
    for p in prescriptions:
        result.append({
            "id": p.id,
            "date": p.date.strftime("%Y-%m-%d %H:%M:%S"),
            "extracted_data": json.loads(p.extracted_data)
        })
    return jsonify({"prescriptions": result})

@app.route("/api/medicine-info", methods=["POST"])
def medicine_info():
    data = request.get_json()
    medicine = data.get("medicine")
    
    prompt = f"""Provide detailed information for the medicine: '{medicine}'. 
Respond ONLY as a valid JSON object with these exact keys:
"medicine_name", "chemical_formula", "purpose", "dosage_guidelines", "side_effects" (as a list of strings)."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return jsonify(json.loads(content))
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route("/api/alternative", methods=["POST"])
def alternative_medicine():
    data = request.get_json()
    medicine = data.get("medicine")
    
    prompt = f"""Suggest 3 common alternative medicines for '{medicine}' with similar therapeutic functions. 
Respond ONLY with a valid JSON array of strings containing the names of the alternatives."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        return jsonify({"alternatives": json.loads(content)})
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route("/api/interactions", methods=["POST"])
def check_interactions():
    data = request.get_json()
    medicines = data.get("medicines", [])
    
    if len(medicines) < 2:
        return jsonify({"interactions": "At least 2 medicines are needed to check interactions."})
        
    med_str = ", ".join(medicines)
    prompt = f"""Check for interactions between these medicines: {med_str}. 
Provide a short, simple explanation of any harmful interactions. If none are known, say so clearly."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                 {"role": "system", "content": "You are a helpful healthcare assistant. Provide simple and accurate information."},
                 {"role": "user", "content": prompt}
            ]
        )
        return jsonify({"interactions": response.choices[0].message.content})
    except Exception as e:
         return jsonify({"error": str(e)}), 500

@app.route("/api/predict-disease", methods=["POST"])
def predict_disease():
    data = request.get_json()
    symptoms = data.get("symptoms", [])
    
    prediction = "Unable to predict."
    
    if ml_model and mlb and symptoms:
        try:
            # We want to match whatever symptoms the user typed to our known symptoms
            valid_symptoms = list(mlb.classes_)
            
            # Very basic string match for mock
            matched = []
            for s in symptoms:
                s_lower = s.lower().replace(" ", "_")
                for vs in valid_symptoms:
                    if vs in s_lower or s_lower in vs:
                        matched.append(vs)
            
            matched = list(set(matched))
            if matched:
                X_input = mlb.transform([matched])
                pred = ml_model.predict(X_input)
                prediction = pred[0]
            else:
                 prediction = "Symptoms unknown or not enough data."
        except Exception as e:
            pass

    # Ask LLM for brief recommendations based on prediction
    recommendations = ""
    if prediction not in ["Unable to predict.", "Symptoms unknown or not enough data."]:
        prompt = f"The patient might have '{prediction}'. Suggest 2-3 common over-the-counter medicines or home remedies. Provide a brief paragraph."
        try:
             response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
             )
             recommendations = response.choices[0].message.content
        except:
             pass

    return jsonify({"disease": prediction, "recommendations": recommendations})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message")
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful Healthcare Copilot Assistant. You help patients understand their prescriptions, symptoms, and medications. Be empathetic, short, and clear. Always advise consulting a doctor."},
                {"role": "user", "content": message}
            ]
        )
        return jsonify({"reply": response.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
