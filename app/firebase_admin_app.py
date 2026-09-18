import os

import firebase_admin

from app.settings import settings


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    if not settings.firebase_project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID is not set")
    if settings.firebase_auth_emulator_host:
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = settings.firebase_auth_emulator_host
    if settings.firestore_emulator_host:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
    firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
