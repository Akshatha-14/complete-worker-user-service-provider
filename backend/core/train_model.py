import json
import os
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.multiclass import unique_labels

# Paths
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "models/chatbot_model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "models/vectorizer.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "models/label_encoder.pkl")

# Load intents
with open(os.path.join(BASE_DIR, "data", "intents.json"), encoding="utf-8") as f:
    intents = json.load(f)

# Prepare data
texts = []
labels = []
for intent in intents["intents"]:
    for pattern in intent["patterns"]:
        texts.append(pattern.lower())
        labels.append(intent["tag"])

# Encode labels
encoder = LabelEncoder()
y = encoder.fit_transform(labels)

# Vectorize text
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = MultinomialNB()
model.fit(X_train, y_train)

# Evaluate accuracy
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Model Accuracy: {acc * 100:.2f}%")
labels = np.arange(len(encoder.classes_))  # All class indices
print("\nClassification Report:\n", classification_report(
    y_test, y_pred, labels=labels, target_names=encoder.classes_, zero_division=0
))
# Save model, vectorizer, and encoder
joblib.dump(model, MODEL_PATH)
joblib.dump(vectorizer, VECTORIZER_PATH)
joblib.dump(encoder, ENCODER_PATH)

print(f"\nModel saved to {MODEL_PATH}")