#!/usr/bin/env python3
"""
LocalStack 테스트 스크립트
AWS 서비스 에뮬레이션 환경에서 Lambda, DynamoDB, S3 등의 서비스 테스트
"""
import boto3
import json
import zipfile
import io
import time


class LocalStackTester:
    """LocalStack 테스트 실행기"""

    def __init__(self):
        # LocalStack 엔드포인트 설정
        self.endpoint_url = "http://localhost:4566"
        self.region = "us-east-1"

        # AWS 클라이언트 초기화
        self.lambda_client = boto3.client(
            "lambda",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id="dummy",
            aws_secret_access_key="dummy"
        )

        self.dynamodb_client = boto3.client(
            "dynamodb",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id="dummy",
            aws_secret_access_key="dummy"
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id="dummy",
            aws_secret_access_key="dummy"
        )

    def test_lambda_service(self) -> bool:
        """Lambda 서비스 테스트"""
        print("[INFO] Testing Lambda service...")

        try:
            # 간단한 Lambda 함수 코드 생성
            lambda_code = """
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Hello from LocalStack Lambda!',
            'timestamp': str(context.aws_request_id)
        })
    }
"""

            # ZIP 파일 생성 (메모리에서)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('lambda_function.py', lambda_code)

            zip_buffer.seek(0)
            zip_content = zip_buffer.read()

            # 기존 함수 정리
            function_name = "test-currency-function"
            try:
                self.lambda_client.delete_function(FunctionName=function_name)
                print(f"[INFO] Deleted existing function: {function_name}")
                time.sleep(1)  # 함수 삭제 완료 대기
            except:
                pass  # 함수가 없으면 무시

            # Lambda 함수 생성
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.9",
                Role="arn:aws:iam::000000000000:role/lambda-role",
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zip_content},
                Description="Test function for LocalStack",
                Timeout=30,
                MemorySize=128
            )

            print(f"[OK] Lambda function created: {response['FunctionName']}")

            # Lambda 함수가 준비될 때까지 대기
            print("Waiting for Lambda function to be ready...")
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # 함수 상태 확인
                    func_response = self.lambda_client.get_function(FunctionName=function_name)
                    state = func_response.get('Configuration', {}).get('State', 'Pending')

                    if state == 'Active':
                        print(f"[OK] Lambda function is active (attempt {attempt + 1})")
                        break
                    elif state == 'Failed':
                        print(f"[FAIL] Lambda function failed to activate")
                        return False
                    else:
                        print(f"Lambda function state: {state}, waiting... (attempt {attempt + 1})")
                        time.sleep(2)
                except Exception as e:
                    print(f"Error checking function state: {e}")
                    time.sleep(1)

            # 함수 실행 테스트
            test_event = {"test": "data"}

            invoke_response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(test_event)
            )

            if invoke_response['StatusCode'] == 200:
                payload = json.loads(invoke_response['Payload'].read())
                print(f"[OK] Lambda function invoked successfully")
                return True
            else:
                print(f"[FAIL] Lambda function invocation failed: {invoke_response['StatusCode']}")
                return False

        except Exception as e:
            print(f"[FAIL] Lambda service test failed: {e}")
            return False

    def test_dynamodb_service(self) -> bool:
        """DynamoDB 서비스 테스트"""
        print("[INFO] Testing DynamoDB service...")

        try:
            # 기존 테이블 정리
            table_name = "test-currency-table"
            try:
                self.dynamodb_client.delete_table(TableName=table_name)
                print(f"[INFO] Deleted existing table: {table_name}")
                time.sleep(2)  # 테이블 삭제 완료 대기
            except:
                pass  # 테이블이 없으면 무시

            # 테이블 생성
            self.dynamodb_client.create_table(
                TableName=table_name,
                KeySchema=[
                    {"AttributeName": "id", "KeyType": "HASH"}
                ],
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST"
            )

            print(f"[OK] DynamoDB table created: {table_name}")

            # 아이템 삽입
            test_item = {
                "id": {"S": "test-123"},
                "currency": {"S": "USD"},
                "rate": {"N": "1350.50"},
                "timestamp": {"S": str(int(time.time()))}
            }

            self.dynamodb_client.put_item(
                TableName=table_name,
                Item=test_item
            )

            print("[OK] Item inserted into DynamoDB table")

            # 아이템 조회
            response = self.dynamodb_client.get_item(
                TableName=table_name,
                Key={"id": {"S": "test-123"}}
            )

            if "Item" in response:
                print("[OK] Item retrieved from DynamoDB table")
                return True
            else:
                print("[FAIL] Item not found in DynamoDB table")
                return False

        except Exception as e:
            print(f"[FAIL] DynamoDB service test failed: {e}")
            return False

    def test_s3_service(self) -> bool:
        """S3 서비스 테스트"""
        print("[INFO] Testing S3 service...")

        try:
            # 버킷 생성
            bucket_name = "test-currency-bucket"

            # LocalStack에서는 LocationConstraint를 지정하지 않거나 빈 값으로 설정
            try:
                self.s3_client.create_bucket(Bucket=bucket_name)
            except Exception:
                # LocalStack 버전 차이에 따라 LocationConstraint가 필요할 수 있음
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': 'us-east-1'}
                )

            print(f"[OK] S3 bucket created: {bucket_name}")

            # 객체 업로드
            test_content = "Test currency data for LocalStack"
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key="test-data.json",
                Body=test_content,
                ContentType="application/json"
            )

            print("[OK] Object uploaded to S3 bucket")

            # 객체 조회
            response = self.s3_client.get_object(
                Bucket=bucket_name,
                Key="test-data.json"
            )

            if response['Body'].read().decode() == test_content:
                print("[OK] Object retrieved from S3 bucket")
                return True
            else:
                print("[FAIL] Object content mismatch")
                return False

        except Exception as e:
            print(f"[FAIL] S3 service test failed: {e}")
            return False

    def test_service_health(self) -> bool:
        """LocalStack 서비스 헬스 체크"""
        print("[INFO] Testing LocalStack health...")

        try:
            # LocalStack 헬스 체크 엔드포인트 호출
            import requests

            response = requests.get(f"{self.endpoint_url}/_localstack/health", timeout=10)

            if response.status_code == 200:
                health_data = response.json()
                services = health_data.get('services', {})

                print("[OK] LocalStack health check passed")
                print(f"   Available services: {list(services.keys())}")

                # 필수 서비스 확인
                required_services = ['dynamodb', 's3', 'lambda']
                missing_services = []

                for service in required_services:
                    if service not in services or services[service] != 'running':
                        missing_services.append(service)

                if missing_services:
                    print(f"[FAIL] Missing or not running services: {missing_services}")
                    return False

                return True
            else:
                print(f"[FAIL] LocalStack health check failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"[FAIL] LocalStack health check error: {e}")
            return False

    def run_all_tests(self):
        """모든 LocalStack 테스트 실행"""
        print("[START] Starting LocalStack Service Tests\n")

        tests = [
            ("LocalStack Health", self.test_service_health),
            ("DynamoDB Service", self.test_dynamodb_service),
            ("S3 Service", self.test_s3_service),
            ("Lambda Service", self.test_lambda_service)
        ]

        results = {}

        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print('='*50)

            try:
                result = test_func()
                results[test_name] = result

                if result:
                    print(f"[OK] {test_name}: PASSED")
                else:
                    print(f"[FAIL] {test_name}: FAILED")

            except Exception as e:
                print(f"[FAIL] {test_name}: ERROR - {e}")
                results[test_name] = False

        return results


def main():
    """메인 함수"""
    print("LocalStack Service Test Suite")
    print("=" * 40)

    # LocalStack 연결 확인
    print("Testing LocalStack connection...")
    try:
        import requests
        response = requests.get("http://localhost:4566/_localstack/health", timeout=5)
        if response.status_code == 200:
            print("[OK] LocalStack is running")
        else:
            print("[FAIL] LocalStack is not responding properly")
            return 1
    except:
        print("[FAIL] Cannot connect to LocalStack. Make sure it's running on localhost:4566")
        print("   Start with: docker-compose up -d localstack")
        return 1

    # 테스트 실행
    tester = LocalStackTester()
    results = tester.run_all_tests()

    # 결과 요약
    print(f"\n{'='*50}")
    print("LOCALSTACK TEST RESULTS SUMMARY")
    print('='*50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:20} : {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All LocalStack tests passed! AWS services are working correctly.")
        return 0
    else:
        print("[WARNING] Some LocalStack tests failed. Check the LocalStack configuration.")
        print("\n[FIX] Troubleshooting:")
        print("  1. Make sure LocalStack is running: docker-compose ps")
        print("  2. Check LocalStack logs: docker-compose logs localstack")
        print("  3. Restart LocalStack: docker-compose restart localstack")
        print("  4. Clear LocalStack data: docker-compose down -v && docker-compose up -d")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)