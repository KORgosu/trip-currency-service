"""
Ranking Service - 사용자 활동 기록 및 랭킹 서비스
FastAPI 기반 웹 서버 (로컬 개발용)
AWS Lambda 배포 시에는 lambda_handler 함수 사용
"""
import os
import sys
import time
from contextlib import asynccontextmanager

# 상위 디렉토리의 shared 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional, Dict, Any

from shared.config import init_config, get_config
from shared.database import init_database, get_db_manager
import logging
from shared.logging import set_correlation_id, set_request_id
from shared.models import (
    UserSelection, RankingResponse, CountryStats, 
    RankingPeriod, CountryCode, SuccessResponse, ErrorResponse
)
from shared.exceptions import (
    BaseServiceException, InvalidCountryCodeError, 
    InvalidPeriodError, RateLimitExceededError, get_http_status_code
)
from shared.utils import SecurityUtils, ValidationUtils

from app.services.selection_recorder import SelectionRecorder
from app.services.ranking_provider import RankingProvider
from shared.database import DynamoDBHelper
from pydantic import BaseModel, Field
from shared.database import RedisHelper
from datetime import datetime, timedelta

# 로거 초기화
logger = logging.getLogger(__name__)

# 전역 변수
selection_recorder: Optional[SelectionRecorder] = None
ranking_provider: Optional[RankingProvider] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global selection_recorder, ranking_provider
    
    try:
        # 설정 초기화
        config = init_config("ranking-service")
        logger.info(f"Ranking Service starting - version: {config.service_version}")
        
        # 데이터베이스 초기화
        await init_database()
        logger.info("Database connections initialized")
        
        # 서비스 프로바이더 초기화
        selection_recorder = SelectionRecorder()
        ranking_provider = RankingProvider()
        
        # 서비스 초기화
        await selection_recorder.initialize()
        await ranking_provider.initialize()
        
        logger.info("Ranking Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start Ranking Service: {e}")
        raise
    finally:
        # 정리 작업
        if selection_recorder:
            await selection_recorder.close()
        if ranking_provider:
            await ranking_provider.close()
        
        db_manager = get_db_manager()
        await db_manager.close()
        logger.info("Ranking Service stopped")


# 설정을 미리 초기화하여 CORS 미들웨어에서 사용 가능하게 함
config = init_config("ranking-service")

