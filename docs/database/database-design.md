# 데이터베이스 설계 문서

## 1. 데이터베이스 아키텍처 개요

여행 물가 비교 서비스는 **폴리글랏 퍼시스턴스(Polyglot Persistence)** 패턴을 적용하여 각 데이터의 특성과 접근 패턴에 최적화된 데이터베이스를 선택했습니다.

### 1.1 데이터베이스 구성
- **Amazon Aurora MySQL**: 환율 이력 데이터 (OLTP)
- **Amazon DynamoDB**: 사용자 활동 및 랭킹 데이터 (NoSQL)
- **Amazon ElastiCache Redis**: 실시간 캐시 데이터 (In-Memory)
- **Amazon S3**: 원본 데이터 백업 및 정적 파일 (Object Storage)

### 1.2 데이터 분류
```
┌─────────────────┬──────────────────┬─────────────────┬─────────────────┐
│   데이터 유형    │    접근 패턴      │   데이터베이스   │    서비스 사용   │
├─────────────────┼──────────────────┼─────────────────┼─────────────────┤
│ 환율 이력       │ 시계열 조회      │ Aurora MySQL    │ History Service │
│ 실시간 환율     │ 빠른 읽기        │ Redis Cache     │ Currency Service│
│ 사용자 선택     │ 대량 쓰기        │ DynamoDB        │ Ranking Service │
│ 랭킹 결과       │ 빠른 읽기        │ DynamoDB        │ Ranking Service │
│ 원본 데이터     │ 아카이브         │ S3              │ Data Ingestor   │
└─────────────────┴──────────────────┴─────────────────┴─────────────────┘
```

## 2. Aurora MySQL 설계

### 2.1 환율 이력 테이블
```sql
-- 환율 이력 메인 테이블
CREATE TABLE exchange_rate_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL COMMENT '통화 코드 (USD, JPY 등)',
    currency_name VARCHAR(50) NOT NULL COMMENT '통화명 (미국 달러, 일본 엔 등)',
    deal_base_rate DECIMAL(18, 4) NOT NULL COMMENT '매매 기준율',
    tts DECIMAL(18, 4) COMMENT '송금 보낼 때 환율',
    ttb DECIMAL(18, 4) COMMENT '받을 때 환율',
    source VARCHAR(50) NOT NULL COMMENT '데이터 소스 (BOK, Fed 등)',
    recorded_at DATETIME NOT NULL COMMENT '환율 기록 시각',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '레코드 생성 시각',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 인덱스
    INDEX idx_currency_date (currency_code, recorded_at DESC),
    INDEX idx_recorded_at (recorded_at DESC),
    INDEX idx_currency_source (currency_code, source),
    INDEX idx_created_at (created_at DESC)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='환율 변동 이력 데이터';

-- 파티셔닝 설정 (월별)
ALTER TABLE exchange_rate_history 
PARTITION BY RANGE (YEAR(recorded_at) * 100 + MONTH(recorded_at)) (
    PARTITION p202501 VALUES LESS THAN (202502),
    PARTITION p202502 VALUES LESS THAN (202503),
    PARTITION p202503 VALUES LESS THAN (202504),
    PARTITION p202504 VALUES LESS THAN (202505),
    PARTITION p202505 VALUES LESS THAN (202506),
    PARTITION p202506 VALUES LESS THAN (202507),
    PARTITION p202507 VALUES LESS THAN (202508),
    PARTITION p202508 VALUES LESS THAN (202509),
    PARTITION p202509 VALUES LESS THAN (202510),
    PARTITION p202510 VALUES LESS THAN (202511),
    PARTITION p202511 VALUES LESS THAN (202512),
    PARTITION p202512 VALUES LESS THAN (202601),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);
```

