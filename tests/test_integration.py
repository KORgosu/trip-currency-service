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
        print("🔍 Testing all services health check...")
        
        all_healthy = True
        
        for service_name, base_url in self.services.items():
            try:
                async with self.session.get(f"{base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ {service_name.title()} Service: {data['data']['status']}")
                    else:
                        print(f"❌ {service_name.title()} Service: HTTP {response.status}")
                        all_healthy = False
            except Exception as e:
                print(f"❌ {service_name.title()} Service: {e}")
                all_healthy = False
        
        return all_healthy
    
    async def test_currency_service(self) -> bool:
        """Currency Service 테스트"""
        print("🔍 Testing Currency Service...")
        
        base_url = self.services["currency"]
        
        try:
            # 최신 환율 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=USD,JPY") as response:
                if response.status == 200:
                    data = await response.json()
                    rates = data['data']['rates']
                    print(f"✅ Latest rates: {rates}")
                else:
                    print(f"❌ Latest rates failed: HTTP {response.status}")
                    return False
            
            # 통화 정보 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/USD") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Currency info: {data['data']['currency_name']}")
                else:
                    print(f"❌ Currency info failed: HTTP {response.status}")
                    return False
            
            # 물가 지수 조회
            async with self.session.get(f"{base_url}/api/v1/currencies/price-index?country=JP") as response:
                if response.status == 200:
                    data = await response.json()
                    indices = data['data']['indices']
                    print(f"✅ Price index: BigMac {indices['bigmac_index']}, Composite {indices['composite_index']}")
                    return True
                else:
                    print(f"❌ Price index failed: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Currency Service error: {e}")
            return False
    
    async def test_ranking_service(self) -> bool:
        """Ranking Service 테스트"""
        print("🔍 Testing Ranking Service...")
        
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
                    print(f"✅ Selection recorded: {data['data']['selection_id']}")
                else:
                    print(f"❌ Selection recording failed: HTTP {response.status}")
                    return False
            
            # 랭킹 조회
            async with self.session.get(f"{base_url}/api/v1/rankings?period=daily&limit=5") as response:
                if response.status == 200:
                    data = await response.json()
                    ranking = data['data']['ranking']
                    top_3 = [f"{r['rank']}. {r['country_name']}" for r in ranking[:3]]
                    print(f"✅ Rankings retrieved: Top 3 - {top_3}")
                else:
                    print(f"❌ Rankings failed: HTTP {response.status}")
                    return False
            
            # 국가별 통계
            async with self.session.get(f"{base_url}/api/v1/rankings/stats/JP?period=7d") as response:
                if response.status == 200:
                    data = await response.json()
                    stats = data['data']['statistics']
                    print(f"✅ Country stats: Total {stats['total_selections']}, Avg {stats['daily_average']}")
                    return True
                else:
                    print(f"❌ Country stats failed: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Ranking Service error: {e}")
            return False
    
    async def test_history_service(self) -> bool:
        """History Service 테스트"""
        print("🔍 Testing History Service...")
        
        base_url = self.services["history"]
        
        try:
            # 환율 이력 조회
            async with self.session.get(f"{base_url}/api/v1/history?period=1w&target=USD") as response:
                if response.status == 200:
                    data = await response.json()
                    results = data['data']['results']
                    stats = data['data']['statistics']
                    print(f"✅ History data: {len(results)} points, Avg {stats['average']:.2f}")
                else:
                    print(f"❌ History data failed: HTTP {response.status}")
                    return False
            
            # 통계 분석
            async with self.session.get(f"{base_url}/api/v1/history/stats?target=USD&period=1m") as response:
                if response.status == 200:
                    data = await response.json()
                    stats = data['data']['statistics']
                    print(f"✅ Statistics: Trend {stats['trend_direction']}, Volatility {stats['volatility_index']}")
                else:
                    print(f"❌ Statistics failed: HTTP {response.status}")
                    return False
            
            # 통화 비교
            async with self.session.get(f"{base_url}/api/v1/history/compare?targets=USD,JPY&period=1w") as response:
                if response.status == 200:
                    data = await response.json()
                    currencies = data['data']['currencies']
                    print(f"✅ Comparison: {len(currencies)} currencies compared")
                    return True
                else:
                    print(f"❌ Comparison failed: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ History Service error: {e}")
            return False
    
    async def test_data_ingestor(self) -> bool:
        """Data Ingestor 테스트"""
        print("🔍 Testing Data Ingestor...")
        
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
                print("✅ Data Ingestor executed successfully")
                print(f"   Output: {result.stdout.split()[-1] if result.stdout else 'No output'}")
                return True
            else:
                print(f"❌ Data Ingestor failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Data Ingestor timeout")
            return False
        except Exception as e:
            print(f"❌ Data Ingestor error: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """에러 처리 테스트"""
        print("🔍 Testing error handling...")
        
        try:
            # Currency Service 에러 테스트
            base_url = self.services["currency"]
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=INVALID") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"✅ Currency Service error handled: {data['error']['code']}")
                else:
                    print(f"❌ Currency Service error handling failed")
                    return False
            
            # Ranking Service 에러 테스트
            base_url = self.services["ranking"]
            async with self.session.get(f"{base_url}/api/v1/rankings?period=invalid") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"✅ Ranking Service error handled: {data['error']['code']}")
                else:
                    print(f"❌ Ranking Service error handling failed")
                    return False
            
            # History Service 에러 테스트
            base_url = self.services["history"]
            async with self.session.get(f"{base_url}/api/v1/history?period=invalid&target=USD") as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"✅ History Service error handled: {data['error']['code']}")
                    return True
                else:
                    print(f"❌ History Service error handling failed")
                    return False
                    
        except Exception as e:
            print(f"❌ Error handling test error: {e}")
            return False
    
    async def test_service_integration(self) -> bool:
        """서비스 간 통합 테스트"""
        print("🔍 Testing service integration...")
        
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
                print("   ❌ Data collection failed")
                return False
            
            # 2. Currency Service에서 최신 데이터 확인
            print("   Step 2: Checking updated currency data...")
            await asyncio.sleep(2)  # 데이터 처리 대기
            
            base_url = self.services["currency"]
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=USD") as response:
                if response.status != 200:
                    print("   ❌ Currency data not available")
                    return False
                
                data = await response.json()
                if "USD" not in data['data']['rates']:
                    print("   ❌ USD rate not found")
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
                    print("   ❌ Selection recording failed")
                    return False
            
            # 4. History Service에서 이력 데이터 확인
            print("   Step 4: Checking historical data...")
            base_url = self.services["history"]
            async with self.session.get(f"{base_url}/api/v1/history?period=1w&target=USD") as response:
                if response.status != 200:
                    print("   ❌ Historical data not available")
                    return False
                
                data = await response.json()
                if len(data['data']['results']) == 0:
                    print("   ❌ No historical data found")
                    return False
            
            print("✅ Service integration test completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Service integration error: {e}")
            return False
    
    async def test_performance(self) -> bool:
        """성능 테스트"""
        print("🔍 Testing performance...")
        
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
                            print(f"❌ {service_name} performance test failed at request {i+1}")
                            all_services_fast = False
                            break
                
                if times:
                    avg_time = sum(times) / len(times)
                    print(f"   {service_name.title()} Service: {avg_time:.2f}ms avg")
                    
                    if avg_time > 2000:  # 2초 이상이면 느림
                        all_services_fast = False
            
            return all_services_fast
            
        except Exception as e:
            print(f"❌ Performance test error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """모든 테스트 실행"""
        print("🚀 Starting Currency Service Integration Tests\n")
        
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
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
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
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:20} : {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! The entire Currency Travel Service is working correctly.")
            print("\n📋 System Status:")
            print("  ✅ All 4 services are operational")
            print("  ✅ Data flow is working end-to-end")
            print("  ✅ Error handling is proper")
            print("  ✅ Performance is acceptable")
            return 0
        else:
            print("⚠️  Some tests failed. Please check the service configurations.")
            print("\n🔧 Troubleshooting:")
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
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)