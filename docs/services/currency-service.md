# Currency Service 상세 문서

## 1. 서비스 개요

**Currency Service**는 실시간 환율 정보 조회를 담당하는 마이크로서비스입니다. Redis 캐시에서 최신 환율 데이터를 빠르게 조회하여 사용자에게 제공합니다.

### 1.1 주요 기능
- 최신 환율 정보 조회 (Redis 캐시 기반)
- 다중 통화 동시 조회 지원
- 물가 지수 계산 (빅맥/스타벅스 지수)
- 캐시 미스 시 Aurora DB 폴백

### 1.2 기술 스택
- **런타임**: AWS Lambda (Python 3.11)
- **프레임워크**: FastAPI
- **캐시**: Amazon ElastiCache for Redis
- **데이터베이스**: Amazon Aurora (폴백용)
- **배포**: AWS Lambda + API Gateway

## 2. 아키텍처

```
[사용자 요청] 
    ↓
[API Gateway] 
    ↓
[Currency Service Lambda]
    ↓
[ElastiCache Redis] ← 캐시 히트
    ↓ (캐시 미스 시)
[Aurora DB] ← 폴백 조회
```

### 2.1 데이터 플로우
1. 사용자가 환율 조회 요청
2. API Gateway가 Currency Service Lambda 호출
3. Redis에서 최신 환율 데이터 조회
4. 캐시 미스 시 Aurora DB에서 조회
5. 결과를 JSON 형태로 반환

## 3. API 명세

### 3.1 최신 환율 조회
```http
GET /api/v1/currencies/latest?symbols=USD,JPY,EUR
```

**요청 파라미터:**
- `symbols` (선택): 쉼표로 구분된 통화 코드

**응답 예시:**
```json
{
  "base": "KRW",
  "timestamp": 1757082445,
  "rates": {
    "USD": 1392.4,
    "JPY": 9.46,
    "EUR": 1456.8
  }
}
```

### 3.2 물가 지수 조회
```http
GET /api/v1/currencies/price-index?country=JP
```

**응답 예시:**
```json
{
  "country_code": "JP",
  "bigmac_index": 85.2,
  "starbucks_index": 92.1,
  "composite_index": 88.1,
  "last_updated": "2025-09-05T10:30:00Z"
}
```

## 4. 데이터베이스 스키마

### 4.1 Redis 캐시 구조
```
Key: rate:{currency_code}
TTL: 600초 (10분)

Hash Fields:
- currency_name: "미국 달러"
- deal_base_rate: "1392.4"
- tts: "1395.2"
- last_updated_at: "2025-09-05T10:30:00Z"
```

### 4.2 Aurora 폴백 테이블
```sql
-- 최신 환율 조회용 뷰
CREATE VIEW latest_exchange_rates AS
SELECT 
    currency_code,
    currency_name,
    deal_base_rate,
    recorded_at
FROM exchange_rate_history 
WHERE recorded_at = (
    SELECT MAX(recorded_at) 
    FROM exchange_rate_history AS sub 
    WHERE sub.currency_code = exchange_rate_history.currency_code
);
```

## 5. 환경 설정

### 5.1 환경 변수
```bash
# Redis 연결 정보
REDIS_ENDPOINT=your-redis-cluster.cache.amazonaws.com
REDIS_PORT=6379

# Aurora 연결 정보 (폴백용)
DB_HOST=your-aurora-cluster.cluster-xxx.ap-northeast-2.rds.amazonaws.com
DB_NAME=currency_db
DB_USER=currency_user
DB_PASSWORD_PARAM=/currency-service/db/password

# 캐시 설정
CACHE_TTL=600
DEFAULT_CURRENCIES=USD,JPY,EUR,GBP,CNY
```

### 5.2 Lambda 함수 설정
```yaml
# lambda-config.yaml
FunctionName: currency-service
Runtime: python3.11
Handler: main.lambda_handler
MemorySize: 512
Timeout: 30
Environment:
  Variables:
    REDIS_ENDPOINT: !Ref RedisEndpoint
    DB_HOST: !Ref AuroraEndpoint
```

## 6. 배포 가이드

### 6.1 로컬 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# 로컬 서버 실행
uvicorn main:app --reload --port 8000

# 테스트
curl http://localhost:8000/api/v1/currencies/latest
```

### 6.2 Lambda 배포
```bash
# 패키지 생성
zip -r currency-service.zip . -x "*.git*" "tests/*" "*.md"

# Lambda 함수 업데이트
aws lambda update-function-code \
  --function-name currency-service \
  --zip-file fileb://currency-service.zip
```

## 7. 모니터링 및 알림

### 7.1 CloudWatch 메트릭
- Lambda 실행 시간
- 에러율
- Redis 연결 실패율
- Aurora 폴백 호출 빈도

### 7.2 알림 설정
```yaml
# cloudwatch-alarms.yaml
CurrencyServiceErrorRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: currency-service-error-rate
    MetricName: Errors
    Threshold: 5
    ComparisonOperator: GreaterThanThreshold
    EvaluationPeriods: 2
```

## 8. 성능 최적화

### 8.1 캐시 전략
- Redis 캐시 우선 조회
- 캐시 미스 시에만 DB 조회
- 배치 업데이트로 캐시 워밍

### 8.2 Lambda 최적화
- 연결 풀링으로 DB 연결 재사용
- 메모리 크기 최적화 (512MB)
- 콜드 스타트 최소화

## 9. 보안 고려사항

### 9.1 네트워크 보안
- VPC 내부 통신
- Security Group으로 포트 제한
- Redis AUTH 활성화

### 9.2 데이터 보안
- Parameter Store로 민감 정보 관리
- IAM 역할 기반 권한 제어
- 전송 중 암호화 (TLS)