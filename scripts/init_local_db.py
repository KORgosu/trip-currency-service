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
    print("🗄️ Initializing local MySQL database...")
    
    try:
        # 환경 변수 설정
        os.environ['ENVIRONMENT'] = 'local'
        os.environ['DB_HOST'] = 'currency-mysql'
        os.environ['DB_PORT'] = '3306'
        os.environ['DB_USER'] = 'currency_user'
        os.environ['DB_PASSWORD'] = 'password'
        os.environ['DB_NAME'] = 'currency_db'
        os.environ['REDIS_HOST'] = 'currency-redis'
        
        from shared.config import init_config
        from shared.database import init_database, MySQLHelper
        
        # 설정 초기화
        config = init_config("db-init")
        print(f"✅ Configuration loaded for {config.environment.value} environment")
        
        # 데이터베이스 연결 초기화
        await init_database()
        print("✅ Database connection established")
        
        mysql_helper = MySQLHelper()
        
        # SQL 스크립트 실행
        sql_file = project_root / "scripts" / "init-db.sql"
        
        if sql_file.exists():
            print("📄 Executing SQL initialization script...")
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # SQL 문을 세미콜론으로 분리하여 실행
            sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            for i, statement in enumerate(sql_statements):
                if statement.upper().startswith(('CREATE', 'INSERT', 'ALTER', 'DROP')):
                    try:
                        await mysql_helper.execute_update(statement)
                        print(f"  ✅ Executed statement {i+1}/{len(sql_statements)}")
                    except Exception as e:
                        if "already exists" in str(e).lower() or "duplicate entry" in str(e).lower():
                            print(f"  ⚠️ Statement {i+1} skipped (already exists)")
                        else:
                            print(f"  ❌ Statement {i+1} failed: {e}")
                elif statement.upper().startswith('SELECT'):
                    try:
                        result = await mysql_helper.execute_query(statement)
                        if result:
                            print(f"  ✅ {result[0]}")
                    except Exception as e:
                        print(f"  ⚠️ Query failed: {e}")
            
            print("✅ SQL script execution completed")
        else:
            print("❌ SQL initialization script not found")
            return False
        
        # 데이터 검증
        print("🔍 Verifying database setup...")
        
        # 통화 테이블 확인
        currencies_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM currencies")
        print(f"  📊 Currencies table: {currencies_count[0]['count']} records")
        
        # 환율 이력 테이블 확인
        history_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM exchange_rate_history")
        print(f"  📈 Exchange rate history: {history_count[0]['count']} records")
        
        # 일별 집계 테이블 확인
        daily_count = await mysql_helper.execute_query("SELECT COUNT(*) as count FROM daily_exchange_rates")
        print(f"  📅 Daily aggregates: {daily_count[0]['count']} records")
        
        print("🎉 Local database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

async def main():
    """메인 함수"""
    print("Currency Service - Local Database Initialization")
    print("=" * 60)
    
    success = await init_local_database()
    
    if success:
        print("\n✅ Database is ready for local development!")
        print("\n📋 Next steps:")
        print("  1. Start Redis: docker run -d -p 6379:6379 redis:7-alpine")
        print("  2. Run services: make run-currency")
        print("  3. Test API: curl http://localhost:8001/health")
        return 0
    else:
        print("\n❌ Database initialization failed!")
        print("\n🔧 Troubleshooting:")
        print("  1. Check MySQL is running: docker ps")
        print("  2. Check connection: mysql -h localhost -u currency_user -p")
        print("  3. Check database exists: SHOW DATABASES;")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Database initialization interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)