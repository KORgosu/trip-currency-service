# 모니터링 및 관찰성 가이드

## 1. 모니터링 아키텍처 개요

여행 물가 비교 서비스는 **다층 모니터링 아키텍처**를 통해 시스템의 상태를 실시간으로 관찰하고, 문제 발생 시 신속한 대응이 가능하도록 설계되었습니다.

### 1.1 모니터링 스택
```
┌─────────────────────────────────────────────────────────────┐
│                    관찰성 레이어 (Observability)              │
├─────────────────────────────────────────────────────────────┤
│ Metrics (메트릭)  │ Logs (로그)      │ Traces (추적)      │
│ - Prometheus      │ - CloudWatch     │ - X-Ray           │
│ - CloudWatch      │ - OpenSearch     │ - Jaeger          │
│ - Grafana         │ - Fluentd        │                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    알림 레이어 (Alerting)                    │
├─────────────────────────────────────────────────────────────┤
│ - CloudWatch Alarms                                         │
│ - SNS (이메일, SMS)                                         │
│ - Slack 통합                                                │
│ - PagerDuty (중요 알림)                                     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 모니터링 대상
- **애플리케이션 메트릭**: Lambda 실행 시간, 에러율, 처리량
- **인프라 메트릭**: CPU, 메모리, 네트워크, 디스크 사용률
- **비즈니스 메트릭**: 환율 조회 수, 사용자 선택 수, 랭킹 변동
- **보안 메트릭**: 비정상 접근, API 남용, 인증 실패

## 2. 메트릭 수집 및 시각화

### 2.1 CloudWatch 메트릭

#### 2.1.1 Lambda 함수 메트릭
```yaml
# Lambda 메트릭 설정
LambdaMetrics:
  CurrencyService:
    - Duration (실행 시간)
    - Errors (에러 수)
    - Invocations (호출 수)
    - Throttles (스로틀링)
    - ConcurrentExecutions (동시 실행)
    - DeadLetterErrors (DLQ 에러)
    
  RankingService:
    - Duration
    - Errors  
    - Invocations
    - IteratorAge (DynamoDB Streams)
    
  HistoryService:
    - Duration
    - Errors
    - Invocations
    - MemoryUtilization (메모리 사용률)
```

#### 2.1.2 DynamoDB 메트릭
```yaml
DynamoDBMetrics:
  Tables:
    - ConsumedReadCapacityUnits
    - ConsumedWriteCapacityUnits
    - ProvisionedReadCapacityUnits
    - ProvisionedWriteCapacityUnits
    - ReadThrottledEvents
    - WriteThrottledEvents
    - ItemCount
    - TableSizeBytes
    
  GlobalSecondaryIndexes:
    - ConsumedReadCapacityUnits
    - ConsumedWriteCapacityUnits
    - OnlineIndexPercentageProgress
```

#### 2.1.3 Aurora 메트릭
```yaml
AuroraMetrics:
  Cluster:
    - DatabaseConnections
    - CPUUtilization
    - FreeableMemory
    - ReadLatency
    - WriteLatency
    - ReadIOPS
    - WriteIOPS
    - NetworkReceiveThroughput
    - NetworkTransmitThroughput
    
  Instance:
    - CPUUtilization
    - DatabaseConnections
    - FreeableMemory
    - ReadLatency
    - WriteLatency
```

### 2.2 커스텀 메트릭 생성

#### 2.2.1 비즈니스 메트릭 수집
```python
# services/shared/metrics.py
import boto3
from datetime import datetime
from typing import Dict, List

