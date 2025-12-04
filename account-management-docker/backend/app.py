from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from jose import jwt, jwk
from jose.utils import base64url_decode
import json
import requests
import os

REGION = os.getenv("REGION", "us-east-1")
USERPOOL_ID = os.getenv("USERPOOL_ID")
APP_CLIENT_ID = os.getenv("CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"

DB_FILE = "db.json"

if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({}, f)

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

app = FastAPI()

jwks = requests.get(JWKS_URL).json()["keys"]

def verify_token(token):
    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]
    key = next((k for k in jwks if k["kid"] == kid), None)
    if not key:
        raise HTTPException(401, "Invalid token key")

    public_key = jwk.construct(key)
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())

    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(401, "Bad signature")

    decoded = jwt.get_unverified_claims(token)

    if decoded.get("aud") != APP_CLIENT_ID:
        raise HTTPException(401, "Invalid client ID")

    return decoded

@app.get("/profile")
def get_profile(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(401, "Missing token")

    token = token.replace("Bearer ", "")
    claims = verify_token(token)
    user_id = claims["sub"]

    db = load_db()
    return db.get(user_id, {"user_id": user_id, "user_name": None, "gameid": None})

@app.put("/profile")
async def put_profile(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(401, "Missing token")

    token = token.replace("Bearer ", "")
    claims = verify_token(token)
    user_id = claims["sub"]

    body = await request.json()   # FIXED LINE

    db = load_db()
    db[user_id] = {
        "user_id": user_id,
        "user_name": body.get("user_name"),
        "gameid": body.get("gameid")
    }
    save_db(db)

    return {"status": "updated", "user": db[user_id]}
