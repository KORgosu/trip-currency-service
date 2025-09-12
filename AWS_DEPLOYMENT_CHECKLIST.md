# AWS 배포 체크리스트

## 🎯 배포 개요

이 체크리스트는 Currency Travel Service를 AWS 프로덕션 환경에 안전하고 체계적으로 배포하기 위한 단계별 가이드입니다.

## 📋 사전 준비 체크리스트

### ✅ 계정 및 권한 설정
- [ ] AWS 계정 생성 및 설정 완료
- [ ] IAM 사용자 생성 (프로그래밍 방식 액세스)
- [ ] 필요한 IAM 정책 연결
  - [ ] AmazonVPCFullAccess
  - [ ] AmazonRDSFullAccess
  - [ ] AmazonDynamoDBFullAccess
  - [ ] AWSLambda_FullAccess
  - [ ] AmazonAPIGatewayAdministrator
  - [ ] AmazonEKSClusterPolicy
  - [ ] AmazonS3FullAccess
- [ ] AWS CLI 설치 및 구성
- [ ] Terraform 설치 (v1.5+)
- [ ] kubectl 설치
- [ ] Docker 설치

### ✅ 코드 준비
- [ ] 모든 테스트 통과 확인
- [ ] 코드 리뷰 완료
- [ ] 보안 스캔 완료
- [ ] 문서 업데이트 완료
- [ ] 버전 태깅 완료

## 🏗️ Phase 1: 기본 인프라 구성

### 1.1 네트워크 인프라
```bash
# Terraform 초기화
cd infrastructure/terraform
terraform init
```

#### 체크리스트
- [ ] VPC 생성 (10.0.0.0/16)
- [ ] Public Subnets 생성 (3개 AZ)
- [ ] Private Subnets 생성 (3개 AZ)
- [ ] Database Subnets 생성 (3개 AZ)
- [ ] Internet Gateway 생성
- [ ] NAT Gateway 생성 (각 AZ별)
- [ ] Route Tables 구성
- [ ] Security Groups 생성

#### 검증 명령어
```bash
# VPC 확인
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=currency-service-vpc"

# 서브넷 확인
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxxxxxxxx"

# 보안 그룹 확인
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-xxxxxxxxx"
```

### 1.2 데이터베이스 구성

#### Aurora MySQL 클러스터
- [ ] Aurora MySQL 8.0 클러스터 생성
- [ ] 서브넷 그룹 생성
- [ ] 파라미터 그룹 생성 및 최적화
- [ ] 보안 그룹 설정 (포트 3306)
- [ ] 암호화 활성화
- [ ] 자동 백업 설정 (7일 보관)
- [ ] 모니터링 활성화

```bash
# Aurora 클러스터 상태 확인
aws rds describe-db-clusters --db-cluster-identifier currency-service-aurora

# 엔드포인트 확인
aws rds describe-db-cluster-endpoints --db-cluster-identifier currency-service-aurora
```

#### ElastiCache Redis
- [ ] Redis 7.0 클러스터 생성
- [ ] 서브넷 그룹 생성
- [ ] 파라미터 그룹 생성
- [ ] 보안 그룹 설정 (포트 6379)
- [ ] 전송 중 암호화 활성화
- [ ] 저장 시 암호화 활성화

```bash
# Redis 클러스터 상태 확인
aws elasticache describe-cache-clusters --cache-cluster-id currency-service-redis

# 엔드포인트 확인
aws elasticache describe-cache-clusters --cache-cluster-id currency-service-redis --show-cache-node-info
```

#### DynamoDB 테이블
- [ ] travel_destination_selections 테이블 생성
- [ ] RankingResults 테이블 생성
- [ ] GSI (Global Secondary Index) 설정
- [ ] Auto Scaling 설정
- [ ] Point-in-time Recovery 활성화
- [ ] 암호화 활성화

```bash
# DynamoDB 테이블 확인
aws dynamodb describe-table --table-name travel_destination_selections
aws dynamodb describe-table --table-name RankingResults
```

## 🚀 Phase 2: 애플리케이션 배포

### 2.1 ECR 리포지토리 생성
```bash
# 각 서비스별 ECR 리포지토리 생성
services=("currency-service" "ranking-service" "history-service" "data-ingestor")

for service in "${services[@]}"; do
  aws ecr create-repository --repository-name currency-service/${service}
done
```

