import os
import firebase_admin
from firebase_admin import credentials

_initialized = False


def get_firebase_app():
    global _initialized
    if not _initialized:
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _initialized = True
    return firebase_admin.get_app() if _initialized else None