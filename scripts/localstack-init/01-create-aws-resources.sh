#!/bin/bash

# --- 1. 환경에 따라 사용할 AWS CLI 명령어 및 변수 설정 ---
# ENVIRONMENT 변수가 'local'이면 awslocal을, 아니면 aws를 사용
if [ "${ENVIRONMENT:-local}" == "local" ]; then
    CLI_COMMAND="awslocal"
    # LocalStack의 ARN은 계정 ID가 000000000000으로 고정됨
    export AWS_ACCOUNT_ID="000000000000"
    
    # 💥 [수정] export를 추가하여 환경 변수로 만들어줍니다.
    export AWS_REGION="ap-northeast-2"
    export AWS_DEFAULT_REGION="ap-northeast-2" # boto3 등은 이 변수를 우선적으로 읽을 수 있으므로 함께 설정
else
    CLI_COMMAND="aws"
    # 실제 AWS 환경에서는 현재 사용자의 계정 ID와 리전을 동적으로 조회
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
    export AWS_REGION=$(aws configure get region)
    export AWS_DEFAULT_REGION=$(aws configure get region)
fi
echo "Using AWS CLI command: '$CLI_COMMAND' for environment: '${ENVIRONMENT:-local}'"

# 이하 모든 aws/awslocal 명령어는 이제 ap-northeast-2 리전을 인식하게 됩니다.


# --- 2. 서비스 준비 대기 ---
echo "⏳ Waiting for services to be ready..."
if [ "$CLI_COMMAND" == "awslocal" ]; then
  # LocalStack 대기
  until $CLI_COMMAND s3 ls > /dev/null 2>&1; do
      echo "Waiting for LocalStack to be fully available..."
      sleep 2
  done
else
  # 실제 AWS는 항상 준비되어 있으므로, 간단한 자격 증명 확인만 수행
  echo "Verifying AWS credentials..."
  aws sts get-caller-identity > /dev/null
fi
echo "✅ Services are ready!"


# --- 3. DynamoDB 테이블 생성 (멱등성 보장) ---
echo "📊 Checking/Creating DynamoDB tables..."
TABLES=("travel_destination_selections" "RankingResults")
for TABLE_NAME in "${TABLES[@]}"; do
    if ! $CLI_COMMAND dynamodb describe-table --table-name "$TABLE_NAME" > /dev/null 2>&1; then
        echo "Table '$TABLE_NAME' does not exist. Creating..."
        if [ "$TABLE_NAME" == "travel_destination_selections" ]; then
            $CLI_COMMAND dynamodb create-table \
                --table-name travel_destination_selections \
                --attribute-definitions AttributeName=selection_date,AttributeType=S AttributeName=selection_timestamp_userid,AttributeType=S AttributeName=country_code,AttributeType=S \
                --key-schema AttributeName=selection_date,KeyType=HASH AttributeName=selection_timestamp_userid,KeyType=RANGE \
                --global-secondary-indexes 'IndexName=country-date-index,KeySchema=[{AttributeName=country_code,KeyType=HASH},{AttributeName=selection_date,KeyType=RANGE}],Projection={ProjectionType=ALL}' \
                --billing-mode PAY_PER_REQUEST
        elif [ "$TABLE_NAME" == "RankingResults" ]; then
            $CLI_COMMAND dynamodb create-table \
                --table-name RankingResults \
                --attribute-definitions AttributeName=period,AttributeType=S \
                --key-schema AttributeName=period,KeyType=HASH \
                --billing-mode PAY_PER_REQUEST
        fi
    else
        echo "Table '$TABLE_NAME' already exists. Skipping."
    fi
done
echo "✅ DynamoDB tables checked/created."