#### 체크리스트
- [ ] currency-service ECR 리포지토리 생성
- [ ] ranking-service ECR 리포지토리 생성
- [ ] history-service ECR 리포지토리 생성
- [ ] data-ingestor ECR 리포지토리 생성
- [ ] 리포지토리 정책 설정
- [ ] 이미지 스캔 활성화

### 2.2 Lambda 함수 배포

#### Currency Service Lambda
```bash
# Docker 이미지 빌드 및 푸시
cd services/currency-service
docker build -t currency-service .
docker tag currency-service:latest ${ECR_URI}/currency-service/currency-service:latest
docker push ${ECR_URI}/currency-service/currency-service:latest

# Lambda 함수 생성
aws lambda create-function \
  --function-name currency-service \
  --package-type Image \
  --code ImageUri=${ECR_URI}/currency-service/currency-service:latest \
  --role arn:aws:iam::${ACCOUNT_ID}:role/lambda-execution-role
```

#### 체크리스트
- [ ] Currency Service Lambda 함수 생성
- [ ] Ranking Service Lambda 함수 생성
- [ ] History Service Lambda 함수 생성
- [ ] Lambda 실행 역할 생성 및 연결
- [ ] VPC 설정 (데이터베이스 접근용)
- [ ] 환경 변수 설정
- [ ] 메모리 및 타임아웃 최적화
- [ ] 동시 실행 제한 설정

#### 검증
```bash
# Lambda 함수 상태 확인
aws lambda get-function --function-name currency-service

# 테스트 실행
aws lambda invoke --function-name currency-service --payload '{}' response.json
```

### 2.3 API Gateway 설정

#### REST API 생성
```bash
# API Gateway 생성
aws apigateway create-rest-api --name currency-service-api

# 리소스 및 메서드 생성
aws apigateway create-resource --rest-api-id ${API_ID} --parent-id ${ROOT_ID} --path-part currencies
```

