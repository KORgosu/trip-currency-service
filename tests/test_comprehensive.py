#!/usr/bin/env python3
"""
포괄적인 통합 테스트 시스템
Docker Compose와 LocalStack을 활용한 전체 시스템 테스트
"""
import asyncio
import aiohttp
import aiomysql
import redis.asyncio as aioredis
import json
import time
import subprocess
import os
import sys
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class ComprehensiveTester:
    """포괄적인 통합 테스트 실행기"""
    
    def __init__(self):
        self.services = {
            "currency": "http://localhost:8001",
            "ranking": "http://localhost:8002", 
            "history": "http://localhost:8003"
        }
        self.session = None
        self.results: List[TestResult] = []
        
        # TODO: AWS 실시간 서비스 변경 - 로컬 연결에서 AWS 서비스 연결로 변경
        # - db_config: Aurora MySQL 클러스터 엔드포인트로 변경
        # - redis_url: ElastiCache Redis 엔드포인트로 변경
        # - localstack_endpoint: 실제 AWS 서비스 엔드포인트로 변경 또는 제거
        # AWS 배포 시 수정 필요사항:
        # 1. Aurora 클러스터 엔드포인트 및 인증 정보 설정
        # 2. ElastiCache Redis 엔드포인트 설정
        # 3. DynamoDB, S3, SQS 실제 엔드포인트 사용
        # 4. VPC 내에서 서비스 간 통신 설정

        # 현재: 로컬 개발 환경 설정
        self.db_config = {
            'host': 'localhost',  # AWS 실시간 시 Aurora 엔드포인트로 변경
            'port': 3306,
            'user': 'currency_user',  # AWS 실시간 시 실제 사용자명으로 변경
            'password': 'password',  # AWS 실시간 시 Secrets Manager 사용
            'db': 'currency_db'
        }

        self.redis_url = "redis://localhost:6379"  # AWS 실시간 시 ElastiCache 엔드포인트로 변경
        self.localstack_endpoint = "http://localhost:4566"  # AWS 실시간 시 실제 서비스 엔드포인트로 변경
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _log_test_start(self, test_name: str):
        """테스트 시작 로그"""
        print(f"{test_name}")
        print("-" * 50)
    
    def _log_test_result(self, result: TestResult):
        """테스트 결과 로그"""
        status_emoji = {
            TestStatus.PASSED: "[OK]",
            TestStatus.FAILED: "[FAIL]",
            TestStatus.SKIPPED: "[SKIP]",
            TestStatus.RUNNING: "[RUNNING]"
        }
        
        emoji = status_emoji.get(result.status, "[?]")
        print(f"{emoji} {result.name}: {result.status.value.upper()}")
        if result.message:
            print(f"   {result.message}")
        if result.duration > 0:
            print(f"   Duration: {result.duration:.2f}s")
    
    async def _run_test(self, test_name: str, test_func) -> TestResult:
        """개별 테스트 실행"""
        self._log_test_start(test_name)
        
        result = TestResult(name=test_name, status=TestStatus.RUNNING)
        start_time = time.time()
        
        try:
            success, message, details = await test_func()
            result.status = TestStatus.PASSED if success else TestStatus.FAILED
            result.message = message
            result.details = details or {}
            
        except Exception as e:
            result.status = TestStatus.FAILED
            result.message = f"Exception: {str(e)}"
            result.details = {"exception": str(e)}
        
        result.duration = time.time() - start_time
        self._log_test_result(result)
        self.results.append(result)
        
        return result
    
    async def test_infrastructure_health(self) -> tuple[bool, str, Dict]:
        """인프라 헬스 체크"""
        health_status = {}
        
        # MySQL 연결 테스트
        try:
            connection = await aiomysql.connect(**self.db_config)
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
            connection.close()
            health_status["mysql"] = "healthy" if result and result[0] == 1 else "unhealthy"
        except Exception as e:
            health_status["mysql"] = f"error: {e}"
        
        # Redis 연결 테스트
        try:
            redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.aclose()
            health_status["redis"] = "healthy"
        except Exception as e:
            health_status["redis"] = f"error: {e}"
        
        # LocalStack 연결 테스트 (선택적)
        try:
            async with self.session.get(f"{self.localstack_endpoint}/health") as response:
                if response.status == 200:
                    health_status["localstack"] = "healthy"
                else:
                    health_status["localstack"] = f"unhealthy: HTTP {response.status}"
        except Exception as e:
            health_status["localstack"] = f"unavailable: {e}"
        
        all_critical_healthy = (
            health_status.get("mysql") == "healthy" and 
            health_status.get("redis") == "healthy"
        )
        
        message = f"MySQL: {health_status['mysql']}, Redis: {health_status['redis']}"
        if "localstack" in health_status:
            message += f", LocalStack: {health_status['localstack']}"
        
        return all_critical_healthy, message, health_status
    
    async def test_database_schema(self) -> tuple[bool, str, Dict]:
        """데이터베이스 스키마 검증"""
        schema_info = {}
        
        try:
            connection = await aiomysql.connect(**self.db_config)
            async with connection.cursor() as cursor:
                # 필수 테이블 확인
                required_tables = [
                    'currencies',
                    'exchange_rate_history', 
                    'daily_exchange_rates'
                ]
                
                for table in required_tables:
                    await cursor.execute(f"SHOW TABLES LIKE '{table}'")
                    result = await cursor.fetchone()
                    schema_info[table] = "exists" if result else "missing"
                
                # 데이터 개수 확인
                for table in required_tables:
                    if schema_info[table] == "exists":
                        await cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = await cursor.fetchone()
                        schema_info[f"{table}_count"] = count[0] if count else 0
            
            connection.close()
            
            all_tables_exist = all(
                schema_info.get(table) == "exists" 
                for table in required_tables
            )
            
            message = f"Tables: {', '.join([f'{t}({schema_info.get(t)})' for t in required_tables])}"
            
            return all_tables_exist, message, schema_info
            
        except Exception as e:
            return False, f"Database error: {e}", {"error": str(e)}
    
    async def test_services_health(self) -> tuple[bool, str, Dict]:
        """모든 서비스 헬스 체크"""
        service_status = {}
        
        for service_name, base_url in self.services.items():
            try:
                async with self.session.get(f"{base_url}/health", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        service_status[service_name] = {
                            "status": "healthy",
                            "response": data.get('data', {}).get('status', 'unknown')
                        }
                    else:
                        service_status[service_name] = {
                            "status": "unhealthy",
                            "http_status": response.status
                        }
            except Exception as e:
                service_status[service_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        all_healthy = all(
            status.get("status") == "healthy" 
            for status in service_status.values()
        )
        
        healthy_count = sum(1 for s in service_status.values() if s.get("status") == "healthy")
        message = f"{healthy_count}/{len(self.services)} services healthy"
        
        return all_healthy, message, service_status
    
    async def test_currency_service_endpoints(self) -> tuple[bool, str, Dict]:
        """Currency Service 엔드포인트 테스트"""
        base_url = self.services["currency"]
        endpoint_results = {}
        
        # 테스트할 엔드포인트들
        endpoints = [
            ("/api/v1/currencies/latest?symbols=USD,JPY", "latest_rates"),
            ("/api/v1/currencies/USD", "currency_info"),
            ("/api/v1/price-index?country=JP", "price_index")
        ]
        
        for endpoint, test_name in endpoints:
            try:
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        endpoint_results[test_name] = {
                            "status": "success",
                            "data_keys": list(data.get('data', {}).keys())
                        }
                    else:
                        endpoint_results[test_name] = {
                            "status": "failed",
                            "http_status": response.status
                        }
            except Exception as e:
                endpoint_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        success_count = sum(1 for r in endpoint_results.values() if r.get("status") == "success")
        all_success = success_count == len(endpoints)
        
        message = f"{success_count}/{len(endpoints)} endpoints working"
        
        return all_success, message, endpoint_results
    
    async def test_ranking_service_endpoints(self) -> tuple[bool, str, Dict]:
        """Ranking Service 엔드포인트 테스트"""
        base_url = self.services["ranking"]
        endpoint_results = {}
        
        # 1. 선택 기록 테스트
        try:
            selection_data = {
                "user_id": "test-comprehensive-user",
                "country_code": "JP",
                "session_id": "comprehensive-test-session"
            }
            
            async with self.session.post(f"{base_url}/api/v1/rankings/selections", json=selection_data) as response:
                if response.status == 201:
                    data = await response.json()
                    endpoint_results["record_selection"] = {
                        "status": "success",
                        "selection_id": data.get('data', {}).get('selection_id')
                    }
                else:
                    endpoint_results["record_selection"] = {
                        "status": "failed",
                        "http_status": response.status
                    }
        except Exception as e:
            endpoint_results["record_selection"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 2. 랭킹 조회 테스트
        try:
            async with self.session.get(f"{base_url}/api/v1/rankings?period=daily&limit=5") as response:
                if response.status == 200:
                    data = await response.json()
                    ranking = data.get('data', {}).get('ranking', [])
                    endpoint_results["get_rankings"] = {
                        "status": "success",
                        "ranking_count": len(ranking)
                    }
                else:
                    endpoint_results["get_rankings"] = {
                        "status": "failed",
                        "http_status": response.status
                    }
        except Exception as e:
            endpoint_results["get_rankings"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 3. 통계 조회 테스트
        try:
            async with self.session.get(f"{base_url}/api/v1/rankings/stats/JP?period=7d") as response:
                if response.status == 200:
                    data = await response.json()
                    stats = data.get('data', {}).get('statistics', {})
                    endpoint_results["get_stats"] = {
                        "status": "success",
                        "stats_keys": list(stats.keys())
                    }
                else:
                    endpoint_results["get_stats"] = {
                        "status": "failed",
                        "http_status": response.status
                    }
        except Exception as e:
            endpoint_results["get_stats"] = {
                "status": "error",
                "error": str(e)
            }
        
        success_count = sum(1 for r in endpoint_results.values() if r.get("status") == "success")
        all_success = success_count == 3
        
        message = f"{success_count}/3 endpoints working"
        
        return all_success, message, endpoint_results
    
    async def test_history_service_endpoints(self) -> tuple[bool, str, Dict]:
        """History Service 엔드포인트 테스트"""
        base_url = self.services["history"]
        endpoint_results = {}
        
        # 테스트할 엔드포인트들
        endpoints = [
            ("/api/v1/history?period=1w&target=USD", "history_data"),
            ("/api/v1/history/stats?target=USD&period=1m", "statistics"),
            ("/api/v1/history/compare?targets=USD,JPY&period=1w", "comparison")
        ]
        
        for endpoint, test_name in endpoints:
            try:
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        endpoint_results[test_name] = {
                            "status": "success",
                            "data_keys": list(data.get('data', {}).keys())
                        }
                    else:
                        endpoint_results[test_name] = {
                            "status": "failed",
                            "http_status": response.status
                        }
            except Exception as e:
                endpoint_results[test_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        success_count = sum(1 for r in endpoint_results.values() if r.get("status") == "success")
        all_success = success_count == len(endpoints)
        
        message = f"{success_count}/{len(endpoints)} endpoints working"
        
        return all_success, message, endpoint_results
    
    async def test_data_ingestor_execution(self) -> tuple[bool, str, Dict]:
        """Data Ingestor 실행 테스트"""
        execution_results = {}
        
        try:
            # Data Ingestor 단일 실행
            start_time = time.time()

            # PYTHONPATH 설정하여 import 경로 문제 해결
            env = os.environ.copy()
            env["EXECUTION_MODE"] = "single"
            env["PYTHONPATH"] = os.path.abspath(".")

            result = subprocess.run([
                sys.executable, "services/data-ingestor/main.py"
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120  # 2분 타임아웃
            )
            
            execution_time = time.time() - start_time
            
            execution_results = {
                "return_code": result.returncode,
                "execution_time": execution_time,
                "stdout_lines": len(result.stdout.split('\n')) if result.stdout else 0,
                "stderr_lines": len(result.stderr.split('\n')) if result.stderr else 0
            }
            
            if result.returncode == 0:
                message = f"Executed successfully in {execution_time:.2f}s"
                return True, message, execution_results
            else:
                message = f"Failed with return code {result.returncode}"
                execution_results["stderr_sample"] = result.stderr[:200] if result.stderr else ""
                return False, message, execution_results
                
        except subprocess.TimeoutExpired:
            return False, "Execution timeout (120s)", {"timeout": True}
        except Exception as e:
            return False, f"Execution error: {e}", {"error": str(e)}
    
    async def test_end_to_end_workflow(self) -> tuple[bool, str, Dict]:
        """엔드투엔드 워크플로우 테스트"""
        workflow_steps = {}
        
        try:
            # Step 1: Data Ingestor 실행
            print("   Step 1: Running data collection...")
            # PYTHONPATH 설정하여 import 경로 문제 해결
            env = os.environ.copy()
            env["EXECUTION_MODE"] = "single"
            env["PYTHONPATH"] = os.path.abspath(".")

            ingestor_result = subprocess.run([
                sys.executable, "services/data-ingestor/main.py"
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60
            )
            
            workflow_steps["data_collection"] = {
                "success": ingestor_result.returncode == 0,
                "return_code": ingestor_result.returncode
            }
            
            if ingestor_result.returncode != 0:
                return False, "Data collection failed", workflow_steps
            
            # Step 2: 데이터 처리 대기
            await asyncio.sleep(3)
            
            # Step 3: Currency Service에서 최신 데이터 확인
            print("   Step 2: Verifying currency data...")
            base_url = self.services["currency"]
            async with self.session.get(f"{base_url}/api/v1/currencies/latest?symbols=USD,JPY") as response:
                workflow_steps["currency_verification"] = {
                    "success": response.status == 200,
                    "status_code": response.status
                }
                
                if response.status == 200:
                    data = await response.json()
                    rates = data.get('data', {}).get('rates', {})
                    workflow_steps["currency_verification"]["rates_count"] = len(rates)
            
            # Step 4: Ranking Service에 선택 기록
            print("   Step 3: Recording user selection...")
            base_url = self.services["ranking"]
            selection_data = {
                "user_id": "e2e-test-user",
                "country_code": "US",
                "session_id": "e2e-test-session"
            }
            
            async with self.session.post(f"{base_url}/api/v1/rankings/selections", json=selection_data) as response:
                workflow_steps["selection_recording"] = {
                    "success": response.status == 201,
                    "status_code": response.status
                }
                
                if response.status == 201:
                    data = await response.json()
                    workflow_steps["selection_recording"]["selection_id"] = data.get('data', {}).get('selection_id')
            
            # Step 5: History Service에서 이력 데이터 확인
            print("   Step 4: Checking historical data...")
            base_url = self.services["history"]
            async with self.session.get(f"{base_url}/api/v1/history?period=1w&target=USD") as response:
                workflow_steps["history_verification"] = {
                    "success": response.status == 200,
                    "status_code": response.status
                }
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('data', {}).get('results', [])
                    workflow_steps["history_verification"]["data_points"] = len(results)
            
            # 모든 단계 성공 여부 확인
            all_steps_success = all(
                step.get("success", False) 
                for step in workflow_steps.values()
            )
            
            successful_steps = sum(1 for step in workflow_steps.values() if step.get("success", False))
            message = f"{successful_steps}/{len(workflow_steps)} workflow steps completed"
            
            return all_steps_success, message, workflow_steps
            
        except Exception as e:
            workflow_steps["error"] = str(e)
            return False, f"Workflow error: {e}", workflow_steps
    
    async def test_performance_benchmarks(self) -> tuple[bool, str, Dict]:
        """성능 벤치마크 테스트"""
        performance_results = {}
        
        # 각 서비스별 성능 테스트
        service_endpoints = {
            "currency": "/api/v1/currencies/latest?symbols=USD",
            "ranking": "/api/v1/rankings?period=daily&limit=5",
            "history": "/api/v1/history?period=1w&target=USD"
        }
        
        for service_name, endpoint in service_endpoints.items():
            base_url = self.services[service_name]
            times = []
            
            # 10번 요청으로 성능 측정
            for i in range(10):
                start_time = time.time()
                
                try:
                    async with self.session.get(f"{base_url}{endpoint}") as response:
                        if response.status == 200:
                            await response.json()
                            end_time = time.time()
                            times.append((end_time - start_time) * 1000)  # ms
                        else:
                            break
                except Exception:
                    break
            
            if times:
                performance_results[service_name] = {
                    "avg_response_time": sum(times) / len(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "successful_requests": len(times)
                }
            else:
                performance_results[service_name] = {
                    "error": "No successful requests"
                }
        
        # 성능 기준 확인 (2초 이하)
        all_fast = all(
            result.get("avg_response_time", float('inf')) < 2000 
            for result in performance_results.values()
            if "avg_response_time" in result
        )
        
        avg_times = [
            result.get("avg_response_time", 0) 
            for result in performance_results.values()
            if "avg_response_time" in result
        ]
        
        overall_avg = sum(avg_times) / len(avg_times) if avg_times else 0
        message = f"Overall avg response time: {overall_avg:.2f}ms"
        
        return all_fast, message, performance_results
    
    async def test_error_handling(self) -> tuple[bool, str, Dict]:
        """에러 처리 테스트"""
        error_tests = {}
        
        # 각 서비스별 에러 케이스 테스트
        error_cases = [
            ("currency", "/api/v1/currencies/latest?symbols=INVALID", 400),
            ("ranking", "/api/v1/rankings?period=invalid", 400),
            ("history", "/api/v1/history?period=invalid&target=USD", 400)
        ]
        
        for service_name, endpoint, expected_status in error_cases:
            base_url = self.services[service_name]
            
            try:
                async with self.session.get(f"{base_url}{endpoint}") as response:
                    error_tests[f"{service_name}_error_handling"] = {
                        "expected_status": expected_status,
                        "actual_status": response.status,
                        "handled_correctly": response.status == expected_status
                    }
                    
                    if response.status == expected_status:
                        try:
                            data = await response.json()
                            error_tests[f"{service_name}_error_handling"]["has_error_structure"] = (
                                "error" in data
                            )
                        except:
                            error_tests[f"{service_name}_error_handling"]["has_error_structure"] = False
                            
            except Exception as e:
                error_tests[f"{service_name}_error_handling"] = {
                    "error": str(e),
                    "handled_correctly": False
                }
        
        correctly_handled = sum(
            1 for test in error_tests.values() 
            if test.get("handled_correctly", False)
        )
        
        all_handled = correctly_handled == len(error_cases)
        message = f"{correctly_handled}/{len(error_cases)} error cases handled correctly"
        
        return all_handled, message, error_tests
    
    async def run_comprehensive_tests(self) -> Dict[str, TestResult]:
        """모든 포괄적 테스트 실행"""
        print("Currency Service - Comprehensive Integration Tests")
        print("=" * 70)
        
        # 테스트 목록 정의
        tests = [
            ("Infrastructure Health", self.test_infrastructure_health),
            ("Database Schema", self.test_database_schema),
            ("Services Health", self.test_services_health),
            ("Currency Service Endpoints", self.test_currency_service_endpoints),
            ("Ranking Service Endpoints", self.test_ranking_service_endpoints),
            ("History Service Endpoints", self.test_history_service_endpoints),
            ("Data Ingestor Execution", self.test_data_ingestor_execution),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
            ("Performance Benchmarks", self.test_performance_benchmarks),
            ("Error Handling", self.test_error_handling)
        ]
        
        # 테스트 실행
        for test_name, test_func in tests:
            await self._run_test(test_name, test_func)
        
        return {result.name: result for result in self.results}
    
    def generate_report(self) -> str:
        """테스트 결과 보고서 생성"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        total = len(self.results)
        
        report = f"""
{'='*70}
COMPREHENSIVE TEST REPORT
{'='*70}

SUMMARY:
  Total Tests: {total}
  Passed: {passed}
  Failed: {failed}
  Success Rate: {(passed/total*100):.1f}%

DETAILED RESULTS:
"""
        
        for result in self.results:
            status_emoji = {
                TestStatus.PASSED: "[OK]",
                TestStatus.FAILED: "[FAIL]",
                TestStatus.SKIPPED: "[SKIP]"
            }
            
            emoji = status_emoji.get(result.status, "[?]")
            report += f"\n{emoji} {result.name}"
            report += f"\n   Status: {result.status.value.upper()}"
            report += f"\n   Duration: {result.duration:.2f}s"
            
            if result.message:
                report += f"\n   Message: {result.message}"
            
            if result.status == TestStatus.FAILED and result.details:
                report += f"\n   Details: {json.dumps(result.details, indent=6)}"
        
        if passed == total:
            report += f"""

ALL TESTS PASSED!
The Currency Travel Service is fully operational and ready for production.

System Status:
  - All infrastructure components are healthy
  - All 3 microservices are operational
  - Data flow is working end-to-end
  - Performance meets requirements
  - Error handling is proper
"""
        else:
            report += f"""

SOME TESTS FAILED
Please review the failed tests and fix the issues before deployment.

Next Steps:
  1. Check failed test details above
  2. Verify service configurations
  3. Check database connections
  4. Review error logs
  5. Re-run tests after fixes
"""
        
        return report


async def main():
    """메인 함수"""
    print("Currency Travel Service - Comprehensive Test Suite")
    print("This will test the entire system including all services and infrastructure")
    print()
    
    # 환경 확인
    print("Environment Check:")
    print("  Services Expected:")
    services = {
        "Currency Service": "http://localhost:8001",
        "Ranking Service": "http://localhost:8002", 
        "History Service": "http://localhost:8003"
    }
    
    for name, url in services.items():
        print(f"    - {name}: {url}")
    
    print("  Infrastructure Expected:")
    print("    - MySQL: localhost:3306")
    print("    - Redis: localhost:6379")
    print("    - LocalStack: localhost:4566 (optional)")
    print()
    
    # 테스트 실행
    async with ComprehensiveTester() as tester:
        results = await tester.run_comprehensive_tests()
        
        # 보고서 생성 및 출력
        report = tester.generate_report()
        print(report)
        
        # 결과에 따른 종료 코드 반환
        passed = sum(1 for r in results.values() if r.status == TestStatus.PASSED)
        total = len(results)
        
        if passed == total:
            return 0  # 모든 테스트 성공
        else:
            return 1  # 일부 테스트 실패


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)