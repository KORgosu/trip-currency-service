#!/usr/bin/env python3
"""
통합 테스트 스크립트
로컬 개발 환경에서 전체 시스템 동작 확인
4개 서비스 모두 테스트: Currency, Ranking, History, Data Ingestor
"""
import asyncio
import aiohttp
import json
import time
import subprocess
import os
from typing import Dict, Any, List


class IntegrationTester:
    """통합 테스트 실행기"""

    def __init__(self):
        self.services = {
            "currency": "http://localhost:8001",
            "ranking": "http://localhost:8002",
            "history": "http://localhost:8003"
        }
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_all_health_checks(self) -> bool:
        """모든 서비스 헬스 체크 테스트"""
        print("[INFO] Testing all services health check...")

        all_healthy = True

        for service_name, base_url in self.services.items():
            try:
                async with self.session.get(f"{base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"[OK] {service_name.title()} Service: {data['data']['status']}")
                    else:
                        print(f"[FAIL] {service_name.title()} Service: HTTP {response.status}")
                        all_healthy = False
            except Exception as e:
                print(f"[FAIL] {service_name.title()} Service: {e}")
                all_healthy = False

        return all_healthy

    async def test_currency_service(self) -> bool:
        """Currency Service 테스트"""
        print("[INFO] Testing Currency Service...")

        base_url = self.services["currency"]

        try:
            # 최신 환율 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=USD,JPY") as response:
                if response.status == 200:
                    data = await response.json()
                    rates = data['data']['rates']
                    print(f"[OK] Latest rates: {rates}")
                else:
                    print(f"[FAIL] Latest rates failed: HTTP {response.status}")
                    return False

            # 통화 정보 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/USD") as response:
                if response.status == 200:
                    data = await response.json()
                    currency_name = data['data']['currency_name']
                    print(f"[OK] Currency info: {currency_name.encode('utf-8').decode('utf-8', errors='ignore')}")
                else:
                    print(f"[FAIL] Currency info failed: HTTP {response.status}")
                    return False

            # 물가 지수 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/price-index?country=JP") as response:
                if response.status == 200:
                    data = await response.json()
                    indices = data['data']['indices']
                    print(f"[OK] Price index retrieved successfully")
                    return True
                else:
                    print(f"[FAIL] Price index failed: HTTP {response.status}")
                    return False

        except Exception as e:
            print(f"[FAIL] Currency Service error: {e}")
            return False

    async def test_ranking_service(self) -> bool:
        """Ranking Service 테스트"""
        print("[INFO] Testing Ranking Service...")

        base_url = self.services["ranking"]

        try:
            # 선택 기록
            selection_data = {
                "user_id": "test-user-12345",
                "country_code": "JP",
                "session_id": "test-session-123"
            }

            async with self.session.post(f"{base_url}/api/v1/rankings/selections", json=selection_data) as response:
                if response.status == 201:
                    data = await response.json()
                    print(f"[OK] Selection recorded: {data['data']['selection_id']}")
                else:
                    print(f"[FAIL] Selection recording failed: HTTP {response.status}")
                    return False

            # 랭킹 조회
            async with self.session.get(f"{base_url}/api/v1/rankings?period=daily&limit=5") as response:
                if response.status == 200:
                    data = await response.json()
                    ranking = data['data']['ranking']
                    top_3 = [f"{r['rank']}. {r['country_name']}" for r in ranking[:3]]
                    print(f"[OK] Rankings retrieved: Top 3 - {top_3}")
                else:
                    print(f"[FAIL] Rankings failed: HTTP {response.status}")
                    return False

            # 국가별 통계
            async with self.session.get(f"{base_url}/api/v1/rankings/stats/JP?period=7d") as response:
                if response.status == 200:
                    data = await response.json()
                    stats = data['data']['statistics']
                    print(f"[OK] Country stats: Total {stats['total_selections']}, Avg {stats['daily_average']}")
                    return True
                else:
                    print(f"[FAIL] Country stats failed: HTTP {response.status}")
                    return False

        except Exception as e:
            print(f"[FAIL] Ranking Service error: {e}")
            return False

    async def test_history_service(self) -> bool:
        """History Service 테스트"""
        print("[INFO] Testing History Service...")

        base_url = self.services["history"]

        try:
            # 환율 이력 조회
            async with self.session.get(f"{base_url}/api/v1/history?period=1w&target=USD") as response:
                if response.status == 200:
                    data = await response.json()
                    results = data['data']['results']
                    stats = data['data']['statistics']
                    print(f"[OK] History data: {len(results)} points, Avg {stats['average']:.2f}")
                else:
                    print(f"[FAIL] History data failed: HTTP {response.status}")
                    return False

            # 통계 분석
            async with self.session.get(f"{base_url}/api/v1/history/stats?target=USD&period=1m") as response:
                if response.status == 200:
                    data = await response.json()
                    stats = data['data']['statistics']
                    print(f"[OK] Statistics: Trend {stats['trend_direction']}, Volatility {stats['volatility_index']}")
                else:
                    print(f"[FAIL] Statistics failed: HTTP {response.status}")
                    # 디버깅을 위해 응답 내용 출력
                    try:
                        error_data = await response.json()
                        print(f"   Error details: {error_data}")
                        # 'currencies' 키 에러가 있는 경우 처리
                        if 'error' in error_data and 'currencies' in str(error_data['error']):
                            print("   Note: This might be a test data structure issue, not a service error")
                    except:
                        text = await response.text()
                        print(f"   Response: {text}")
                    return False

            # 통화 비교
            async with self.session.get(f"{base_url}/api/v1/history/compare?targets=USD,JPY&period=1w") as response:
                if response.status == 200:
                    data = await response.json()
                    comparison = data['data']['comparison']
                    print(f"[OK] Comparison: {len(comparison)} currencies compared")
                    return True
                else:
                    print(f"[FAIL] Comparison failed: HTTP {response.status}")
                    return False

        except Exception as e:
            print(f"[FAIL] History Service error: {e}")
            return False

    async def test_data_ingestor(self) -> bool:
        """Data Ingestor 테스트"""
        print("[INFO] Testing Data Ingestor...")

        try:
            # Data Ingestor 단일 실행
            result = subprocess.run([
                "python", "services/data-ingestor/main.py"
            ],
            env={**os.environ, "EXECUTION_MODE": "single"},
            capture_output=True,
            text=True,
            timeout=60
            )

            if result.returncode == 0:
                print("[OK] Data Ingestor executed successfully")
                print(f"   Output: {result.stdout.split()[-1] if result.stdout else 'No output'}")
                return True
            else:
                print(f"[FAIL] Data Ingestor failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("[FAIL] Data Ingestor timeout")
            return False
        except Exception as e:
            print(f"[FAIL] Data Ingestor error: {e}")
            return False

    async def test_error_handling(self) -> bool:
        """에러 처리 테스트"""
        print("[INFO] Testing error handling...")

        try:
            # Currency Service 에러 테스트
            base_url = self.services["currency"]
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=INVALID") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"[OK] Currency Service error handled: {data['error']['code']}")
                else:
                    print(f"[FAIL] Currency Service error handling failed")
                    return False

            # Ranking Service 에러 테스트
            base_url = self.services["ranking"]
            async with self.session.get(f"{base_url}/api/v1/rankings?period=invalid") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"[OK] Ranking Service error handled: {data['error']['code']}")
                else:
                    print(f"[FAIL] Ranking Service error handling failed")
                    return False

            # History Service 에러 테스트
            base_url = self.services["history"]
            async with self.session.get(f"{base_url}/api/v1/history?period=invalid&target=USD") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"[OK] History Service error handled: {data['error']['code']}")
                    return True
                else:
                    print(f"[FAIL] History Service error handling failed")
                    return False

        except Exception as e:
            print(f"[FAIL] Error handling test error: {e}")
            return False

    async def test_service_integration(self) -> bool:
        """서비스 간 통합 테스트"""
        print("[INFO] Testing service integration...")

        try:
            # 1. Data Ingestor로 데이터 수집
            print("   Step 1: Running data collection...")
            ingestor_result = subprocess.run([
                "python", "services/data-ingestor/main.py"
            ],
            env={**os.environ, "EXECUTION_MODE": "single"},
            capture_output=True,
            text=True,
            timeout=30
            )

            if ingestor_result.returncode != 0:
                print("   [FAIL] Data collection failed")
                return False

            # 2. Currency Service에서 최신 데이터 확인
            print("   Step 2: Checking updated currency data...")
            await asyncio.sleep(2)  # 데이터 처리 대기

            base_url = self.services["currency"]
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=USD") as response:
                if response.status != 200:
                    print("   [FAIL] Currency data not available")
                    return False

                data = await response.json()
                if "USD" not in data['data']['rates']:
                    print("   [FAIL] USD rate not found")
                    return False

            # 3. Ranking Service에 사용자 선택 기록
            print("   Step 3: Recording user selection...")
            base_url = self.services["ranking"]
            selection_data = {
                "user_id": "integration-test-user",
                "country_code": "US"
            }

            async with self.session.post(f"{base_url}/api/v1/rankings/selections", json=selection_data) as response:
                if response.status != 201:
                    print("   [FAIL] Selection recording failed")
                    return False

            # 4. History Service에서 이력 데이터 확인
            print("   Step 4: Checking historical data...")
            base_url = self.services["history"]
            async with self.session.get(f"{base_url}/api/v1/history?period=1w&target=USD") as response:
                if response.status != 200:
                    print("   [FAIL] Historical data not available")
                    return False

                data = await response.json()
                if len(data['data']['results']) == 0:
                    print("   [FAIL] No historical data found")
                    return False

            print("[OK] Service integration test completed successfully")
            return True

        except Exception as e:
            print(f"[FAIL] Service integration error: {e}")
            return False

    async def test_performance(self) -> bool:
        """성능 테스트"""
        print("[INFO] Testing performance...")

        try:
            # 각 서비스별 성능 테스트
            all_services_fast = True

            for service_name, base_url in self.services.items():
                times = []

                # 각 서비스별 적절한 엔드포인트 선택
                if service_name == "currency":
                    test_url = f"{base_url}/api/v1/currencies/latest?symbols=USD"
                elif service_name == "ranking":
                    test_url = f"{base_url}/api/v1/rankings?period=daily&limit=5"
                elif service_name == "history":
                    test_url = f"{base_url}/api/v1/history?period=1w&target=USD"

                # 5번 요청으로 성능 측정
                for i in range(5):
                    start_time = time.time()

                    async with self.session.get(test_url) as response:
                        if response.status == 200:
                            await response.json()
                            end_time = time.time()
                            times.append((end_time - start_time) * 1000)  # ms
                        else:
                            print(f"[FAIL] {service_name} performance test failed at request {i+1}")
                            all_services_fast = False
                            break

                if times:
                    avg_time = sum(times) / len(times)
                    print(f"   {service_name.title()} Service: {avg_time:.2f}ms avg")

                    if avg_time > 2000:  # 2초 이상이면 느림
                        all_services_fast = False

            return all_services_fast

        except Exception as e:
            print(f"[FAIL] Performance test error: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """모든 테스트 실행"""
        print("[START] Starting Currency Service Integration Tests\n")

        tests = [
            ("All Health Checks", self.test_all_health_checks),
            ("Currency Service", self.test_currency_service),
            ("Ranking Service", self.test_ranking_service),
            ("History Service", self.test_history_service),
            ("Data Ingestor", self.test_data_ingestor),
            ("Service Integration", self.test_service_integration),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance)
        ]

        results = {}

        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            print('='*50)

            try:
                result = await test_func()
                results[test_name] = result

                if result:
                    print(f"[OK] {test_name}: PASSED")
                else:
                    print(f"[FAIL] {test_name}: FAILED")

            except Exception as e:
                print(f"[FAIL] {test_name}: ERROR - {e}")
                results[test_name] = False

        return results


async def main():
    """메인 함수"""
    print("Currency Travel Service - Full Integration Test")
    print("=" * 60)

    # 서비스 URL 확인
    print("Testing services:")
    services = {
        "Currency Service": "http://localhost:8001",
        "Ranking Service": "http://localhost:8002",
        "History Service": "http://localhost:8003"
    }

    for name, url in services.items():
        print(f"  - {name}: {url}")

    async with IntegrationTester() as tester:
        results = await tester.run_all_tests()

        # 결과 요약
        print(f"\n{'='*50}")
        print("TEST RESULTS SUMMARY")
        print('='*50)

        passed = sum(1 for result in results.values() if result)
        total = len(results)

        for test_name, result in results.items():
            status = "[OK] PASSED" if result else "[FAIL] FAILED"
            print(f"{test_name:20} : {status}")

        print(f"\nOverall: {passed}/{total} tests passed")

        if passed == total:
            print("[SUCCESS] All tests passed! The entire Currency Travel Service is working correctly.")
            print("\n[LIST] System Status:")
            print("  [OK] All 4 services are operational")
            print("  [OK] Data flow is working end-to-end")
            print("  [OK] Error handling is proper")
            print("  [OK] Performance is acceptable")
            return 0
        else:
            print("[WARNING] Some tests failed. Please check the service configurations.")
            print("\n[FIX] Troubleshooting:")
            print("  1. Make sure all services are running:")
            print("     - Currency Service: python services/currency-service/main.py")
            print("     - Ranking Service: python services/ranking-service/main.py")
            print("     - History Service: python services/history-service/main.py")
            print("  2. Check database connections (make start)")
            print("  3. Verify environment variables (.env file)")
            return 1


if __name__ == "__main__":
    import sys

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[STOP] Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Test execution failed: {e}")
        sys.exit(1)