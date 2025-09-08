#!/usr/bin/env python3
"""
통합 테스트 실행기
다양한 테스트 시나리오를 선택적으로 실행할 수 있는 유틸리티
"""
import asyncio
import argparse
import sys
import os
import subprocess
import time
from typing import List, Dict, Any


class TestRunner:
    """테스트 실행 관리자"""
    
    def __init__(self):
        self.available_tests = {
            "basic": {
                "file": "tests/test_fixed.py",
                "description": "Basic connectivity tests (MySQL, Redis, Shared modules)"
            },
            "integration": {
                "file": "tests/test_integration.py", 
                "description": "Full integration tests (All services + Data Ingestor)"
            },
            "comprehensive": {
                "file": "tests/test_comprehensive.py",
                "description": "Comprehensive tests (Infrastructure + Performance + E2E)"
            }
        }
        
        self.services = [
            ("Currency Service", "services/currency-service/main.py", 8001),
            ("Ranking Service", "services/ranking-service/main.py", 8002),
            ("History Service", "services/history-service/main.py", 8003)
        ]
    
    def print_banner(self):
        """배너 출력"""
        print("=" * 70)
        print("Currency Travel Service - Test Runner")
        print("=" * 70)
        print()
    
    def list_available_tests(self):
        """사용 가능한 테스트 목록 출력"""
        print("Available Test Suites:")
        print()
        
        for test_name, test_info in self.available_tests.items():
            print(f"  {test_name:15} - {test_info['description']}")
        
        print()
        print("Usage Examples:")
        print("  python test_runner.py --test basic")
        print("  python test_runner.py --test integration --start-services")
        print("  python test_runner.py --test comprehensive --full-setup")
        print("  python test_runner.py --all")
        print()
    
    def check_service_running(self, port: int) -> bool:
        """서비스가 실행 중인지 확인"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_services_status(self) -> Dict[str, bool]:
        """모든 서비스 상태 확인"""
        status = {}
        
        print("Checking service status...")
        
        for service_name, _, port in self.services:
            is_running = self.check_service_running(port)
            status[service_name] = is_running
            
            status_emoji = "[V]" if is_running else "[X]"
            print(f"  {status_emoji} {service_name} (:{port})")
        
        return status
    
    def start_services(self) -> bool:
        """서비스들을 백그라운드에서 시작"""
        print("Starting services...")
        
        processes = []
        
        for service_name, script_path, port in self.services:
            if self.check_service_running(port):
                print(f"  [INFO] {service_name} already running on port {port}")
                continue
            
            try:
                print(f"  [STARTING] {service_name}...")
                
                # 백그라운드에서 서비스 시작
                process = subprocess.Popen([
                    sys.executable, script_path
                ], 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
                )
                
                processes.append((service_name, process, port))
                
                # 서비스 시작 대기
                for i in range(30):  # 30초 대기
                    time.sleep(1)
                    if self.check_service_running(port):
                        print(f"  [OK] {service_name} started successfully")
                        break
                else:
                    print(f"  [FAIL] {service_name} failed to start within 30 seconds")
                    process.terminate()
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Failed to start {service_name}: {e}")
                return False
        
        if processes:
            print(f"\n[OK] Started {len(processes)} services")
            print("[WARN] Note: Services are running in background. Use 'make stop' to stop them.")
        
        return True
    
    def setup_infrastructure(self) -> bool:
        """인프라 설정 (Docker Compose)"""
        print("Setting up infrastructure...")
        
        try:
            # Docker Compose 시작
            result = subprocess.run([
                "docker-compose", "up", "-d", "mysql", "redis"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[FAIL] Failed to start infrastructure: {result.stderr}")
                return False
            
            print("[OK] Infrastructure started")
            
            # 데이터베이스 초기화 대기
            print("[INFO] Waiting for database to be ready...")
            time.sleep(10)
            
            # 데이터베이스 초기화
            print("[INFO] Initializing database...")
            result = subprocess.run([
                sys.executable, "scripts/init_services.py"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[FAIL] Database initialization failed: {result.stderr}")
                return False
            
            print("[OK] Database initialized")
            return True
            
        except Exception as e:
            print(f"[FAIL] Infrastructure setup failed: {e}")
            return False
    
    def run_test(self, test_name: str) -> bool:
        """특정 테스트 실행"""
        if test_name not in self.available_tests:
            print(f"[FAIL] Unknown test: {test_name}")
            return False
        
        test_info = self.available_tests[test_name]
        test_file = test_info["file"]
        
        print(f"Running {test_name} tests...")
        print(f"   File: {test_file}")
        print(f"   Description: {test_info['description']}")
        print()
        
        try:
            result = subprocess.run([
                sys.executable, test_file
            ], text=True)
            
            success = result.returncode == 0
            
            if success:
                print(f"\n[OK] {test_name} tests completed successfully!")
            else:
                print(f"\n[FAIL] {test_name} tests failed!")
            
            return success
            
        except Exception as e:
            print(f"[FAIL] Failed to run {test_name} tests: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """모든 테스트 순차 실행"""
        print("Running all test suites...")
        print()
        
        results = {}
        
        # 테스트 순서: basic -> integration -> comprehensive
        test_order = ["basic", "integration", "comprehensive"]
        
        for test_name in test_order:
            print(f"\n{'='*50}")
            print(f"Running {test_name.upper()} Tests")
            print('='*50)
            
            success = self.run_test(test_name)
            results[test_name] = success
            
            if not success:
                print(f"\n[WARN] {test_name} tests failed. Stopping test execution.")
                break
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """테스트 결과 요약 출력"""
        print("\n" + "="*70)
        print("TEST EXECUTION SUMMARY")
        print("="*70)
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        for test_name, success in results.items():
            status = "[OK] PASSED" if success else "[FAIL] FAILED"
            description = self.available_tests[test_name]["description"]
            print(f"{test_name:15} : {status:10} - {description}")
        
        print(f"\nOverall Result: {passed}/{total} test suites passed")
        
        if passed == total:
            print("\n[SUCCESS] All tests passed! The system is ready for use.")
        else:
            print(f"\n[FAIL] {total - passed} test suite(s) failed. Please check the issues above.")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="Currency Travel Service Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py --list                    # List available tests
  python test_runner.py --test basic              # Run basic tests only
  python test_runner.py --test integration        # Run integration tests
  python test_runner.py --test comprehensive      # Run comprehensive tests
  python test_runner.py --all                     # Run all tests
  python test_runner.py --all --full-setup        # Full setup + all tests
  python test_runner.py --test integration --start-services  # Start services + integration tests
        """
    )
    
    parser.add_argument("--list", action="store_true", 
                       help="List available test suites")
    parser.add_argument("--test", choices=["basic", "integration", "comprehensive"],
                       help="Run specific test suite")
    parser.add_argument("--all", action="store_true",
                       help="Run all test suites")
    parser.add_argument("--start-services", action="store_true",
                       help="Start services before running tests")
    parser.add_argument("--full-setup", action="store_true",
                       help="Setup infrastructure and start services")
    parser.add_argument("--check-status", action="store_true",
                       help="Check current service status")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    runner.print_banner()
    
    # 인수가 없으면 도움말 표시
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    # 사용 가능한 테스트 목록 표시
    if args.list:
        runner.list_available_tests()
        return 0
    
    # 서비스 상태 확인
    if args.check_status:
        runner.check_services_status()
        return 0
    
    # 전체 설정
    if args.full_setup:
        print("Full setup mode: Infrastructure + Services + Tests")
        print()
        
        if not runner.setup_infrastructure():
            print("[FAIL] Infrastructure setup failed")
            return 1
        
        if not runner.start_services():
            print("[FAIL] Service startup failed")
            return 1
    
    # 서비스 시작
    elif args.start_services:
        if not runner.start_services():
            print("[FAIL] Service startup failed")
            return 1
    
    # 테스트 실행
    results = {}
    
    if args.all:
        results = runner.run_all_tests()
    elif args.test:
        success = runner.run_test(args.test)
        results[args.test] = success
    else:
        print("❌ No test specified. Use --test, --all, or --list")
        return 1
    
    # 결과 요약
    if results:
        runner.print_summary(results)
        
        # 모든 테스트가 성공했으면 0, 아니면 1 반환
        all_passed = all(results.values())
        return 0 if all_passed else 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest runner failed: {e}")
        sys.exit(1)