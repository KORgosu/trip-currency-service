#!/bin/bash

# LocalStack AWS 리소스 생성 스크립트
# DynamoDB 테이블, S3 버킷, SQS 큐 등을 생성

set -e

echo "🚀 Creating AWS resources in LocalStack..."

# AWS CLI 설정 (LocalStack용)
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-northeast-2
export AWS_ENDPOINT_URL=http://localhost:4566

# LocalStack이 준비될 때까지 대기
echo "⏳ Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/_localstack/health | grep -q '"dynamodb": "available"'; do
    echo "Waiting for LocalStack DynamoDB..."
    sleep 2
done

echo "✅ LocalStack is ready!"

# 1. DynamoDB 테이블 생성
echo "📊 Creating DynamoDB tables..."

# 사용자 선택 기록 테이블
aws dynamodb create-table \
    --table-name travel_destination_selections \
    --attribute-definitions \
        AttributeName=selection_date,AttributeType=S \
        AttributeName=selection_timestamp_userid,AttributeType=S \
        AttributeName=country_code,AttributeType=S \
    --key-schema \
        AttributeName=selection_date,KeyType=HASH \
        AttributeName=selection_timestamp_userid,KeyType=RANGE \
    --global-secondary-indexes \
        'IndexName=country-date-index,KeySchema=[{AttributeName=country_code,KeyType=HASH},{AttributeName=selection_date,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
    --endpoint-url=$AWS_ENDPOINT_URL

# 랭킹 결과 테이블
aws dynamodb create-table \
    --table-name RankingResults \
    --attribute-definitions AttributeName=period,AttributeType=S \
    --key-schema AttributeName=period,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url=$AWS_ENDPOINT_URL

echo "✅ DynamoDB tables created"

# 2. S3 버킷 생성
echo "🪣 Creating S3 buckets..."

aws s3 mb s3://currency-data-backup --endpoint-url=$AWS_ENDPOINT_URL
aws s3 mb s3://currency-service-logs --endpoint-url=$AWS_ENDPOINT_URL

echo "✅ S3 buckets created"

# 3. SQS 큐 생성
echo "📬 Creating SQS queues..."

aws sqs create-queue \
    --queue-name ranking-calculation-queue \
    --endpoint-url=$AWS_ENDPOINT_URL

aws sqs create-queue \
    --queue-name data-processing-dlq \
    --endpoint-url=$AWS_ENDPOINT_URL

echo "✅ SQS queues created"

# 4. SNS 토픽 생성
echo "📢 Creating SNS topics..."

aws sns create-topic \
    --name currency-service-alerts \
    --endpoint-url=$AWS_ENDPOINT_URL

echo "✅ SNS topics created"

# 5. 샘플 데이터 삽입
echo "📝 Inserting sample data..."

# 랭킹 결과 샘플 데이터
aws dynamodb put-item \
    --table-name RankingResults \
    --item '{
        "period": {"S": "daily"},
        "ranking_data": {"L": [
            {"M": {
                "rank": {"N": "1"},
                "country_code": {"S": "JP"},
                "country_name": {"S": "일본"},
                "score": {"N": "1502"},
                "percentage": {"N": "15.2"},
                "change": {"S": "UP"},
                "change_value": {"N": "2"}
            }},
            {"M": {
                "rank": {"N": "2"},
                "country_code": {"S": "US"},
                "country_name": {"S": "미국"},
                "score": {"N": "987"},
                "percentage": {"N": "10.1"},
                "change": {"S": "DOWN"},
                "change_value": {"N": "-1"}
            }}
        ]},
        "last_updated": {"S": "2025-09-05T10:30:00Z"},
        "calculation_metadata": {"M": {
            "total_records": {"N": "9876"},
            "calculation_time_ms": {"N": "1250"}
        }}
    }' \
    --endpoint-url=$AWS_ENDPOINT_URL

echo "✅ Sample data inserted"

# 6. 리소스 확인
echo "🔍 Verifying created resources..."

echo "DynamoDB Tables:"
aws dynamodb list-tables --endpoint-url=$AWS_ENDPOINT_URL

echo "S3 Buckets:"
aws s3 ls --endpoint-url=$AWS_ENDPOINT_URL

echo "SQS Queues:"
aws sqs list-queues --endpoint-url=$AWS_ENDPOINT_URL

echo "🎉 All AWS resources created successfully in LocalStack!"
echo ""
echo "📋 Available resources:"
echo "  - DynamoDB: travel_destination_selections, RankingResults"
echo "  - S3: currency-data-backup, currency-service-logs"
echo "  - SQS: ranking-calculation-queue, data-processing-dlq"
echo "  - SNS: currency-service-alerts"
echo ""
echo "🌐 LocalStack Dashboard: http://localhost:4566"