#!/usr/bin/env python3
"""
LocalStack 서비스 테스트 스크립트
S3, DynamoDB, SQS, Lambda, API Gateway, IAM, CloudWatch 테스트
"""
import boto3
import json
from datetime import datetime

def test_s3():
    """S3 버킷 생성 및 테스트"""
    print("Testing S3...")
    try:
        # TODO: AWS 실시간 서비스 변경 - LocalStack에서 실제 AWS S3로 변경
        # - endpoint_url 제거 (실제 AWS S3 사용)
        # - region_name: 실제 리전으로 변경 (예: ap-northeast-2)
        # - aws_access_key_id, aws_secret_access_key: 실제 AWS 자격 증명 사용 또는 IAM 역할 사용
        # AWS 배포 시 수정 필요사항:
        # 1. S3 버킷 생성 및 권한 설정
        # 2. IAM 역할에 s3:GetObject, s3:PutObject 권한 추가
        # 3. VPC 엔드포인트 또는 NAT 게이트웨이를 통한 인터넷 접근 허용

        # 현재: LocalStack용 설정
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',  # AWS 실시간 시 제거
            region_name='us-east-1',  # AWS 실시간 시 실제 리전으로 변경
            aws_access_key_id='dummy',  # AWS 실시간 시 실제 키 또는 IAM 역할 사용
            aws_secret_access_key='dummy'  # AWS 실시간 시 실제 키 또는 IAM 역할 사용
        )

        # 버킷 생성
        bucket_name = 'currency-data-bucket'
        s3.create_bucket(Bucket=bucket_name)
        print(f"[OK] Created S3 bucket: {bucket_name}")

        # 파일 업로드
        test_data = {"test": "data", "timestamp": datetime.utcnow().isoformat()}
        s3.put_object(
            Bucket=bucket_name,
            Key='test.json',
            Body=json.dumps(test_data),
            ContentType='application/json'
        )
        print("[OK] Uploaded test file to S3")

        # 파일 목록 조회
        response = s3.list_objects_v2(Bucket=bucket_name)
        objects = response.get('Contents', [])
        print(f"[OK] S3 bucket contains {len(objects)} objects")

        return True
    except Exception as e:
        print(f"[FAIL] S3 test failed: {e}")
        return False

def test_dynamodb():
    """DynamoDB 테이블 조회 및 테스트"""
    print("Testing DynamoDB...")
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 테이블 목록 조회
        tables = dynamodb.list_tables()
        print(f"[OK] DynamoDB tables: {tables['TableNames']}")

        # 테이블 설명
        for table_name in tables['TableNames']:
            desc = dynamodb.describe_table(TableName=table_name)
            item_count = desc['Table']['ItemCount']
            print(f"   [INFO] {table_name}: {item_count} items")

        return True
    except Exception as e:
        print(f"[FAIL] DynamoDB test failed: {e}")
        return False

def test_sqs():
    """SQS 큐 생성 및 테스트"""
    print("Testing SQS...")
    try:
        sqs = boto3.client(
            'sqs',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 큐 생성
        queue_name = 'currency-queue'
        response = sqs.create_queue(QueueName=queue_name)
        queue_url = response['QueueUrl']
        print(f"[OK] Created SQS queue: {queue_name}")

        # 메시지 전송
        test_message = {
            "type": "test",
            "data": {"currency": "USD", "rate": 1392.4},
            "timestamp": datetime.utcnow().isoformat()
        }

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(test_message)
        )
        print("[OK] Sent test message to SQS")

        # 메시지 수신
        response = sqs.receive_message(QueueUrl=queue_url)
        messages = response.get('Messages', [])
        print(f"[OK] Received {len(messages)} messages from SQS")

        return True
    except Exception as e:
        print(f"[FAIL] SQS test failed: {e}")
        return False

def test_lambda():
    """Lambda 함수 생성 및 테스트"""
    print("Testing Lambda...")
    try:
        lambda_client = boto3.client(
            'lambda',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 간단한 Lambda 함수 생성
        function_name = 'test-function'
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::000000000000:role/lambda-role',  # LocalStack용 더미 ARN
            Handler='index.handler',
            Code={'ZipFile': b'fake code'},
            Description='Test function for LocalStack'
        )
        print(f"[OK] Created Lambda function: {function_name}")

        # 함수 목록 조회
        functions = lambda_client.list_functions()
        print(f"[OK] Lambda functions: {len(functions.get('Functions', []))} functions")

        return True
    except Exception as e:
        print(f"[FAIL] Lambda test failed: {e}")
        return False

def test_cloudwatch():
    """CloudWatch 메트릭 및 로그 테스트"""
    print("Testing CloudWatch...")
    try:
        cloudwatch = boto3.client(
            'cloudwatch',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 메트릭 데이터 전송
        cloudwatch.put_metric_data(
            Namespace='CurrencyService',
            MetricData=[
                {
                    'MetricName': 'TestMetric',
                    'Value': 42.0,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        print("[OK] Sent metric data to CloudWatch")

        # 로그 그룹 생성
        logs = boto3.client(
            'logs',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        log_group_name = '/aws/lambda/currency-service'
        logs.create_log_group(logGroupName=log_group_name)
        print(f"[OK] Created CloudWatch log group: {log_group_name}")

        return True
    except Exception as e:
        print(f"[FAIL] CloudWatch test failed: {e}")
        return False

def test_iam():
    """IAM 역할 및 정책 테스트"""
    print("Testing IAM...")
    try:
        iam = boto3.client(
            'iam',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 역할 생성
        role_name = 'currency-service-role'
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description='Test role for Currency Service'
        )
        print(f"[OK] Created IAM role: {role_name}")

        # 역할 목록 조회
        roles = iam.list_roles()
        print(f"[OK] IAM roles: {len(roles.get('Roles', []))} roles")

        return True
    except Exception as e:
        print(f"[FAIL] IAM test failed: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("LocalStack 서비스 테스트 시작")
    print("=" * 50)

    tests = [
        ("S3", test_s3),
        ("DynamoDB", test_dynamodb),
        ("SQS", test_sqs),
        ("Lambda", test_lambda),
        ("CloudWatch", test_cloudwatch),
        ("IAM", test_iam)
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        success = test_func()
        results[test_name] = success

    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"   {test_name}: {status}")

    print(f"\n전체 결과: {passed}/{total} 테스트 통과")

    if passed == total:
        print("모든 LocalStack 서비스가 정상 작동 중입니다!")
    else:
        print("일부 서비스에 문제가 있습니다.")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)