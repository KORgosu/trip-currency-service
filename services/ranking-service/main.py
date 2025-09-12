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
from typing import List, Optional

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


# FastAPI 앱 생성
app = FastAPI(
    title="Ranking Service",
    description="사용자 활동 기록 및 랭킹 서비스",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
config = get_config() if 'config' in globals() else None
if config and config.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 개발 환경에서는 모든 origin 허용
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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


# CORS OPTIONS 핸들러 추가
@app.options("/{path:path}")
async def options_handler(path: str):
    """CORS preflight 요청 처리"""
    return {"message": "OK"}


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
        
        return RankingResponse(data=ranking_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve rankings")


@app.get("/api/v1/rankings/debug/counters")
async def debug_counters():
    """디버그용: Redis count:total:* / 오늘 일별 키 값 조회"""
    try:
        from shared.database import RedisHelper
        r = RedisHelper()
        total_keys = await r.client.keys("count:total:*")
        today = time.strftime('%Y-%m-%d')
        daily_keys = await r.client.keys(f"count:{today}:*")
        result = {}
        for k in total_keys:
            try:
                v = await r.client.get(k)
                result[k] = int(v) if v else 0
            except:
                result[k] = None
        for k in daily_keys:
            try:
                v = await r.client.get(k)
                result[k] = int(v) if v else 0
            except:
                result[k] = None
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Debug counters failed: {e}")
        return {"success": False, "error": str(e)}


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
    # NOTE: 컨테이너 내부에서는 8000으로 리스닝하고 docker-compose가 host 8002 -> container 8000 매핑
    # 기존 기본값 8002 때문에 컨테이너가 8002에서 뜨고 호스트 8002->컨테이너 8000 포워딩이 실패하여 접근 불가 현상 발생
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting Ranking Service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"
    )