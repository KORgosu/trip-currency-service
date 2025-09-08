#!/usr/bin/env python3
"""
LocalStack DynamoDB 테이블 생성 스크립트
"""
import boto3
from botocore.exceptions import ClientError

def create_dynamodb_tables():
    """DynamoDB 테이블들을 LocalStack에서 생성"""
    
    # LocalStack DynamoDB 클라이언트 생성
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    
    print("Creating DynamoDB tables in LocalStack...")
    
    # 1. travel_destination_selections 테이블 생성
    try:
        dynamodb.create_table(
            TableName='travel_destination_selections',
            KeySchema=[
                {
                    'AttributeName': 'selection_date',
                    'KeyType': 'HASH'  # Partition Key
                },
                {
                    'AttributeName': 'selection_timestamp_userid',
                    'KeyType': 'RANGE'  # Sort Key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'selection_date',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'selection_timestamp_userid',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("[OK] Created table: travel_destination_selections")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("[INFO] Table 'travel_destination_selections' already exists")
        else:
            print(f"[ERROR] Failed to create travel_destination_selections: {e}")
    
    # 2. RankingResults 테이블 생성
    try:
        dynamodb.create_table(
            TableName='RankingResults',
            KeySchema=[
                {
                    'AttributeName': 'ranking_period',
                    'KeyType': 'HASH'  # Partition Key
                },
                {
                    'AttributeName': 'calculated_at',
                    'KeyType': 'RANGE'  # Sort Key  
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'ranking_period',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'calculated_at',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("[OK] Created table: RankingResults")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("[INFO] Table 'RankingResults' already exists")
        else:
            print(f"[ERROR] Failed to create RankingResults: {e}")
    
    # 테이블 목록 확인
    try:
        tables = dynamodb.list_tables()
        print(f"\n[INFO] Current tables in LocalStack: {tables['TableNames']}")
    except Exception as e:
        print(f"[ERROR] Failed to list tables: {e}")

if __name__ == "__main__":
    create_dynamodb_tables()