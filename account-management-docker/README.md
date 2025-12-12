README — Cognito Account Management App

A complete authentication + profile management system using:

AWS Cognito (Hosted UI, JWT authentication)

FastAPI backend

HTML/JavaScript frontend

Docker (optional)

CloudFormation template for Cognito resources

This guide explains how to deploy your own Cognito environment, configure the backend/frontend, and run the app locally from scratch.

1. Project Structure
account-management/
│
├── backend/
│   ├── app.py
│   ├── db.json
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html
│   └── config.js.example
│
├── docker-compose.yaml
└── cognito-local.yaml

2. Deploy Cognito Resources (CloudFormation)

Deploy your own Cognito User Pool, App Client, and Hosted UI domain:

aws cloudformation deploy \
  --template-file cognito-local.yaml \
  --stack-name cognito-local \
  --parameter-overrides \
      CallbackURL=http://localhost:5500/frontend/index.html \
      LogoutURL=http://localhost:5500/frontend/index.html \
  --capabilities CAPABILITY_IAM

3. Retrieve Cognito Outputs

Run this after deployment:

aws cloudformation describe-stacks \
  --stack-name cognito-local \
  --query "Stacks[0].Outputs" \
  --output table


Record the following values:

(or use env-writer.sh script with stack name as argument to write the .env automatically)

UserPoolId

UserPoolClientId

HostedUILoginURL

CognitoDomain

Example:

UserPoolId: us-east-1_XXXXXX
UserPoolClientId: 12345example
HostedUILoginURL: https://auth-xxxxx.auth.us-east-1.amazoncognito.com/login?client_id=...
CognitoDomain: https://auth-xxxxx.auth.us-east-1.amazoncognito.com

4. Backend Setup (.env)

Create your backend environment file:

cd backend
cp .env.example .env


Edit .env with your CloudFormation outputs:

REGION=us-east-1
USERPOOL_ID=<YOUR_USERPOOL_ID>
CLIENT_ID=<YOUR_APP_CLIENT_ID>
COGNITO_DOMAIN=<YOUR_COGNITO_DOMAIN>
BACKEND_URL=http://localhost:8000


Install dependencies:

pip install -r requirements.txt


Run backend locally:

uvicorn app:app --reload --port 8000

or

docker-compose up --build (need to install docker compose)

5. Frontend Setup (config.js)

Create your frontend config file:

cd frontend
cp config.js.example config.js


Edit config.js:

window.APP_CONFIG = {
  DOMAIN: "<YOUR_COGNITO_DOMAIN>",
  CLIENT_ID: "<YOUR_CLIENT_ID>",
  BACKEND_URL: "http://localhost:8000",
  REDIRECT: "http://localhost:5500/frontend/index.html"
};


Run frontend locally:

python3 -m http.server 5500


Open in browser:

http://localhost:5500/frontend/index.html

6. Login Flow

Open the frontend page

Click “Login”

Cognito Hosted UI opens

Enter username/password

Redirect returns with your ID token

Profile is displayed

You can update username + gameid

7. API Endpoints
Get profile
GET /profile
Authorization: Bearer <id_token>

Update profile
PUT /profile
Authorization: Bearer <id_token>
Content-Type: application/json

{
  "user_name": "Alice",
  "gameid": "G100"
}

8. Optional: Run Backend with Docker
docker compose up --build


Backend will run on:

http://localhost:8000


Make sure .env exists before running Docker.

9. Troubleshooting
Hosted UI says “refused to connect”

Your domain may not exist yet:

aws cognito-idp describe-user-pool-domain --domain <your-domain-prefix>

Profile loads empty

Values in .env or config.js are incorrect.

Docker cannot read env

Ensure you created:

backend/.env