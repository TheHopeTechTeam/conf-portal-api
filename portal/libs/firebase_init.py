"""
Firebase Admin SDK initialization (shared by API and ARQ worker).
"""

import firebase_admin
from firebase_admin import credentials

from portal.config import settings
from portal.libs.logger import logger


def init_firebase() -> None:
    """
    Initialize Firebase app if not already initialized.
    """
    if firebase_admin._apps:
        return
    credential = credentials.Certificate(settings.GOOGLE_FIREBASE_CERTIFICATE)
    firebase_admin.initialize_app(
        credential=credential,
    )


def init_firebase_safe() -> None:
    """
    Same as init_firebase but logs errors instead of raising to callers.
    """
    try:
        init_firebase()
    except Exception as exc:
        logger.error("Error initializing firebase: %s", exc, exc_info=True)
