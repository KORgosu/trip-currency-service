# History Service 상세 문서

## 1. 서비스 개요

**History Service**는 환율의 과거 데이터 조회 및 분석을 담당하는 마이크로서비스입니다. Aurora 데이터베이스에 저장된 환율 이력을 기반으로 차트용 데이터와 통계 분석 결과를 제공합니다.

### 1.1 주요 기능
- 기간별 환율 변동 이력 조회 (1주/1개월/6개월)
- 환율 차트용 시계열 데이터 제공
- 환율 통계 분석 (평균, 최고, 최저, 변동률)
- 환율 예측 트렌드 분석
- 대용량 이력 데이터 효율적 조회

### 1.2 기술 스택
- **런타임**: AWS Lambda (Python 3.11)
- **프레임워크**: FastAPI
- **데이터베이스**: Amazon Aurora (MySQL 호환)
- **캐싱**: Amazon ElastiCache for Redis
- **배포**: AWS Lambda + API Gateway

## 2. 아키텍처

```
[사용자 요청] 
    ↓
[API Gateway] 
    ↓
[History Service Lambda]
    ↓
[Redis Cache] ← 캐시된 차트 데이터
    ↓ (캐시 미스 시)
[Aurora DB] ← 이력 데이터 조회
    ↓
[데이터 집계 & 분석]
    ↓
[응답 반환 & 캐시 저장]
```

### 2.1 데이터 플로우
1. 사용자가 환율 이력 조회 요청
2. API Gateway가 History Service Lambda 호출
3. Redis에서 캐시된 차트 데이터 확인
4. 캐시 미스 시 Aurora DB에서 원본 데이터 조회
5. 데이터 집계 및 통계 계산
6. 결과를 캐시에 저장하고 응답 반환

## 3. API 명세

### 3.1 기간별 환율 이력 조회
```http
GET /api/v1/history?period=1m&target=USD&base=KRW
```

**요청 파라미터:**
- `period` (필수): 1w, 1m, 6m
- `target` (필수): 대상 통화 코드 (USD, JPY, EUR 등)
- `base` (선택): 기준 통화 코드 (기본값: KRW)

**응답 예시:**
```json
{
  "base": "KRW",
  "target": "USD",
  "period": "1m",
  "data_points": 30,
  "results": [
    {
      "date": "2025-08-05",
      "rate": 1380.5,
      "change": 2.3,
      "change_percent": 0.17
    },
    {
      "date": "2025-08-06", 
      "rate": 1382.1,
      "change": 1.6,
      "change_percent": 0.12
    }
  ],
  "statistics": {
    "average": 1385.2,
    "min": 1375.8,
    "max": 1395.6,
    "volatility": 0.85,
    "trend": "stable"
  }
}
```

### 3.2 환율 통계 분석
```http
GET /api/v1/history/stats?target=USD&period=6m
```

**응답 예시:**
```json
{
  "currency_pair": "KRW/USD",
  "period": "6m",
  "analysis_date": "2025-09-05T10:30:00Z",
  "statistics": {
    "current_rate": 1392.4,
    "period_average": 1385.2,
    "period_min": 1365.8,
    "period_max": 1405.6,
    "total_change": 26.6,
    "total_change_percent": 1.94,
    "volatility_index": 2.15,
    "trend_direction": "upward",
    "support_level": 1375.0,
    "resistance_level": 1400.0
  },
  "monthly_breakdown": [
    {
      "month": "2025-03",
      "average": 1378.5,
      "min": 1365.8,
      "max": 1385.2,
      "change_percent": -0.85
    }
  ]
}
```

### 3.3 환율 비교 분석
```http
GET /api/v1/history/compare?targets=USD,JPY,EUR&period=1m
```

**응답 예시:**
```json
{
  "base": "KRW",
  "period": "1m",
  "comparison": [
    {
      "currency": "USD",
      "current_rate": 1392.4,
      "change_percent": 1.2,
      "volatility": 0.85,
      "performance_rank": 2
    },
    {
      "currency": "JPY", 
      "current_rate": 9.46,
      "change_percent": -0.5,
      "volatility": 1.12,
      "performance_rank": 3
    }
  ],
  "correlation_matrix": {
    "USD_JPY": 0.75,
    "USD_EUR": 0.68,
    "JPY_EUR": 0.82
  }
}
```

