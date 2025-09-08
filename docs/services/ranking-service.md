# Ranking Service 상세 문서

## 1. 서비스 개요

**Ranking Service**는 사용자의 여행지 선택 기록을 수집하고, 인기 여행지 랭킹을 제공하는 마이크로서비스입니다. 실시간 사용자 활동을 DynamoDB에 저장하고 미리 계산된 랭킹 결과를 빠르게 제공합니다.

### 1.1 주요 기능
- 사용자 여행지 선택 기록 수집
- 실시간 인기 여행지 랭킹 제공
- 기간별 랭킹 조회 (일간/주간/월간)
- 랭킹 변동 추이 분석

### 1.2 기술 스택
- **런타임**: AWS Lambda (Python 3.11)
- **프레임워크**: FastAPI
- **데이터베이스**: Amazon DynamoDB (Global Tables)
- **메시징**: Amazon SQS
- **배포**: AWS Lambda + API Gateway

## 2. 아키텍처

```
[사용자 선택] 
    ↓
[API Gateway] 
    ↓
[Ranking Service Lambda]
    ↓
[DynamoDB] ← 선택 기록 저장
    ↓
[SQS] ← 랭킹 계산 이벤트
    ↓
[Ranking Calculator Lambda] ← 주기적 실행
    ↓
[DynamoDB] ← 랭킹 결과 저장
```

### 2.1 데이터 플로우
1. 사용자가 국가 선택
2. API Gateway가 Ranking Service Lambda 호출
3. 선택 기록을 DynamoDB에 저장
4. SQS로 랭킹 계산 이벤트 발송
5. 별도 Lambda가 주기적으로 랭킹 계산
6. 계산된 랭킹을 DynamoDB에 저장

## 3. API 명세

### 3.1 여행지 선택 기록
```http
POST /api/v1/rankings/selections
Content-Type: application/json

{
  "user_id": "anonymous-uuid-123",
  "country_code": "JP",
  "session_id": "sess_abc123"
}
```

**응답 예시:**
```json
{
  "status": "success",
  "message": "Selection recorded successfully",
  "selection_id": "sel_20250905_123456"
}
```

### 3.2 인기 여행지 랭킹 조회
```http
GET /api/v1/rankings?period=daily&limit=10
```

**요청 파라미터:**
- `period` (필수): daily, weekly, monthly
- `limit` (선택): 결과 개수 (기본값: 10)

**응답 예시:**
```json
{
  "period": "daily",
  "last_updated": "2025-09-05T10:30:00Z",
  "ranking": [
    {
      "rank": 1,
      "country_code": "JP",
      "country_name": "일본",
      "score": 1502,
      "change": "UP",
      "change_value": 2
    },
    {
      "rank": 2,
      "country_code": "US",
      "country_name": "미국",
      "score": 987,
      "change": "DOWN",
      "change_value": -1
    }
  ]
}
```

### 3.3 국가별 선택 통계
```http
GET /api/v1/rankings/stats/{country_code}?period=7d
```

**응답 예시:**
```json
{
  "country_code": "JP",
  "country_name": "일본",
  "period": "7d",
  "total_selections": 10547,
  "daily_breakdown": [
    {"date": "2025-09-05", "count": 1502},
    {"date": "2025-09-04", "count": 1456}
  ]
}
```

## 4. 데이터베이스 스키마

### 4.1 사용자 선택 기록 테이블
```
Table: travel_destination_selections

Partition Key: selection_date (String) - "2025-09-05"
Sort Key: selection_timestamp_userid (String) - "20250905103000_uuid123"

Attributes:
- country_code (String): "JP"
- country_name (String): "일본"
- user_id (String): "anonymous-uuid-123"
- session_id (String): "sess_abc123"
- ip_address (String): "192.168.1.1" (해시화)
- user_agent (String): "Mozilla/5.0..." (해시화)
- created_at (String): "2025-09-05T10:30:00Z"

GSI: country-date-index
- Partition Key: country_code
- Sort Key: selection_date
```

### 4.2 랭킹 결과 테이블
```
Table: RankingResults

Partition Key: period (String) - "daily", "weekly", "monthly"

Attributes:
- ranking_data (List): [
    {
      "rank": 1,
      "country_code": "JP",
      "country_name": "일본",
      "score": 1502,
      "change": "UP",
      "change_value": 2
    }
  ]
- last_updated (String): "2025-09-05T10:30:00Z"
- calculation_metadata (Map): {
    "total_records": 50000,
    "calculation_time_ms": 1250,
    "data_range": "2025-09-05"
  }
```

## 5. 랭킹 계산 로직

### 5.1 일간 랭킹 계산
```python
def calculate_daily_ranking():
    """일간 랭킹 계산 (매일 자정 실행)"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # DynamoDB에서 오늘 선택 기록 조회
    response = dynamodb.query(
        TableName='travel_destination_selections',
        KeyConditionExpression='selection_date = :date',
        ExpressionAttributeValues={':date': today}
    )
    
    # 국가별 선택 횟수 집계
    country_counts = {}
    for item in response['Items']:
        country = item['country_code']
        country_counts[country] = country_counts.get(country, 0) + 1
    
    # 순위 계산 및 변동 추이 분석
    ranking = calculate_rank_changes(country_counts)
    
    # 결과를 DynamoDB에 저장
    save_ranking_result('daily', ranking)
```