### 2.2 성능 최적화용 집계 테이블
```sql
-- 일별 환율 집계 테이블 (성능 최적화용)
CREATE TABLE daily_exchange_rates (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL COMMENT '거래일',
    open_rate DECIMAL(18, 4) NOT NULL COMMENT '시가',
    close_rate DECIMAL(18, 4) NOT NULL COMMENT '종가',
    high_rate DECIMAL(18, 4) NOT NULL COMMENT '최고가',
    low_rate DECIMAL(18, 4) NOT NULL COMMENT '최저가',
    avg_rate DECIMAL(18, 4) NOT NULL COMMENT '평균가',
    volume INT DEFAULT 0 COMMENT '데이터 포인트 수',
    volatility DECIMAL(8, 4) COMMENT '일일 변동성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 유니크 제약조건
    UNIQUE KEY uk_currency_date (currency_code, trade_date),
    
    -- 인덱스
    INDEX idx_trade_date (trade_date DESC),
    INDEX idx_currency_code (currency_code)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='일별 환율 집계 데이터';
```

### 2.3 통화 마스터 테이블
```sql
-- 통화 정보 마스터 테이블
CREATE TABLE currencies (
    currency_code VARCHAR(10) PRIMARY KEY,
    currency_name_ko VARCHAR(50) NOT NULL COMMENT '한글 통화명',
    currency_name_en VARCHAR(50) NOT NULL COMMENT '영문 통화명',
    country_code VARCHAR(3) NOT NULL COMMENT '국가 코드 (ISO 3166-1)',
    country_name_ko VARCHAR(50) NOT NULL COMMENT '한글 국가명',
    country_name_en VARCHAR(50) NOT NULL COMMENT '영문 국가명',
    symbol VARCHAR(10) COMMENT '통화 기호 ($, ¥ 등)',
    decimal_places TINYINT DEFAULT 2 COMMENT '소수점 자릿수',
    is_active BOOLEAN DEFAULT TRUE COMMENT '활성 상태',
    display_order INT DEFAULT 999 COMMENT '표시 순서',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_country_code (country_code),
    INDEX idx_display_order (display_order, is_active)
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci
  COMMENT='통화 정보 마스터';

-- 초기 데이터 삽입
INSERT INTO currencies (currency_code, currency_name_ko, currency_name_en, country_code, country_name_ko, country_name_en, symbol, display_order) VALUES
('USD', '미국 달러', 'US Dollar', 'US', '미국', 'United States', '$', 1),
('JPY', '일본 엔', 'Japanese Yen', 'JP', '일본', 'Japan', '¥', 2),
('EUR', '유로', 'Euro', 'EU', '유럽연합', 'European Union', '€', 3),
('GBP', '영국 파운드', 'British Pound', 'GB', '영국', 'United Kingdom', '£', 4),
('CNY', '중국 위안', 'Chinese Yuan', 'CN', '중국', 'China', '¥', 5),
('AUD', '호주 달러', 'Australian Dollar', 'AU', '호주', 'Australia', 'A$', 6),
('CAD', '캐나다 달러', 'Canadian Dollar', 'CA', '캐나다', 'Canada', 'C$', 7),
('CHF', '스위스 프랑', 'Swiss Franc', 'CH', '스위스', 'Switzerland', 'CHF', 8),
('HKD', '홍콩 달러', 'Hong Kong Dollar', 'HK', '홍콩', 'Hong Kong', 'HK$', 9),
('SGD', '싱가포르 달러', 'Singapore Dollar', 'SG', '싱가포르', 'Singapore', 'S$', 10);
```

