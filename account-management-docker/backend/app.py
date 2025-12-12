from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, HTTPException
from jose import jwt, jwk
from jose.utils import base64url_decode
import requests
import os


REGION = os.getenv("REGION", "us-east-1")
USERPOOL_ID = os.getenv("USERPOOL_ID")
APP_CLIENT_ID = os.getenv("CLIENT_ID")

if not USERPOOL_ID or not APP_CLIENT_ID:
    raise RuntimeError("Missing USERPOOL_ID or CLIENT_ID")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"

app = FastAPI()

# JWKS fetch (public keys used to verify Cognito tokens)
jwks = requests.get(JWKS_URL).json()["keys"]


def verify_token(token: str):
    """
    Cognito JWT validation.
    """
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


@app.get("/me")
def me(request: Request):
    token = get_bearer_token(request)
    claims = verify_token(token)

    # return whatever you want here; this is just proof auth worked
    return {
        "sub": claims.get("sub"),
        "aud": claims.get("aud"),
        "email": claims.get("email"),
        "username": claims.get("cognito:username"),
    }
