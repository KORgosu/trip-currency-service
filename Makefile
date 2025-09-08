# Currency Travel Service Makefile
# 로컬 개발 및 테스트를 위한 명령어들

.PHONY: help setup start stop test clean lint format init-check build test-basic test-integration test-comprehensive test-all test-runner

# 기본 타겟
help:
	@echo "Available commands:"
	@echo ""
	@echo "🏗️  Setup & Environment:"
	@echo "  setup         - 개발 환경 설정"
	@echo "  start         - 로컬 개발 환경 시작 (Docker Compose)"
	@echo "  stop          - 로컬 개발 환경 중지"
	@echo "  init-check    - 서비스 초기화 상태 확인"
	@echo "  build         - Docker 이미지 빌드"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test          - 기본 연결성 테스트"
	@echo "  test-basic    - 기본 테스트 (MySQL, Redis, Shared modules)"
	@echo "  test-integration - 통합 테스트 (All services + Data Ingestor)"
	@echo "  test-comprehensive - 포괄적 테스트 (Infrastructure + Performance + E2E)"
	@echo "  test-all      - 모든 테스트 순차 실행"
	@echo "  test-runner   - 대화형 테스트 실행기"
	@echo "  test-api      - API 엔드포인트 테스트"
	@echo ""
	@echo "🔧 Development:"
	@echo "  clean         - 정리"
	@echo "  lint          - 코드 린팅"
	@echo "  format        - 코드 포맷팅"

# 개발 환경 설정
setup:
	@echo "🔧 Setting up development environment..."
	copy .env.example .env
	cmd /c "chcp 65001 && set PYTHONIOENCODING=utf-8 && pip install -r requirements.txt"
	@echo "✅ Development environment setup completed"

# 초기화 상태 확인
init-check:
	@echo "� Cthecking service initialization status..."
	@echo "1. MySQL Connection:"
	@docker-compose exec mysql mysqladmin ping -h localhost 2>/dev/null && echo "✅ MySQL ready" || echo "❌ MySQL not ready"
	@echo "2. Redis Connection:"
	@docker-compose exec redis redis-cli ping 2>/dev/null && echo "✅ Redis ready" || echo "❌ Redis not ready"
	@echo "3. LocalStack Health:"
	@curl -s http://localhost:4566/_localstack/health >/dev/null 2>&1 && echo "✅ LocalStack ready" || echo "❌ LocalStack not ready"
	@echo "4. Service Health Checks:"
	@curl -s http://localhost:8001/health >/dev/null 2>&1 && echo "✅ Currency Service ready" || echo "❌ Currency Service not ready"
	@curl -s http://localhost:8002/health >/dev/null 2>&1 && echo "✅ Ranking Service ready" || echo "❌ Ranking Service not ready"
	@curl -s http://localhost:8003/health >/dev/null 2>&1 && echo "✅ History Service ready" || echo "❌ History Service not ready"

# Docker 이미지 빌드
build:
	@echo "🔨 Building Docker images..."
	docker-compose build --no-cache
	@echo "✅ Docker images built successfully"

# 로컬 개발 환경 시작
start:
	@echo "🚀 Starting Currency Travel Services..."
	@echo "⏳ This may take a few minutes for initial setup..."
	docker-compose up -d
	@echo "⏳ Waiting for services to initialize..."
	@sleep 30
	@echo "✅ Services started!"
	@echo ""
	@echo "📊 Available services:"
	@echo "  - Currency Service: http://localhost:8001"
	@echo "  - Ranking Service: http://localhost:8002"
	@echo "  - History Service: http://localhost:8003"
	@echo "  - Kafka UI: http://localhost:8081"
	@echo "  - MySQL: localhost:3306"
	@echo "  - Redis: localhost:6379"
	@echo "  - LocalStack: http://localhost:4566"
	@echo ""
	@echo "🔍 Check status with: make init-check"

# 로컬 개발 환경 중지
stop:
	@echo "🛑 Stopping Currency Travel Services..."
	docker-compose down
	@echo "✅ Services stopped"

# 기본 테스트 실행
test:
	@echo "🧪 Running basic connectivity tests..."
	python test_fixed.py
	@echo "✅ Basic tests completed"

# 기본 테스트 (MySQL, Redis, Shared modules)
test-basic:
	@echo "🧪 Running basic tests..."
	python test_runner.py --test basic
	@echo "✅ Basic tests completed"

# 통합 테스트 (All services + Data Ingestor)
test-integration:
	@echo "🧪 Running integration tests..."
	python test_runner.py --test integration
	@echo "✅ Integration tests completed"

# 포괄적 테스트 (Infrastructure + Performance + E2E)
test-comprehensive:
	@echo "🧪 Running comprehensive tests..."
	python test_runner.py --test comprehensive
	@echo "✅ Comprehensive tests completed"

# 모든 테스트 순차 실행
test-all:
	@echo "🧪 Running all test suites..."
	python test_runner.py --all
	@echo "✅ All tests completed"

# 대화형 테스트 실행기
test-runner:
	@echo "🧪 Starting interactive test runner..."
	python test_runner.py --list
	@echo ""
	@echo "💡 Usage examples:"
	@echo "  python test_runner.py --test basic"
	@echo "  python test_runner.py --test integration --start-services"
	@echo "  python test_runner.py --all --full-setup"

