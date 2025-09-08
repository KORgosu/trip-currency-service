# 시스템 아키텍처 상세 설계

## 1. 전체 시스템 개요

여행 물가 비교 서비스는 **4개의 핵심 마이크로서비스**로 구성된 클라우드 네이티브 아키텍처입니다. 각 서비스는 독립적으로 배포되고 확장 가능하며, 서로 다른 AWS 서비스를 활용하여 최적의 성능과 비용 효율성을 달성합니다.

### 1.1 서비스 구성
- **Currency Service** (Lambda): 실시간 환율 조회
- **Ranking Service** (Lambda): 사용자 활동 기록 및 랭킹 제공  
- **Data Ingestor** (CronJob): 외부 데이터 수집 및 처리
- **History Service** (Lambda): 환율 이력 분석 및 차트 데이터

### 1.2 아키텍처 원칙
- **마이크로서비스**: 각 서비스는 단일 책임을 가지며 독립적으로 배포
- **서버리스 우선**: Lambda를 활용한 비용 효율적 운영
- **이벤트 기반**: 비동기 메시징으로 서비스 간 결합도 최소화
- **폴리글랏 퍼시스턴스**: 각 데이터 특성에 맞는 최적의 저장소 선택

## 2. 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                글로벌 레이어                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│  Route 53 (DNS) → CloudFront (CDN) → WAF (보안)                                │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
            │   서울 리전   │ │   도쿄 리전  │ │ 싱가포르 리전│
            └──────────────┘ └─────────────┘ └────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              서울 리전 상세 구성                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │   사용자 요청    │    │                 API Gateway                      │   │
│  └─────────────────┘    └──────────────────┬───────────────────────────────┘   │
│                                           │                                   │
│  ┌─────────────────────────────────────────┼─────────────────────────────────┐ │
│  │                    Lambda 서비스 레이어                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│  │  │ Currency    │  │ Ranking     │  │ History     │  │ User        │     │ │
│  │  │ Service     │  │ Service     │  │ Service     │  │ Selection   │     │ │
│  │  │ (Lambda)    │  │ (Lambda)    │  │ (Lambda)    │  │ Handler     │     │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│  └─────────────────────────────────────────┼─────────────────────────────────┘ │
│                                           │                                   │
│  ┌─────────────────────────────────────────┼─────────────────────────────────┐ │
│  │                    데이터 수집 레이어                                       │ │
│  │  ┌─────────────────────────────────────┐                                 │ │
│  │  │        EKS 클러스터                  │                                 │ │
│  │  │  ┌─────────────────────────────────┐ │                                 │ │
│  │  │  │     Data Ingestor CronJob       │ │                                 │ │
│  │  │  │   (매 5분마다 실행)              │ │                                 │ │
│  │  │  └─────────────────────────────────┘ │                                 │ │
│  │  └─────────────────────────────────────┘                                 │ │
│  └─────────────────────────────────────────┼─────────────────────────────────┘ │
│                                           │                                   │
│  ┌─────────────────────────────────────────┼─────────────────────────────────┐ │
│  │                   메시징 레이어                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                       │ │
│  │  │    MSK      │  │     SQS     │  │ EventBridge │                       │ │
│  │  │  (Kafka)    │  │  (Fallback) │  │ (Scheduler) │                       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                       │ │
│  └─────────────────────────────────────────┼─────────────────────────────────┘ │
│                                           │                                   │
│  ┌─────────────────────────────────────────┼─────────────────────────────────┐ │
│  │                   데이터 레이어                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │ │
│  │  │   Aurora    │  │ ElastiCache │  │ DynamoDB    │  │     S3      │     │ │
│  │  │ (이력 데이터) │  │  (캐시)     │  │(사용자 활동) │  │ (백업/정적) │     │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3. 서비스별 상세 아키텍처

### 3.1 Currency Service (실시간 환율 조회)

```
[API Gateway] → [Currency Service Lambda] → [ElastiCache Redis]
                                         ↓ (캐시 미스 시)
                                    [Aurora DB (폴백)]
```

**주요 특징:**
- **배포 방식**: AWS Lambda (서버리스)
- **응답 시간**: < 100ms (Redis 캐시 활용)
- **확장성**: 자동 스케일링 (동시 실행 제한: 100)
- **데이터 소스**: Redis 우선, Aurora 폴백

