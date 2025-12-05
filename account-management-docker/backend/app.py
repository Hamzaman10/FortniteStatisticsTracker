from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json
import requests
import os
import uuid
from datetime import datetime

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")


# ---------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------

app = FastAPI()


# ---------------------------------------------------
# STATIC + FRONTEND ROUTES
# ---------------------------------------------------

FRONTEND_DIR = "../frontend"

# serve JS/CSS as /static/*.js
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)

@app.get("/")
def serve_home():
    return FileResponse(f"{FRONTEND_DIR}/index.html")

@app.get("/payment.html")
def serve_payment():
    return FileResponse(f"{FRONTEND_DIR}/payment.html")


# ---------------------------------------------------
# CORS (CLOUD9 SAFE)
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# COGNITO CONFIG FOR PROFILE SYSTEM
# ---------------------------------------------------

REGION = os.getenv("REGION", "us-east-1")
USERPOOL_ID = os.getenv("USERPOOL_ID")
APP_CLIENT_ID = os.getenv("CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"


# ---------------------------------------------------
# LOCAL PROFILE DB (REAL ACCOUNT SYSTEM)
# ---------------------------------------------------

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


# JWKS fetch
jwks = requests.get(JWKS_URL).json()["keys"]


def verify_token(token: str):
    """
    Cognito JWT validation.
    DO NOT MODIFY.
    """
    from jose import jwt, jwk
    from jose.utils import base64url_decode

    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]

    key = next((k for k in jwks if k["kid"] == kid), None)
    if not key:
        raise HTTPException(401, "Invalid token key")

    public_key = jwk.construct(key)
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())

    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(401, "Signature mismatch")

    decoded = jwt.get_unverified_claims(token)

    if decoded.get("aud") != APP_CLIENT_ID:
        raise HTTPException(401, "Wrong client ID")

    return decoded


# ---------------------------------------------------
# PROFILE ENDPOINTS (REAL)
# ---------------------------------------------------

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

    body = await request.json()

    db = load_db()
    db[user_id] = {
        "user_id": user_id,
        "user_name": body.get("user_name"),
        "gameid": body.get("gameid"),
    }
    save_db(db)

    return {"status": "updated", "user": db[user_id]}


# ---------------------------------------------------
# PAYMENT STORAGE (LOCAL JSON FILE)
# ---------------------------------------------------

HARDCODED_USER_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

PAYMENTS_FILE = "payments_db.json"
if not os.path.exists(PAYMENTS_FILE):
    with open(PAYMENTS_FILE, "w") as f:
        json.dump({}, f)

def load_payments():
    with open(PAYMENTS_FILE, "r") as f:
        return json.load(f)

def save_payments(data):
    with open(PAYMENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class CardInput(BaseModel):
    name_on_card: str
    card_number: str
    exp_month: int
    exp_year: int
    billing_zip: str
    billing_country: str


# ---------------------------------------------------
# PAYMENT ENDPOINTS
# ---------------------------------------------------

@app.get("/cards")
def get_cards():
    """
    Returns stored cards for the demo user.
    """
    db = load_payments()
    return db.get(HARDCODED_USER_ID, [])


@app.post("/card")
async def save_card(request: Request):
    """
    Stores a card for the demo user.
    """
    body = await request.json()

    db = load_payments()
    cards = db.get(HARDCODED_USER_ID, [])

    # optional business rule: 1 card max
    if len(cards) >= 1:
        raise HTTPException(400, "Limit reached: only 1 card allowed.")

    token = f"pay_{uuid.uuid4().hex[:10]}"
    last4 = body["card_number"][-4:]

    new_card = {
        "user_id": HARDCODED_USER_ID,
        "card_token": token,
        "last4": last4,
        "masked": f"**** **** **** {last4}",
        "exp_month": body["exp_month"],
        "exp_year": body["exp_year"],
        "name_on_card": body["name_on_card"],
        "billing_zip": body["billing_zip"],
        "billing_country": body["billing_country"],
        "created_at": datetime.utcnow().isoformat(),
    }

    cards.append(new_card)
    db[HARDCODED_USER_ID] = cards
    save_payments(db)

    return {"status": "saved", "token": token}


@app.delete("/card/{card_token}")
def delete_card(card_token: str):
    """
    Deletes a stored card.
    """
    db = load_payments()
    cards = db.get(HARDCODED_USER_ID, [])

    cards = [c for c in cards if c["card_token"] != card_token]

    db[HARDCODED_USER_ID] = cards
    save_payments(db)

    return {"status": "deleted"}