# --- 4. S3 버킷 생성 (멱등성 보장) ---
echo "🪣 Checking/Creating S3 buckets..."
BUCKETS=("currency-data-backup" "currency-service-logs")
for BUCKET_NAME in "${BUCKETS[@]}"; do
    if ! $CLI_COMMAND s3api head-bucket --bucket "$BUCKET_NAME" > /dev/null 2>&1; then
        echo "Bucket '$BUCKET_NAME' does not exist. Creating..."
        $CLI_COMMAND s3 mb "s3://$BUCKET_NAME"
    else
        echo "Bucket '$BUCKET_NAME' already exists. Skipping."
    fi
done
echo "✅ S3 buckets checked/created."


# --- 5. SQS 큐 생성 (DLQ 포함, 멱등성 보장) ---
echo "📬 Checking/Creating SQS queues..."
DLQ_NAME="data-processing-dlq"
if ! $CLI_COMMAND sqs get-queue-url --queue-name "$DLQ_NAME" > /dev/null 2>&1; then
    $CLI_COMMAND sqs create-queue --queue-name "$DLQ_NAME"
fi
DLQ_URL=$($CLI_COMMAND sqs get-queue-url --queue-name "$DLQ_NAME" --query "QueueUrl" --output text)
DLQ_ARN=$($CLI_COMMAND sqs get-queue-attributes --queue-url "$DLQ_URL" --attribute-names QueueArn --query "Attributes.QueueArn" --output text)

# [수정됨] 임시 속성 파일을 생성합니다.
# API가 요구하는 'RedrivePolicy'의 값이 '문자열'인 JSON 객체를 파일에 씁니다.
# 쉘의 따옴표 문제를 원천적으로 차단하기 위해 임시 파일을 사용합니다.
ATTRIBUTES_FILE="/tmp/sqs-attributes.json"
cat > ${ATTRIBUTES_FILE} <<EOF
{
  "RedrivePolicy": "{\"deadLetterTargetArn\": \"${DLQ_ARN}\", \"maxReceiveCount\": \"5\"}"
}
EOF

MAIN_QUEUES=("exchange-rates" "user-events" "ranking-events")
for QUEUE_NAME in "${MAIN_QUEUES[@]}"; do
    if ! $CLI_COMMAND sqs get-queue-url --queue-name "$QUEUE_NAME" > /dev/null 2>&1; then
        echo "Creating main queue '$QUEUE_NAME' with DLQ..."
        # [수정됨] file:// 구문을 사용하여 쉘 해석을 우회하고 파일을 직접 읽도록 합니다.
        $CLI_COMMAND sqs create-queue \
            --queue-name "$QUEUE_NAME" \
            --attributes file://${ATTRIBUTES_FILE}
    else
        echo "Main queue '$QUEUE_NAME' already exists. Skipping."
    fi
done
echo "✅ SQS queues and DLQ configuration completed."

# --- 6. SNS 토픽 생성 (멱등성 보장) ---
echo "📢 Checking/Creating SNS topics..."
TOPIC_NAME="currency-service-alerts"
TOPIC_ARN="arn:aws:sns:$AWS_REGION:$AWS_ACCOUNT_ID:$TOPIC_NAME"
# list-topics는 ARN 전체를 반환하므로 grep으로 확인
if ! $CLI_COMMAND sns list-topics | grep -q "$TOPIC_ARN"; then
    echo "Topic '$TOPIC_NAME' does not exist. Creating..."
    $CLI_COMMAND sns create-topic --name "$TOPIC_NAME"
else
    echo "Topic '$TOPIC_NAME' already exists. Skipping."
fi
echo "✅ SNS topics checked/created."


# --- 7. 최종 확인 ---
echo ""
echo "🔍 Verifying all created resources..."
echo "--- DynamoDB Tables ---"
$CLI_COMMAND dynamodb list-tables
echo "--- S3 Buckets ---"
$CLI_COMMAND s3 ls
echo "--- SQS Queues ---"
$CLI_COMMAND sqs list-queues
echo "--- SNS Topics ---"
$CLI_COMMAND sns list-topics

echo ""
echo "🎉 All specified AWS resources are ready!"