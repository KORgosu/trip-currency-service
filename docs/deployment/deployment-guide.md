# 배포 가이드 (Deployment Guide)

## 1. 배포 개요

본 가이드는 여행 물가 비교 서비스의 4개 마이크로서비스를 AWS 환경에 배포하는 전체 과정을 다룹니다. **Infrastructure as Code (IaC)** 원칙에 따라 Terraform으로 인프라를 구성하고, Jenkins CI/CD 파이프라인으로 애플리케이션을 자동 배포합니다.

### 1.1 배포 아키텍처
- **Currency Service**: AWS Lambda + API Gateway
- **Ranking Service**: AWS Lambda + API Gateway  
- **Data Ingestor**: EKS CronJob
- **History Service**: AWS Lambda + API Gateway

### 1.2 배포 순서
1. 기본 인프라 구성 (VPC, 보안 그룹 등)
2. 데이터 레이어 구성 (Aurora, DynamoDB, ElastiCache)
3. 메시징 레이어 구성 (MSK, SQS)
4. 애플리케이션 배포 (Lambda, EKS)
5. 모니터링 및 알림 설정

## 2. 사전 준비사항

### 2.1 필수 도구 설치
```bash
# AWS CLI 설치 및 설정
aws configure
aws sts get-caller-identity

# Terraform 설치 (v1.5+)
terraform --version

# kubectl 설치 (EKS 관리용)
kubectl version --client

# Docker 설치 (이미지 빌드용)
docker --version

# Helm 설치 (EKS 애플리케이션 배포용)
helm version
```

### 2.2 AWS 권한 설정
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "iam:*",
        "lambda:*",
        "apigateway:*",
        "rds:*",
        "dynamodb:*",
        "elasticache:*",
        "eks:*",
        "kafka:*",
        "sqs:*",
        "s3:*",
        "cloudwatch:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.3 환경 변수 설정
```bash
# 배포 환경 설정
export AWS_REGION=ap-northeast-2
export PROJECT_NAME=currency-service
export ENVIRONMENT=prod
export DOMAIN_NAME=your-domain.com

# ECR 리포지토리 URL
export ECR_REGISTRY=123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
```

## 3. 인프라 배포 (Terraform)

### 3.1 Terraform 백엔드 설정
```bash
# S3 버킷 생성 (Terraform 상태 저장용)
aws s3 mb s3://currency-service-terraform-state-${AWS_REGION}

# DynamoDB 테이블 생성 (상태 잠금용)
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### 3.2 Terraform 초기화 및 계획
```bash
cd infrastructure/terraform

# Terraform 초기화
terraform init

# 배포 계획 확인
terraform plan -var-file="environments/${ENVIRONMENT}.tfvars"

# 인프라 배포
terraform apply -var-file="environments/${ENVIRONMENT}.tfvars"
```

### 3.3 주요 Terraform 모듈

#### 3.3.1 네트워크 모듈
```hcl
# infrastructure/terraform/modules/network/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "public" {
  count = length(var.availability_zones)
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]
  
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Type = "public"
  }
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-private-${count.index + 1}"
    Type = "private"
  }
}
```

#### 3.3.2 데이터베이스 모듈
```hcl
# infrastructure/terraform/modules/database/main.tf
resource "aws_rds_cluster" "aurora" {
  cluster_identifier      = "${var.project_name}-aurora"
  engine                 = "aurora-mysql"
  engine_version         = "8.0.mysql_aurora.3.02.0"
  database_name          = var.database_name
  master_username        = var.master_username
  master_password        = var.master_password
  
  vpc_security_group_ids = [aws_security_group.aurora.id]
  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  
  skip_final_snapshot = var.environment != "prod"
  
  tags = {
    Name = "${var.project_name}-aurora"
    Environment = var.environment
  }
}