### 2.4 뷰 및 저장 프로시저
```sql
-- 최신 환율 조회 뷰
CREATE VIEW v_latest_exchange_rates AS
SELECT 
    c.currency_code,
    c.currency_name_ko,
    c.currency_name_en,
    c.country_code,
    c.symbol,
    h.deal_base_rate,
    h.tts,
    h.ttb,
    h.source,
    h.recorded_at,
    h.created_at
FROM currencies c
INNER JOIN exchange_rate_history h ON c.currency_code = h.currency_code
INNER JOIN (
    SELECT 
        currency_code, 
        MAX(recorded_at) as max_recorded_at
    FROM exchange_rate_history 
    GROUP BY currency_code
) latest ON h.currency_code = latest.currency_code 
         AND h.recorded_at = latest.max_recorded_at
WHERE c.is_active = TRUE
ORDER BY c.display_order;

-- 일별 집계 데이터 생성 저장 프로시저
DELIMITER //
CREATE PROCEDURE sp_generate_daily_aggregates(IN target_date DATE)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- 기존 데이터 삭제 (재실행 시)
    DELETE FROM daily_exchange_rates WHERE trade_date = target_date;
    
    -- 일별 집계 데이터 생성
    INSERT INTO daily_exchange_rates (
        currency_code, trade_date, open_rate, close_rate, 
        high_rate, low_rate, avg_rate, volume, volatility
    )
    SELECT 
        currency_code,
        DATE(recorded_at) as trade_date,
        FIRST_VALUE(deal_base_rate) OVER (
            PARTITION BY currency_code, DATE(recorded_at) 
            ORDER BY recorded_at ASC 
            ROWS UNBOUNDED PRECEDING
        ) as open_rate,
        FIRST_VALUE(deal_base_rate) OVER (
            PARTITION BY currency_code, DATE(recorded_at) 
            ORDER BY recorded_at DESC 
            ROWS UNBOUNDED PRECEDING
        ) as close_rate,
        MAX(deal_base_rate) as high_rate,
        MIN(deal_base_rate) as low_rate,
        AVG(deal_base_rate) as avg_rate,
        COUNT(*) as volume,
        STDDEV(deal_base_rate) as volatility
    FROM exchange_rate_history 
    WHERE DATE(recorded_at) = target_date
    GROUP BY currency_code, DATE(recorded_at);
    
    COMMIT;
END //
DELIMITER ;
```

## 3. DynamoDB 설계

### 3.1 사용자 선택 기록 테이블
```json
{
  "TableName": "travel_destination_selections",
  "KeySchema": [
    {
      "AttributeName": "selection_date",
      "KeyType": "HASH"
    },
    {
      "AttributeName": "selection_timestamp_userid", 
      "KeyType": "RANGE"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "selection_date",
      "AttributeType": "S"
    },
    {
      "AttributeName": "selection_timestamp_userid",
      "AttributeType": "S"
    },
    {
      "AttributeName": "country_code",
      "AttributeType": "S"
    }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "country-date-index",
      "KeySchema": [
        {
          "AttributeName": "country_code",
          "KeyType": "HASH"
        },
        {
          "AttributeName": "selection_date",
          "KeyType": "RANGE"
        }
      ],
      "Projection": {
        "ProjectionType": "ALL"
      },
      "ProvisionedThroughput": {
        "ReadCapacityUnits": 5,
        "WriteCapacityUnits": 5
      }
    }
  ],
  "BillingMode": "ON_DEMAND",
  "StreamSpecification": {
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  }
}
```

**샘플 데이터:**
```json
{
  "selection_date": "2025-09-05",
  "selection_timestamp_userid": "20250905103045_uuid-12345",
  "country_code": "JP",
  "country_name": "일본",
  "user_id": "anonymous-uuid-12345",
  "session_id": "sess_abc123def456",
  "ip_address_hash": "sha256_hash_of_ip",
  "user_agent_hash": "sha256_hash_of_user_agent",
  "referrer": "https://google.com",
  "created_at": "2025-09-05T10:30:45Z",
  "ttl": 1767225045
}
```

### 3.2 랭킹 결과 테이블
```json
{
  "TableName": "RankingResults",
  "KeySchema": [
    {
      "AttributeName": "period",
      "KeyType": "HASH"
    }
  ],
  "AttributeDefinitions": [
    {
      "AttributeName": "period",
      "AttributeType": "S"
    }
  ],
  "BillingMode": "PROVISIONED",
  "ProvisionedThroughput": {
    "ReadCapacityUnits": 10,
    "WriteCapacityUnits": 2
  }
}
```

**샘플 데이터:**
```json
{
  "period": "daily",
  "ranking_data": [
    {
      "rank": 1,
      "country_code": "JP",
      "country_name": "일본",
      "score": 1502,
      "change": "UP",
      "change_value": 2,
      "percentage": 15.2
    },
    {
      "rank": 2,
      "country_code": "US", 
      "country_name": "미국",
      "score": 987,
      "change": "DOWN",
      "change_value": -1,
      "percentage": 10.1
    }
  ],
  "last_updated": "2025-09-05T10:30:00Z",
  "calculation_metadata": {
    "total_records": 9876,
    "calculation_time_ms": 1250,
    "data_range_start": "2025-09-05T00:00:00Z",
    "data_range_end": "2025-09-05T23:59:59Z",
    "algorithm_version": "v2.1"
  },
  "ttl": 1725638400
}
```

