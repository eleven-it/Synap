# main.py
from fastapi import FastAPI, Depends
from firebase_config import *
from auth import get_current_user

app = FastAPI()

@app.get("/protected")
def protected_route(user_data=Depends(get_current_user)):
    return {"message": f"Hola {user_data.get('email')}", "uid": user_data.get('uid')}