## 4. 데이터베이스 스키마

### 4.1 환율 이력 테이블
```sql
-- 환율 이력 메인 테이블
CREATE TABLE exchange_rate_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    currency_name VARCHAR(50) NOT NULL,
    deal_base_rate DECIMAL(18, 4) NOT NULL,
    tts DECIMAL(18, 4),  -- 송금 보낼 때
    ttb DECIMAL(18, 4),  -- 받을 때
    source VARCHAR(50) NOT NULL,
    recorded_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_currency_date (currency_code, recorded_at DESC),
    INDEX idx_recorded_at (recorded_at DESC),
    INDEX idx_currency_source (currency_code, source)
);

-- 일별 집계 테이블 (성능 최적화용)
CREATE TABLE daily_exchange_rates (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_rate DECIMAL(18, 4) NOT NULL,
    close_rate DECIMAL(18, 4) NOT NULL,
    high_rate DECIMAL(18, 4) NOT NULL,
    low_rate DECIMAL(18, 4) NOT NULL,
    avg_rate DECIMAL(18, 4) NOT NULL,
    data_points INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_currency_date (currency_code, trade_date),
    INDEX idx_trade_date (trade_date DESC)
);
```

### 4.2 Redis 캐시 구조
```
# 차트 데이터 캐시
Key: chart:{period}:{base}:{target}
TTL: 1800초 (30분)
Value: JSON 형태의 차트 데이터

# 통계 데이터 캐시  
Key: stats:{period}:{currency}
TTL: 3600초 (1시간)
Value: JSON 형태의 통계 분석 결과

# 비교 분석 캐시
Key: compare:{period}:{currencies_hash}
TTL: 1800초 (30분)
Value: JSON 형태의 비교 분석 결과
```

## 5. 데이터 처리 로직

### 5.1 이력 데이터 조회
```python
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

class HistoryDataProvider:
    def __init__(self):
        self.db_connection = get_aurora_connection()
        self.redis_client = get_redis_client()
    
    async def get_exchange_rate_history(
        self, 
        target_currency: str,
        base_currency: str = "KRW",
        period: str = "1m"
    ) -> Dict:
        """환율 이력 데이터 조회"""
        
        # 캐시 확인
        cache_key = f"chart:{period}:{base_currency}:{target_currency}"
        cached_data = await self.redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # DB에서 데이터 조회
        start_date, end_date = self.calculate_date_range(period)
        
        # 성능 최적화: 기간에 따라 다른 테이블 사용
        if period in ['1w', '1m']:
            # 상세 데이터 사용
            query = """
                SELECT 
                    DATE(recorded_at) as date,
                    AVG(deal_base_rate) as rate,
                    MIN(deal_base_rate) as min_rate,
                    MAX(deal_base_rate) as max_rate,
                    COUNT(*) as data_points
                FROM exchange_rate_history 
                WHERE currency_code = %s 
                    AND recorded_at BETWEEN %s AND %s
                GROUP BY DATE(recorded_at)
                ORDER BY date ASC
            """
        else:
            # 집계 테이블 사용 (6개월 이상)
            query = """
                SELECT 
                    trade_date as date,
                    close_rate as rate,
                    low_rate as min_rate,
                    high_rate as max_rate,
                    data_points
                FROM daily_exchange_rates
                WHERE currency_code = %s 
                    AND trade_date BETWEEN %s AND %s
                ORDER BY trade_date ASC
            """
        
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute(query, (target_currency, start_date, end_date))
        raw_data = cursor.fetchall()
        
        # 데이터 처리 및 분석
        processed_data = self.process_historical_data(raw_data)
        
        # 캐시에 저장
        await self.redis_client.setex(
            cache_key, 
            1800,  # 30분 TTL
            json.dumps(processed_data)
        )
        
        return processed_data
    
    def process_historical_data(self, raw_data: List[Dict]) -> Dict:
        """이력 데이터 처리 및 분석"""
        if not raw_data:
            return {"results": [], "statistics": {}}
        
        df = pd.DataFrame(raw_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 변동률 계산
        df['change'] = df['rate'].diff()
        df['change_percent'] = (df['change'] / df['rate'].shift(1)) * 100
        
        # 통계 계산
        statistics = {
            "average": float(df['rate'].mean()),
            "min": float(df['rate'].min()),
            "max": float(df['rate'].max()),
            "volatility": float(df['change_percent'].std()),
            "trend": self.calculate_trend(df['rate'].values),
            "data_points": len(df)
        }
        
        # 결과 포맷팅
        results = []
        for _, row in df.iterrows():
            results.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "rate": float(row['rate']),
                "change": float(row['change']) if pd.notna(row['change']) else 0,
                "change_percent": float(row['change_percent']) if pd.notna(row['change_percent']) else 0
            })
        
        return {
            "results": results,
            "statistics": statistics
        }
```