class MetricsCollector:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'CurrencyService/Business'
    
    def record_currency_request(self, currency_code: str, response_time_ms: int):
        """환율 조회 요청 메트릭 기록"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    'MetricName': 'CurrencyRequests',
                    'Dimensions': [
                        {'Name': 'Currency', 'Value': currency_code}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'ResponseTime',
                    'Dimensions': [
                        {'Name': 'Currency', 'Value': currency_code}
                    ],
                    'Value': response_time_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    
    def record_ranking_selection(self, country_code: str):
        """랭킹 선택 메트릭 기록"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    'MetricName': 'CountrySelections',
                    'Dimensions': [
                        {'Name': 'Country', 'Value': country_code}
                    ],
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    
    def record_data_collection_success(self, source: str, currency_count: int):
        """데이터 수집 성공 메트릭 기록"""
        self.cloudwatch.put_metric_data(
            Namespace='CurrencyService/DataCollection',
            MetricData=[
                {
                    'MetricName': 'CollectionSuccess',
                    'Dimensions': [
                        {'Name': 'Source', 'Value': source}
                    ],
                    'Value': 1,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'CurrenciesCollected',
                    'Dimensions': [
                        {'Name': 'Source', 'Value': source}
                    ],
                    'Value': currency_count,
                    'Unit': 'Count'
                }
            ]
        )
```

#### 2.2.2 성능 메트릭 데코레이터
```python
# services/shared/decorators.py
import time
import functools
from .metrics import MetricsCollector