## 4. Redis 캐시 설계

### 4.1 환율 데이터 캐시
```
Key Pattern: rate:{currency_code}
TTL: 600초 (10분)
Data Type: Hash

Example:
Key: rate:USD
Fields:
  currency_name: "미국 달러"
  deal_base_rate: "1392.4"
  tts: "1420.85"
  ttb: "1363.95"
  source: "BOK"
  last_updated_at: "2025-09-05T10:30:00Z"
```

### 4.2 랭킹 데이터 캐시
```
Key Pattern: ranking:{period}
TTL: 300초 (5분)
Data Type: String (JSON)

Example:
Key: ranking:daily
Value: {
  "period": "daily",
  "ranking": [...],
  "last_updated": "2025-09-05T10:30:00Z"
}
```

### 4.3 차트 데이터 캐시
```
Key Pattern: chart:{period}:{base}:{target}
TTL: 1800초 (30분)
Data Type: String (JSON)

Example:
Key: chart:1m:KRW:USD
Value: {
  "base": "KRW",
  "target": "USD", 
  "period": "1m",
  "results": [...],
  "statistics": {...}
}
```

### 4.4 Redis 클러스터 설정
```yaml
# ElastiCache Redis 클러스터 설정
CacheCluster:
  Engine: redis
  CacheNodeType: cache.r6g.large
  NumCacheNodes: 3
  Port: 6379
  
  # 클러스터 모드 활성화
  ReplicationGroupDescription: "Currency Service Cache Cluster"
  NumNodeGroups: 3
  ReplicasPerNodeGroup: 1
  
  # 백업 설정
  SnapshotRetentionLimit: 7
  SnapshotWindow: "03:00-05:00"
  
  # 보안 설정
  AtRestEncryptionEnabled: true
  TransitEncryptionEnabled: true
  AuthToken: !Ref RedisAuthToken
```

## 5. 데이터 마이그레이션 전략

### 5.1 초기 데이터 로드
```sql
-- 환율 이력 데이터 초기 로드 (CSV 파일에서)
LOAD DATA LOCAL INFILE '/tmp/exchange_rate_history.csv'
INTO TABLE exchange_rate_history
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(currency_code, currency_name, deal_base_rate, tts, ttb, source, recorded_at);

-- 일별 집계 데이터 생성 (과거 1년)
CALL sp_generate_daily_aggregates('2024-01-01');
-- ... (각 날짜별로 실행)
```

### 5.2 DynamoDB 데이터 마이그레이션
```python
# scripts/migrate_dynamodb.py
import boto3
import json
from datetime import datetime, timedelta

def migrate_historical_selections():
    """과거 선택 기록 데이터 마이그레이션"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('travel_destination_selections')
    
    # 샘플 데이터 생성 (실제로는 기존 시스템에서 추출)
    sample_data = generate_sample_selections()
    
    with table.batch_writer() as batch:
        for item in sample_data:
            batch.put_item(Item=item)
    
    print(f"Migrated {len(sample_data)} selection records")

def generate_sample_selections():
    """샘플 선택 기록 데이터 생성"""
    countries = ['JP', 'US', 'EU', 'GB', 'CN', 'AU', 'CA']
    selections = []
    
    # 과거 30일간의 샘플 데이터
    for days_ago in range(30):
        date = datetime.now() - timedelta(days=days_ago)
        date_str = date.strftime('%Y-%m-%d')
        
        # 하루에 100-500개의 선택 기록
        daily_count = random.randint(100, 500)
        
        for i in range(daily_count):
            timestamp = date + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            
            selections.append({
                'selection_date': date_str,
                'selection_timestamp_userid': f"{timestamp.strftime('%Y%m%d%H%M%S')}_user_{i}",
                'country_code': random.choice(countries),
                'country_name': get_country_name(random.choice(countries)),
                'user_id': f"user_{random.randint(1000, 9999)}",
                'session_id': f"sess_{random.randint(100000, 999999)}",
                'created_at': timestamp.isoformat(),
                'ttl': int((timestamp + timedelta(days=365)).timestamp())
            })
    
    return selections
```

## 6. 백업 및 복구 전략

