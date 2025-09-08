---

### `technology-stack.md`

# 🛠️ 기술 스택 및 사용처 (Technology Stack and Usage)

본 문서는 '여행 물가 비교 서비스' 프로젝트를 구성하는 모든 기술 스택과 각 기술의 역할, 그리고 구체적인 사용처를 정의합니다.

## 1. 인프라 관리 (Infrastructure Management)

인프라를 코드로 관리하여 모든 환경(개발, 운영)에 일관되고 안정적인 인프라를 구축하고 유지합니다.

* **Terraform (테라폼)**
    * **사용처:** AWS의 모든 핵심 인프라(VPC, Subnet, ECS 클러스터, Aurora DB, ElastiCache, MSK 등)를 코드로 정의하고 생성/관리합니다. `aws/` 폴더 내 `.tf` 파일들이 여기에 해당합니다.
    * **역할:** **인프라 프로비저닝 자동화.**

* **AWS System Manager (Parameter Store)**
    * **사용처:** DB 접속 정보, 외부 API 키 등 민감한 설정 값들을 안전하게 저장하고 관리합니다. ECS 태스크 정의에서 이 값들을 참조하여 컨테이너에 환경 변수로 주입합니다.
    * **역할:** **보안 및 구성 관리.**

---

## 2. CI/CD (지속적 통합 및 배포)

코드 변경 사항을 자동으로 빌드, 테스트하고 안정적으로 서버에 배포하는 과정을 자동화합니다.

* **Jenkins (젠킨스)**
    * **사용처:** Git 푸시를 감지하여 전체 CI/CD 파이프라인을 실행하는 오케스트레이션 도구입니다. `jenkins/` 폴더의 `Jenkinsfile`로 파이프라인을 코드로 관리합니다.
    * **역할:** **CI/CD 파이프라인 실행 및 제어.**

* **Amazon ECR (Elastic Container Registry)**
    * **사용처:** Jenkins에서 빌드된 모든 마이크로서비스의 Docker 이미지를 버전별로 안전하게 저장하는 প্রাই빗 저장소입니다. ECS는 여기에서 이미지를 가져와 컨테이너를 실행합니다.
    * **역할:** **Docker 이미지 저장 및 관리.**

* **AWS CodeDeploy (코드디플로이)**
    * **사용처:** ECS에 새로운 버전의 애플리케이션을 배포할 때, 중단 시간을 최소화하는 롤링 업데이트(Rolling Update)나 블루/그린(Blue/Green) 배포 전략을 자동화하고 관리합니다.
    * **역할:** **안전하고 자동화된 배포 전략 실행.**

---

## 3. 데이터 파이프라인 (Data Pipeline)

외부 환율 데이터를 주기적으로 수집하고, 안정적으로 처리하여 각 데이터베이스에 분산 저장합니다.

* **Amazon EventBridge (이벤트브릿지)**
    * **사용처:** "매 10분마다"와 같은 Cron 표현식을 사용하여 `data-ingestor-lambda`를 주기적으로 트리거합니다.
    * **역할:** **스케줄링 및 이벤트 기반 트리거.**

* **AWS Lambda (람다)**
    * **사용처:** `data-ingestor-lambda`, `rate-processor-lambda`, `ranking-calculator-lambda`, `failover-handler-lambda` 등 특정 이벤트에 반응하여 코드를 실행하는 서버리스 컴퓨팅의 핵심입니다.
    * **역할:** **이벤트 기반 경량 작업 수행.**

    ### ##  Lambda 함수 전체 목록

아래는 우리 프로젝트에 필요한 모든 Lambda 함수와 그 역할을 정리한 최종 표입니다.

| Lambda 함수 이름 | 별칭 | 역할 (Role) | 트리거 (Trigger) |
| :--- | :--- | :--- | :--- |
| `data-ingestor-lambda` | **일꾼 A** | **[수집]** 환율 API 호출 → SQS/Kafka 전송 | **EventBridge** (시간 기반) |
| `rate-processor-lambda` | **일꾼 B** | **[처리]** SQS/Kafka 메시지 처리 → S3, Aurora, Redis 저장 | **SQS/Kafka** (메시지 기반) |
| `user-selection-handler-lambda` | **일꾼 C** | **[기록]** 사용자 선택 실시간 기록 → DynamoDB 저장 | **API Gateway** (HTTP 요청) |
| `ranking-calculator-lambda` | **일꾼 D** | **[계산]** 주기적 랭킹 집계 및 계산 → DynamoDB 저장 | **EventBridge** (시간 기반) |
| `failover-handler-lambda` | **일꾼 E** | **[대응]** 리전 장애 감지 → Route 53 트래픽 전환 | **CloudWatch Alarm** (상태 기반) |

* **Amazon SQS / Apache Kafka (on MSK)**
    * **사용처:** 데이터 수집 Lambda와 처리 Lambda 사이에서 데이터를 임시 저장하는 메시지 큐입니다. 시스템 간의 결합도를 낮추고, 트래픽 폭증 시 데이터를 유실 없이 처리하는 버퍼 역할을 합니다.
    * **역할:** **비동기 메시징 및 시스템 디커플링.**

---

## 4. 데이터베이스 및 스토리지 (Databases & Storage)

데이터를 목적에 맞게 영구적으로 또는 일시적으로 저장합니다.



