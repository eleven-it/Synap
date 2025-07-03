# auth.py
from fastapi import Depends, HTTPException, status, Request
from django_project.firebase_config import get_firebase_app
import firebase_admin
from firebase_admin import auth

def get_current_user(request: Request):
    authorization: str = request.headers.get("Authorization")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente o inválido")

    id_token = authorization.split(" ")[1]

    try:
        get_firebase_app()
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token  # contiene 'uid', 'email', etc.
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
