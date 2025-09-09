# Currency Travel Service 🌍💱

**여행 물가 비교를 위한 마이크로서비스 아키텍처 기반 환율 서비스**

실시간 환율 정보, 사용자 활동 기반 랭킹, 환율 이력 분석을 제공하는 완전한 클라우드 네이티브 서비스입니다.

## 🎯 주요 기능

- 🔄 **실시간 환율 조회**: 다중 소스 기반 최신 환율 정보
- 🏆 **인기 여행지 랭킹**: 사용자 선택 기반 실시간 랭킹
- 📈 **환율 이력 분석**: 기술적 지표 및 트렌드 분석
- 🤖 **자동 데이터 수집**: 외부 API 기반 주기적 데이터 수집
- 💰 **물가 지수 계산**: 빅맥/스타벅스 지수 기반 구매력 비교

## 🏗️ 시스템 아키텍처

### 📦 마이크로서비스 구성
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Currency Service│ Ranking Service │ History Service │ Data Ingestor   │
│ (포트: 8001)     │ (포트: 8002)     │ (포트: 8003)     │ (CronJob/배치)   │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ • 실시간 환율    │ • 사용자 선택    │ • 환율 이력      │ • 외부 API 수집  │
│ • 물가 지수      │ • 랭킹 계산      │ • 통계 분석      │ • 데이터 정제    │
│ • Redis 캐시     │ • DynamoDB      │ • 기술적 지표    │ • 메시징 전송    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### 🛠️ 기술 스택
- **Backend**: Python 3.11, FastAPI, Pydantic 2.x
- **Database**: MySQL 8.0 (Aurora), Redis 7, DynamoDB
- **Messaging**: Apache Kafka (MSK), SQS
- **Infrastructure**: AWS Lambda, EKS, API Gateway, LocalStack
- **Monitoring**: CloudWatch, Prometheus, Grafana
- **Testing**: pytest, Docker Compose

## 🚀 빠른 시작

### 📋 사전 요구사항
- Python 3.11+
- Docker & Docker Compose
- Make (선택사항)

### 🔧 로컬 개발 환경 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd currency_project

# 2. 환경 설정 (선택사항)
cp .env.example .env
# .env 파일을 편집하여 외부 API 키 추가 (선택사항)

# 3. 개발 환경 설정
make setup

# 4. Docker Compose로 전체 시스템 시작
make start

# 5. 서비스 초기화 상태 확인 (30초 후)
make init-check

# 6. API 테스트
make test-api
```

### 🧪 테스트 실행

```bash
# 기본 기능 테스트 (로컬 모듈)
python test_simple.py

# 연결성 테스트 (Docker 서비스)
python test_connectivity.py

# 통합 테스트
python test_integration.py
```

### 🌐 서비스 접근

서비스가 정상적으로 시작되면 다음 URL로 접근할 수 있습니다:

- **Currency Service**: http://localhost:8001
  - Health Check: http://localhost:8001/health
  - API 문서: http://localhost:8001/docs (FastAPI 자동 생성)
- **Ranking Service**: http://localhost:8002
  - Health Check: http://localhost:8002/health
  - API 문서: http://localhost:8002/docs
- **History Service**: http://localhost:8003
  - Health Check: http://localhost:8003/health
  - API 문서: http://localhost:8003/docs
- **Kafka UI**: http://localhost:8080
- **LocalStack Dashboard**: http://localhost:4566

### 📊 주요 명령어

```bash
# 전체 시스템 상태 확인
make status

# 로그 확인
make logs

# 특정 서비스 로그
make logs-currency
make logs-ranking
make logs-history

# 데이터베이스 상태 확인
make db-status

# 시스템 정리
make clean

# 2. 환경 설정
cp .env.example .env
# .env 파일에서 필요한 설정 수정

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 기본 테스트 (선택사항)
python test_simple.py
```

### 🐳 Docker Compose로 전체 환경 시작

```bash
# 전체 인프라 시작 (MySQL, Redis, Kafka, LocalStack 등)
make start
# 또는
docker-compose up -d

# 서비스 상태 확인
make status
# 또는
docker-compose ps
```

### 🎮 개별 서비스 실행

```bash
# Currency Service 실행
make run-currency
# 또는
cd services/currency-service && python main.py

