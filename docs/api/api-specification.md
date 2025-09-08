# API 명세서 (API Specification)

## 1. API 개요

여행 물가 비교 서비스는 RESTful API 아키텍처를 따르며, 4개의 마이크로서비스가 각각 독립적인 API 엔드포인트를 제공합니다.

### 1.1 기본 정보
- **Base URL**: `https://api.currency-travel.com/api/v1`
- **Protocol**: HTTPS
- **Data Format**: JSON
- **Authentication**: API Key (향후 구현)
- **Rate Limiting**: 1000 requests/hour per IP

### 1.2 공통 응답 형식
```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2025-09-05T10:30:00Z",
  "version": "v1"
}
```

### 1.3 에러 응답 형식
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "The parameter 'currency' is required",
    "details": {
      "parameter": "currency",
      "provided": null,
      "expected": "3-letter currency code"
    }
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

## 2. Currency Service API

### 2.1 최신 환율 조회
```http
GET /currencies/latest
```

**설명**: 지정된 통화들의 최신 환율 정보를 조회합니다.

**Query Parameters**:
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `symbols` | string | No | 쉼표로 구분된 통화 코드 | `USD,JPY,EUR` |
| `base` | string | No | 기준 통화 (기본값: KRW) | `KRW` |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "base": "KRW",
    "timestamp": 1725525000,
    "rates": {
      "USD": 1392.4,
      "JPY": 9.46,
      "EUR": 1456.8
    },
    "source": "redis_cache",
    "cache_hit": true
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: 잘못된 통화 코드
- `503 Service Unavailable`: 캐시 및 DB 모두 사용 불가

### 2.2 통화별 상세 정보 조회
```http
GET /currencies/{currency_code}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `currency_code` | string | Yes | 3자리 통화 코드 |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "currency_code": "USD",
    "currency_name": "미국 달러",
    "country_code": "US",
    "country_name": "미국",
    "symbol": "$",
    "current_rate": 1392.4,
    "tts": 1420.85,
    "ttb": 1363.95,
    "last_updated": "2025-09-05T10:25:00Z",
    "source": "BOK"
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 2.3 물가 지수 조회
```http
GET /currencies/price-index
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `country` | string | Yes | 국가 코드 (ISO 3166-1) |
| `base_country` | string | No | 기준 국가 (기본값: KR) |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "country_code": "JP",
    "country_name": "일본",
    "base_country": "KR",
    "indices": {
      "bigmac_index": 85.2,
      "starbucks_index": 92.1,
      "composite_index": 88.1
    },
    "price_data": {
      "bigmac_price_local": 450,
      "bigmac_price_usd": 3.12,
      "starbucks_latte_local": 520,
      "starbucks_latte_usd": 3.61
    },
    "last_updated": "2025-09-05T08:00:00Z"
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

## 3. Ranking Service API

### 3.1 여행지 선택 기록
```http
POST /rankings/selections
```

**Request Body**:
```json
{
  "user_id": "anonymous-uuid-12345",
  "country_code": "JP",
  "session_id": "sess_abc123def456",
  "referrer": "https://google.com"
}
```

**Response Example**:
```json
{
  "success": true,
  "data": {
    "selection_id": "sel_20250905_103045_12345",
    "message": "Selection recorded successfully"
  },
  "timestamp": "2025-09-05T10:30:45Z"
}
```

**Error Responses**:
- `400 Bad Request`: 필수 필드 누락 또는 잘못된 형식
- `429 Too Many Requests`: Rate limit 초과

### 3.2 인기 여행지 랭킹 조회
```http
GET /rankings
```