def monitor_performance(metric_name: str, dimensions: Dict[str, str] = None):
    """함수 실행 시간을 모니터링하는 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = MetricsCollector()
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # 성능 메트릭 기록
                metric_data = [
                    {
                        'MetricName': f'{metric_name}Duration',
                        'Value': duration_ms,
                        'Unit': 'Milliseconds'
                    },
                    {
                        'MetricName': f'{metric_name}Success' if success else f'{metric_name}Error',
                        'Value': 1,
                        'Unit': 'Count'
                    }
                ]
                
                if dimensions:
                    for metric in metric_data:
                        metric['Dimensions'] = [
                            {'Name': k, 'Value': v} for k, v in dimensions.items()
                        ]
                
                metrics.cloudwatch.put_metric_data(
                    Namespace='CurrencyService/Performance',
                    MetricData=metric_data
                )
            
            return result
        return wrapper
    return decorator

# 사용 예시
@monitor_performance('CurrencyLookup', {'Service': 'CurrencyService'})
def get_latest_rates(currency_codes: List[str]):
    # 환율 조회 로직
    pass
```

### 2.3 Grafana 대시보드

#### 2.3.1 서비스 개요 대시보드
```json
{
  "dashboard": {
    "title": "Currency Service - Overview",
    "panels": [
      {
        "title": "Request Volume",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(aws_lambda_invocations_total[5m])) by (function_name)",
            "legendFormat": "{{function_name}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "sum(rate(aws_lambda_errors_total[5m])) / sum(rate(aws_lambda_invocations_total[5m])) * 100",
            "legendFormat": "Error Rate %"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(aws_lambda_duration_seconds_bucket[5m]))",
            "legendFormat": "P95 Duration"
          }
        ]
      }
    ]
  }
}
```

#### 2.3.2 비즈니스 메트릭 대시보드
```json
{
  "dashboard": {
    "title": "Currency Service - Business Metrics",
    "panels": [
      {
        "title": "Top Requested Currencies",
        "type": "piechart",
        "targets": [
          {
            "expr": "topk(10, sum(increase(currency_requests_total[1h])) by (currency))",
            "legendFormat": "{{currency}}"
          }
        ]
      },
      {
        "title": "Country Selection Trends",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(country_selections_total[5m])) by (country)",
            "legendFormat": "{{country}}"
          }
        ]
      },
      {
        "title": "Data Collection Status",
        "type": "table",
        "targets": [
          {
            "expr": "sum(increase(data_collection_success_total[1h])) by (source)",
            "legendFormat": "{{source}}"
          }
        ]
      }
    ]
  }
}
```

## 3. 로그 관리

### 3.1 로그 수집 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Lambda Logs   │───▶│ CloudWatch Logs │───▶│   OpenSearch    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐              │
│  EKS Pod Logs   │───▶│    Fluentd      │─────────────┘
└─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐              │
│   VPC Flow      │──────────────┘
│     Logs        │
└─────────────────┘
```

### 3.2 구조화된 로깅

#### 3.2.1 로그 포맷 표준화
```python
# services/shared/logging.py
import json
import logging
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    def __init__(self, service_name: str, version: str):
        self.service_name = service_name
        self.version = version
        self.logger = logging.getLogger(service_name)
        
        # JSON 포맷터 설정
        formatter = logging.Formatter(
            '%(message)s'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _create_log_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """구조화된 로그 엔트리 생성"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'service': self.service_name,
            'version': self.version,
            'message': message,
            'correlation_id': kwargs.get('correlation_id'),
            'user_id': kwargs.get('user_id'),
            'request_id': kwargs.get('request_id')
        }
        
        # 추가 필드들
        for key, value in kwargs.items():
            if key not in ['correlation_id', 'user_id', 'request_id']:
                log_entry[key] = value
        
        # None 값 제거
        return {k: v for k, v in log_entry.items() if v is not None}
    
    def info(self, message: str, **kwargs):
        log_entry = self._create_log_entry('INFO', message, **kwargs)
        self.logger.info(json.dumps(log_entry))
    
    def error(self, message: str, error: Exception = None, **kwargs):
        log_entry = self._create_log_entry('ERROR', message, **kwargs)
        
        if error:
            log_entry['error'] = {
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        self.logger.error(json.dumps(log_entry))
    
    def warning(self, message: str, **kwargs):
        log_entry = self._create_log_entry('WARNING', message, **kwargs)
        self.logger.warning(json.dumps(log_entry))

# 사용 예시
logger = StructuredLogger('currency-service', 'v1.2.0')

logger.info(
    'Currency rate retrieved successfully',
    currency='USD',
    rate=1392.4,
    source='redis_cache',
    response_time_ms=45,
    correlation_id='req_12345'
)
```

#### 3.2.2 Lambda 로그 설정
```python
# services/currency-service/main.py
import os
from shared.logging import StructuredLogger

# 환경 변수에서 로그 레벨 설정
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logger = StructuredLogger('currency-service', os.getenv('SERVICE_VERSION', 'unknown'))

def lambda_handler(event, context):
    correlation_id = event.get('headers', {}).get('X-Correlation-ID', context.aws_request_id)
    
    logger.info(
        'Lambda function started',
        correlation_id=correlation_id,
        request_id=context.aws_request_id,
        function_name=context.function_name,
        memory_limit=context.memory_limit_in_mb
    )
    
    try:
        # 비즈니스 로직 실행
        result = process_request(event)
        
        logger.info(
            'Lambda function completed successfully',
            correlation_id=correlation_id,
            execution_time_ms=context.get_remaining_time_in_millis()
        )
        
        return result
        
    except Exception as e:
        logger.error(
            'Lambda function failed',
            error=e,
            correlation_id=correlation_id,
            request_id=context.aws_request_id
        )
        raise
```

### 3.3 EKS 로그 수집 (Fluentd)

#### 3.3.1 Fluentd 설정
```yaml
# k8s/fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: kube-system
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*currency-system*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
      time_format %Y-%m-%dT%H:%M:%S.%NZ
    </source>
    
    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>
    
    <filter kubernetes.**>
      @type parser
      key_name log
      reserve_data true
      <parse>
        @type json
      </parse>
    </filter>
    
    <match kubernetes.**>
      @type opensearch
      host opensearch.currency-system.svc.cluster.local
      port 9200
      index_name currency-logs
      type_name _doc
      
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_thread_count 2
        flush_interval 5s
        retry_forever
        retry_max_interval 30
        chunk_limit_size 2M
        queue_limit_length 8
        overflow_action block
      </buffer>
    </match>
```

## 4. 분산 추적 (Distributed Tracing)

### 4.1 AWS X-Ray 설정

#### 4.1.1 Lambda X-Ray 추적
```python
# services/shared/tracing.py
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import boto3

# AWS SDK 자동 추적
patch_all()

class TracingHelper:
    @staticmethod
    def create_subsegment(name: str, metadata: dict = None):
        """서브세그먼트 생성"""
        subsegment = xray_recorder.begin_subsegment(name)
        
        if metadata:
            subsegment.put_metadata('custom', metadata)
        
        return subsegment
    
    @staticmethod
    def add_annotation(key: str, value: str):
        """추적 가능한 어노테이션 추가"""
        xray_recorder.put_annotation(key, value)
    
    @staticmethod
    def add_metadata(namespace: str, data: dict):
        """메타데이터 추가"""
        xray_recorder.put_metadata(namespace, data)

# 사용 예시
@xray_recorder.capture('get_exchange_rate')
def get_exchange_rate(currency_code: str):
    TracingHelper.add_annotation('currency', currency_code)
    TracingHelper.add_metadata('request', {'currency': currency_code})
    
    # Redis 조회
    with TracingHelper.create_subsegment('redis_lookup') as subsegment:
        rate = redis_client.get(f'rate:{currency_code}')
        subsegment.put_metadata('cache', {'hit': rate is not None})
    
    if not rate:
        # DB 조회
        with TracingHelper.create_subsegment('db_lookup') as subsegment:
            rate = db_client.get_latest_rate(currency_code)
            subsegment.put_metadata('database', {'query_time_ms': 150})
    
    return rate
```

### 4.2 서비스 간 추적 연결

#### 4.2.1 HTTP 헤더를 통한 추적 ID 전파
```python
# services/shared/http_client.py
import requests
from aws_xray_sdk.core import xray_recorder

class TracedHTTPClient:
    def __init__(self):
        self.session = requests.Session()
    
    @xray_recorder.capture('http_request')
    def get(self, url: str, **kwargs):
        # X-Ray 추적 헤더 추가
        headers = kwargs.get('headers', {})
        
        # 현재 추적 ID를 헤더에 추가
        trace_header = xray_recorder.get_trace_entity().trace_id
        headers['X-Amzn-Trace-Id'] = trace_header
        
        kwargs['headers'] = headers
        
        # 요청 메타데이터 추가
        xray_recorder.put_metadata('http', {
            'url': url,
            'method': 'GET',
            'headers': headers
        })
        
        response = self.session.get(url, **kwargs)
        
        # 응답 메타데이터 추가
        xray_recorder.put_metadata('http_response', {
            'status_code': response.status_code,
            'response_time_ms': response.elapsed.total_seconds() * 1000
        })
        
        return response
```

## 5. 알림 및 경고

### 5.1 CloudWatch 알람 설정

#### 5.1.1 Lambda 함수 알람
```yaml
# monitoring/cloudwatch-alarms.yaml
CurrencyServiceErrorRate:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: currency-service-high-error-rate
    AlarmDescription: Currency Service error rate is too high
    MetricName: Errors
    Namespace: AWS/Lambda
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: FunctionName
        Value: !Ref CurrencyServiceFunction
    AlarmActions:
      - !Ref CriticalAlertsSnsTopic

CurrencyServiceDuration:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: currency-service-high-duration
    AlarmDescription: Currency Service duration is too high
    MetricName: Duration
    Namespace: AWS/Lambda
    Statistic: Average
    Period: 300
    EvaluationPeriods: 3
    Threshold: 5000  # 5초
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: FunctionName
        Value: !Ref CurrencyServiceFunction
    AlarmActions:
      - !Ref WarningAlertsSnsTopic
```

#### 5.1.2 DynamoDB 알람
```yaml
DynamoDBReadThrottle:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: dynamodb-read-throttle
    AlarmDescription: DynamoDB read requests are being throttled
    MetricName: ReadThrottledEvents
    Namespace: AWS/DynamoDB
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 1
    Threshold: 0
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: TableName
        Value: travel_destination_selections
    AlarmActions:
      - !Ref CriticalAlertsSnsTopic

DynamoDBWriteThrottle:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: dynamodb-write-throttle
    AlarmDescription: DynamoDB write requests are being throttled
    MetricName: WriteThrottledEvents
    Namespace: AWS/DynamoDB
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 1
    Threshold: 0
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: TableName
        Value: travel_destination_selections
    AlarmActions:
      - !Ref CriticalAlertsSnsTopic
```

### 5.2 복합 알람 및 대시보드

#### 5.2.1 서비스 상태 복합 알람
```yaml
ServiceHealthComposite:
  Type: AWS::CloudWatch::CompositeAlarm
  Properties:
    AlarmName: currency-service-health-composite
    AlarmDescription: Overall health of Currency Service
    AlarmRule: !Sub |
      ALARM(${CurrencyServiceErrorRate}) OR 
      ALARM(${CurrencyServiceDuration}) OR 
      ALARM(${DynamoDBReadThrottle}) OR 
      ALARM(${DynamoDBWriteThrottle})
    ActionsEnabled: true
    AlarmActions:
      - !Ref CriticalAlertsSnsTopic
```

### 5.3 Slack 통합

#### 5.3.1 Slack 알림 Lambda
```python
# monitoring/slack-notifier/main.py
import json
import boto3
import requests
from typing import Dict, Any

def lambda_handler(event, context):
    """SNS 메시지를 Slack으로 전송"""
    
    # SNS 메시지 파싱
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])
    
    alarm_name = sns_message['AlarmName']
    alarm_description = sns_message['AlarmDescription']
    new_state = sns_message['NewStateValue']
    reason = sns_message['NewStateReason']
    
    # Slack 메시지 생성
    slack_message = create_slack_message(
        alarm_name, alarm_description, new_state, reason
    )
    
    # Slack으로 전송
    webhook_url = get_slack_webhook_url()
    response = requests.post(webhook_url, json=slack_message)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Notification sent to Slack')
    }

