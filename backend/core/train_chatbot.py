import json
import os
import random
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the full path to intents.json inside the same folder
intents_path = os.path.join(BASE_DIR,"data", "intents.json")

# Load the JSON file
with open(intents_path, encoding="utf-8") as f:
    data = json.load(f)

# Prepare training data
X = []
y = []
for intent in data["intents"]:
    for pattern in intent["patterns"]:
        X.append(pattern)
        y.append(intent["tag"])

# Vectorize text
vectorizer = TfidfVectorizer()
X_vect = vectorizer.fit_transform(X)

# Train model
model = LogisticRegression()
model.fit(X_vect, y)

# Save model & vectorizer
models_dir = os.path.join(BASE_DIR, "models")
os.makedirs(models_dir, exist_ok=True)

joblib.dump(model, os.path.join(models_dir, "chatbot_model.pkl"))
joblib.dump(vectorizer, os.path.join(models_dir, "vectorizer.pkl"))

print(f"✅ Chatbot training complete! Model saved in {models_dir}")