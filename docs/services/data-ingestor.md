# Data Ingestor Service 상세 문서

## 1. 서비스 개요

**Data Ingestor Service**는 외부 금융기관 API로부터 실시간 환율 및 물가 데이터를 주기적으로 수집하는 CronJob 기반 서비스입니다. 수집된 데이터를 검증하고 여러 데이터 저장소에 분산 저장합니다.

### 1.1 주요 기능
- 다중 소스 환율 데이터 수집 (한국은행, Fed, ECB, BOJ)
- 물가 지수 데이터 수집 (빅맥/스타벅스 가격)
- 데이터 검증 및 정제
- 실시간 스트리밍 파이프라인 (Kafka/SQS)
- 장애 복구 및 백업 소스 전환

### 1.2 기술 스택
- **런타임**: Kubernetes CronJob (Python 3.11)
- **프레임워크**: FastAPI + Celery
- **메시징**: Apache Kafka (MSK) + Amazon SQS
- **스토리지**: Amazon S3 (원본 데이터)
- **스케줄링**: Kubernetes CronJob (*/5 * * * *)

## 2. 아키텍처

```
[CronJob Scheduler]
    ↓ (매 5분)
[Data Ingestor Pod]
    ↓
[외부 API 호출] → [한국은행/Fed/ECB/BOJ APIs]
    ↓
[데이터 검증 & 정제]
    ↓
[S3 원본 저장] ← 백업용
    ↓
[Kafka Producer] → [MSK Cluster]
    ↓
[SQS Fallback] ← Kafka 장애 시
    ↓
[다운스트림 서비스들]
```

### 2.1 데이터 수집 플로우
1. Kubernetes CronJob이 5분마다 Pod 실행
2. 다중 외부 API 동시 호출
3. 수집된 데이터 검증 및 정제
4. S3에 원본 데이터 백업 저장
5. Kafka로 실시간 스트리밍
6. Kafka 장애 시 SQS로 폴백

## 3. 데이터 소스 및 API

### 3.1 환율 데이터 소스
```python
# 데이터 소스 설정
EXCHANGE_RATE_SOURCES = {
    "primary": {
        "bok": {  # 한국은행
            "url": "https://ecos.bok.or.kr/api/StatisticSearch",
            "api_key": "${BOK_API_KEY}",
            "currencies": ["USD", "JPY", "EUR", "GBP", "CNY"],
            "timeout": 10
        },
        "fed": {  # 미국 연준
            "url": "https://api.stlouisfed.org/fred/series/observations",
            "api_key": "${FED_API_KEY}",
            "currencies": ["USD"],
            "timeout": 10
        }
    },
    "backup": {
        "exchangerate_api": {
            "url": "https://api.exchangerate-api.com/v4/latest/KRW",
            "api_key": "${EXCHANGERATE_API_KEY}",
            "timeout": 15
        }
    }
}
```

### 3.2 물가 데이터 소스
```python
# 물가 지수 데이터 소스
PRICE_INDEX_SOURCES = {
    "bigmac": {
        "url": "https://raw.githubusercontent.com/TheEconomist/big-mac-data/master/output-data/big-mac-full-index.csv",
        "format": "csv",
        "timeout": 20
    },
    "starbucks": {
        "scraping_targets": [
            {"country": "US", "url": "https://www.starbucks.com/menu/drinks/espresso/caffe-latte"},
            {"country": "JP", "url": "https://www.starbucks.co.jp/menu/drink/espresso/"},
            {"country": "KR", "url": "https://www.starbucks.co.kr/menu/drink_view.do?product_cd=9200000002487"}
        ],
        "timeout": 30
    }
}
```

## 4. 데이터 수집 로직

### 4.1 메인 수집 함수
```python
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional

class DataIngestor:
    def __init__(self):
        self.kafka_producer = KafkaProducer()
        self.sqs_client = boto3.client('sqs')
        self.s3_client = boto3.client('s3')
        
    async def collect_all_data(self):
        """모든 데이터 소스에서 동시 수집"""
        tasks = [
            self.collect_exchange_rates(),
            self.collect_price_indices(),
            self.collect_economic_indicators()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 처리 및 스트리밍
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Data collection failed: {result}")
                continue
                
            await self.process_and_stream(result)
    
    async def collect_exchange_rates(self) -> Dict:
        """환율 데이터 수집"""
        collected_data = {}
        
        # Primary 소스 시도
        for source_name, config in EXCHANGE_RATE_SOURCES["primary"].items():
            try:
                data = await self.fetch_from_api(config)
                collected_data[source_name] = data
                logger.info(f"Successfully collected from {source_name}")
            except Exception as e:
                logger.warning(f"Failed to collect from {source_name}: {e}")
        
        # Primary 소스 실패 시 Backup 소스 사용
        if not collected_data:
            logger.warning("All primary sources failed, trying backup sources")
            for source_name, config in EXCHANGE_RATE_SOURCES["backup"].items():
                try:
                    data = await self.fetch_from_api(config)
                    collected_data[source_name] = data
                    break
                except Exception as e:
                    logger.error(f"Backup source {source_name} also failed: {e}")
        
        return {
            "type": "exchange_rates",
            "timestamp": datetime.utcnow().isoformat(),
            "sources": collected_data
        }
```

