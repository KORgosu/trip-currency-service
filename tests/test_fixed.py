#!/usr/bin/env python3
"""
수정된 기본 연결성 테스트
MySQL, Redis 연결 및 shared 모듈 테스트
"""
import asyncio
import sys
import os

# 상위 디렉토리의 shared 모듈 import를 위한 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import aiomysql
import redis.asyncio as redis


async def test_mysql_connection():
    """MySQL 연결 테스트"""
    print("Testing MySQL connection...")
    
    try:
        connection = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='currency_user',
            password='password',
            db='currency_db'
        )
        
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()
            
        connection.close()
        
        if result and result[0] == 1:
            print("[OK] MySQL connection successful")
            return True
        else:
            print("[FAIL] MySQL connection failed - unexpected result")
            return False
            
    except Exception as e:
        print(f"[FAIL] MySQL connection failed: {e}")
        return False


async def test_redis_connection():
    """Redis 연결 테스트"""
    print("Testing Redis connection...")
    
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        
        # 연결 테스트
        await redis_client.ping()
        
        # 간단한 읽기/쓰기 테스트
        await redis_client.set("test_key", "test_value", ex=10)
        value = await redis_client.get("test_key")
        
        await redis_client.aclose()
        
        if value == "test_value":
            print("[OK] Redis connection successful")
            return True
        else:
            print("[FAIL] Redis connection failed - unexpected value")
            return False
            
    except Exception as e:
        print(f"[FAIL] Redis connection failed: {e}")
        return False


async def test_shared_modules():
    """Shared 모듈 import 테스트"""
    print("Testing shared modules...")
    
    try:
        # 환경 변수 설정
        os.environ['ENVIRONMENT'] = 'local'
        os.environ['DB_HOST'] = 'localhost'
        os.environ['REDIS_HOST'] = 'localhost'
        
        # 기본 모듈들만 테스트 (순환 참조 방지)
        from services.shared.models import CurrencyCode
        from services.shared.exceptions import BaseServiceException
        from services.shared.utils import DateTimeUtils
        
        # 기본 기능 테스트
        assert CurrencyCode.USD == "USD"
        
        # DateTimeUtils 테스트
        now = DateTimeUtils.utc_now()
        assert now is not None
        
        # Config 초기화 (순환 참조 없이)
        from services.shared.config import init_config
        config = init_config("test-service")
        
        assert config.service_name == "test-service"
        
        print("[OK] Shared modules import successful")
        return True
        
    except Exception as e:
        print(f"[FAIL] Shared modules import failed: {e}")
        return False


async def test_database_schema():
    """데이터베이스 스키마 테스트"""
    print("Testing database schema...")
    
    try:
        connection = await aiomysql.connect(
            host='localhost',
            port=3306,
            user='currency_user',
            password='password',
            db='currency_db'
        )
        
        async with connection.cursor() as cursor:
            # 테이블 존재 확인
            tables_to_check = [
                'currencies',
                'exchange_rate_history',
                'daily_exchange_rates'
            ]
            
            for table in tables_to_check:
                await cursor.execute(f"SHOW TABLES LIKE '{table}'")
                result = await cursor.fetchone()
                if not result:
                    print(f"[WARN] Table '{table}' does not exist")
                else:
                    print(f"[OK] Table '{table}' exists")
        
        connection.close()
        print("[OK] Database schema check completed")
        return True
        
    except Exception as e:
        print(f"[FAIL] Database schema test failed: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("Starting comprehensive connectivity tests...\n")
    
    results = []
    
    # 1. MySQL 연결 테스트
    results.append(await test_mysql_connection())
    
    # 2. Redis 연결 테스트
    results.append(await test_redis_connection())
    
    # 3. Shared 모듈 테스트
    results.append(await test_shared_modules())
    
    # 4. 데이터베이스 스키마 테스트
    results.append(await test_database_schema())
    
    # 결과 요약
    print("\nTest Results Summary:")
    print(f"[OK] Passed: {sum(results)}")
    print(f"[FAIL] Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[WARN] Some tests failed. Check the logs above.")
        return 1



if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)