resource "aws_rds_cluster_instance" "aurora_instances" {
  count              = var.instance_count
  identifier         = "${var.project_name}-aurora-${count.index}"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version
}
```

#### 3.3.3 Lambda 모듈
```hcl
# infrastructure/terraform/modules/lambda/main.tf
resource "aws_lambda_function" "service" {
  function_name = "${var.project_name}-${var.service_name}"
  role         = aws_iam_role.lambda_role.arn
  
  image_uri    = "${var.ecr_repository_url}:${var.image_tag}"
  package_type = "Image"
  
  memory_size = var.memory_size
  timeout     = var.timeout
  
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }
  
  environment {
    variables = var.environment_variables
  }
  
  tags = {
    Name = "${var.project_name}-${var.service_name}"
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.service.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.api_gateway_arn}/*/*"
}
```

## 4. 애플리케이션 배포

### 4.1 ECR 리포지토리 생성
```bash
# 각 서비스별 ECR 리포지토리 생성
services=("currency-service" "ranking-service" "data-ingestor" "history-service")

for service in "${services[@]}"; do
  aws ecr create-repository \
    --repository-name ${PROJECT_NAME}/${service} \
    --region ${AWS_REGION}
done
```

### 4.2 Docker 이미지 빌드 및 푸시

#### 4.2.1 Currency Service 배포
```bash
cd services/currency-service

# Docker 이미지 빌드
docker build -t currency-service .

# ECR 로그인
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

# 이미지 태깅 및 푸시
docker tag currency-service:latest ${ECR_REGISTRY}/${PROJECT_NAME}/currency-service:latest
docker push ${ECR_REGISTRY}/${PROJECT_NAME}/currency-service:latest

# Lambda 함수 업데이트
aws lambda update-function-code \
  --function-name ${PROJECT_NAME}-currency-service \
  --image-uri ${ECR_REGISTRY}/${PROJECT_NAME}/currency-service:latest
```

#### 4.2.2 Data Ingestor (EKS) 배포
```bash
cd services/data-ingestor

# Docker 이미지 빌드 및 푸시
docker build -t data-ingestor .
docker tag data-ingestor:latest ${ECR_REGISTRY}/${PROJECT_NAME}/data-ingestor:latest
docker push ${ECR_REGISTRY}/${PROJECT_NAME}/data-ingestor:latest

# EKS 클러스터 연결
aws eks update-kubeconfig --region ${AWS_REGION} --name ${PROJECT_NAME}-eks

# Kubernetes 매니페스트 적용
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/cronjob.yaml
```

### 4.3 EKS CronJob 매니페스트

#### 4.3.1 네임스페이스 생성
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: currency-system
  labels:
    name: currency-system
```

#### 4.3.2 ConfigMap 설정
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: data-ingestor-config
  namespace: currency-system
data:
  KAFKA_BOOTSTRAP_SERVERS: "your-msk-cluster.kafka.ap-northeast-2.amazonaws.com:9092"
  S3_BUCKET: "currency-data-backup"
  COLLECTION_INTERVAL: "300"  # 5분
  MAX_RETRY_ATTEMPTS: "3"
```

#### 4.3.3 Secret 설정
```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: data-ingestor-secrets
  namespace: currency-system
type: Opaque
data:
  BOK_API_KEY: <base64-encoded-key>
  FED_API_KEY: <base64-encoded-key>
  SQS_QUEUE_URL: <base64-encoded-url>
```

#### 4.3.4 CronJob 정의
```yaml
# k8s/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: data-ingestor
  namespace: currency-system
spec:
  schedule: "*/5 * * * *"
  timeZone: "Asia/Seoul"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: data-ingestor-sa
          restartPolicy: OnFailure
          containers:
          - name: data-ingestor
            image: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/currency-service/data-ingestor:latest
            imagePullPolicy: Always
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
            envFrom:
            - configMapRef:
                name: data-ingestor-config
            - secretRef:
                name: data-ingestor-secrets
