#!/usr/bin/env python3
"""
로컬 데이터베이스 초기화 스크립트
MySQL 데이터베이스에 초기 스키마와 데이터를 설정
"""
import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "services"))

async def init_local_database():
    """로컬 데이터베이스 초기화"""
    print("Initializing local MySQL database...")

    try:
        # TODO: AWS 실시간 서비스 변경 - 로컬 DB에서 AWS Aurora로 변경
        # - DB_HOST: 실제 Aurora 클러스터 엔드포인트로 변경 (예: currency-service-aurora.cluster-xxxx.ap-northeast-2.rds.amazonaws.com)
        # - DB_USER: 실제 Aurora 사용자명으로 변경
        # - DB_PASSWORD: 실제 Aurora 비밀번호로 변경 또는 AWS Secrets Manager 사용
        # - DB_NAME: 실제 데이터베이스 이름으로 변경
        # - REDIS_HOST: 실제 ElastiCache Redis 엔드포인트로 변경 (예: currency-redis.xxxxxx.ng.0001.apn2.cache.amazonaws.com)
        # AWS 배포 시 수정 필요사항:
        # 1. Aurora MySQL 클러스터 생성 (Multi-AZ 설정)
        # 2. ElastiCache Redis 클러스터 생성
        # 3. VPC 보안 그룹에서 Lambda/ECS 접근 허용
        # 4. IAM 역할에 rds-db:connect, elasticache:* 권한 추가
        # 5. Parameter Store 또는 Secrets Manager로 민감 정보 관리

        # 현재: 로컬 Docker 환경 설정
        os.environ['ENVIRONMENT'] = 'local'
        os.environ['DB_HOST'] = 'localhost'  # AWS 실시간 시 Aurora 엔드포인트로 변경
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'currency_user'  # AWS 실시간 시 실제 사용자명으로 변경
        os.environ['DB_PASSWORD'] = 'password'  # AWS 실시간 시 Secrets Manager 사용
        os.environ['DB_NAME'] = 'currency_db'
        os.environ['REDIS_HOST'] = 'localhost'  # AWS 실시간 시 ElastiCache 엔드포인트로 변경
        
        from shared.config import init_config
        from shared.database import init_database, MySQLHelper
        
        # 설정 초기화
        config = init_config("db-init")
        print(f"[OK] Configuration loaded for {config.environment.value} environment")
        
        # 데이터베이스 연결 초기화
        await init_database()
        print("[OK] Database connection established")
        
        mysql_helper = MySQLHelper()
        
        # SQL 스크립트 실행
        sql_file = project_root / "scripts" / "init-db.sql"
        
        if sql_file.exists():
            print("[INFO] Executing SQL initialization script...")

            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # SQL 문을 세미콜론으로 분리하여 실행
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

            for i, statement in enumerate(sql_statements):
                if statement.upper().startswith(('CREATE', 'INSERT', 'ALTER', 'DROP')):
                    try:
                        await mysql_helper.execute_update(statement)
                        print(f"  [OK] Executed statement {i+1}/{len(sql_statements)}")
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate entry" in str(e).lower():
                            print(f"  [WARN] Statement {i+1} skipped (already exists)")
                        else:
                            print(f"  [FAIL] Statement {i+1} failed: {e}")
                elif statement.upper().startswith('SELECT'):
                    try:
                        result = await mysql_helper.execute_query(statement)
                        if result:
                            print(f"  [INFO] Query result: {result[0]}")
                    except Exception as e:
                        print(f"  [WARN] Query failed: {e}")

            print("[OK] SQL script execution completed")
        else:
            print("[FAIL] SQL initialization script not found")
            return False
        
        # 데이터 검증
        print("[INFO] Verifying database setup...")

        # 통화 테이블 확인
        currencies_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM currencies")
        print(f"  [INFO] Currencies table: {currencies_count[0]['count']} records")

        # 환율 이력 테이블 확인
        history_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM exchange_rate_history")
        print(f"  [INFO] Exchange rate history: {history_count[0]['count']} records")

        # 일별 집계 테이블 확인
        daily_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM daily_exchange_rates")
        print(f"  [INFO] Daily aggregates: {daily_count[0]['count']} records")

        print("[SUCCESS] Local database initialization completed successfully!")
        return True

    except Exception as e:
        print(f"[FAIL] Database initialization failed: {e}")
        return False

async def main():
    """메인 함수"""
    print("Currency Service - Local Database Initialization")
    print("=" * 60)
    
    success = await init_local_database()
    
    if success:
        print("\n[SUCCESS] Database is ready for local development!")
        print("\n[INFO] Next steps:")
        print("  1. Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
        print("  2. Run services: make run-currency")
        print("  3. Test API: curl http://localhost:8001/health")
        return 0
    else:
        print("\n[FAIL] Database initialization failed!")
        print("\n[INFO] Troubleshooting:")
        print("  1. Check MySQL is running: docker ps")
        print("  2. Check connection: mysql -h localhost -u currency_user -p")
        print("  3. Check database exists: SHOW DATABASES;")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] Database initialization interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Initialization failed: {e}")
        sys.exit(1)