# Ranking Service 실행  
make run-ranking
# 또는
cd services/ranking-service && python main.py

# History Service 실행
make run-history
# 또는
cd services/history-service && python main.py

# Data Ingestor 실행 (단일 실행)
make run-ingestor
# 또는
cd services/data-ingestor && EXECUTION_MODE=single python main.py
```

## 🧪 테스트

### 📊 테스트 레벨

```bash
# 1. 기본 기능 테스트
python test_simple.py

# 2. 통합 테스트 (모든 서비스가 실행된 상태에서)
python test_integration.py

# 3. 단위 테스트
pytest tests/ -v

# 4. 커버리지 포함 테스트
pytest tests/ --cov=services --cov-report=html

# 5. 전체 테스트 (Make 사용)
make test
```

### 🔍 API 테스트 예시

```bash
# Currency Service - 최신 환율 조회
curl "http://localhost:8001/api/v1/currencies/latest?symbols=USD,JPY,EUR"

# Currency Service - 물가 지수 조회
curl "http://localhost:8001/api/v1/currencies/price-index?country=JP"

# Ranking Service - 여행지 선택 기록
curl -X POST "http://localhost:8002/api/v1/rankings/selections" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test-user-123","country_code":"JP"}'

# Ranking Service - 랭킹 조회
curl "http://localhost:8002/api/v1/rankings?period=daily&limit=5"

# History Service - 환율 이력 조회
curl "http://localhost:8003/api/v1/history?period=1w&target=USD"

# History Service - 통화 비교
curl "http://localhost:8003/api/v1/history/compare?targets=USD,JPY,EUR&period=1m"
```

## 📚 문서

### 📖 핵심 문서
- 📋 [API 명세서](docs/api/api-specification.md) - 전체 API 엔드포인트 상세 가이드
- 🏗️ [시스템 아키텍처](docs/architecture/system-architecture.md) - 마이크로서비스 아키텍처 설계
- 🗄️ [데이터베이스 설계](docs/database/database-design.md) - 폴리글랏 퍼시스턴스 설계
- 🚀 [배포 가이드](docs/deployment/deployment-guide.md) - AWS 배포 상세 가이드

### 📋 서비스별 문서
- 💱 [Currency Service](docs/services/currency-service.md) - 환율 조회 서비스
- 🏆 [Ranking Service](docs/services/ranking-service.md) - 랭킹 서비스

### 🔧 운영 문서
- 📊 [모니터링 가이드](docs/monitoring/monitoring-guide.md) - 관찰성 및 알림 설정
- ✅ [의존성 분석 및 테스트](DEPENDENCY_ANALYSIS_AND_TESTING.md) - 버전 호환성 및 테스트 전략
- 🚀 [실제 서비스 구현 가이드](REAL_SERVICE_IMPLEMENTATION_GUIDE.md) - AWS 프로덕션 배포
- 🔄 [버전 호환성 체크](VERSION_COMPATIBILITY_CHECK.md) - 라이브러리 버전 관리
- ☁️ [AWS 배포 체크리스트](AWS_DEPLOYMENT_CHECKLIST.md) - 단계별 배포 가이드

## 🌐 서비스 접근 정보

### 🔗 로컬 개발 환경
- **Currency Service**: http://localhost:8001
  - API 문서: http://localhost:8001/docs
  - 헬스체크: http://localhost:8001/health
- **Ranking Service**: http://localhost:8002
  - API 문서: http://localhost:8002/docs
  - 헬스체크: http://localhost:8002/health
- **History Service**: http://localhost:8003
  - API 문서: http://localhost:8003/docs
  - 헬스체크: http://localhost:8003/health

### 🛠️ 개발 도구
- **Kafka UI**: http://localhost:8080 (Kafka 클러스터 관리)
- **MySQL**: localhost:3306 (currency_user/password)
- **Redis**: localhost:6379
- **LocalStack**: http://localhost:4566 (AWS 서비스 에뮬레이션)

## 🚀 AWS 배포

### ☁️ 프로덕션 배포

```bash
# 1. AWS 인프라 구성 (Terraform)
cd infrastructure/terraform
terraform init
terraform plan -var-file="environments/prod.tfvars"
terraform apply