* **Amazon S3 (Simple Storage Service)**
    * **사용처:** 1) 수집된 모든 데이터 원본(JSON)을 영구 보관하는 데이터 아카이브, 2) React 프론트엔드 빌드 결과물(HTML, JS, CSS)을 호스팅하는 정적 웹 호스팅, 3) 장기 보관용 로그 저장소로 사용됩니다.
    * **역할:** **객체 스토리지, 데이터 아카이브, 웹 호스팅.**

* **Amazon Aurora (Global Database)**
    * **사용처:** 모든 환율 변동 내역(`exchange_rate_history`)을 시간 순서대로 영구 저장합니다. 과거 데이터 조회 및 통계 분석의 기준이 되는 '기록의 원천'입니다.
    * **역할:** **관계형 데이터의 영구 저장 및 분석.**

* **Amazon ElastiCache for Redis**
    * **사용처:** 최신 환율 정보를 Key-Value 형태로 저장하는 인메모리 캐시입니다. DB 조회를 최소화하여 API 응답 속도를 극대화합니다.
    * **역할:** **데이터 캐싱 및 성능 향상.**

* **Amazon DynamoDB (Global Tables)**
    * **사용처:** 1) 사용자의 모든 선택 기록(`travel_destination_selections`), 2) 주기적으로 미리 계산된 랭킹 결과(`RankingResults`)를 저장합니다. 대규모의 쓰기/읽기 요청을 빠르고 안정적으로 처리합니다.
    * **역할:** **NoSQL 데이터 저장 및 대규모 트래픽 처리.**

---

## 5. 애플리케이션 및 네트워킹 (Application & Networking)

사용자 요청을 받아 비즈니스 로직을 수행하고, 안정적인 서비스 연결을 보장합니다.

* **Amazon ECS (Elastic Container Service)**
    * **사용처:** `currency-service`, `ranking-service` 등 모든 마이크로서비스 Docker 컨테이너를 실행하고 관리하는 오케스트레이션 서비스입니다.
    * **역할:** **컨테이너 실행 및 관리.**

* **Application Load Balancer (ALB)**
    * **사용처:** 외부 사용자의 HTTP 요청을 받아 등록된 여러 ECS 서비스 컨테이너로 트래픽을 분산합니다. SSL 인증서 관리 및 L7 라우팅을 담당합니다.
    * **역할:** **트래픽 분산 및 L7 라우팅.**

* **Amazon API Gateway**
    * **사용처:** 외부 요청을 Lambda 함수(`user-selection-handler-lambda`)로 라우팅하고, API 요청에 대한 인증, 속도 제한(Throttling) 등을 관리합니다.
    * **역할:** **서버리스 애플리케이션의 진입점(Entry Point).**

* **Amazon CloudFront**
    * **사용처:** S3에 호스팅된 프론트엔드 정적 파일(이미지, JS 등)을 전 세계 엣지 로케이션에 캐싱하여 사용자에게 가장 가까운 곳에서 빠르게 콘텐츠를 전송합니다.
    * **역할:** **콘텐츠 전송 네트워크(CDN) 및 속도 향상.**

* **Amazon Route 53**
    * **사용처:** 서비스의 도메인 이름(DNS)을 관리하며, 지연 시간 기반 라우팅을 통해 사용자를 가장 가까운 리전으로 안내합니다. 리전 장애 발생 시 상태 확인(Health Check)을 통해 정상적인 다른 리전으로 트래픽을 자동 전환(Failover)합니다.
    * **역할:** **DNS, 트래픽 라우팅, 장애 조치.**

* **AWS ARC (Application Recovery Controller)**
    * **사용처:** Route 53의 장애 조치 과정을 더 안정적이고 정교하게 제어하기 위한 서비스입니다. `failover-handler` Lambda가 ARC를 제어하여 리전 간 트래픽 전환을 자동화합니다.
    * **역할:** **고가용성 및 재해 복구 관리.**

---

## 6. 모니터링 및 로깅 (Monitoring & Logging)

시스템의 상태를 실시간으로 관찰하고, 문제 발생 시 원인을 신속하게 파악하고 대응합니다.

* **Prometheus (프로메테우스)**
    * **사용처:** 각 마이크로서비스의 상태(CPU 사용량, 메모리, API 요청 수 등)를 나타내는 메트릭을 주기적으로 수집하고 저장합니다.
    * **역할:** **시스템 메트릭 수집.**

* **Grafana (그라파나)**
    * **사용처:** Prometheus가 수집한 메트릭 데이터를 시각적으로 표현하는 대시보드를 구축합니다. 시스템의 상태를 한눈에 파악하고 이상 징후를 감지합니다.
    * **역할:** **메트릭 시각화 및 대시보드.**

* **EFK Stack (Elasticsearch, Fluentd, Kibana)**
    * **Fluentd:** 각 컨테이너와 서비스에서 발생하는 모든 로그(애플리케이션 로그, 에러 로그 등)를 수집하여 Elasticsearch로 전송합니다.
    * **Elasticsearch (Amazon OpenSearch Service):** 수집된 대규모 로그 데이터를 저장하고, 빠른 검색 및 집계가 가능하도록 인덱싱합니다.
    * **Kibana:** Elasticsearch에 저장된 로그를 시각화하고, 특정 조건(예: "ERROR" 로그)으로 필터링하여 검색하는 등 로그 분석을 위한 UI를 제공합니다.
    * **역할:** **중앙화된 로그 수집, 검색, 분석.**