def create_slack_message(alarm_name: str, description: str, state: str, reason: str) -> Dict[str, Any]:
    """Slack 메시지 포맷 생성"""
    
    # 상태에 따른 색상 및 이모지
    color_map = {
        'ALARM': '#FF0000',
        'OK': '#00FF00', 
        'INSUFFICIENT_DATA': '#FFFF00'
    }
    
    emoji_map = {
        'ALARM': '🚨',
        'OK': '✅',
        'INSUFFICIENT_DATA': '⚠️'
    }
    
    return {
        'attachments': [
            {
                'color': color_map.get(state, '#808080'),
                'title': f"{emoji_map.get(state, '❓')} {alarm_name}",
                'text': description,
                'fields': [
                    {
                        'title': 'State',
                        'value': state,
                        'short': True
                    },
                    {
                        'title': 'Reason',
                        'value': reason,
                        'short': False
                    }
                ],
                'footer': 'Currency Service Monitoring',
                'ts': int(time.time())
            }
        ]
    }

def get_slack_webhook_url() -> str:
    """Parameter Store에서 Slack Webhook URL 조회"""
    ssm = boto3.client('ssm')
    
    response = ssm.get_parameter(
        Name='/currency-service/slack/webhook-url',
        WithDecryption=True
    )
    
    return response['Parameter']['Value']
