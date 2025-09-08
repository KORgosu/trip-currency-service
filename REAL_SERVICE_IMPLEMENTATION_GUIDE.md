# 실제 서비스 구현 가이드

## 🎯 개요

이 문서는 현재 구현된 Currency Travel Service를 실제 운영 환경에 배포하기 위한 상세 가이드입니다. 로컬 개발 환경에서 AWS 프로덕션 환경으로의 전환 과정을 단계별로 설명합니다.

## �️ 현*재 구현 상태

### ✅ 완료된 구현
- **4개 마이크로서비스** 완전 구현
- **공통 모듈** (shared) 완전 구현
- **로컬 개발 환경** Docker Compose 구성
- **테스트 시스템** 단위/통합 테스트
- **API 문서** 완전한 명세서
- **데이터베이스 스키마** MySQL + DynamoDB

### 🔧 수정 필요 사항
- AWS 서비스 연동 설정
- 보안 설정 강화
- 모니터링 시스템 구축
- CI/CD 파이프라인 구성

## 🚀 AWS 배포 로드맵

### Phase 1: 기본 인프라 구성 (1-2주)

#### 1.1 VPC 및 네트워크 설정
```bash
# Terraform으로 VPC 생성
cd infrastructure/terraform
terraform init
terraform plan -var-file="environments/prod.tfvars"
terraform apply
```

**필요한 리소스:**
- VPC (10.0.0.0/16)
- Public Subnets (ALB용)
- Private Subnets (Lambda, EKS용)
- Database Subnets (Aurora, ElastiCache용)
- NAT Gateway, Internet Gateway
- Route Tables, Security Groups

#### 1.2 데이터베이스 구성
```yaml
# Aurora MySQL Serverless v2
AuroraCluster:
  Engine: aurora-mysql
  EngineVersion: 8.0.mysql_aurora.3.02.0
  ServerlessV2ScalingConfiguration:
    MinCapacity: 0.5
    MaxCapacity: 16
  BackupRetentionPeriod: 7
  DeletionProtection: true
```

**설정 체크리스트:**
- [ ] Aurora MySQL 클러스터 생성
- [ ] 읽기 전용 복제본 설정
- [ ] 자동 백업 활성화
- [ ] 암호화 활성화
- [ ] Parameter Group 최적화

#### 1.3 캐시 및 NoSQL 구성
```yaml
# ElastiCache Redis
RedisCluster:
  CacheNodeType: cache.r6g.large
  NumCacheNodes: 3
  Engine: redis
  EngineVersion: 7.0
  AtRestEncryptionEnabled: true
  TransitEncryptionEnabled: true

# DynamoDB Tables
DynamoDBTables:
  - travel_destination_selections
  - RankingResults
```

### Phase 2: 애플리케이션 배포 (2-3주)

#### 2.1 Lambda 함수 배포
각 서비스를 Lambda 함수로 배포:

```python
# services/currency-service/main.py 수정
def lambda_handler(event, context):
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    return handler(event, context)
```

**배포 스크립트:**
```bash
# ECR 이미지 빌드 및 푸시
./scripts/deploy-lambda.sh currency-service
./scripts/deploy-lambda.sh ranking-service
./scripts/deploy-lambda.sh history-service
```

#### 2.2 API Gateway 설정
```yaml
# API Gateway REST API
APIGateway:
  Type: AWS::ApiGateway::RestApi
  Properties:
    Name: currency-service-api
    EndpointConfiguration:
      Types: [REGIONAL]
    
# Lambda 통합
LambdaIntegration:
  Type: AWS::ApiGateway::Method
  Properties:
    HttpMethod: ANY
    ResourceId: !Ref ProxyResource
    RestApiId: !Ref APIGateway
    Integration:
      Type: AWS_PROXY
      IntegrationHttpMethod: POST
      Uri: !Sub 'arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${CurrencyServiceFunction.Arn}/invocations'
```

#### 2.3 EKS 클러스터 (Data Ingestor용)
```yaml
# EKS 클러스터
EKSCluster:
  Type: AWS::EKS::Cluster
  Properties:
    Name: currency-service-eks
    Version: '1.28'
    RoleArn: !GetAtt EKSServiceRole.Arn
    ResourcesVpcConfig:
      SubnetIds: 
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2

# CronJob 매니페스트
apiVersion: batch/v1
kind: CronJob
metadata:
  name: data-ingestor
spec:
  schedule: "*/5 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: data-ingestor
            image: your-account.dkr.ecr.region.amazonaws.com/data-ingestor:latest
            env:
            - name: EXECUTION_MODE
              value: "cronjob"
```

### Phase 3: 메시징 및 스토리지 (1-2주)