### 4.2 데이터 검증 및 정제
```python
class DataValidator:
    @staticmethod
    def validate_exchange_rate(rate_data: Dict) -> bool:
        """환율 데이터 유효성 검증"""
        required_fields = ['currency_code', 'rate', 'timestamp']
        
        # 필수 필드 확인
        for field in required_fields:
            if field not in rate_data:
                return False
        
        # 환율 값 범위 검증
        rate = float(rate_data['rate'])
        if rate <= 0 or rate > 10000:  # 비현실적인 환율
            return False
        
        # 통화 코드 검증
        if not re.match(r'^[A-Z]{3}$', rate_data['currency_code']):
            return False
        
        return True
    
    @staticmethod
    def normalize_exchange_rate(raw_data: Dict) -> Dict:
        """환율 데이터 정규화"""
        return {
            "currency_code": raw_data['currency_code'].upper(),
            "currency_name": CURRENCY_NAMES.get(raw_data['currency_code']),
            "deal_base_rate": round(float(raw_data['rate']), 4),
            "tts": round(float(raw_data['rate']) * 1.02, 4),  # 송금 시 2% 수수료
            "ttb": round(float(raw_data['rate']) * 0.98, 4),  # 받을 시 2% 할인
            "source": raw_data.get('source', 'unknown'),
            "collected_at": datetime.utcnow().isoformat(),
            "recorded_at": raw_data.get('timestamp', datetime.utcnow().isoformat())
        }
```

### 4.3 스트리밍 파이프라인
```python
class StreamingPipeline:
    def __init__(self):
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
    async def stream_to_kafka(self, data: Dict):
        """Kafka로 데이터 스트리밍"""
        try:
            topic = self.get_topic_by_data_type(data['type'])
            key = self.generate_partition_key(data)
            
            future = self.kafka_producer.send(
                topic=topic,
                key=key,
                value=data
            )
            
            # 비동기 전송 결과 확인
            record_metadata = await asyncio.wrap_future(future)
            logger.info(f"Sent to Kafka: {record_metadata.topic}:{record_metadata.partition}")
            
        except Exception as e:
            logger.error(f"Kafka streaming failed: {e}")
            # SQS 폴백
            await self.fallback_to_sqs(data)
    
    async def fallback_to_sqs(self, data: Dict):
        """Kafka 실패 시 SQS로 폴백"""
        try:
            queue_url = os.getenv('SQS_FALLBACK_QUEUE_URL')
            
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(data),
                MessageAttributes={
                    'DataType': {
                        'StringValue': data['type'],
                        'DataType': 'String'
                    },
                    'Source': {
                        'StringValue': 'data-ingestor-fallback',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Fallback to SQS successful: {response['MessageId']}")
            
        except Exception as e:
            logger.error(f"SQS fallback also failed: {e}")
            # 최후 수단: S3에 저장
            await self.emergency_save_to_s3(data)
```

## 5. Kubernetes CronJob 설정

### 5.1 CronJob 매니페스트
```yaml
# data-ingestor-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: data-ingestor
  namespace: currency-system
spec:
  schedule: "*/5 * * * *"  # 매 5분마다 실행
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid  # 동시 실행 방지
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: data-ingestor
            image: your-ecr-repo/data-ingestor:latest
            imagePullPolicy: Always
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
            env:
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: "your-msk-cluster.kafka.ap-northeast-2.amazonaws.com:9092"
            - name: S3_BUCKET
              value: "currency-data-backup"
            - name: SQS_FALLBACK_QUEUE_URL
              valueFrom:
                secretKeyRef:
                  name: data-ingestor-secrets
                  key: sqs-queue-url
            - name: BOK_API_KEY
              valueFrom:
                secretKeyRef:
                  name: api-keys
                  key: bok-api-key
            volumeMounts:
            - name: config-volume
              mountPath: /app/config
          volumes:
          - name: config-volume
            configMap:
              name: data-ingestor-config
```

### 5.2 ConfigMap 설정
```yaml
# data-ingestor-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: data-ingestor-config
  namespace: currency-system
data:
  collection-config.yaml: |
    collection:
      batch_size: 100
      timeout_seconds: 30
      retry_attempts: 3
      retry_delay_seconds: 5
    
    kafka:
      topics:
        exchange_rates: "exchange-rates"
        price_indices: "price-indices"
        economic_indicators: "economic-indicators"
      
    validation:
      exchange_rate_min: 0.001
      exchange_rate_max: 10000
      required_currencies: ["USD", "JPY", "EUR"]
```

