#!/bin/bash

# Usage:
#   bash env-writer.sh <cloudformation-stack-name>
# Example:
#   bash env-writer.sh cognito-local

STACK_NAME=$1

if [ -z "$STACK_NAME" ]; then
  echo "❌ Please specify the CloudFormation stack name"
  echo "Usage: bash env-writer.sh cognito-local"
  exit 1
fi

echo "🔍 Fetching CloudFormation outputs for stack: $STACK_NAME ..."

# Extract outputs
USERPOOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text)

HOSTED_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='HostedUILoginURL'].OutputValue" \
  --output text)

REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$USERPOOL_ID" ] || [ -z "$CLIENT_ID" ]; then
  echo "❌ ERROR: Could not retrieve Cognito outputs from stack."
  exit 1
fi

echo "📦 Writing environment file: .env"

cat <<EOF > .env
# Auto-generated environment variables
REGION=$REGION
USERPOOL_ID=$USERPOOL_ID
CLIENT_ID=$CLIENT_ID

# Cognito Hosted UI domain
COGNITO_DOMAIN=https://auth-$ACCOUNT_ID-$REGION.auth.$REGION.amazoncognito.com

# Hosted login URL (full link to be used in frontend)
HOSTED_LOGIN_URL=$HOSTED_URL
EOF

echo "✅ .env file created successfully!"
echo
echo "🌎 REGION:            $REGION"
echo "🆔 USERPOOL_ID:       $USERPOOL_ID"
echo "🔑 CLIENT_ID:         $CLIENT_ID"
echo "🌐 Hosted Login URL:"
echo "$HOSTED_URL"
echo
echo "🎉 Done! Your backend is now ready to run with:"
echo "   uvicorn app:app --reload --port 8000"