#### 3.1 MSK (Managed Kafka) 설정
```yaml
MSKCluster:
  Type: AWS::MSK::Cluster
  Properties:
    ClusterName: currency-service-kafka
    KafkaVersion: 2.8.1
    NumberOfBrokerNodes: 3
    BrokerNodeGroupInfo:
      InstanceType: kafka.m5.large
      ClientSubnets:
        - !Ref PrivateSubnet1
        - !Ref PrivateSubnet2
        - !Ref PrivateSubnet3
    ClientAuthentication:
      Sasl:
        Iam:
          Enabled: true
    EncryptionInfo:
      EncryptionInTransit:
        ClientBroker: TLS
        InCluster: true
```

#### 3.2 S3 및 SQS 설정
```yaml
# S3 버킷
S3Buckets:
  - currency-data-backup
  - currency-service-logs
  - currency-static-assets

# SQS 큐
SQSQueues:
  - ranking-calculation-queue
  - data-processing-dlq
```

### Phase 4: 보안 및 모니터링 (2-3주)

#### 4.1 IAM 역할 및 정책
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/travel_destination_selections"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds-data:ExecuteStatement",
        "rds-data:BatchExecuteStatement"
      ],
      "Resource": "arn:aws:rds:*:*:cluster:currency-service-aurora"
    }
  ]
}
```

#### 4.2 Parameter Store 설정
```bash
# 데이터베이스 비밀번호
aws ssm put-parameter \
  --name "/currency-service/db/password" \
  --value "your-secure-password" \
  --type "SecureString"

# API 키들
aws ssm put-parameter \
  --name "/currency-service/api/bok-key" \
  --value "your-bok-api-key" \
  --type "SecureString"
```

#### 4.3 CloudWatch 모니터링
```yaml
# CloudWatch 대시보드
Dashboard:
  Type: AWS::CloudWatch::Dashboard
  Properties:
    DashboardName: CurrencyService-Overview
    DashboardBody: !Sub |
      {
        "widgets": [
          {
            "type": "metric",
            "properties": {
              "metrics": [
                ["AWS/Lambda", "Duration", "FunctionName", "${CurrencyServiceFunction}"],
                ["AWS/Lambda", "Errors", "FunctionName", "${CurrencyServiceFunction}"],
                ["AWS/Lambda", "Invocations", "FunctionName", "${CurrencyServiceFunction}"]
              ],
              "period": 300,
              "stat": "Average",
              "region": "${AWS::Region}",
              "title": "Currency Service Metrics"
            }
          }
        ]
      }
```

## 🔧 코드 수정 가이드

### 1. 설정 파일 수정

#### shared/config.py
```python
def _load_aws_config(self) -> AppConfig:
    """AWS 환경 설정"""
    return AppConfig(
        environment=self.environment,
        service_name=self.service_name,
        
        database=DatabaseConfig(
            # Parameter Store에서 로드
            aurora_password=self._load_from_parameter_store(
                f"/{self.service_name}/db/password"
            ),
            aurora_host=os.getenv("AURORA_ENDPOINT"),
            
            # ElastiCache 설정
            redis_host=os.getenv("REDIS_ENDPOINT"),
            redis_ssl=True,
            
            # DynamoDB 설정
            dynamodb_region=os.getenv("AWS_REGION", "ap-northeast-2")
        ),
        
        external_apis=ExternalAPIConfig(
            bok_api_key=self._load_from_parameter_store(
                f"/{self.service_name}/api/bok-key"
            )
        )
    )
```

### 2. 데이터베이스 연결 수정

#### shared/database.py
```python
async def _init_mysql(self):
    """Aurora 연결 초기화"""
    db_config = self.config.database
    
    # Aurora Data API 사용 (서버리스 환경)
    if self.config.environment != Environment.LOCAL:
        self._aurora_client = boto3.client('rds-data')
        self._cluster_arn = os.getenv("AURORA_CLUSTER_ARN")
        self._secret_arn = os.getenv("AURORA_SECRET_ARN")
    else:
        # 로컬에서는 기존 방식 사용
        self._mysql_pool = await aiomysql.create_pool(...)
```

### 3. 메시징 시스템 수정

#### shared/messaging.py
```python
async def _init_kafka_producer(self):
    """MSK 프로듀서 초기화"""
    if self.config.environment != Environment.LOCAL:
        # MSK IAM 인증 사용
        self.kafka_producer = AIOKafkaProducer(
            bootstrap_servers=self.config.messaging.kafka_bootstrap_servers,
            security_protocol='SASL_SSL',
            sasl_mechanism='AWS_MSK_IAM',
            sasl_oauth_token_provider=MSKTokenProvider()
        )
    else:
        # 로컬에서는 PLAINTEXT 사용
        self.kafka_producer = AIOKafkaProducer(...)
