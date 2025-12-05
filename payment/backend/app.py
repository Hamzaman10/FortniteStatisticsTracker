import boto3
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
from datetime import datetime
from botocore.exceptions import ClientError

app = FastAPI()

# ---------------------------
# 1. THE VIDEO HACK (Serve Frontend)
# ---------------------------
# This tells Python: "If they ask for a file, look in the 'static' folder"
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

@app.get("/payment.html")
def serve_payment():
    return FileResponse("static/payment.html")

# ---------------------------
# 2. DATABASE LOGIC
# ---------------------------
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("PaymentMethods")

class CardInput(BaseModel):
    name_on_card: str
    card_number: str
    exp_month: int
    exp_year: int
    billing_zip: str
    billing_country: str

@app.get("/cards")
def get_cards(user_id: str):
    if not user_id: raise HTTPException(400, "Missing user_id")
    try:
        response = table.query(KeyConditionExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id})
        return response.get("Items", [])
    except ClientError as e:
        print(f"DB ERROR: {e}")
        # Return empty list on error so frontend doesn't crash
        return []

@app.post("/card")
def save_card(user_id: str, payload: CardInput):
    # 1. CHECK LIMIT
    try:
        existing = table.query(KeyConditionExpression="user_id = :uid", ExpressionAttributeValues={":uid": user_id})
        if existing.get("Count", 0) > 0:
            raise HTTPException(400, "Limit reached: You can only have 1 card.")
    except ClientError:
        pass # If check fails, try to save anyway

    # 2. SAVE
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
        raise HTTPException(500, str(e))

@app.delete("/card")
def delete_card(user_id: str, card_token: str):
    try:
        table.delete_item(Key={"user_id": user_id, "card_token": card_token})
        return {"status": "deleted"}
    except ClientError as e:
        raise HTTPException(500, str(e))