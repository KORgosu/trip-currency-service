# 의존성 분석 및 테스트 가이드

## 📋 의존성 분석

### 🔍 현재 의존성 상태

#### ✅ 핵심 의존성 (정상)
- **FastAPI 0.104.1**: 웹 프레임워크
- **Uvicorn 0.24.0**: ASGI 서버
- **Pydantic 2.5.0**: 데이터 검증
- **aioredis 2.0.1**: Redis 비동기 클라이언트
- **aiomysql 0.2.0**: MySQL 비동기 클라이언트
- **boto3 1.34.0**: AWS SDK
- **aiokafka 0.9.0**: Kafka 비동기 클라이언트

#### ⚠️ 버전 호환성 주의사항

1. **aioredis 2.x vs 1.x**
   - 2.x에서 API가 크게 변경됨
   - `from_url()` 메서드 사용 필요
   - 연결 방식 변경: `aioredis.from_url()` 사용

2. **Pydantic 2.x vs 1.x**
   - 설정 방식 변경: `model_config` 사용
   - 검증 방식 개선
   - 성능 향상

3. **FastAPI + Pydantic 호환성**
   - FastAPI 0.104.1은 Pydantic 2.x 완전 지원
   - 이전 버전 사용 시 호환성 문제 발생 가능

### 🔧 의존성 해결 방법

#### 1. Redis 클라이언트 업데이트
```python
# 기존 (asyncio-redis)
import asyncio_redis
conn = await asyncio_redis.Connection.create()

# 신규 (aioredis 2.x)
import aioredis
redis = aioredis.from_url("redis://localhost:6379")
```

#### 2. Pydantic 모델 업데이트
```python
# 기존 (Pydantic 1.x)
class Config:
    json_encoders = {...}

# 신규 (Pydantic 2.x)
model_config = ConfigDict(
    json_encoders={...}
)
```

## 🧪 테스트 전략

### 📊 테스트 레벨

#### 1. 단위 테스트 (Unit Tests)
- **범위**: 개별 함수/클래스
- **도구**: pytest, pytest-asyncio
- **위치**: `tests/test_*.py`

```bash
# 단위 테스트 실행
pytest tests/ -v

# 특정 서비스 테스트
pytest tests/test_currency_service.py -v

# 커버리지 포함
pytest tests/ --cov=services --cov-report=html
```

#### 2. 통합 테스트 (Integration Tests)
- **범위**: 서비스 간 연동
- **도구**: aiohttp, TestClient
- **위치**: `test_integration.py`

```bash
# 통합 테스트 실행 (서비스들이 실행된 상태에서)
python test_integration.py
```

#### 3. 시스템 테스트 (System Tests)
- **범위**: 전체 시스템 동작
- **도구**: Docker Compose
- **위치**: `test_simple.py`

```bash
# 시스템 테스트 실행
python test_simple.py
```

### 🔍 테스트 환경 설정

#### 1. 로컬 테스트 환경
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env

# 3. 데이터베이스 시작
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0

# 4. Redis 시작
docker run -d -p 6379:6379 redis:7-alpine

# 5. 테스트 실행
python test_simple.py
```

#### 2. Docker 테스트 환경
```bash
# 전체 환경 시작
make start

# 테스트 실행
make test

# 환경 정리
make clean
```

### 📈 테스트 커버리지 목표

#### 현재 커버리지
- **공통 모듈**: 85%+
- **Currency Service**: 80%+
- **Ranking Service**: 75%+
- **History Service**: 70%+
- **Data Ingestor**: 70%+

#### 테스트 우선순위
1. **Critical Path**: 환율 조회, 데이터 수집
2. **Business Logic**: 랭킹 계산, 통계 분석
3. **Error Handling**: 예외 처리, 장애 복구
4. **Performance**: 응답 시간, 처리량

### 🚀 CI/CD 테스트 파이프라인

#### GitHub Actions 예시
```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: password
          MYSQL_DATABASE: currency_db
        ports:
          - 3306:3306
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run unit tests
      run: |
        pytest tests/ -v --cov=services
    
    - name: Run integration tests
      run: |
        python test_integration.py
```

## 🔧 문제 해결 가이드

### ❌ 일반적인 문제들

#### 1. Redis 연결 실패
```
ConnectionError: Error 111 connecting to localhost:6379
```
**해결방법:**
```bash
# Redis 서버 시작
docker run -d -p 6379:6379 redis:7-alpine

# 연결 테스트
redis-cli ping
```

#### 2. MySQL 연결 실패
```
OperationalError: (2003, "Can't connect to MySQL server")
```
**해결방법:**
```bash
# MySQL 서버 시작
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0

# 연결 테스트
mysql -h localhost -u root -p
```

#### 3. 모듈 import 에러
```
ModuleNotFoundError: No module named 'shared'
```
**해결방법:**
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/services"

# 또는 sys.path 추가
import sys
sys.path.append('services')
```

#### 4. 비동기 테스트 에러
```
RuntimeError: There is no current event loop
```
**해결방법:**
```python
# pytest-asyncio 사용
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 🔍 디버깅 도구

#### 1. 로그 레벨 조정
```bash
# 디버그 모드
export LOG_LEVEL=DEBUG

# 특정 모듈만
export LOG_LEVEL=INFO
```

#### 2. 성능 프로파일링
```python
# 함수 실행 시간 측정
from shared.utils import PerformanceUtils

@PerformanceUtils.measure_time
async def slow_function():
    # 함수 로직
    pass
```

#### 3. 메모리 사용량 모니터링
```bash
# 메모리 사용량 확인
docker stats

# 프로세스별 메모리 사용량
ps aux --sort=-%mem | head
```

## 📊 성능 테스트

### 🎯 성능 목표
- **응답 시간**: < 200ms (95th percentile)
- **처리량**: > 1000 RPS
- **메모리 사용량**: < 512MB per service
- **CPU 사용률**: < 70% under load

### 🔧 성능 테스트 도구

#### 1. 부하 테스트 (Locust)
```python
from locust import HttpUser, task, between

class CurrencyServiceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_latest_rates(self):
        self.client.get("/api/v1/currencies/latest?symbols=USD,JPY")
    
    @task
    def get_currency_info(self):
        self.client.get("/api/v1/currencies/USD")
```

#### 2. 스트레스 테스트 (Artillery)
```yaml
config:
  target: 'http://localhost:8001'
  phases:
    - duration: 60
      arrivalRate: 10
    - duration: 120
      arrivalRate: 50
    - duration: 60
      arrivalRate: 100

scenarios:
  - name: "Currency API Test"
    requests:
      - get:
          url: "/api/v1/currencies/latest"
```

### 📈 모니터링 메트릭

#### 1. 애플리케이션 메트릭
- 요청 수 (RPS)
- 응답 시간 (P50, P95, P99)
- 에러율 (4xx, 5xx)
- 활성 연결 수

#### 2. 시스템 메트릭
- CPU 사용률
- 메모리 사용률
- 디스크 I/O
- 네트워크 I/O

#### 3. 데이터베이스 메트릭
- 연결 수
- 쿼리 실행 시간
- 캐시 히트율
- 락 대기 시간

## 🎯 테스트 자동화

### 🔄 지속적 테스트
1. **Pre-commit hooks**: 코드 품질 검사
2. **CI Pipeline**: 자동 테스트 실행
3. **CD Pipeline**: 배포 전 검증
4. **Monitoring**: 운영 환경 모니터링

### 📋 테스트 체크리스트
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 보안 테스트 통과
- [ ] 코드 커버리지 목표 달성
- [ ] 문서 업데이트 완료