#!/bin/bash
# LocalStack 초기화 스크립트
# AWS 리소스 생성

echo "🌩️ Initializing LocalStack AWS resources..."

# DynamoDB 테이블 생성
echo "Creating DynamoDB tables..."

# 여행지 선택 테이블
awslocal dynamodb create-table \
    --table-name travel_destination_selections \
    --attribute-definitions \
        AttributeName=selection_date,AttributeType=S \
        AttributeName=selection_timestamp_userid,AttributeType=S \
        AttributeName=country_code,AttributeType=S \
    --key-schema \
        AttributeName=selection_date,KeyType=HASH \
        AttributeName=selection_timestamp_userid,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --global-secondary-indexes '[\
        {\
            "IndexName": "country-date-index",\
            "KeySchema": [\
                {"AttributeName":"country_code", "KeyType":"HASH"},\
                {"AttributeName":"selection_date", "KeyType":"RANGE"}\
            ],\
            "Projection": {\
                "ProjectionType": "ALL"\
            },\
            "ProvisionedThroughput": {\
                "ReadCapacityUnits": 5,\n                "WriteCapacityUnits": 5\
            }\
        }\
    ]' \
    --region ap-northeast-2

# 랭킹 결과 테이블
awslocal dynamodb create-table \
    --table-name RankingResults \
    --attribute-definitions AttributeName=period,AttributeType=S \
    --key-schema AttributeName=period,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=2 \
    --region ap-northeast-2

# S3 버킷 생성
echo "Creating S3 buckets..."
awslocal s3 mb s3://currency-data-bucket --region ap-northeast-2
awslocal s3 mb s3://currency-logs-bucket --region ap-northeast-2

# SQS 큐 생성
echo "Creating SQS queues..."
awslocal sqs create-queue \
    --queue-name currency-data-queue \
    --region ap-northeast-2

awslocal sqs create-queue \
    --queue-name currency-notifications-queue \
    --region ap-northeast-2

echo "✅ LocalStack AWS resources initialized successfully!"