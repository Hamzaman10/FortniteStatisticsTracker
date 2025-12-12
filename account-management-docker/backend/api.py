from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import json

from auth import get_token, verify_token


FORTNITE_LAMBDA_URL = os.getenv("FORTNITE_LAMBDA_URL")
if not FORTNITE_LAMBDA_URL:
    raise RuntimeError("Missing FORTNITE_LAMBDA_URL")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def call_fortnite_lambda(payload: dict):
    r = requests.post(FORTNITE_LAMBDA_URL, json=payload, timeout=15)
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)

    data = r.json()

    # Your Lambda returns: {"statusCode": 200, "body": "<json string>"}
    if isinstance(data, dict) and "body" in data and isinstance(data["body"], str):
        try:
            return json.loads(data["body"])
        except Exception:
            return {"error": "Lambda body was not JSON", "body": data["body"]}

    return data


@app.get("/itemshop")
def itemshop():
    # Works with your lambda_handler(event): mode == "itemshop"
    return call_fortnite_lambda({"mode": "itemshop"})


@app.get("/stats")
def stats(request: Request, username: str, platform: str = "epic"):
    # Require Cognito login for stats
    token = get_token(request)
    verify_token(token)

    # Works with your lambda_handler(event): mode == "stats"
    # Also passes username/platform that your stats function expects
    return call_fortnite_lambda({"mode": "stats", "username": username, "platform": platform})
