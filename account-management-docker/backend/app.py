from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, jwk
from jose.utils import base64url_decode
import requests
import os
import time
import json


REGION = os.getenv("REGION", "us-east-1")
USERPOOL_ID = os.getenv("USERPOOL_ID")
APP_CLIENT_ID = os.getenv("CLIENT_ID")
FORTNITE_LAMBDA_URL = os.getenv("FORTNITE_LAMBDA_URL")

if not USERPOOL_ID or not APP_CLIENT_ID:
    raise RuntimeError("Missing USERPOOL_ID or CLIENT_ID")
if not FORTNITE_LAMBDA_URL:
    raise RuntimeError("Missing FORTNITE_LAMBDA_URL")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_jwks():
    r = requests.get(JWKS_URL, timeout=10)
    r.raise_for_status()
    return r.json()["keys"]


jwks = load_jwks()


def verify_token(token: str):
    global jwks

    try:
        headers = jwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(401, "Malformed token")

    kid = headers.get("kid")
    if not kid:
        raise HTTPException(401, "Malformed token")

    key = next((k for k in jwks if k.get("kid") == kid), None)
    if not key:
        jwks = load_jwks()
        key = next((k for k in jwks if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(401, "Invalid token key")

    public_key = jwk.construct(key)

    try:
        message, encoded_sig = token.rsplit(".", 1)
        decoded_sig = base64url_decode(encoded_sig.encode())
    except Exception:
        raise HTTPException(401, "Malformed token")

    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(401, "Bad signature")

    claims = jwt.get_unverified_claims(token)

    exp = claims.get("exp")
    if exp is not None and int(time.time()) >= int(exp):
        raise HTTPException(401, "Token expired")

    if claims.get("aud") != APP_CLIENT_ID:
        raise HTTPException(401, "Invalid client ID")

    return claims


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(401, "Missing token")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Invalid Authorization header")
    return auth.replace("Bearer ", "", 1).strip()


def call_fortnite_lambda(payload: dict):
    r = requests.post(FORTNITE_LAMBDA_URL, json=payload, timeout=15)
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    data = r.json()

    if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
        try:
            return json.loads(data["body"])
        except Exception:
            return data["body"]

    return data


@app.get("/itemshop")
def itemshop():
    return call_fortnite_lambda({"mode": "itemshop"})


@app.get("/stats")
def stats(request: Request, username: str, platform: str = "epic"):
    token = get_bearer_token(request)
    verify_token(token)
    return call_fortnite_lambda({"mode": "stats", "username": username, "platform": platform})