**Query Parameters**:
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `period` | string | Yes | 랭킹 기간 (daily, weekly, monthly) | - |
| `limit` | integer | No | 결과 개수 제한 | 10 |
| `offset` | integer | No | 페이지네이션 오프셋 | 0 |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "period": "daily",
    "total_selections": 9876,
    "last_updated": "2025-09-05T10:00:00Z",
    "ranking": [
      {
        "rank": 1,
        "country_code": "JP",
        "country_name": "일본",
        "score": 1502,
        "percentage": 15.2,
        "change": "UP",
        "change_value": 2,
        "previous_rank": 3
      },
      {
        "rank": 2,
        "country_code": "US",
        "country_name": "미국", 
        "score": 987,
        "percentage": 10.0,
        "change": "DOWN",
        "change_value": -1,
        "previous_rank": 1
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 3,
      "has_next": true,
      "has_previous": false
    }
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 3.3 국가별 선택 통계
```http
GET /rankings/stats/{country_code}
```

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `country_code` | string | Yes | 국가 코드 |

**Query Parameters**:
| Parameter | Type | Required | Description | Default |
|-----------|------|----------|-------------|---------|
| `period` | string | No | 통계 기간 (7d, 30d, 90d) | 7d |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "country_code": "JP",
    "country_name": "일본",
    "period": "7d",
    "statistics": {
      "total_selections": 10547,
      "daily_average": 1507,
      "peak_day": "2025-09-03",
      "peak_selections": 2156,
      "growth_rate": 12.5
    },
    "daily_breakdown": [
      {
        "date": "2025-09-05",
        "count": 1502,
        "rank": 1
      },
      {
        "date": "2025-09-04", 
        "count": 1456,
        "rank": 1
      }
    ]
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

## 4. History Service API

### 4.1 환율 이력 조회
```http
GET /history
```

**Query Parameters**:
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `period` | string | Yes | 조회 기간 (1w, 1m, 6m) | 1m |
| `target` | string | Yes | 대상 통화 코드 | USD |
| `base` | string | No | 기준 통화 코드 | KRW |
| `interval` | string | No | 데이터 간격 (daily, hourly) | daily |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "base": "KRW",
    "target": "USD",
    "period": "1m",
    "interval": "daily",
    "data_points": 30,
    "results": [
      {
        "date": "2025-08-05",
        "rate": 1380.5,
        "change": 2.3,
        "change_percent": 0.17,
        "volume": 24
      },
      {
        "date": "2025-08-06",
        "rate": 1382.1, 
        "change": 1.6,
        "change_percent": 0.12,
        "volume": 26
      }
    ],
    "statistics": {
      "average": 1385.2,
      "min": 1375.8,
      "max": 1395.6,
      "volatility": 0.85,
      "trend": "stable",
      "correlation": 0.92
    }
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 4.2 환율 통계 분석
```http
GET /history/stats
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target` | string | Yes | 대상 통화 코드 |
| `period` | string | Yes | 분석 기간 |
| `base` | string | No | 기준 통화 코드 |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "currency_pair": "KRW/USD",
    "period": "6m",
    "analysis_date": "2025-09-05T10:30:00Z",
    "current_rate": 1392.4,
    "statistics": {
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
    "technical_indicators": {
      "sma_20": 1388.5,
      "sma_50": 1382.1,
      "rsi": 65.2,
      "bollinger_upper": 1398.7,
      "bollinger_lower": 1371.9
    },
    "monthly_breakdown": [
      {
        "month": "2025-03",
        "average": 1378.5,
        "min": 1365.8,
        "max": 1385.2,
        "change_percent": -0.85,
        "volatility": 1.2
      }
    ]
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 4.3 환율 비교 분석
```http
GET /history/compare
```

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `targets` | string | Yes | 쉼표로 구분된 통화 코드들 |
| `period` | string | Yes | 비교 기간 |
| `base` | string | No | 기준 통화 코드 |

**Response Example**:
```json
{
  "success": true,
  "data": {
    "base": "KRW",
    "period": "1m",
    "comparison_date": "2025-09-05T10:30:00Z",
    "currencies": [
      {
        "currency": "USD",
        "current_rate": 1392.4,
        "period_change_percent": 1.2,
        "volatility": 0.85,
        "performance_rank": 2,
        "sharpe_ratio": 1.45
      },
      {
        "currency": "JPY",
        "current_rate": 9.46,
        "period_change_percent": -0.5,
        "volatility": 1.12,
        "performance_rank": 3,
        "sharpe_ratio": -0.32
      }
    ],
    "correlation_matrix": {
      "USD_JPY": 0.75,
      "USD_EUR": 0.68,
      "JPY_EUR": 0.82
    },
    "portfolio_analysis": {
      "best_performer": "USD",
      "worst_performer": "JPY",
      "most_volatile": "JPY",
      "least_volatile": "USD"
    }
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

## 5. 공통 API

### 5.1 서비스 상태 확인
```http
GET /health
```

**Response Example**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "services": {
      "currency_service": {
        "status": "healthy",
        "response_time_ms": 45,
        "last_check": "2025-09-05T10:30:00Z"
      },
      "ranking_service": {
        "status": "healthy", 
        "response_time_ms": 32,
        "last_check": "2025-09-05T10:30:00Z"
      },
      "history_service": {
        "status": "healthy",
        "response_time_ms": 78,
        "last_check": "2025-09-05T10:30:00Z"
      },
      "data_ingestor": {
        "status": "healthy",
        "last_run": "2025-09-05T10:25:00Z",
        "next_run": "2025-09-05T10:35:00Z"
      }
    },
    "dependencies": {
      "aurora_db": "healthy",
      "redis_cache": "healthy", 
      "dynamodb": "healthy",
      "kafka": "healthy"
    }
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

### 5.2 API 버전 정보
```http
GET /version
```

**Response Example**:
```json
{
  "success": true,
  "data": {
    "api_version": "v1.2.0",
    "services": {
      "currency_service": "v1.2.0",
      "ranking_service": "v1.1.5",
      "history_service": "v1.2.0",
      "data_ingestor": "v1.1.8"
    },
    "deployment_date": "2025-09-01T12:00:00Z",
    "environment": "production"
  },
  "timestamp": "2025-09-05T10:30:00Z"
}
```

## 6. 에러 코드 정의

### 6.1 HTTP 상태 코드
| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | 성공적인 요청 |
| 201 | Created | 리소스 생성 성공 |
| 400 | Bad Request | 잘못된 요청 파라미터 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 없음 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 429 | Too Many Requests | Rate limit 초과 |
| 500 | Internal Server Error | 서버 내부 오류 |
| 503 | Service Unavailable | 서비스 일시 불가 |

### 6.2 커스텀 에러 코드
| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_CURRENCY_CODE` | 잘못된 통화 코드 | 400 |
| `INVALID_PERIOD` | 잘못된 기간 파라미터 | 400 |
| `MISSING_PARAMETER` | 필수 파라미터 누락 | 400 |
| `RATE_LIMIT_EXCEEDED` | 요청 제한 초과 | 429 |
| `CACHE_UNAVAILABLE` | 캐시 서비스 불가 | 503 |
| `DATABASE_UNAVAILABLE` | 데이터베이스 불가 | 503 |
| `EXTERNAL_API_ERROR` | 외부 API 오류 | 503 |

## 7. Rate Limiting

### 7.1 제한 정책
```
기본 제한: 1000 requests/hour per IP
인증된 사용자: 5000 requests/hour per API key
프리미엄 사용자: 10000 requests/hour per API key
```

### 7.2 Rate Limit 헤더
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1725528600
X-RateLimit-Window: 3600
```

## 8. 인증 (향후 구현)

### 8.1 API Key 인증
```http
GET /currencies/latest
Authorization: Bearer your-api-key-here
```

### 8.2 JWT 토큰 인증
```http
GET /rankings/selections
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 9. SDK 및 클라이언트 라이브러리

### 9.1 JavaScript SDK 예시
```javascript
// npm install currency-travel-sdk
import CurrencyTravelAPI from 'currency-travel-sdk';

const api = new CurrencyTravelAPI({
  baseURL: 'https://api.currency-travel.com/api/v1',
  apiKey: 'your-api-key'
});

// 최신 환율 조회
const rates = await api.currencies.getLatest(['USD', 'JPY']);

// 랭킹 조회
const ranking = await api.rankings.get('daily');

// 환율 이력 조회
const history = await api.history.get('USD', '1m');
```

### 9.2 Python SDK 예시
```python
# pip install currency-travel-sdk
from currency_travel import CurrencyTravelAPI

api = CurrencyTravelAPI(
    base_url='https://api.currency-travel.com/api/v1',
    api_key='your-api-key'
)

# 최신 환율 조회
rates = api.currencies.get_latest(['USD', 'JPY'])

# 랭킹 조회  
ranking = api.rankings.get('daily')

# 환율 이력 조회
history = api.history.get('USD', '1m')
```

이 API 명세서는 모든 엔드포인트의 상세한 사용법과 예시를 제공하여 개발자들이 쉽게 통합할 수 있도록 설계되었습니다.