### 5.2 통계 분석 로직
```python
class StatisticalAnalyzer:
    @staticmethod
    def calculate_trend(rates: np.array) -> str:
        """트렌드 방향 계산"""
        if len(rates) < 2:
            return "insufficient_data"
        
        # 선형 회귀로 트렌드 계산
        x = np.arange(len(rates))
        slope, _ = np.polyfit(x, rates, 1)
        
        if slope > 0.1:
            return "upward"
        elif slope < -0.1:
            return "downward"
        else:
            return "stable"
    
    @staticmethod
    def calculate_support_resistance(rates: np.array) -> tuple:
        """지지선/저항선 계산"""
        if len(rates) < 10:
            return None, None
        
        # 최근 데이터의 분위수 기반 계산
        recent_rates = rates[-30:]  # 최근 30일
        support = np.percentile(recent_rates, 25)
        resistance = np.percentile(recent_rates, 75)
        
        return float(support), float(resistance)
    
    @staticmethod
    def calculate_volatility_index(rates: np.array) -> float:
        """변동성 지수 계산"""
        if len(rates) < 2:
            return 0.0
        
        returns = np.diff(rates) / rates[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # 연환산
        
        return float(volatility * 100)  # 백분율로 변환
```

### 5.3 비교 분석 로직
```python
class ComparisonAnalyzer:
    async def compare_currencies(
        self, 
        currencies: List[str], 
        period: str = "1m"
    ) -> Dict:
        """다중 통화 비교 분석"""
        
        comparison_data = []
        correlation_data = {}
        
        # 각 통화별 데이터 수집
        for currency in currencies:
            history_data = await self.get_exchange_rate_history(
                currency, period=period
            )
            
            if history_data['results']:
                rates = [item['rate'] for item in history_data['results']]
                
                comparison_data.append({
                    "currency": currency,
                    "current_rate": rates[-1],
                    "change_percent": self.calculate_period_change(rates),
                    "volatility": history_data['statistics']['volatility'],
                    "rates": rates
                })
        
        # 성과 순위 계산
        comparison_data.sort(key=lambda x: x['change_percent'], reverse=True)
        for i, item in enumerate(comparison_data, 1):
            item['performance_rank'] = i
            del item['rates']  # 응답에서 제외
        
        # 상관관계 계산
        if len(currencies) > 1:
            correlation_matrix = self.calculate_correlation_matrix(
                [item['rates'] for item in comparison_data]
            )
        
        return {
            "comparison": comparison_data,
            "correlation_matrix": correlation_matrix
        }
    
    def calculate_correlation_matrix(self, rate_series: List[List]) -> Dict:
        """통화 간 상관관계 계산"""
        correlations = {}
        
        for i in range(len(rate_series)):
            for j in range(i + 1, len(rate_series)):
                corr = np.corrcoef(rate_series[i], rate_series[j])[0, 1]
                key = f"{currencies[i]}_{currencies[j]}"
                correlations[key] = float(corr)
        
        return correlations
```

## 6. 성능 최적화