```

## 6. 성능 모니터링 및 최적화

### 6.1 성능 벤치마킹

#### 6.1.1 자동 성능 테스트
```python
# monitoring/performance-test/load_test.py
import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics

class PerformanceTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
    
    async def test_currency_service(self, concurrent_users: int = 100, duration_seconds: int = 60):
        """Currency Service 부하 테스트"""
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for _ in range(concurrent_users):
                task = asyncio.create_task(
                    self._currency_request_loop(session, duration_seconds)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        
        return self._calculate_statistics()
    
    async def _currency_request_loop(self, session: aiohttp.ClientSession, duration: int):
        """개별 사용자의 요청 루프"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            start_time = time.time()
            
            try:
                async with session.get(f"{self.base_url}/currencies/latest?symbols=USD,JPY") as response:
                    await response.json()
                    
                    response_time = (time.time() - start_time) * 1000
                    self.results.append({
                        'response_time_ms': response_time,
                        'status_code': response.status,
                        'success': response.status == 200
                    })
                    
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                self.results.append({
                    'response_time_ms': response_time,
                    'status_code': 0,
                    'success': False,
                    'error': str(e)
                })
            
            # 요청 간 간격
            await asyncio.sleep(0.1)
    
    def _calculate_statistics(self) -> Dict:
        """성능 통계 계산"""
        response_times = [r['response_time_ms'] for r in self.results]
        success_count = sum(1 for r in self.results if r['success'])
        
        return {
            'total_requests': len(self.results),
            'successful_requests': success_count,
            'error_rate': (len(self.results) - success_count) / len(self.results) * 100,
            'avg_response_time': statistics.mean(response_times),
            'p50_response_time': statistics.median(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18],  # 95th percentile
            'p99_response_time': statistics.quantiles(response_times, n=100)[98], # 99th percentile
            'min_response_time': min(response_times),
            'max_response_time': max(response_times)
        }

# 실행 예시
async def main():
    tester = PerformanceTester('https://api.currency-travel.com/api/v1')
    results = await tester.test_currency_service(concurrent_users=50, duration_seconds=30)
    
    print(f"Performance Test Results:")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Success Rate: {100 - results['error_rate']:.2f}%")
    print(f"Average Response Time: {results['avg_response_time']:.2f}ms")
    print(f"P95 Response Time: {results['p95_response_time']:.2f}ms")

if __name__ == "__main__":
    asyncio.run(main())
```

### 6.2 자동 스케일링 모니터링

#### 6.2.1 Lambda 동시 실행 모니터링
```python
# monitoring/scaling-monitor/lambda_monitor.py
import boto3
from datetime import datetime, timedelta

class LambdaScalingMonitor:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.lambda_client = boto3.client('lambda')
    
    def check_concurrency_limits(self, function_names: List[str]):
        """Lambda 동시 실행 제한 확인"""
        
        for function_name in function_names:
            # 현재 동시 실행 수 조회
            current_concurrency = self._get_current_concurrency(function_name)
            
            # 설정된 제한 조회
            reserved_concurrency = self._get_reserved_concurrency(function_name)
            
            # 사용률 계산
            if reserved_concurrency:
                utilization = (current_concurrency / reserved_concurrency) * 100
                
                if utilization > 80:
                    self._send_scaling_alert(function_name, utilization, current_concurrency, reserved_concurrency)
    
    def _get_current_concurrency(self, function_name: str) -> int:
        """현재 동시 실행 수 조회"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        response = self.cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='ConcurrentExecutions',
            Dimensions=[
                {'Name': 'FunctionName', 'Value': function_name}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Maximum']
        )
        
        if response['Datapoints']:
            return int(response['Datapoints'][-1]['Maximum'])
        return 0
    
    def _get_reserved_concurrency(self, function_name: str) -> int:
        """예약된 동시 실행 제한 조회"""
        try:
            response = self.lambda_client.get_function_concurrency(
                FunctionName=function_name
            )
            return response.get('ReservedConcurrencyExecutions', 1000)  # 기본값
        except:
            return 1000  # 기본 계정 제한
```

이 모니터링 가이드를 통해 시스템의 모든 계층에서 발생하는 이벤트를 실시간으로 관찰하고, 문제 발생 시 신속하게 대응할 수 있는 체계를 구축할 수 있습니다.