### 3.2 Ranking Service (랭킹 및 사용자 활동)

```
[API Gateway] → [Ranking Service Lambda] → [DynamoDB]
                                        ↓
                [SQS] → [Ranking Calculator Lambda] → [DynamoDB]
```

**주요 특징:**
- **배포 방식**: AWS Lambda (서버리스)
- **데이터 저장**: DynamoDB Global Tables
- **비동기 처리**: SQS를 통한 랭킹 계산 분리
- **실시간성**: 사용자 선택 즉시 기록, 랭킹은 주기적 계산

### 3.3 Data Ingestor (데이터 수집)

```
[EventBridge Scheduler] → [EKS CronJob] → [외부 APIs]
                                       ↓
                        [데이터 검증] → [S3 백업] → [MSK Kafka]
                                                  ↓ (장애 시)
                                              [SQS Fallback]
```

**주요 특징:**
- **배포 방식**: Kubernetes CronJob (매 5분 실행)
- **데이터 소스**: 한국은행, Fed, ECB, BOJ APIs
- **장애 복구**: 다중 소스 + 백업 API 자동 전환
- **스트리밍**: Kafka 우선, SQS 폴백

### 3.4 History Service (환율 이력 분석)

```
[API Gateway] → [History Service Lambda] → [Redis Cache]
                                        ↓ (캐시 미스 시)
                                    [Aurora DB] → [데이터 분석]
```

**주요 특징:**
- **배포 방식**: AWS Lambda (서버리스)
- **데이터 분석**: 통계 계산, 트렌드 분석, 상관관계 분석
- **성능 최적화**: 집계 테이블 + 파티셔닝
- **캐싱 전략**: 기간별 차등 TTL 적용

## 4. 데이터 플로우

### 4.1 실시간 데이터 수집 플로우

```
1. [EventBridge] → 매 5분마다 트리거
2. [Data Ingestor CronJob] → 외부 API 호출
3. [데이터 검증 & 정제] → 품질 보장
4. [S3 원본 저장] → 백업 및 감사
5. [MSK Kafka] → 실시간 스트리밍
6. [Rate Processor Lambda] → Kafka 메시지 소비
7. [Aurora + Redis] → 데이터 저장 및 캐싱
```

### 4.2 사용자 요청 처리 플로우

```
1. [사용자 요청] → Route 53 DNS 해석
2. [CloudFront] → 가장 가까운 엣지에서 응답
3. [API Gateway] → 요청 라우팅 및 인증
4. [Lambda 서비스] → 비즈니스 로직 처리
5. [데이터 레이어] → 캐시 우선 조회
6. [응답 반환] → JSON 형태로 결과 제공
```

## 5. 네트워크 및 보안 아키텍처

### 5.1 VPC 구성

```
VPC (10.0.0.0/16)
├── Public Subnet (10.0.1.0/24)  # ALB, NAT Gateway
├── Private Subnet (10.0.2.0/24) # EKS Worker Nodes
├── DB Subnet (10.0.3.0/24)      # Aurora, ElastiCache
└── Lambda Subnet (10.0.4.0/24)  # Lambda ENI (VPC 연결 시)
```

### 5.2 보안 그룹 설정

```yaml
# ALB Security Group
ALBSecurityGroup:
  Ingress:
    - Port: 80, 443
      Source: 0.0.0.0/0
  Egress:
    - Port: 8000-8003
      Target: EKSSecurityGroup

# EKS Security Group  
EKSSecurityGroup:
  Ingress:
    - Port: 8000-8003
      Source: ALBSecurityGroup
  Egress:
    - Port: 3306, 6379
      Target: DatabaseSecurityGroup

# Database Security Group
DatabaseSecurityGroup:
  Ingress:
    - Port: 3306 (Aurora)
      Source: EKSSecurityGroup, LambdaSecurityGroup
    - Port: 6379 (Redis)
      Source: EKSSecurityGroup, LambdaSecurityGroup
```

## 6. 고가용성 및 재해 복구

### 6.1 멀티 리전 구성