### 6.1 데이터베이스 최적화
```sql
-- 파티셔닝으로 대용량 데이터 처리 최적화
ALTER TABLE exchange_rate_history 
PARTITION BY RANGE (YEAR(recorded_at)) (
    PARTITION p2023 VALUES LESS THAN (2024),
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

-- 커버링 인덱스로 조회 성능 향상
CREATE INDEX idx_currency_date_rate 
ON exchange_rate_history (currency_code, recorded_at DESC, deal_base_rate);
```

### 6.2 캐싱 전략
```python
class CacheManager:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cache_ttl = {
            "1w": 900,   # 15분
            "1m": 1800,  # 30분  
            "6m": 3600   # 1시간
        }
    
    async def get_or_calculate(self, cache_key: str, calculation_func, ttl: int):
        """캐시 우선 조회 또는 계산"""
        cached_result = await self.redis_client.get(cache_key)
        
        if cached_result:
            return json.loads(cached_result)
        
        # 캐시 미스 시 계산
        result = await calculation_func()
        
        # 결과 캐싱
        await self.redis_client.setex(cache_key, ttl, json.dumps(result))
        
        return result
```

## 7. 환경 설정

### 7.1 환경 변수
```bash
# Aurora 연결 정보
AURORA_ENDPOINT=your-aurora-cluster.cluster-xxx.ap-northeast-2.rds.amazonaws.com
AURORA_PORT=3306
AURORA_DATABASE=currency_history
AURORA_USERNAME=history_user
AURORA_PASSWORD_PARAM=/history-service/db/password

# Redis 연결 정보
REDIS_ENDPOINT=your-redis-cluster.cache.amazonaws.com
REDIS_PORT=6379

# 성능 설정
DB_CONNECTION_POOL_SIZE=10
CACHE_DEFAULT_TTL=1800
MAX_QUERY_RESULTS=1000
```

### 7.2 Lambda 함수 설정
```yaml
# history-service-config.yaml
FunctionName: history-service
Runtime: python3.11
Handler: main.lambda_handler
MemorySize: 1024
Timeout: 60
Environment:
  Variables:
    AURORA_ENDPOINT: !Ref AuroraEndpoint
    REDIS_ENDPOINT: !Ref RedisEndpoint
ReservedConcurrencyLimit: 50
```

## 8. 모니터링 및 알림

### 8.1 성능 메트릭
```python
class PerformanceMonitor:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    def record_query_performance(self, query_type: str, duration_ms: int):
        """쿼리 성능 메트릭 기록"""
        self.cloudwatch.put_metric_data(
            Namespace='HistoryService',
            MetricData=[
                {
                    'MetricName': 'QueryDuration',
                    'Dimensions': [
                        {'Name': 'QueryType', 'Value': query_type}
                    ],
                    'Value': duration_ms,
                    'Unit': 'Milliseconds'
                }
            ]
        )
```

### 8.2 알림 설정
```yaml
# history-service-alarms.yaml
SlowQueryAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: history-service-slow-query
    MetricName: QueryDuration
    Namespace: HistoryService
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 5000  # 5초
    ComparisonOperator: GreaterThanThreshold

CacheHitRateAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: history-service-low-cache-hit-rate
    MetricName: CacheHitRate
    Threshold: 70  # 70% 미만
    ComparisonOperator: LessThanThreshold
```

## 9. 보안 및 최적화

### 9.1 쿼리 보안
```python
def validate_query_parameters(period: str, currency: str) -> bool:
    """쿼리 파라미터 검증"""
    valid_periods = ['1w', '1m', '6m']
    valid_currencies = ['USD', 'JPY', 'EUR', 'GBP', 'CNY']
    
    if period not in valid_periods:
        raise ValueError(f"Invalid period: {period}")
    
    if not re.match(r'^[A-Z]{3}$', currency):
        raise ValueError(f"Invalid currency code: {currency}")
    
    return True
```

### 9.2 리소스 제한
```python
# 대용량 쿼리 방지
MAX_QUERY_RANGE_DAYS = 365
MAX_RESULT_ROWS = 1000

def validate_query_scope(start_date: datetime, end_date: datetime):
    """쿼리 범위 검증"""
    if (end_date - start_date).days > MAX_QUERY_RANGE_DAYS:
        raise ValueError("Query range too large")
```