import json
import random
import os
from difflib import SequenceMatcher
import joblib

# ------------------------
# Paths
# ------------------------
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "models/chatbot_model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "models/vectorizer.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "models/label_encoder.pkl")
INTENTS_PATH = os.path.join(BASE_DIR, "data/intents.json")
SYNONYMS_PATH = os.path.join(BASE_DIR, "data/synonyms.json")

# ------------------------
# Load data and model
# ------------------------
with open(INTENTS_PATH, encoding="utf-8") as f:
    intents = json.load(f)["intents"]

with open(SYNONYMS_PATH, encoding="utf-8") as f:
    synonym_map = json.load(f)["synonyms"]

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)
encoder = joblib.load(ENCODER_PATH)

# ------------------------
# Utilities
# ------------------------
def normalize_text(text):
    text = text.lower().strip()
    for base, variants in synonym_map.items():
        for word in variants:
            text = text.replace(word, base)
    return text

def fuzzy_token_match(user_input, pattern, threshold=0.6):
    """Token-level fuzzy matching for short inputs"""
    user_tokens = user_input.split()
    pattern_tokens = pattern.split()
    matches = 0
    for ut in user_tokens:
        for pt in pattern_tokens:
            if SequenceMatcher(None, ut, pt).ratio() >= threshold:
                matches += 1
                break
    return matches / max(len(pattern_tokens), 1) >= 0.8

def rule_based_match(user_input):
    """Fallback using fuzzy matching on patterns"""
    user_input_norm = normalize_text(user_input)

    for intent in intents:
        for pattern in intent["patterns"]:
            if len(user_input_norm.split()) <= 3:
                # short input: use token-level fuzzy match
                if fuzzy_token_match(user_input_norm, pattern.lower()):
                    return intent["responses"][0]  # always pick first response
            else:
                # longer input: full string fuzzy match
                if SequenceMatcher(None, user_input_norm, pattern.lower()).ratio() >= 0.6:
                    return intent["responses"][0]  # always pick first response

    # Default fallback
    for intent in intents:
        if intent["tag"] == "default":
            return intent["responses"][0]
    return "Sorry, I didn’t understand that."

# ------------------------
# Chatbot response
# ------------------------
def chatbot_response(user_input):
    """ML prediction first, fallback to fuzzy rules"""
    user_input_norm = normalize_text(user_input)

    # ML prediction
    X_test = vectorizer.transform([user_input_norm])
    pred_proba = model.predict_proba(X_test)[0]
    pred_index = pred_proba.argmax()
    confidence = pred_proba[pred_index]
    tag = encoder.inverse_transform([pred_index])[0]

    if confidence > 0.35:  # lower threshold for more coverage
        for intent in intents:
            if intent["tag"] == tag:
                response = intent["responses"][0]  # always first
                break
    else:
        response = rule_based_match(user_input)

    # Split lines and strip spaces for proper display
    response_lines = [line.strip() for line in response.split("\n") if line.strip()]
    return "\n".join(response_lines)

# ------------------------
# Optional: terminal test
# ------------------------
if __name__ == "__main__":
    print("Chatbot ready! Type 'quit' to exit.")
    while True:
        msg = input("You: ")
        if msg.lower() in ["quit", "exit"]:
            break
        print("Bot:")
        # print line by line
        for line in chatbot_response(msg).split("\n"):
            print(line)