```

## 5. CI/CD 파이프라인 설정

### 5.1 Jenkins 파이프라인 (Jenkinsfile)
```groovy
pipeline {
    agent any
    
    environment {
        AWS_REGION = 'ap-northeast-2'
        ECR_REGISTRY = '123456789012.dkr.ecr.ap-northeast-2.amazonaws.com'
        PROJECT_NAME = 'currency-service'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        script {
                            sh '''
                                cd services/${SERVICE_NAME}
                                pip install -r requirements.txt
                                python -m pytest tests/ -v
                            '''
                        }
                    }
                }
                
                stage('Security Scan') {
                    steps {
                        sh '''
                            # Snyk 보안 스캔
                            snyk test --severity-threshold=high
                        '''
                    }
                }
            }
        }
        
        stage('Build') {
            steps {
                script {
                    def services = ['currency-service', 'ranking-service', 'history-service']
                    
                    services.each { service ->
                        sh """
                            cd services/${service}
                            docker build -t ${service}:${BUILD_NUMBER} .
                            docker tag ${service}:${BUILD_NUMBER} ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:${BUILD_NUMBER}
                            docker tag ${service}:${BUILD_NUMBER} ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:latest
                        """
                    }
                }
            }
        }
        
        stage('Push to ECR') {
            steps {
                script {
                    sh '''
                        # ECR 로그인
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    '''
                    
                    def services = ['currency-service', 'ranking-service', 'history-service']
                    
                    services.each { service ->
                        sh """
                            docker push ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:${BUILD_NUMBER}
                            docker push ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:latest
                        """
                    }
                }
            }
        }
        
        stage('Deploy') {
            parallel {
                stage('Deploy Lambda Services') {
                    steps {
                        script {
                            def lambdaServices = ['currency-service', 'ranking-service', 'history-service']
                            
                            lambdaServices.each { service ->
                                sh """
                                    aws lambda update-function-code \
                                        --function-name ${PROJECT_NAME}-${service} \
                                        --image-uri ${ECR_REGISTRY}/${PROJECT_NAME}/${service}:${BUILD_NUMBER} \
                                        --region ${AWS_REGION}
                                """
                            }
                        }
                    }
                }
                
                stage('Deploy EKS CronJob') {
                    steps {
                        sh '''
                            # EKS 클러스터 연결
                            aws eks update-kubeconfig --region ${AWS_REGION} --name ${PROJECT_NAME}-eks
                            
                            # 이미지 태그 업데이트
                            kubectl set image cronjob/data-ingestor \
                                data-ingestor=${ECR_REGISTRY}/${PROJECT_NAME}/data-ingestor:${BUILD_NUMBER} \
                                -n currency-system
                        '''
                    }
                }
            }
        }
        
        stage('Integration Tests') {
            steps {
                sh '''
                    # API 엔드포인트 테스트
                    python tests/integration/test_api_endpoints.py
                    
                    # 데이터 플로우 테스트
                    python tests/integration/test_data_flow.py
                '''
            }
        }
    }
    
    post {
        success {
            slackSend(
                channel: '#deployments',
                color: 'good',
                message: "✅ 배포 성공: ${PROJECT_NAME} - Build #${BUILD_NUMBER}"
            )
        }
        
        failure {
            slackSend(
                channel: '#deployments',
                color: 'danger',
                message: "❌ 배포 실패: ${PROJECT_NAME} - Build #${BUILD_NUMBER}"
            )
        }
    }
}
```

### 5.2 GitHub Actions 워크플로우 (대안)
```yaml
# .github/workflows/deploy.yml
name: Deploy Currency Service

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: ap-northeast-2
  ECR_REGISTRY: 123456789012.dkr.ecr.ap-northeast-2.amazonaws.com
  PROJECT_NAME: currency-service

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    
    - name: Run tests
      run: |
        pytest tests/ -v
  
  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker images
      run: |
        services=("currency-service" "ranking-service" "history-service")
        
        for service in "${services[@]}"; do
          cd services/$service
          
          docker build -t $service .
          docker tag $service:latest $ECR_REGISTRY/$PROJECT_NAME/$service:$GITHUB_SHA
          docker tag $service:latest $ECR_REGISTRY/$PROJECT_NAME/$service:latest
          
          docker push $ECR_REGISTRY/$PROJECT_NAME/$service:$GITHUB_SHA
          docker push $ECR_REGISTRY/$PROJECT_NAME/$service:latest
          
          cd ../..
        done
    
    - name: Deploy Lambda functions
      run: |
        services=("currency-service" "ranking-service" "history-service")
        
        for service in "${services[@]}"; do
          aws lambda update-function-code \
            --function-name $PROJECT_NAME-$service \
            --image-uri $ECR_REGISTRY/$PROJECT_NAME/$service:$GITHUB_SHA
        done
    
    - name: Deploy EKS CronJob
      run: |
        aws eks update-kubeconfig --region $AWS_REGION --name $PROJECT_NAME-eks
        
        kubectl set image cronjob/data-ingestor \
          data-ingestor=$ECR_REGISTRY/$PROJECT_NAME/data-ingestor:$GITHUB_SHA \
          -n currency-system
```

## 6. 배포 검증

### 6.1 헬스 체크 스크립트
```bash
#!/bin/bash
# scripts/health-check.sh

API_BASE_URL="https://api.your-domain.com/api/v1"

echo "🔍 서비스 헬스 체크 시작..."

# Currency Service 테스트
echo "📊 Currency Service 테스트"
response=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/currencies/latest?symbols=USD")
if [ $response -eq 200 ]; then
    echo "✅ Currency Service: OK"
else
    echo "❌ Currency Service: FAIL (HTTP $response)"
fi

# Ranking Service 테스트
echo "🏆 Ranking Service 테스트"
response=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/rankings?period=daily")
if [ $response -eq 200 ]; then
    echo "✅ Ranking Service: OK"
else
    echo "❌ Ranking Service: FAIL (HTTP $response)"
fi