# FastAPI 앱 생성
app = FastAPI(
    title="Ranking Service",
    description="사용자 활동 기록 및 랭킹 서비스",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
if config and config.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# 의존성 함수들
def get_selection_recorder() -> SelectionRecorder:
    """Selection Recorder 의존성"""
    if selection_recorder is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return selection_recorder


def get_ranking_provider() -> RankingProvider:
    """Ranking Provider 의존성"""
    if ranking_provider is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return ranking_provider


# Rate Limiting 체크 (간단한 구현)
rate_limit_store = {}

async def check_rate_limit(request: Request):
    """Rate Limiting 체크"""
    client_ip = request.client.host
    current_time = int(time.time())
    window = 60  # 1분
    limit = 100  # 분당 100회
    
    # 윈도우 초기화
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []
    
    # 오래된 요청 제거
    rate_limit_store[client_ip] = [
        timestamp for timestamp in rate_limit_store[client_ip]
        if current_time - timestamp < window
    ]
    
    # 현재 요청 추가
    rate_limit_store[client_ip].append(current_time)
    
    # 제한 확인
    if len(rate_limit_store[client_ip]) > limit:
        raise RateLimitExceededError(limit, window, 60)


# 미들웨어
@app.middleware("http")
async def logging_middleware(request, call_next):
    """로깅 미들웨어"""
    # 상관관계 ID 설정
    correlation_id = request.headers.get("X-Correlation-ID") or SecurityUtils.generate_correlation_id()
    set_correlation_id(correlation_id)
    
    # 요청 ID 설정
    request_id = request.headers.get("X-Request-ID") or SecurityUtils.generate_uuid()
    set_request_id(request_id)
    
    logger.info(f"Request started: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        
        logger.info(f"Request completed: {request.method} {request.url} - {response.status_code}")
        
        # 응답 헤더에 상관관계 ID 추가
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url} - {e}")
        raise


# 예외 처리기
@app.exception_handler(BaseServiceException)
async def service_exception_handler(request, exc: BaseServiceException):
    """서비스 예외 처리기"""
    logger.error(f"Service exception: {exc.error_code} - {exc.message}")
    
    error_response = ErrorResponse(error=exc.to_dict())
    return JSONResponse(
        status_code=get_http_status_code(exc),
        content={
            "success": False,
            "timestamp": error_response.timestamp.isoformat() + 'Z',
            "version": error_response.version,
            "error": exc.to_dict()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """일반 예외 처리기"""
    logger.error(f"Unexpected error occurred: {exc}")
    
    from datetime import datetime
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "version": "v1",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


# API 엔드포인트들
@app.get("/health")
async def health_check():
    """헬스 체크"""
    return SuccessResponse(
        data={
            "status": "healthy",
            "service": "ranking-service",
            "version": get_config().service_version
        }
    )


@app.post("/api/v1/rankings/selections", response_model=SuccessResponse, status_code=201)
async def record_selection(
    selection: UserSelection,
    request: Request,
    recorder: SelectionRecorder = Depends(get_selection_recorder)
):
    """
    여행지 선택 기록
    
    - **user_id**: 사용자 ID (익명 UUID)
    - **country_code**: 선택한 국가 코드
    - **session_id**: 세션 ID (선택사항)
    - **referrer**: 리퍼러 URL (선택사항)
    """
    try:
        # Rate Limiting 체크
        await check_rate_limit(request)
        
        # 클라이언트 정보 수집
        client_ip = request.client.host
        user_agent = request.headers.get("User-Agent", "")
        
        # 선택 기록
        selection_id = await recorder.record_selection(
            selection=selection,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        return SuccessResponse(
            data={
                "selection_id": selection_id,
                "message": "Selection recorded successfully"
            }
        )
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to record selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to record selection")


@app.get("/api/v1/rankings", response_model=RankingResponse)
async def get_rankings(
    period: str = Query(..., description="랭킹 기간 (daily, weekly, monthly)"),
    limit: int = Query(10, ge=1, le=50, description="결과 개수 제한"),
    offset: int = Query(0, ge=0, description="페이지네이션 오프셋"),
    provider: RankingProvider = Depends(get_ranking_provider)
):
    """
    인기 여행지 랭킹 조회
    
    - **period**: 랭킹 기간 (daily, weekly, monthly)
    - **limit**: 결과 개수 제한 (1-50)
    - **offset**: 페이지네이션 오프셋
    """
    try:
        # 기간 검증
        valid_periods = [p.value for p in RankingPeriod]
        period = ValidationUtils.validate_period(period, valid_periods)
        
        # 랭킹 데이터 조회
        ranking_data = await provider.get_rankings(period, limit, offset)

        # 프론트 호환성: selection_count alias 및 rank 보정
        items = ranking_data.get("ranking", [])
        normalized = []
        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                normalized.append(it)
                continue
            item = dict(it)
            if "selection_count" not in item and "score" in item:
                item["selection_count"] = item["score"]
            if "rank" not in item:
                item["rank"] = (idx + 1) + (ranking_data.get("pagination", {}).get("items_per_page") and 0 or 0)
            normalized.append(item)
        ranking_data["ranking"] = normalized
        
        return RankingResponse(data=ranking_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rankings")


@app.get("/api/v1/rankings/stats/{country_code}", response_model=SuccessResponse)
async def get_country_stats(
    country_code: str,
    period: str = Query("7d", description="통계 기간 (7d, 30d, 90d)"),
    provider: RankingProvider = Depends(get_ranking_provider)
):
    """
    국가별 선택 통계
    
    - **country_code**: 국가 코드
    - **period**: 통계 기간 (7d, 30d, 90d)
    """
    try:
        # 국가 코드 검증
        country_code = ValidationUtils.validate_country_code(country_code)
        
        # 기간 검증
        valid_periods = ["7d", "30d", "90d"]
        period = ValidationUtils.validate_period(period, valid_periods)
        
        # 통계 데이터 조회
        stats_data = await provider.get_country_stats(country_code, period)
        
        return SuccessResponse(data=stats_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get country stats for {country_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve country statistics")


@app.post("/api/v1/rankings/calculate", response_model=SuccessResponse)
async def trigger_ranking_calculation(
    period: str = Query(..., description="계산할 랭킹 기간"),
    provider: RankingProvider = Depends(get_ranking_provider)
):
    """
    랭킹 계산 트리거 (관리자용)
    
    - **period**: 계산할 랭킹 기간
    """
    try:
        # 기간 검증
        valid_periods = [p.value for p in RankingPeriod]
        period = ValidationUtils.validate_period(period, valid_periods)
        
        # 랭킹 계산 트리거
        calculation_id = await provider.trigger_ranking_calculation(period)
        
        return SuccessResponse(
            data={
                "calculation_id": calculation_id,
                "period": period,
                "message": "Ranking calculation triggered successfully"
            }
        )
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger ranking calculation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger ranking calculation")


# ----- Ranking store read/write APIs (DynamoDB: RankingResults) -----

class RankingStoreItem(BaseModel):
    period: str = Field(..., description="랭킹 기간 키 (daily|weekly|monthly)")
    ranking: List[Dict[str, Any]] = Field(default_factory=list)
    total_selections: int = 0
    last_updated: Optional[str] = None
    calculation_metadata: Optional[Dict[str, Any]] = None
    ttl: Optional[int] = Field(None, description="TTL epoch seconds (optional)")


def get_rankings_table_helper() -> DynamoDBHelper:
    try:
        return DynamoDBHelper("RankingResults")
    except Exception as e:
        logger.error(f"DynamoDB not initialized: {e}")
        raise HTTPException(status_code=503, detail="DynamoDB not initialized")


@app.post("/api/v1/rankings/store", response_model=SuccessResponse)
async def upsert_ranking_item(payload: RankingStoreItem):
    """랭킹 결과 저장/업데이트 (DynamoDB)"""
    try:
        # 기본 last_updated
        if not payload.last_updated:
            from datetime import datetime
            payload.last_updated = datetime.utcnow().isoformat() + 'Z'

        item = {
            "period": payload.period,
            "ranking_data": payload.ranking,
            "total_selections": payload.total_selections,
            "last_updated": payload.last_updated,
        }
        if payload.calculation_metadata is not None:
            item["calculation_metadata"] = payload.calculation_metadata
        if payload.ttl is not None:
            item["ttl"] = payload.ttl

        helper = get_rankings_table_helper()
        await helper.put_item(item)

        # 캐시 무효화: 저장된 period의 랭킹 캐시 제거
        try:
            redis = RedisHelper()
            await redis.delete_pattern(f"ranking:{payload.period}:*")
        except Exception:
            pass

        return SuccessResponse(data={"message": "Ranking item upserted", "period": payload.period})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert ranking item: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert ranking item")


@app.get("/api/v1/rankings/store/{period}", response_model=SuccessResponse)
async def get_ranking_item(period: str):
    """특정 기간의 랭킹 결과 조회 (DynamoDB)"""
    try:
        helper = get_rankings_table_helper()
        item = await helper.get_item({"period": period})
        if not item:
            raise HTTPException(status_code=404, detail="Ranking item not found")

        # 호환되는 응답 구조로 반환
        raw_items = item.get("ranking_data", [])
        normalized = []
        for idx, it in enumerate(raw_items):
            if isinstance(it, dict):
                obj = dict(it)
                if "selection_count" not in obj and "score" in obj:
                    obj["selection_count"] = obj["score"]
                if "rank" not in obj:
                    obj["rank"] = idx + 1
                normalized.append(obj)
            else:
                normalized.append(it)

        data = {
            "period": item.get("period", period),
            "total_selections": item.get("total_selections", 0),
            "last_updated": item.get("last_updated"),
            "ranking": normalized,
            "calculation_metadata": item.get("calculation_metadata")
        }
        return SuccessResponse(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ranking item: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ranking item")


@app.get("/api/v1/rankings/store", response_model=SuccessResponse)
async def list_ranking_items():
    """저장된 랭킹 키 목록 조회 (DynamoDB)"""
    try:
        helper = get_rankings_table_helper()
        items = await helper.scan(ProjectionExpression="#p, last_updated",
                                  ExpressionAttributeNames={"#p": "period"})
        periods = [
            {"period": it.get("period"), "last_updated": it.get("last_updated")}
            for it in items
        ]
        return SuccessResponse(data={"items": periods, "count": len(periods)})
    except Exception as e:
        logger.error(f"Failed to list ranking items: {e}")
        raise HTTPException(status_code=500, detail="Failed to list ranking items")


# ----- Increment scores for selected countries (page entry) -----
class UpdateRankingRequest(BaseModel):
    countries: List[str] = Field(..., description="선택된 국가 코드 리스트 (예: ['US','JP'])")
    period: Optional[str] = Field('daily', description="업데이트할 랭킹 기간 (기본: daily)")


@app.post("/api/v1/rankings/update", response_model=SuccessResponse)
async def update_ranking_counts(payload: UpdateRankingRequest):
    """선택된 나라들의 점수를 1씩 증가

    동작:
    - 우선 DynamoDB의 RankingResults[{period}]가 있으면 해당 문서의 ranking_data를 수정 후 저장
    - 문서가 없거나 DynamoDB 사용 불가하면 Redis 카운터를 증가 (기존 fallback)
    """
    try:
        period = (payload.period or 'daily').lower()

        # 1) 시도: DynamoDB 문서 업데이트
        try:
            helper = get_rankings_table_helper()
            item = await helper.get_item({"period": period})
            if item:
                now_iso = datetime.utcnow().isoformat() + 'Z'
                ranking_list = list(item.get("ranking_data", []))

                # 인덱스 맵 구성
                index_by_code = {}
                for idx, entry in enumerate(ranking_list):
                    if isinstance(entry, dict) and 'country_code' in entry:
                        index_by_code[str(entry['country_code']).upper()] = idx

                # 스코어 증가 또는 신규 추가
                for code in payload.countries:
                    cc = str(code).upper().strip()
                    if not cc:
                        continue
                    if cc in index_by_code:
                        entry = dict(ranking_list[index_by_code[cc]])
                        entry['score'] = int(entry.get('score', 0)) + 1
                        # selection_count 필드가 있으면 함께 증가
                        if 'selection_count' in entry:
                            entry['selection_count'] = int(entry['selection_count']) + 1
                        ranking_list[index_by_code[cc]] = entry
                    else:
                        # 간단 기본값으로 신규 엔트리 생성
                        ranking_list.append({
                            'rank': None,
                            'country_code': cc,
                            'country_name': cc,
                            'score': 1,
                            'percentage': 0,
                            'change': 'SAME',
                            'change_value': 0,
                            'previous_rank': None
                        })

                # 정렬 및 순위 재계산 (동점은 동일 순위)
                ranking_list.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
                total = sum(int(x.get('score', 0)) for x in ranking_list) or 0
                last_score = None
                last_rank = 0
                for idx, entry in enumerate(ranking_list, start=1):
                    score = int(entry.get('score', 0))
                    if last_score is None or score != last_score:
                        entry['rank'] = idx
                        last_rank = idx
                        last_score = score
                    else:
                        entry['rank'] = last_rank
                    if total > 0:
                        try:
                            entry['percentage'] = round((score / total) * 100, 2)
                        except Exception:
                            entry['percentage'] = 0

                # 문서 업데이트
                item['ranking_data'] = ranking_list
                item['total_selections'] = total
                item['last_updated'] = now_iso
                await helper.put_item(item)

                # 캐시 무효화: 해당 period의 랭킹 캐시 제거
                try:
                    redis = RedisHelper()
                    await redis.delete_pattern(f"ranking:{period}:*")
                except Exception as _:
                    pass

                return SuccessResponse(data={
                    "updated_countries": [str(c).upper().strip() for c in payload.countries if str(c).strip()],
                    "count": len([c for c in payload.countries if str(c).strip()]),
                    "period": period,
                    "source": "dynamodb"
                })
            else:
                # 문서가 없으면 자동 생성하여 DynamoDB를 소스로 사용
                now_iso = datetime.utcnow().isoformat() + 'Z'
                ranking_list = []

                # 신규 엔트리 생성 (각 국가 score=1)
                for code in payload.countries:
                    cc = str(code).upper().strip()
                    if not cc:
                        continue
                    ranking_list.append({
                        'rank': None,
                        'country_code': cc,
                        'country_name': cc,
                        'score': 1,
                        'percentage': 0,
                        'change': 'SAME',
                        'change_value': 0,
                        'previous_rank': None
                    })

                # 정렬 및 순위/퍼센트 계산 (동점은 동일 순위)
                ranking_list.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
                total = sum(int(x.get('score', 0)) for x in ranking_list) or 0
                last_score = None
                last_rank = 0
                for idx, entry in enumerate(ranking_list, start=1):
                    score = int(entry.get('score', 0))
                    if last_score is None or score != last_score:
                        entry['rank'] = idx
                        last_rank = idx
                        last_score = score
                    else:
                        entry['rank'] = last_rank
                    if total > 0:
                        try:
                            entry['percentage'] = round((score / total) * 100, 2)
                        except Exception:
                            entry['percentage'] = 0

                new_item = {
                    'period': period,
                    'ranking_data': ranking_list,
                    'total_selections': total,
                    'last_updated': now_iso
                }

                await helper.put_item(new_item)

                return SuccessResponse(data={
                    "updated_countries": [str(c).upper().strip() for c in payload.countries if str(c).strip()],
                    "count": len([c for c in payload.countries if str(c).strip()]),
                    "period": period,
                    "source": "dynamodb-created"
                })
        except HTTPException:
            # get_rankings_table_helper가 실패한 경우 등은 Redis 폴백으로 진행
            pass
        except Exception as e:
            logger.warning(f"DynamoDB update path failed, falling back to Redis: {e}")

        # 2) 폴백: Redis 카운터 증가
        redis = RedisHelper()
        if not redis.client:
            # Redis도 없으면 서비스 불가
            raise HTTPException(status_code=503, detail="Datastore not available (DynamoDB/Redis)")

        today = datetime.utcnow().strftime('%Y-%m-%d')
        hour = datetime.utcnow().strftime('%Y-%m-%d-%H')

        updated = []
        for code in payload.countries:
            country_code = str(code).upper().strip()
            if not country_code:
                continue
            try:
                daily_key = f"daily_count:{today}:{country_code}"
                await redis.client.incr(daily_key)
                await redis.client.expire(daily_key, 86400 * 7)

                total_daily_key = f"daily_total:{today}"
                await redis.client.incr(total_daily_key)
                await redis.client.expire(total_daily_key, 86400 * 7)

                hourly_key = f"hourly_count:{hour}:{country_code}"
                await redis.client.incr(hourly_key)
                await redis.client.expire(hourly_key, 86400)

                updated.append(country_code)
            except Exception as inner:
                logger.warning(f"Failed to update counter for {country_code}: {inner}")

        return SuccessResponse(data={
            "updated_countries": updated,
            "count": len(updated),
            "period": period,
            "source": "redis"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update ranking counts: {e}")
        raise HTTPException(status_code=500, detail="Failed to update ranking counts")


# AWS Lambda 핸들러 (배포 시 사용)
def lambda_handler(event, context):
    """
    AWS Lambda 핸들러
    
    AWS 배포 시 수정 필요사항:
    1. Mangum 설치: pip install mangum
    2. DynamoDB 테이블 생성 및 권한 설정
    3. VPC 설정 (Redis 접근용)
    4. SQS 큐 생성 및 권한 설정
    """
    # TODO: AWS 배포 시 아래 코드 활성화
    # from mangum import Mangum
    # handler = Mangum(app, lifespan="off")
    # return handler(event, context)
    pass


# 로컬 개발 서버 실행
if __name__ == "__main__":
    # 환경 변수에서 설정 로드
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8002"))  # Ranking Service는 8002 포트
    
    logger.info(f"Starting Ranking Service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"
    )