### 5.2 순위 변동 계산
```python
def calculate_rank_changes(current_counts):
    """이전 랭킹과 비교하여 순위 변동 계산"""
    # 이전 랭킹 조회
    previous_ranking = get_previous_ranking('daily')
    previous_ranks = {item['country_code']: item['rank'] 
                     for item in previous_ranking}
    
    # 현재 랭킹 생성
    sorted_countries = sorted(current_counts.items(), 
                            key=lambda x: x[1], reverse=True)
    
    ranking = []
    for i, (country_code, score) in enumerate(sorted_countries, 1):
        previous_rank = previous_ranks.get(country_code, None)
        
        if previous_rank is None:
            change = "NEW"
            change_value = 0
        elif previous_rank > i:
            change = "UP"
            change_value = previous_rank - i
        elif previous_rank < i:
            change = "DOWN"
            change_value = previous_rank - i
        else:
            change = "SAME"
            change_value = 0
        
        ranking.append({
            "rank": i,
            "country_code": country_code,
            "country_name": get_country_name(country_code),
            "score": score,
            "change": change,
            "change_value": change_value
        })
    
    return ranking
```

## 6. 환경 설정

### 6.1 환경 변수
```bash
# DynamoDB 테이블
SELECTIONS_TABLE=travel_destination_selections
RANKINGS_TABLE=RankingResults

# SQS 큐
RANKING_CALCULATION_QUEUE=ranking-calculation-queue

# 랭킹 설정
MAX_RANKING_SIZE=50
CALCULATION_SCHEDULE=0 0 * * * # 매일 자정

# 보안 설정
RATE_LIMIT_PER_IP=100
RATE_LIMIT_WINDOW=3600
```

### 6.2 Lambda 함수 설정
```yaml
# ranking-service-config.yaml
Functions:
  RankingService:
    FunctionName: ranking-service
    Runtime: python3.11
    Handler: main.lambda_handler
    MemorySize: 256
    Timeout: 30
    
  RankingCalculator:
    FunctionName: ranking-calculator
    Runtime: python3.11
    Handler: calculator.lambda_handler
    MemorySize: 1024
    Timeout: 300
    Events:
      - Schedule: rate(1 hour)
```

## 7. 배포 가이드

### 7.1 DynamoDB 테이블 생성
```bash
# 선택 기록 테이블 생성
aws dynamodb create-table \
  --table-name travel_destination_selections \
  --attribute-definitions \
    AttributeName=selection_date,AttributeType=S \
    AttributeName=selection_timestamp_userid,AttributeType=S \
    AttributeName=country_code,AttributeType=S \
  --key-schema \
    AttributeName=selection_date,KeyType=HASH \
    AttributeName=selection_timestamp_userid,KeyType=RANGE \
  --global-secondary-indexes \
    IndexName=country-date-index,KeySchema=[{AttributeName=country_code,KeyType=HASH},{AttributeName=selection_date,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5} \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# 랭킹 결과 테이블 생성
aws dynamodb create-table \
  --table-name RankingResults \
  --attribute-definitions AttributeName=period,AttributeType=S \
  --key-schema AttributeName=period,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### 7.2 Lambda 배포
```bash
# 패키지 생성
zip -r ranking-service.zip . -x "*.git*" "tests/*" "*.md"

# Lambda 함수 배포
aws lambda create-function \
  --function-name ranking-service \
  --runtime python3.11 \
  --role arn:aws:iam::account:role/lambda-execution-role \
  --handler main.lambda_handler \
  --zip-file fileb://ranking-service.zip
```

## 8. 모니터링 및 성능

### 8.1 주요 메트릭
- 선택 기록 처리량 (TPS)
- 랭킹 계산 소요 시간
- DynamoDB 읽기/쓰기 용량 사용률
- API 응답 시간

### 8.2 알림 설정
```yaml
# ranking-service-alarms.yaml
SelectionVolumeAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: high-selection-volume
    MetricName: Invocations
    Threshold: 1000
    ComparisonOperator: GreaterThanThreshold
    
RankingCalculationFailure:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: ranking-calculation-failure
    MetricName: Errors
    Threshold: 1
    ComparisonOperator: GreaterThanOrEqualToThreshold
```

## 9. 보안 및 제한사항

### 9.1 Rate Limiting
```python
def check_rate_limit(ip_address):
    """IP별 요청 제한 확인"""
    key = f"rate_limit:{ip_address}"
    current_count = redis.get(key) or 0
    
    if int(current_count) >= RATE_LIMIT_PER_IP:
        raise HTTPException(429, "Too Many Requests")
    
    redis.incr(key)
    redis.expire(key, RATE_LIMIT_WINDOW)
```

### 9.2 데이터 검증
```python
def validate_selection_request(data):
    """선택 요청 데이터 검증"""
    required_fields = ['user_id', 'country_code']
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    if not is_valid_country_code(data['country_code']):
        raise ValueError("Invalid country code")
    
    if len(data['user_id']) > 100:
        raise ValueError("User ID too long")
```