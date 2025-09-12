#!/usr/bin/env python3
"""
LocalStack DynamoDB 테이블 생성 스크립트
AWS 실시간 서비스 변경: LocalStack 대신 실제 AWS DynamoDB 사용
"""
import boto3
from botocore.exceptions import ClientError

def create_dynamodb_tables():
    """DynamoDB 테이블들을 생성"""

    # TODO: AWS 실시간 서비스 변경 - LocalStack에서 실제 AWS DynamoDB로 변경
    # - endpoint_url 제거 (실제 AWS 사용)
    # - region_name: 실제 리전으로 변경 (예: ap-northeast-2)
    # - aws_access_key_id, aws_secret_access_key: 실제 AWS 자격 증명 사용 또는 IAM 역할 사용
    # - 테이블 생성 시 ProvisionedThroughput 대신 OnDemand로 변경 가능
    # AWS 배포 시 수정 필요사항:
    # 1. IAM 역할에 dynamodb:CreateTable, dynamodb:DescribeTable 권한 추가
    # 2. VPC 엔드포인트 또는 NAT 게이트웨이를 통한 인터넷 접근 허용
    # 3. CloudFormation이나 Terraform으로 테이블 생성 자동화 고려

    # 현재: LocalStack용 설정
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:4566',  # AWS 실시간 시 제거
        region_name='us-east-1',  # AWS 실시간 시 실제 리전으로 변경
        aws_access_key_id='dummy',  # AWS 실시간 시 실제 키 또는 IAM 역할 사용
        aws_secret_access_key='dummy'  # AWS 실시간 시 실제 키 또는 IAM 역할 사용
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