# 전체 설정 + 모든 테스트
test-full:
	@echo "🧪 Full setup and comprehensive testing..."
	python test_runner.py --all --full-setup
	@echo "✅ Full test suite completed"

# 서비스 상태 확인
test-status:
	@echo "🔍 Checking service status..."
	python test_runner.py --check-status

# API 테스트
test-api:
	@echo "🧪 Testing API endpoints..."
	@echo "1. Currency Service:"
	@curl -s "http://localhost:8001/api/v1/currencies/latest?symbols=USD,JPY" >/dev/null 2>&1 && echo "✅ Currency API responding" || echo "❌ Currency API not responding"
	@echo "2. Ranking Service:"
	@curl -s "http://localhost:8002/api/v1/rankings?period=daily" >/dev/null 2>&1 && echo "✅ Ranking API responding" || echo "❌ Ranking API not responding"
	@echo "3. History Service:"
	@curl -s "http://localhost:8003/api/v1/history?period=1w&target=USD" >/dev/null 2>&1 && echo "✅ History API responding" || echo "❌ History API not responding"

# 코드 린팅
lint:
	@echo "🔍 Running code linting..."
	flake8 services/ --max-line-length=100 --ignore=E203,W503
	mypy services/ --ignore-missing-imports
	@echo "✅ Linting completed"

# 코드 포맷팅
format:
	@echo "🎨 Formatting code..."
	black services/ --line-length=100
	isort services/ --profile=black
	@echo "✅ Code formatting completed"

# 정리
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed"

# 강제 정리 (모든 데이터 삭제)
clean-all: clean
	@echo "🧹 Removing all Docker images..."
	docker rmi $$(docker images -q) 2>/dev/null || true
	@echo "✅ Complete cleanup finished"

# 개발 서버 실행 (개별 서비스)
run-currency:
	@echo "🚀 Starting Currency Service on port 8001..."
	cd services/currency-service && python main.py

run-ranking:
	@echo "🚀 Starting Ranking Service on port 8002..."
	cd services/ranking-service && python main.py

run-history:
	@echo "🚀 Starting History Service on port 8003..."
	cd services/history-service && python main.py

run-ingestor:
	@echo "🚀 Starting Data Ingestor (single run)..."
	cd services/data-ingestor && EXECUTION_MODE=single python main.py

run-ingestor-scheduler:
	@echo "🚀 Starting Data Ingestor Scheduler..."
	cd services/data-ingestor && EXECUTION_MODE=scheduler python main.py

# 모든 서비스 동시 실행 (백그라운드)
run-all:
	@echo "🚀 Starting all services..."
	@echo "Starting Currency Service..."
	cd services/currency-service && python main.py &
	@echo "Starting Ranking Service..."
	cd services/ranking-service && python main.py &
	@echo "Starting History Service..."
	cd services/history-service && python main.py &
	@echo "Starting Data Ingestor Scheduler..."
	cd services/data-ingestor && EXECUTION_MODE=scheduler python main.py &
	@echo "✅ All services started in background"
	@echo "Use 'make stop-all' to stop all services"

# 모든 서비스 중지
stop-all:
	@echo "🛑 Stopping all services..."
	pkill -f "currency-service/main.py" || true
	pkill -f "ranking-service/main.py" || true
	pkill -f "history-service/main.py" || true
	pkill -f "data-ingestor/main.py" || true
	@echo "✅ All services stopped"

# 데이터베이스 초기화
init-db:
	@echo "📊 Initializing database..."
	python scripts/init_local_db.py
	@echo "✅ Database initialization completed"

# 로그 확인
logs:
	docker-compose logs -f

# 데이터베이스 상태 확인
db-status:
	@echo "📊 Database Status:"
	@echo "1. Currency count:"
	@docker-compose exec mysql mysql -u currency_user -ppassword currency_db -e "SELECT COUNT(*) as currency_count FROM currencies;" 2>/dev/null || echo "❌ MySQL query failed"
	@echo "2. Exchange rate history count:"
	@docker-compose exec mysql mysql -u currency_user -ppassword currency_db -e "SELECT COUNT(*) as history_count FROM exchange_rate_history;" 2>/dev/null || echo "❌ MySQL query failed"
	@echo "3. Redis keys:"
	@docker-compose exec redis redis-cli keys "rate:*" 2>/dev/null | wc -l || echo "❌ Redis query failed"

# 로그 확인
logs:
	docker-compose logs -f

# 특정 서비스 로그
logs-currency:
	docker-compose logs -f currency-service

logs-ranking:
	docker-compose logs -f ranking-service

logs-history:
	docker-compose logs -f history-service

logs-ingestor:
	docker-compose logs -f data-ingestor

logs-mysql:
	docker-compose logs -f mysql

logs-localstack:
	docker-compose logs -f localstack

# 전체 시스템 상태 확인
status:
	@echo "=== Currency Travel Service Status ==="
	@echo "Docker Containers:"
	@docker-compose ps
	@echo ""
	@echo "Service Health:"
	@make init-check
	@echo ""
	@echo "Database Status:"
	@make db-status

# 모니터링 대시보드 정보
monitor:
	@echo "📊 Monitoring Dashboards:"
	@echo "  - Kafka UI: http://localhost:8081"
	@echo "  - LocalStack Dashboard: http://localhost:4566"
	@echo "  - Currency Service Health: http://localhost:8001/health"
	@echo "  - Ranking Service Health: http://localhost:8002/health"
	@echo "  - History Service Health: http://localhost:8003/health"