## 6. 모니터링 및 알림

### 6.1 수집 상태 모니터링
```python
class CollectionMonitor:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    def report_collection_metrics(self, results: Dict):
        """수집 결과 메트릭 전송"""
        metrics = []
        
        for source, data in results.items():
            # 성공/실패 메트릭
            success_count = len(data.get('successful_currencies', []))
            failed_count = len(data.get('failed_currencies', []))
            
            metrics.extend([
                {
                    'MetricName': 'SuccessfulCollections',
                    'Dimensions': [{'Name': 'Source', 'Value': source}],
                    'Value': success_count,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'FailedCollections',
                    'Dimensions': [{'Name': 'Source', 'Value': source}],
                    'Value': failed_count,
                    'Unit': 'Count'
                }
            ])
        
        # CloudWatch로 메트릭 전송
        self.cloudwatch.put_metric_data(
            Namespace='DataIngestor',
            MetricData=metrics
        )
```

### 6.2 알림 설정
```yaml
# data-ingestor-alarms.yaml
DataCollectionFailureAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: data-collection-failure
    AlarmDescription: "Data collection from external APIs failed"
    MetricName: FailedCollections
    Namespace: DataIngestor
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 5
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref SNSTopicArn

KafkaStreamingFailureAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: kafka-streaming-failure
    MetricName: StreamingErrors
    Threshold: 3
    ComparisonOperator: GreaterThanThreshold
```

## 7. 장애 복구 전략

### 7.1 API 소스 장애 대응
```python
class FailoverManager:
    def __init__(self):
        self.source_health = {}
        self.circuit_breaker = {}
    
    async def collect_with_failover(self, sources: Dict):
        """장애 조치가 포함된 데이터 수집"""
        results = {}
        
        for source_name, config in sources.items():
            # Circuit Breaker 확인
            if self.is_circuit_open(source_name):
                logger.warning(f"Circuit breaker open for {source_name}, skipping")
                continue
            
            try:
                data = await self.fetch_from_source(config)
                results[source_name] = data
                self.record_success(source_name)
                
            except Exception as e:
                self.record_failure(source_name, e)
                
                # 백업 소스로 전환
                backup_config = self.get_backup_source(source_name)
                if backup_config:
                    try:
                        data = await self.fetch_from_source(backup_config)
                        results[f"{source_name}_backup"] = data
                        logger.info(f"Successfully failed over to backup for {source_name}")
                    except Exception as backup_error:
                        logger.error(f"Backup source also failed: {backup_error}")
        
        return results
    
    def is_circuit_open(self, source_name: str) -> bool:
        """Circuit Breaker 상태 확인"""
        breaker = self.circuit_breaker.get(source_name, {})
        failure_count = breaker.get('failure_count', 0)
        last_failure = breaker.get('last_failure', 0)
        
        # 5회 연속 실패 시 10분간 차단
        if failure_count >= 5:
            if time.time() - last_failure < 600:  # 10분
                return True
            else:
                # 시간이 지났으므로 재시도 허용
                self.circuit_breaker[source_name] = {'failure_count': 0}
        
        return False
```

## 8. 성능 최적화

### 8.1 비동기 처리
```python
# 동시 API 호출로 수집 시간 단축
async def parallel_collection():
    """병렬 데이터 수집"""
    semaphore = asyncio.Semaphore(10)  # 최대 10개 동시 연결
    
    async def fetch_with_semaphore(source_config):
        async with semaphore:
            return await fetch_from_api(source_config)
    
    tasks = [fetch_with_semaphore(config) for config in all_sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

### 8.2 캐싱 전략
```python
# Redis를 이용한 중복 요청 방지
class RequestCache:
    def __init__(self):
        self.redis = redis.Redis(host=os.getenv('REDIS_HOST'))
    
    async def get_cached_or_fetch(self, cache_key: str, fetch_func, ttl: int = 300):
        """캐시된 데이터 조회 또는 새로 수집"""
        cached_data = self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # 캐시 미스 시 새로 수집
        fresh_data = await fetch_func()
        self.redis.setex(cache_key, ttl, json.dumps(fresh_data))
        
        return fresh_data
```

## 9. 보안 고려사항

### 9.1 API 키 관리
```yaml
# Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
  namespace: currency-system
type: Opaque
data:
  bok-api-key: <base64-encoded-key>
  fed-api-key: <base64-encoded-key>
  exchangerate-api-key: <base64-encoded-key>
```

### 9.2 네트워크 보안
```python
# SSL/TLS 검증 및 타임아웃 설정
async def secure_api_call(url: str, headers: Dict, timeout: int = 10):
    """보안이 강화된 API 호출"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    timeout_config = aiohttp.ClientTimeout(total=timeout)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout_config,
        headers=headers
    ) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()
```