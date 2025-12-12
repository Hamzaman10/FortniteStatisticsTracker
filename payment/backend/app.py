import boto3
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

import os
import requests
from jose import jwt, jwk
from jose.utils import base64url_decode

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("PaymentMethods")


REGION = os.getenv("REGION", "us-east-1")
USERPOOL_ID = os.getenv("USERPOOL_ID")
APP_CLIENT_ID = os.getenv("CLIENT_ID")

if not USERPOOL_ID or not APP_CLIENT_ID:
    raise RuntimeError("Missing USERPOOL_ID or CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"
jwks = requests.get(JWKS_URL).json()["keys"]


def verify_token(token: str):

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


def get_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(401, "Missing token")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Invalid Authorization header")
    return auth.replace("Bearer ", "", 1).strip()


def validate_expiry(exp_month: int, exp_year: int):
    if exp_month < 1 or exp_month > 12:
        raise HTTPException(status_code=400, detail="Invalid expiration month")

    now = datetime.utcnow()
    if exp_year < now.year or (exp_year == now.year and exp_month < now.month):
        raise HTTPException(status_code=400, detail="Card is expired")


class CardInput(BaseModel):
    name_on_card: str
    card_number: str
    exp_month: int
    exp_year: int
    billing_zip: str
    billing_country: str


@app.get("/test")
def test_route():
    return {"status": "Backend is running!"}


@app.get("/cards")
def get_cards(request: Request, user_id: str):
    token = get_bearer_token(request)
    verify_token(token)

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    try:
        response = table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        return response.get("Items", [])
    except ClientError as e:
        print(f"DB ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/card")
def save_card(request: Request, user_id: str, payload: CardInput):
    token = get_bearer_token(request)
    verify_token(token)

    validate_expiry(payload.exp_month, payload.exp_year)

    # 1. CHECK IF USER ALREADY HAS A CARD
    try:
        existing_cards = table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id}
        )
        if existing_cards.get("Count", 0) > 0:
            # User already has a card -> Return Error
            raise HTTPException(status_code=400, detail="You can only add 1 payment method. Please delete the existing one first.")
    except ClientError as e:
        print(f"DB CHECK ERROR: {e}")
        raise HTTPException(status_code=500, detail="Database check failed")

    # 2. PROCEED TO SAVE IF NO CARDS EXIST
    token = f"pay_{uuid.uuid4().hex[:12]}"
    item = {
        "user_id": user_id,
        "card_token": token,
        "last4": payload.card_number[-4:],
        "masked": f"**** **** **** {payload.card_number[-4:]}",
        "exp_month": payload.exp_month,
        "exp_year": payload.exp_year,
        "name_on_card": payload.name_on_card,
        "billing_zip": payload.billing_zip,
        "billing_country": payload.billing_country,
        "created_at": datetime.utcnow().isoformat()
    }

    try:
        table.put_item(Item=item)
        return {"status": "saved", "token": token}
    except ClientError as e:
        print(f"DB SAVE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/card")
def delete_card(request: Request, user_id: str, card_token: str):
    token = get_bearer_token(request)
    verify_token(token)

    try:
        table.delete_item(Key={"user_id": user_id, "card_token": card_token})
        return {"status": "deleted"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