# 2. 서비스 배포
./scripts/deploy-all-services.sh

# 3. 배포 검증
./scripts/verify-deployment.sh
```

### 📋 배포 체크리스트
자세한 배포 과정은 [AWS 배포 체크리스트](AWS_DEPLOYMENT_CHECKLIST.md)를 참조하세요.

## 📊 모니터링 및 운영

### 📈 주요 메트릭
- **응답 시간**: < 200ms (95th percentile)
- **처리량**: > 1000 RPS
- **가용성**: 99.9%
- **에러율**: < 0.1%

### 🔍 모니터링 도구
- **CloudWatch**: AWS 네이티브 모니터링
- **Grafana**: 커스텀 대시보드
- **Prometheus**: 메트릭 수집
- **ELK Stack**: 로그 분석

## 🛠️ 개발 가이드

### 📁 프로젝트 구조
```
currency_project/
├── services/                    # 마이크로서비스들
│   ├── shared/                 # 공통 모듈
│   ├── currency-service/       # 환율 조회 서비스
│   ├── ranking-service/        # 랭킹 서비스
│   ├── history-service/        # 이력 분석 서비스
│   └── data-ingestor/         # 데이터 수집 서비스
├── docs/                       # 문서
├── scripts/                    # 유틸리티 스크립트
├── tests/                      # 테스트 코드
├── infrastructure/             # 인프라 코드 (Terraform)
├── docker-compose.yml         # 로컬 개발 환경
├── Makefile                   # 개발 편의 명령어
└── requirements.txt           # Python 의존성
```

### 🔧 개발 명령어

```bash
# 개발 환경 설정
make setup

# 전체 서비스 시작
make start

# 전체 서비스 중지
make stop

# 테스트 실행
make test

# 코드 포맷팅
make format

# 코드 린팅
make lint

# 환경 정리
make clean
```

### 🎯 코딩 가이드라인
- **Python**: PEP 8 준수, Type Hints 사용
- **API**: RESTful 설계, OpenAPI 3.0 문서화
- **테스트**: 80%+ 커버리지 목표
- **로깅**: 구조화된 JSON 로깅
- **에러 처리**: 일관된 예외 처리 패턴

## 🤝 기여하기

### 📝 기여 절차
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### 🔍 코드 리뷰 체크리스트
- [ ] 모든 테스트 통과
- [ ] 코드 커버리지 80% 이상
- [ ] 린팅 규칙 준수
- [ ] 문서 업데이트 완료
- [ ] 보안 스캔 통과

## 🆘 문제 해결

### 🐛 일반적인 문제들

#### Redis 연결 실패
```bash
# Redis 서버 시작
docker run -d -p 6379:6379 redis:7-alpine

# 연결 테스트
redis-cli ping
```

#### MySQL 연결 실패
```bash
# MySQL 서버 시작
docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8.0

# 연결 테스트
mysql -h localhost -u root -p
```

#### 모듈 import 에러
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/services"
```

### 📞 지원
- **기술 문의**: GitHub Issues
- **문서 개선**: Pull Request
- **버그 신고**: GitHub Issues (bug 라벨)

## 📊 프로젝트 상태

### ✅ 완료된 기능
- [x] 4개 마이크로서비스 완전 구현
- [x] 로컬 개발 환경 구성
- [x] 단위/통합 테스트 시스템
- [x] API 문서화
- [x] Docker 컨테이너화
- [x] AWS 배포 준비

### 🚧 진행 중
- [ ] 성능 최적화
- [ ] 보안 강화
- [ ] 모니터링 확장
- [ ] CI/CD 파이프라인

### 🎯 향후 계획
- [ ] GraphQL API 지원
- [ ] 실시간 알림 시스템
- [ ] 모바일 앱 지원
- [ ] 다국어 지원 확장

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들의 도움을 받았습니다:
- FastAPI, Pydantic, aioredis, aiomysql
- Docker, Kubernetes, Terraform
- AWS SDK, LocalStack

---

**Currency Travel Service** - 여행자를 위한 스마트한 환율 정보 서비스 💱🌍