```

## 📊 성능 최적화

### 1. Lambda 최적화
```python
# Lambda 콜드 스타트 최소화
import json
import os

# 전역 변수로 연결 재사용
db_connection = None
redis_client = None

def lambda_handler(event, context):
    global db_connection, redis_client
    
    if db_connection is None:
        db_connection = initialize_db()
    
    if redis_client is None:
        redis_client = initialize_redis()
    
    # 비즈니스 로직 실행
    return process_request(event, context)
```

### 2. 캐시 전략
```python
# 다층 캐시 구조
class CacheStrategy:
    def __init__(self):
        self.l1_cache = {}  # 메모리 캐시
        self.l2_cache = redis_client  # Redis 캐시
        self.l3_cache = aurora_db  # 데이터베이스
    
    async def get(self, key):
        # L1 캐시 확인
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2 캐시 확인
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        # L3 데이터베이스 조회
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.set(key, value, ttl=600)
            self.l1_cache[key] = value
        
        return value
```

### 3. 데이터베이스 최적화
```sql
-- 인덱스 최적화
CREATE INDEX idx_exchange_rate_composite 
ON exchange_rate_history (currency_code, recorded_at DESC, source);

-- 파티셔닝 (월별)
ALTER TABLE exchange_rate_history 
PARTITION BY RANGE (YEAR(recorded_at) * 100 + MONTH(recorded_at));

-- 읽기 전용 복제본 활용
SELECT * FROM exchange_rate_history 
WHERE currency_code = 'USD' 
ORDER BY recorded_at DESC 
LIMIT 1;
```

## 🔒 보안 강화

### 1. API 보안
```python
# API 키 인증
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(token: str = Security(security)):
    # API 키 검증 로직
    if not is_valid_api_key(token.credentials):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token.credentials
```

### 2. 네트워크 보안
```yaml
# WAF 규칙
WebACL:
  Type: AWS::WAFv2::WebACL
  Properties:
    Rules:
      - Name: RateLimitRule
        Priority: 1
        Statement:
          RateBasedStatement:
            Limit: 1000
            AggregateKeyType: IP
        Action:
          Block: {}
```

### 3. 데이터 암호화
```python
# 민감 데이터 암호화
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY")
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

## 📈 모니터링 및 알림

### 1. 메트릭 수집
```python
# 커스텀 메트릭
import boto3

cloudwatch = boto3.client('cloudwatch')

def put_custom_metric(metric_name: str, value: float, unit: str = 'Count'):
    cloudwatch.put_metric_data(
        Namespace='CurrencyService',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )
```

### 2. 알림 설정
```yaml
# CloudWatch 알람
HighErrorRateAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: CurrencyService-HighErrorRate
    MetricName: Errors
    Namespace: AWS/Lambda
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref SNSTopicArn
```

## 🚀 배포 자동화

### 1. CI/CD 파이프라인
```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-2
    
    - name: Build and push Docker images
      run: |
        ./scripts/build-and-push.sh
    
    - name: Deploy Lambda functions
      run: |
        ./scripts/deploy-lambda.sh
    
    - name: Update EKS deployments
      run: |
        ./scripts/deploy-eks.sh
```

### 2. 블루-그린 배포
```python
# 무중단 배포 스크립트
def blue_green_deploy(service_name: str, new_version: str):
    # 1. 새 버전 배포 (Green)
    deploy_green_version(service_name, new_version)
    
    # 2. 헬스 체크
    if not health_check_passed(service_name, new_version):
        rollback_to_blue(service_name)
        return False
    
    # 3. 트래픽 전환
    switch_traffic_to_green(service_name)
    
    # 4. 이전 버전 정리 (Blue)
    cleanup_blue_version(service_name)
    
    return True
```

## 📋 운영 체크리스트

### 배포 전 체크리스트
- [ ] 모든 테스트 통과
- [ ] 보안 스캔 완료
- [ ] 성능 테스트 통과
- [ ] 문서 업데이트 완료
- [ ] 백업 계획 수립
- [ ] 롤백 계획 수립

### 배포 후 체크리스트
- [ ] 헬스 체크 통과
- [ ] 모니터링 대시보드 확인
- [ ] 알림 시스템 동작 확인
- [ ] 성능 메트릭 정상
- [ ] 로그 수집 정상
- [ ] 사용자 피드백 모니터링

### 운영 중 체크리스트
- [ ] 일일 헬스 체크
- [ ] 주간 성능 리뷰
- [ ] 월간 보안 점검
- [ ] 분기별 재해 복구 테스트
- [ ] 연간 아키텍처 리뷰

이 가이드를 따라 단계별로 진행하면 현재의 로컬 개발 환경을 안정적인 AWS 프로덕션 환경으로 성공적으로 전환할 수 있습니다.