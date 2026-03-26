import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import joblib
import json

# Synthetic Dataset for Symptoms to Diseases
data = [
    {"disease": "Common Cold", "symptoms": ["cough", "runny_nose", "sore_throat", "fever", "fatigue"]},
    {"disease": "Flu", "symptoms": ["fever", "chills", "muscle_aches", "cough", "congestion", "runny_nose", "headache", "fatigue"]},
    {"disease": "COVID-19", "symptoms": ["fever", "cough", "loss_of_taste", "loss_of_smell", "fatigue", "shortness_of_breath", "body_aches"]},
    {"disease": "Allergies", "symptoms": ["sneezing", "runny_nose", "itchy_eyes", "watery_eyes"]},
    {"disease": "Migraine", "symptoms": ["headache", "nausea", "sensitivity_to_light", "sensitivity_to_sound"]},
    {"disease": "Gastroenteritis", "symptoms": ["nausea", "vomiting", "diarrhea", "stomach_cramps", "fever"]},
    {"disease": "Asthma", "symptoms": ["shortness_of_breath", "wheezing", "chest_tightness", "cough"]},
    {"disease": "Pneumonia", "symptoms": ["cough", "fever", "chills", "difficulty_breathing"]},
    {"disease": "Malaria", "symptoms": ["fever", "chills", "sweats", "headache", "nausea", "muscle_aches"]},
    {"disease": "Dengue", "symptoms": ["high_fever", "severe_headache", "pain_behind_eyes", "joint_pain", "muscle_pain", "rash", "mild_bleeding"]},
    {"disease": "Typhoid", "symptoms": ["prolonged_fever", "fatigue", "headache", "nausea", "abdominal_pain", "constipation", "diarrhea"]},
    {"disease": "Sinusitis", "symptoms": ["facial_pain", "headache", "runny_nose", "nasal_congestion", "sore_throat"]},
    {"disease": "Tuberculosis", "symptoms": ["persistent_cough", "chest_pain", "coughing_blood", "fatigue", "fever", "night_sweats"]},
    {"disease": "Anemia", "symptoms": ["fatigue", "weakness", "pale_skin", "chest_pain", "cold_hands", "cold_feet", "shortness_of_breath"]},
    {"disease": "Diabetes", "symptoms": ["increased_thirst", "frequent_urination", "extreme_hunger", "unexplained_weight_loss", "fatigue", "blurred_vision"]}
]

df = pd.DataFrame(data)

mlb = MultiLabelBinarizer()
X = mlb.fit_transform(df['symptoms'])
y = df['disease']

clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# Save the model and the binarizer
joblib.dump(clf, 'symptom_model.pkl')
joblib.dump(mlb, 'symptom_binarizer.pkl')

print("Model trained and saved successfully.")
