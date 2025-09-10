#!/usr/bin/env bash
# Create ClicksToday and ClicksMinute tables using AWS CLI (On-Demand billing)
# Requires AWS CLI configured with appropriate credentials and region.

set -euo pipefail

REGION=${AWS_REGION:-ap-northeast-2}
TODAY_TABLE=${CLICKS_TODAY_TABLE:-ClicksToday}
MINUTE_TABLE=${CLICKS_MINUTE_TABLE:-ClicksMinute}

echo "Creating table $TODAY_TABLE (ClicksToday)..."
aws dynamodb create-table \
  --table-name "$TODAY_TABLE" \
  --attribute-definitions AttributeName=scope,AttributeType=S AttributeName=country,AttributeType=S \
  --key-schema AttributeName=scope,KeyType=HASH AttributeName=country,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" || true

echo "Creating table $MINUTE_TABLE (ClicksMinute)..."
aws dynamodb create-table \
  --table-name "$MINUTE_TABLE" \
  --attribute-definitions AttributeName=minute,AttributeType=S AttributeName=country,AttributeType=S \
  --key-schema AttributeName=minute,KeyType=HASH AttributeName=country,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" || true

echo "Enabling TTL 'ttl' on $MINUTE_TABLE (may take a few minutes)..."
aws dynamodb update-time-to-live \
  --table-name "$MINUTE_TABLE" \
  --time-to-live-specification "Enabled=true,AttributeName=ttl" \
  --region "$REGION" || true

echo "Done. Verify tables in AWS Console or via 'aws dynamodb describe-table --table-name <name>'."
#!/usr/bin/env bash
set -euo pipefail

REGION=${AWS_REGION:-ap-northeast-2}

# Create ClicksToday
aws dynamodb create-table \
  --table-name ClicksToday \
  --attribute-definitions AttributeName=scope,AttributeType=S AttributeName=country,AttributeType=S \
  --key-schema AttributeName=scope,KeyType=HASH AttributeName=country,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ${REGION}

# Create ClicksMinute
aws dynamodb create-table \
  --table-name ClicksMinute \
  --attribute-definitions AttributeName=minute,AttributeType=S AttributeName=country,AttributeType=S \
  --key-schema AttributeName=minute,KeyType=HASH AttributeName=country,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ${REGION}

echo "Tables created. Enable TTL on ClicksMinute with attribute name 'ttl' via AWS Console or CLI."
