#!/usr/bin/env python3
"""
통합 연결 테스트 스크립트
LocalStack + MySQL + Redis + Kafka 연결 테스트
"""
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root / "services"))

async def test_mysql_connection():
    """MySQL 연결 테스트"""
    print("Testing MySQL connection...")
    try:
        from shared.database import MySQLHelper

        # TODO: AWS 실시간 서비스 변경 - 환경 변수 설정 변경
        # - DB_HOST: Aurora MySQL 클러스터 엔드포인트로 변경
        # - DB_USER/DB_PASSWORD: 실제 인증 정보 또는 Secrets Manager로 변경
        # AWS 배포 시 수정 필요사항:
        # 1. Aurora 클러스터 엔드포인트 및 인증 정보 설정
        # 2. Parameter Store 또는 Secrets Manager에서 민감 정보 조회
        # 3. IAM 역할 기반 인증 고려

        # 현재: 로컬 환경 설정
        os.environ['DB_HOST'] = 'localhost'  # AWS 실시간 시 Aurora 엔드포인트로 변경
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'currency_user'  # AWS 실시간 시 실제 사용자명으로 변경
        os.environ['DB_PASSWORD'] = 'password'  # AWS 실시간 시 Secrets Manager 사용
        os.environ['DB_NAME'] = 'currency_db'

        mysql_helper = MySQLHelper()
        result = await mysql_helper.execute_query("SELECT 1 as test")
        print(f"[OK] MySQL connected: {result[0]['test']}")
        return True
    except Exception as e:
        print(f"[FAIL] MySQL connection failed: {e}")
        return False

async def test_redis_connection():
    """Redis 연결 테스트"""
    print("Testing Redis connection...")
    try:
        from shared.database import RedisHelper

        redis_helper = RedisHelper()
        test_key = "test_connection"
        test_value = "success"

        await redis_helper.set(test_key, test_value)
        result = await redis_helper.get(test_key)

        if result == test_value:
            print("[OK] Redis connected and working")
            return True
        else:
            print("[FAIL] Redis data mismatch")
            return False
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        return False

async def test_dynamodb_connection():
    """DynamoDB (LocalStack) 연결 테스트"""
    print("Testing DynamoDB connection...")
    try:
        import boto3

        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 테이블 목록 조회
        tables = dynamodb.list_tables()
        print(f"[OK] DynamoDB connected: {tables['TableNames']}")

        # 테스트 아이템 삽입
        test_item = {
            'selection_date': '2025-09-08',
            'selection_timestamp_userid': '20250908120000_test_user',
            'country_code': 'TEST',
            'user_id': 'test_user',
            'created_at': '2025-09-08T12:00:00Z'
        }

        dynamodb.put_item(
            TableName='travel_destination_selections',
            Item={k: {'S': str(v)} for k, v in test_item.items()}
        )

        # 아이템 조회
        response = dynamodb.get_item(
            TableName='travel_destination_selections',
            Key={
                'selection_date': {'S': '2025-09-08'},
                'selection_timestamp_userid': {'S': '20250908120000_test_user'}
            }
        )

        if 'Item' in response:
            print("[OK] DynamoDB item inserted and retrieved")
            return True
        else:
            print("[FAIL] DynamoDB item not found")
            return False

    except Exception as e:
        print(f"[FAIL] DynamoDB connection failed: {e}")
        return False

async def test_sqs_connection():
    """SQS (LocalStack) 연결 테스트"""
    print("Testing SQS connection...")
    try:
        import boto3

        sqs = boto3.client(
            'sqs',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )

        # 큐 생성
        queue_name = 'test-integration-queue'
        response = sqs.create_queue(QueueName=queue_name)
        queue_url = response['QueueUrl']

        # 메시지 전송
        test_message = {"test": "integration", "timestamp": "2025-09-08T12:00:00Z"}
        import json
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(test_message)
        )

        # 메시지 수신
        response = sqs.receive_message(QueueUrl=queue_url)
        messages = response.get('Messages', [])

        if messages:
            print("[OK] SQS message sent and received")
            return True
        else:
            print("[FAIL] SQS message not received")
            return False

    except Exception as e:
        print(f"[FAIL] SQS connection failed: {e}")
        return False

async def test_kafka_connection():
    """Kafka 연결 테스트"""
    print("Testing Kafka connection...")
    try:
        from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
        import json

        # 프로듀서 테스트
        producer = AIOKafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

        await producer.start()

        test_message = {"test": "kafka_integration", "timestamp": "2025-09-08T12:00:00Z"}
        await producer.send_and_wait('test-topic', test_message)

        await producer.stop()
        print("[OK] Kafka producer working")

        # 컨슈머 테스트 (간단한 확인)
        consumer = AIOKafkaConsumer(
            'test-topic',
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            auto_offset_reset='earliest'
        )

        await consumer.start()
        await consumer.stop()
        print("[OK] Kafka consumer connection working")

        return True

    except Exception as e:
        print(f"[FAIL] Kafka connection failed: {e}")
        return False

async def test_application_integration():
    """실제 애플리케이션 통합 테스트"""
    print("Testing application integration...")
    try:
        # 환경 변수 설정
        os.environ['ENVIRONMENT'] = 'local'
        os.environ['DB_HOST'] = 'localhost'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'currency_user'
        os.environ['DB_PASSWORD'] = 'password'
        os.environ['DB_NAME'] = 'currency_db'
        os.environ['REDIS_HOST'] = 'localhost'
        os.environ['REDIS_PORT'] = '6379'

        from shared.config import init_config
        from shared.database import init_database

        # 설정 초기화
        config = init_config("integration-test")
        await init_database()

        print("[OK] Application configuration and database initialization successful")
        return True

    except Exception as e:
        print(f"[FAIL] Application integration failed: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("통합 연결 테스트 시작")
    print("=" * 50)

    tests = [
        ("MySQL", test_mysql_connection),
        ("Redis", test_redis_connection),
        ("DynamoDB", test_dynamodb_connection),
        ("SQS", test_sqs_connection),
        ("Kafka", test_kafka_connection),
        ("Application", test_application_integration)
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        success = await test_func()
        results[test_name] = success

    # 결과 요약
    print("\n" + "=" * 50)
    print("통합 테스트 결과 요약:")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"   {test_name}: {status}")

    print(f"\n전체 결과: {passed}/{total} 통합 테스트 통과")

    if passed == total:
        print("모든 서비스 간 연결이 정상 작동 중입니다!")
        print("LocalStack + MySQL + Redis + Kafka 통합 성공!")
    else:
        print("일부 서비스 연결에 문제가 있습니다.")

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)