import os
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    if firebase_admin._apps:
        return

    cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found: {cred_path}")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)