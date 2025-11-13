"""
Schema for authentication
"""
from typing import Optional, Union

from firebase_admin import App
from pydantic import BaseModel


class FirebaseObject(BaseModel):
    """
    Firebase Object
    firebase: {
        identities: {
            [key: string]: any;
        };
        sign_in_provider: string;
        sign_in_second_factor?: string;
        second_factor_identifier?: string;
        tenant?: string;
        [key: string]: any;
    }
    """
    identities: dict
    sign_in_provider: str
    sign_in_second_factor: Optional[str] = None
    second_factor_identifier: Optional[str] = None
    tenant: Optional[str] = None
    additional_properties: Optional[dict] = None


class FirebaseTokenPayload(BaseModel):
    """
    Firebase Token Payload
    example: {
        "name": "Temp",
        "picture": "",
        "email": "user@example.com",
        "email_verified": false,
        "auth_time": 1722458533,
        "user_id": "Un5ly0tx5nP6H79dVkq87kYwrHD0",
        "firebase": {
            "identities": {
                "email": [
                    "user@example.com"
                ]
            },
            "sign_in_provider": "password"
        },
        "iat": 1722458533,
        "exp": 1722462133,
        "aud": "thehope-777",
        "iss": "https://securetoken.google.com/thehope-777",
        "sub": "Un5ly0tx5nP6H79dVkq87kYwrHD0"
    }
    """
    name: Optional[str] = None
    aud: str
    auth_time: int
    email_verified: Optional[bool] = None
    email: Optional[str] = None
    exp: int
    firebase: FirebaseObject
    iat: int
    iss: str
    phone_number: Optional[str] = None
    picture: Optional[str] = None
    sub: str
    user_id: str