# History Service 테스트
echo "📈 History Service 테스트"
response=$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}/history?period=1w&target=USD")
if [ $response -eq 200 ]; then
    echo "✅ History Service: OK"
else
    echo "❌ History Service: FAIL (HTTP $response)"
fi

# Data Ingestor CronJob 상태 확인
echo "⚙️ Data Ingestor CronJob 상태 확인"
kubectl get cronjob data-ingestor -n currency-system
kubectl get jobs -n currency-system | grep data-ingestor | head -5

echo "🎉 헬스 체크 완료!"
```

### 6.2 통합 테스트
```python
# tests/integration/test_end_to_end.py
import requests
import pytest
import time

class TestEndToEndFlow:
    def setup_class(self):
        self.base_url = "https://api.your-domain.com/api/v1"
        
    def test_currency_service_response_time(self):
        """환율 서비스 응답 시간 테스트"""
        start_time = time.time()
        response = requests.get(f"{self.base_url}/currencies/latest?symbols=USD,JPY")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 1초 이내 응답
        
        data = response.json()
        assert "rates" in data
        assert "USD" in data["rates"]
        
    def test_ranking_service_data_consistency(self):
        """랭킹 서비스 데이터 일관성 테스트"""
        # 선택 기록
        selection_data = {
            "user_id": "test-user-123",
            "country_code": "JP"
        }
        
        response = requests.post(
            f"{self.base_url}/rankings/selections",
            json=selection_data
        )
        assert response.status_code == 201
        
        # 랭킹 조회 (약간의 지연 후)
        time.sleep(2)
        response = requests.get(f"{self.base_url}/rankings?period=daily")
        assert response.status_code == 200
        
        data = response.json()
        assert "ranking" in data
        assert len(data["ranking"]) > 0
        
    def test_history_service_data_range(self):
        """이력 서비스 데이터 범위 테스트"""
        response = requests.get(f"{self.base_url}/history?period=1m&target=USD")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "statistics" in data
        
        # 1개월 데이터 확인 (대략 30개 데이터 포인트)
        assert len(data["results"]) >= 20
        assert len(data["results"]) <= 35
```

## 7. 롤백 전략

### 7.1 Lambda 함수 롤백
```bash
#!/bin/bash
# scripts/rollback-lambda.sh

SERVICE_NAME=$1
PREVIOUS_VERSION=$2

if [ -z "$SERVICE_NAME" ] || [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: $0 <service-name> <previous-version>"
    exit 1
fi

echo "🔄 Rolling back $SERVICE_NAME to version $PREVIOUS_VERSION"

# 이전 버전으로 롤백
aws lambda update-function-code \
    --function-name ${PROJECT_NAME}-${SERVICE_NAME} \
    --image-uri ${ECR_REGISTRY}/${PROJECT_NAME}/${SERVICE_NAME}:${PREVIOUS_VERSION}

# 롤백 확인
aws lambda get-function --function-name ${PROJECT_NAME}-${SERVICE_NAME} \
    --query 'Code.ImageUri' --output text

echo "✅ Rollback completed for $SERVICE_NAME"
```

### 7.2 EKS CronJob 롤백
```bash
#!/bin/bash
# scripts/rollback-cronjob.sh

PREVIOUS_VERSION=$1

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: $0 <previous-version>"
    exit 1
fi

echo "🔄 Rolling back Data Ingestor CronJob to version $PREVIOUS_VERSION"

# 이미지 버전 롤백
kubectl set image cronjob/data-ingestor \
    data-ingestor=${ECR_REGISTRY}/${PROJECT_NAME}/data-ingestor:${PREVIOUS_VERSION} \
    -n currency-system

# 롤백 확인
kubectl describe cronjob data-ingestor -n currency-system | grep Image

echo "✅ Rollback completed for Data Ingestor CronJob"
```

## 8. 모니터링 및 알림 설정

### 8.1 CloudWatch 대시보드 생성
```bash
# scripts/create-dashboard.sh
aws cloudwatch put-dashboard \
    --dashboard-name "CurrencyService-Overview" \
    --dashboard-body file://monitoring/dashboard.json
```

### 8.2 알림 설정
```bash
# SNS 토픽 생성
aws sns create-topic --name currency-service-alerts

# CloudWatch 알람 생성
aws cloudwatch put-metric-alarm \
    --alarm-name "currency-service-error-rate" \
    --alarm-description "Currency Service error rate too high" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

이 배포 가이드를 따라하면 전체 시스템을 안정적이고 자동화된 방식으로 AWS에 배포할 수 있습니다. 각 단계별로 검증을 수행하고, 문제 발생 시 빠른 롤백이 가능하도록 구성되어 있습니다.