### 6.1 Aurora 백업 설정
```yaml
# Aurora 자동 백업 설정
AuroraCluster:
  BackupRetentionPeriod: 7  # 7일간 백업 보관
  PreferredBackupWindow: "03:00-04:00"  # 새벽 3-4시 백업
  PreferredMaintenanceWindow: "sun:04:00-sun:05:00"  # 일요일 새벽 유지보수
  
  # 스냅샷 설정
  SnapshotIdentifier: !Sub "${ProjectName}-aurora-snapshot"
  
  # 포인트 인 타임 복구 활성화
  EnableCloudwatchLogsExports:
    - error
    - general
    - slowquery
```

### 6.2 DynamoDB 백업 설정
```yaml
# DynamoDB 백업 설정
DynamoDBTable:
  PointInTimeRecoverySpecification:
    PointInTimeRecoveryEnabled: true
  
  # 연속 백업 (35일간)
  ContinuousBackups:
    PointInTimeRecoveryEnabled: true
  
  # 온디맨드 백업
  BackupPolicy:
    PointInTimeRecoveryEnabled: true
```

### 6.3 복구 스크립트
```bash
#!/bin/bash
# scripts/restore-database.sh

RESTORE_TYPE=$1  # "aurora" or "dynamodb"
RESTORE_TIME=$2  # "2025-09-05T10:30:00Z"

case $RESTORE_TYPE in
  "aurora")
    echo "Restoring Aurora cluster to $RESTORE_TIME"
    aws rds restore-db-cluster-to-point-in-time \
      --source-db-cluster-identifier currency-service-aurora \
      --db-cluster-identifier currency-service-aurora-restored \
      --restore-to-time $RESTORE_TIME
    ;;
    
  "dynamodb")
    echo "Restoring DynamoDB table to $RESTORE_TIME"
    aws dynamodb restore-table-to-point-in-time \
      --source-table-name travel_destination_selections \
      --target-table-name travel_destination_selections_restored \
      --restore-date-time $RESTORE_TIME
    ;;
    
  *)
    echo "Usage: $0 {aurora|dynamodb} <restore-time>"
    exit 1
    ;;
esac
```

## 7. 성능 모니터링

### 7.1 Aurora 성능 메트릭
```sql
-- 슬로우 쿼리 모니터링
SELECT 
    sql_text,
    count_star as execution_count,
    avg_timer_wait/1000000000 as avg_duration_seconds,
    sum_timer_wait/1000000000 as total_duration_seconds
FROM performance_schema.events_statements_summary_by_digest 
WHERE avg_timer_wait > 1000000000  -- 1초 이상
ORDER BY avg_timer_wait DESC 
LIMIT 10;

-- 인덱스 사용률 확인
SELECT 
    object_schema,
    object_name,
    index_name,
    count_read,
    count_write,
    count_fetch,
    sum_timer_wait/1000000000 as total_latency_seconds
FROM performance_schema.table_io_waits_summary_by_index_usage 
WHERE object_schema = 'currency_db'
ORDER BY count_read DESC;
```

### 7.2 DynamoDB 성능 메트릭
```python
# scripts/monitor_dynamodb.py
import boto3
from datetime import datetime, timedelta

def monitor_dynamodb_performance():
    """DynamoDB 성능 메트릭 수집"""
    cloudwatch = boto3.client('cloudwatch')
    
    # 지난 1시간 메트릭 조회
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    metrics = [
        'ConsumedReadCapacityUnits',
        'ConsumedWriteCapacityUnits', 
        'ProvisionedReadCapacityUnits',
        'ProvisionedWriteCapacityUnits',
        'ReadThrottledEvents',
        'WriteThrottledEvents'
    ]
    
    for metric in metrics:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/DynamoDB',
            MetricName=metric,
            Dimensions=[
                {'Name': 'TableName', 'Value': 'travel_destination_selections'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,  # 5분 간격
            Statistics=['Average', 'Maximum']
        )
        
        print(f"{metric}: {response['Datapoints']}")
```

이 데이터베이스 설계는 각 서비스의 요구사항에 최적화되어 있으며, 확장성과 성능을 고려한 구조로 되어 있습니다. 정기적인 모니터링과 최적화를 통해 안정적인 서비스 운영이 가능합니다.