```
Primary Region (서울)
├── 모든 서비스 활성 운영
├── Aurora Writer 인스턴스
└── DynamoDB Global Tables

Secondary Region (도쿄)  
├── 모든 서비스 대기 상태
├── Aurora Reader 인스턴스
└── DynamoDB Global Tables

Tertiary Region (싱가포르)
├── 재해 복구용 최소 구성
└── DynamoDB Global Tables
```

### 6.2 장애 조치 메커니즘

```
1. [CloudWatch Alarms] → 서비스 상태 모니터링
2. [Route 53 Health Checks] → 엔드포인트 상태 확인
3. [Failover Lambda] → 자동 트래픽 전환
4. [Route 53 ARC] → 리전 간 트래픽 제어
```

## 7. 모니터링 및 관찰성

### 7.1 메트릭 수집

```
Application Metrics (CloudWatch)
├── Lambda 실행 시간, 에러율, 동시 실행 수
├── API Gateway 요청 수, 지연 시간, 4xx/5xx 에러
├── DynamoDB 읽기/쓰기 용량, 스로틀링
└── Aurora 연결 수, 쿼리 성능, 복제 지연

Infrastructure Metrics (Prometheus)
├── EKS 클러스터 리소스 사용률
├── MSK Kafka 메시지 처리량, 지연 시간
├── ElastiCache 캐시 히트율, 메모리 사용률
└── S3 요청 수, 저장 용량
```

### 7.2 로그 수집 및 분석

```
Log Pipeline
├── [Application Logs] → CloudWatch Logs
├── [EKS Container Logs] → Fluentd → OpenSearch
├── [API Gateway Logs] → CloudWatch Logs
└── [VPC Flow Logs] → S3 → Athena 분석
```

## 8. 성능 최적화 전략

### 8.1 캐싱 전략

```
Multi-Level Caching
├── L1: CloudFront (정적 콘텐츠, TTL: 24시간)
├── L2: API Gateway (API 응답, TTL: 5분)  
├── L3: ElastiCache (환율 데이터, TTL: 10분)
└── L4: DynamoDB DAX (랭킹 데이터, TTL: 1분)
```

### 8.2 데이터베이스 최적화

```sql
-- Aurora 최적화
- Read Replica 활용한 읽기 부하 분산
- 파티셔닝으로 대용량 이력 데이터 관리
- 커버링 인덱스로 쿼리 성능 향상

-- DynamoDB 최적화  
- 적절한 파티션 키 설계로 핫 파티션 방지
- GSI 활용한 다양한 쿼리 패턴 지원
- Auto Scaling으로 트래픽 변화 대응
```

## 9. 비용 최적화

### 9.1 서버리스 우선 전략

```
Cost Optimization
├── Lambda: 실행 시간만 과금, 유휴 비용 없음
├── DynamoDB: On-Demand 모드로 사용량 기반 과금
├── Aurora Serverless: 트래픽에 따른 자동 스케일링
└── S3 Intelligent Tiering: 접근 패턴에 따른 자동 계층화
```

### 9.2 리소스 최적화

```yaml
# Lambda 메모리 최적화
CurrencyService: 512MB (빠른 응답 필요)
RankingService: 256MB (단순 CRUD)
HistoryService: 1024MB (데이터 분석 작업)

# DynamoDB 용량 모드
UserSelections: On-Demand (트래픽 변동 큼)
RankingResults: Provisioned (예측 가능한 읽기)
```

## 10. 확장성 고려사항

### 10.1 수평 확장

```
Horizontal Scaling
├── Lambda: 자동 스케일링 (동시 실행 제한으로 제어)
├── EKS: HPA + Cluster Autoscaler
├── DynamoDB: 파티션 자동 분할
└── ElastiCache: 클러스터 모드로 샤딩
```

### 10.2 수직 확장

```
Vertical Scaling
├── Lambda: 메모리 증가로 CPU 성능 향상
├── Aurora: 인스턴스 클래스 업그레이드
├── ElastiCache: 노드 타입 업그레이드
└── EKS: 워커 노드 인스턴스 타입 변경
```

이 아키텍처는 **클라우드 네이티브 원칙**을 따라 설계되어 높은 가용성, 확장성, 비용 효율성을 제공하며, 각 서비스의 특성에 맞는 최적의 AWS 서비스를 활용합니다.