#### 체크리스트
- [ ] REST API 생성
- [ ] 리소스 구조 생성 (/api/v1/*)
- [ ] Lambda 통합 설정
- [ ] CORS 설정
- [ ] 인증 설정 (API Key)
- [ ] 사용량 계획 생성
- [ ] 스테이지 배포 (dev, prod)
- [ ] 커스텀 도메인 설정

#### 검증
```bash
# API 테스트
curl -X GET "https://${API_ID}.execute-api.ap-northeast-2.amazonaws.com/prod/api/v1/currencies/latest"
```

### 2.4 EKS 클러스터 (Data Ingestor)

#### 클러스터 생성
```bash
# EKS 클러스터 생성
aws eks create-cluster \
  --name currency-service-eks \
  --version 1.28 \
  --role-arn arn:aws:iam::${ACCOUNT_ID}:role/eks-service-role \
  --resources-vpc-config subnetIds=${SUBNET_IDS}
```

#### 체크리스트
- [ ] EKS 클러스터 생성
- [ ] 노드 그룹 생성
- [ ] kubectl 설정
- [ ] RBAC 설정
- [ ] 네임스페이스 생성
- [ ] ConfigMap 및 Secret 생성
- [ ] CronJob 배포
- [ ] 모니터링 설정

#### 검증
```bash
# 클러스터 상태 확인
aws eks describe-cluster --name currency-service-eks

# 노드 확인
kubectl get nodes

# CronJob 확인
kubectl get cronjobs -n currency-system
```

## 📨 Phase 3: 메시징 및 스토리지

### 3.1 MSK (Managed Kafka)

#### 클러스터 생성
```bash
# MSK 클러스터 생성
aws kafka create-cluster \
  --cluster-name currency-service-kafka \
  --broker-node-group-info file://broker-info.json \
  --kafka-version 2.8.1
```

#### 체크리스트
- [ ] MSK 클러스터 생성 (3개 브로커)
- [ ] 보안 그룹 설정
- [ ] IAM 인증 활성화
- [ ] 전송 중 암호화 활성화
- [ ] 모니터링 활성화
- [ ] 토픽 생성

#### 검증
```bash
# 클러스터 상태 확인
aws kafka describe-cluster --cluster-arn ${CLUSTER_ARN}

# 토픽 확인 (EKS 내에서)
kubectl exec -it kafka-client -- kafka-topics --bootstrap-server ${BOOTSTRAP_SERVERS} --list
```

### 3.2 S3 및 SQS

#### S3 버킷 생성
```bash
# S3 버킷 생성
aws s3 mb s3://currency-service-data-backup-${ACCOUNT_ID}
aws s3 mb s3://currency-service-logs-${ACCOUNT_ID}
```

#### 체크리스트
- [ ] 데이터 백업용 S3 버킷 생성
- [ ] 로그 저장용 S3 버킷 생성
- [ ] 버킷 정책 설정
- [ ] 버전 관리 활성화
- [ ] 암호화 설정
- [ ] 생명주기 정책 설정

#### SQS 큐 생성
- [ ] ranking-calculation-queue 생성
- [ ] data-processing-dlq 생성
- [ ] 메시지 보관 기간 설정
- [ ] DLQ 설정

## 🔒 Phase 4: 보안 및 설정

### 4.1 Parameter Store 설정

#### 민감 정보 저장
```bash
# 데이터베이스 비밀번호
aws ssm put-parameter \
  --name "/currency-service/db/password" \
  --value "${DB_PASSWORD}" \
  --type "SecureString"

# API 키들
aws ssm put-parameter \
  --name "/currency-service/api/bok-key" \
  --value "${BOK_API_KEY}" \
  --type "SecureString"
```

#### 체크리스트
- [ ] 데이터베이스 비밀번호 저장
- [ ] 외부 API 키 저장
- [ ] Redis 인증 토큰 저장 (필요시)
- [ ] 암호화 키 저장
- [ ] 파라미터 접근 권한 설정

### 4.2 IAM 역할 및 정책

#### Lambda 실행 역할
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 체크리스트
- [ ] Lambda 실행 역할 생성
- [ ] EKS 서비스 역할 생성
- [ ] EKS 노드 그룹 역할 생성
- [ ] DynamoDB 접근 정책 연결
- [ ] RDS 접근 정책 연결
- [ ] Parameter Store 접근 정책 연결
- [ ] MSK 접근 정책 연결

### 4.3 네트워크 보안

#### 보안 그룹 설정
- [ ] Lambda 보안 그룹 (아웃바운드만)
- [ ] RDS 보안 그룹 (3306 포트, Lambda에서만)
- [ ] ElastiCache 보안 그룹 (6379 포트, Lambda에서만)
- [ ] EKS 보안 그룹 (필요한 포트만)
- [ ] MSK 보안 그룹 (9092, 9094 포트)

#### WAF 설정
- [ ] Web ACL 생성
- [ ] Rate limiting 규칙 설정
- [ ] IP 화이트리스트/블랙리스트 설정
- [ ] SQL 인젝션 방지 규칙
- [ ] XSS 방지 규칙

## 📊 Phase 5: 모니터링 및 알림

### 5.1 CloudWatch 설정

#### 대시보드 생성
```bash
# 대시보드 생성
aws cloudwatch put-dashboard \
  --dashboard-name "CurrencyService-Overview" \
  --dashboard-body file://dashboard.json
```

#### 체크리스트
- [ ] 서비스 개요 대시보드 생성
- [ ] Lambda 메트릭 대시보드
- [ ] 데이터베이스 메트릭 대시보드
- [ ] 비즈니스 메트릭 대시보드
- [ ] 커스텀 메트릭 설정

### 5.2 알림 설정

#### SNS 토픽 및 구독
```bash
# SNS 토픽 생성
aws sns create-topic --name currency-service-alerts

# 이메일 구독
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:${ACCOUNT_ID}:currency-service-alerts \
  --protocol email \
  --notification-endpoint admin@company.com
```

#### CloudWatch 알람
- [ ] Lambda 에러율 알람
- [ ] Lambda 지연 시간 알람
- [ ] DynamoDB 스로틀링 알람
- [ ] RDS 연결 수 알람
- [ ] API Gateway 4xx/5xx 알람

### 5.3 로그 관리

#### CloudWatch Logs
- [ ] Lambda 로그 그룹 설정
- [ ] EKS 로그 수집 설정
- [ ] 로그 보관 기간 설정
- [ ] 로그 필터 설정

## 🧪 Phase 6: 테스트 및 검증

### 6.1 기능 테스트

#### API 엔드포인트 테스트
```bash
# Currency Service 테스트
curl -X GET "${API_ENDPOINT}/api/v1/currencies/latest?symbols=USD,JPY"

# Ranking Service 테스트
curl -X POST "${API_ENDPOINT}/api/v1/rankings/selections" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user","country_code":"JP"}'

# History Service 테스트
curl -X GET "${API_ENDPOINT}/api/v1/history?period=1w&target=USD"
```

#### 체크리스트
- [ ] 모든 API 엔드포인트 테스트
- [ ] 에러 처리 테스트
- [ ] 인증 테스트
- [ ] Rate limiting 테스트
- [ ] CORS 테스트

### 6.2 성능 테스트

#### 부하 테스트
```bash
# Artillery를 사용한 부하 테스트
artillery run load-test.yml
```

#### 체크리스트
- [ ] 응답 시간 테스트 (< 200ms)
- [ ] 처리량 테스트 (> 1000 RPS)
- [ ] 동시 사용자 테스트
- [ ] 스케일링 테스트
- [ ] 장애 복구 테스트

### 6.3 보안 테스트

#### 보안 스캔
```bash
# OWASP ZAP을 사용한 보안 스캔
zap-baseline.py -t ${API_ENDPOINT}
```

#### 체크리스트
- [ ] SQL 인젝션 테스트
- [ ] XSS 테스트
- [ ] 인증 우회 테스트
- [ ] 권한 상승 테스트
- [ ] 데이터 노출 테스트

## 🚀 Phase 7: 배포 및 운영

### 7.1 배포 실행

#### 블루-그린 배포
```bash
# 새 버전 배포 (Green)
./scripts/deploy-green.sh

# 헬스 체크
./scripts/health-check.sh

# 트래픽 전환
./scripts/switch-traffic.sh

# 이전 버전 정리 (Blue)
./scripts/cleanup-blue.sh
```

#### 체크리스트
- [ ] 배포 스크립트 실행
- [ ] 헬스 체크 통과
- [ ] 기능 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 모니터링 확인
- [ ] 로그 확인

### 7.2 운영 준비

#### 문서화
- [ ] 운영 매뉴얼 작성
- [ ] 장애 대응 가이드 작성
- [ ] API 문서 업데이트
- [ ] 모니터링 가이드 작성

#### 팀 교육
- [ ] 운영팀 교육 완료
- [ ] 개발팀 교육 완료
- [ ] 장애 대응 훈련 완료

## 📋 최종 체크리스트

### 배포 완료 확인
- [ ] 모든 서비스 정상 동작
- [ ] 모든 API 엔드포인트 응답
- [ ] 데이터베이스 연결 정상
- [ ] 캐시 시스템 정상
- [ ] 메시징 시스템 정상
- [ ] 모니터링 시스템 정상
- [ ] 알림 시스템 정상
- [ ] 로그 수집 정상

### 성능 확인
- [ ] 응답 시간 목표 달성
- [ ] 처리량 목표 달성
- [ ] 메모리 사용량 정상
- [ ] CPU 사용률 정상
- [ ] 네트워크 사용량 정상

### 보안 확인
- [ ] 모든 보안 그룹 설정 확인
- [ ] IAM 권한 최소화 확인
- [ ] 암호화 설정 확인
- [ ] 접근 로그 확인
- [ ] 보안 스캔 통과

### 운영 준비
- [ ] 백업 시스템 동작 확인
- [ ] 재해 복구 계획 수립
- [ ] 모니터링 대시보드 설정
- [ ] 알림 채널 설정
- [ ] 운영 문서 완성

## 🎉 배포 완료

축하합니다! Currency Travel Service가 AWS에 성공적으로 배포되었습니다.

### 다음 단계
1. **모니터링**: 첫 24시간 동안 집중 모니터링
2. **최적화**: 성능 데이터를 바탕으로 최적화
3. **확장**: 사용자 증가에 따른 스케일링 계획
4. **개선**: 사용자 피드백을 바탕으로 기능 개선

### 지원 연락처
- 기술 지원: tech-support@company.com
- 운영 지원: ops-support@company.com
- 긴급 상황: emergency@company.com