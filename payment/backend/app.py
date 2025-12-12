import boto3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

DYNAMODB SETUP


dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("PaymentMethods")


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
def get_cards(user_id: str):
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
def save_card(user_id: str, payload: CardInput):
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
def delete_card(user_id: str, card_token: str):
    try:
        table.delete_item(Key={"user_id": user_id, "card_token": card_token})
        return {"status": "deleted"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
