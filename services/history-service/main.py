"""
History Service - 환율 이력 분석 및 차트 데이터 서비스
FastAPI 기반 웹 서버 (로컬 개발용)
AWS Lambda 배포 시에는 lambda_handler 함수 사용
"""
import os
import sys
from contextlib import asynccontextmanager

# 상위 디렉토리의 shared 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional

from shared.config import init_config, get_config
from shared.database import init_database, get_db_manager
import logging
from shared.logging import set_correlation_id, set_request_id
from shared.models import (
    HistoryResponse, CurrencyCode, HistoryPeriod, 
    SuccessResponse, ErrorResponse
)
from shared.exceptions import (
    BaseServiceException, InvalidCurrencyCodeError, 
    InvalidPeriodError, get_http_status_code
)
from shared.utils import SecurityUtils, ValidationUtils

from app.services.history_provider import HistoryProvider
from app.services.analysis_provider import AnalysisProvider

# 로거 초기화
logger = logging.getLogger(__name__)

# 전역 변수
history_provider: Optional[HistoryProvider] = None
analysis_provider: Optional[AnalysisProvider] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global history_provider, analysis_provider
    
    try:
        # 설정 초기화
        config = init_config("history-service")
        logger.info("History Service starting", version=config.service_version)
        
        # 데이터베이스 초기화
        await init_database()
        logger.info("Database connections initialized")
        
        # 서비스 프로바이더 초기화
        history_provider = HistoryProvider()
        analysis_provider = AnalysisProvider()
        
        logger.info("History Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start History Service: {e}")
        raise
    finally:
        # 정리 작업
        db_manager = get_db_manager()
        await db_manager.close()
        logger.info("History Service stopped")


# FastAPI 앱 생성
app = FastAPI(
    title="History Service",
    description="환율 이력 분석 및 차트 데이터 서비스",
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


# 의존성 함수들
def get_history_provider() -> HistoryProvider:
    """History Provider 의존성"""
    if history_provider is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return history_provider


def get_analysis_provider() -> AnalysisProvider:
    """Analysis Provider 의존성"""
    if analysis_provider is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return analysis_provider


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
            "service": "history-service",
            "version": get_config().service_version
        }
    )


@app.get("/api/v1/history", response_model=HistoryResponse)
async def get_exchange_rate_history(
    period: str = Query(..., description="조회 기간 (1w, 1m, 6m)"),
    target: str = Query(..., description="대상 통화 코드"),
    base: str = Query("KRW", description="기준 통화 코드"),
    interval: str = Query("daily", description="데이터 간격 (daily, hourly)"),
    provider: HistoryProvider = Depends(get_history_provider)
):
    """
    환율 이력 조회
    
    - **period**: 조회 기간 (1w, 1m, 6m)
    - **target**: 대상 통화 코드 (USD, JPY 등)
    - **base**: 기준 통화 코드 (기본값: KRW)
    - **interval**: 데이터 간격 (daily, hourly)
    """
    try:
        # 파라미터 검증
        valid_periods = [p.value for p in HistoryPeriod]
        period = ValidationUtils.validate_period(period, valid_periods)
        
        target = ValidationUtils.validate_currency_code(target)
        base = ValidationUtils.validate_currency_code(base)
        
        if interval not in ["daily", "hourly"]:
            raise InvalidPeriodError(interval, ["daily", "hourly"])
        
        # 환율 이력 데이터 조회
        history_data = await provider.get_exchange_rate_history(
            period=period,
            target_currency=target,
            base_currency=base,
            interval=interval
        )
        
        return HistoryResponse(data=history_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exchange rate history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exchange rate history")


@app.get("/api/v1/history/stats", response_model=SuccessResponse)
async def get_exchange_rate_stats(
    target: str = Query(..., description="대상 통화 코드"),
    period: str = Query("6m", description="분석 기간"),
    base: str = Query("KRW", description="기준 통화 코드"),
    provider: AnalysisProvider = Depends(get_analysis_provider)
):
    """
    환율 통계 분석
    
    - **target**: 대상 통화 코드
    - **period**: 분석 기간
    - **base**: 기준 통화 코드
    """
    try:
        # 파라미터 검증
        target = ValidationUtils.validate_currency_code(target)
        base = ValidationUtils.validate_currency_code(base)
        
        # 통계 분석 데이터 조회
        stats_data = await provider.get_exchange_rate_statistics(
            target_currency=target,
            base_currency=base,
            period=period
        )
        
        return SuccessResponse(data=stats_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exchange rate stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exchange rate statistics")


@app.get("/api/v1/history/compare", response_model=SuccessResponse)
async def compare_currencies(
    targets: str = Query(..., description="쉼표로 구분된 통화 코드들"),
    period: str = Query("1m", description="비교 기간"),
    base: str = Query("KRW", description="기준 통화 코드"),
    provider: AnalysisProvider = Depends(get_analysis_provider)
):
    """
    환율 비교 분석
    
    - **targets**: 쉼표로 구분된 통화 코드들 (예: USD,JPY,EUR)
    - **period**: 비교 기간
    - **base**: 기준 통화 코드
    """
    try:
        # 파라미터 파싱 및 검증
        currency_codes = [code.strip().upper() for code in targets.split(",")]
        
        for code in currency_codes:
            ValidationUtils.validate_currency_code(code)
        
        base = ValidationUtils.validate_currency_code(base)
        
        if len(currency_codes) > 10:  # 최대 10개 통화까지 비교
            raise InvalidPeriodError("Too many currencies", "Maximum 10 currencies allowed")
        
        # 통화 비교 분석
        comparison_data = await provider.compare_currencies(
            currency_codes=currency_codes,
            base_currency=base,
            period=period
        )
        
        return SuccessResponse(data=comparison_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare currencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare currencies")


@app.get("/api/v1/history/forecast/{currency_code}", response_model=SuccessResponse)
async def get_exchange_rate_forecast(
    currency_code: str,
    days: int = Query(7, ge=1, le=30, description="예측 일수"),
    base: str = Query("KRW", description="기준 통화 코드"),
    provider: AnalysisProvider = Depends(get_analysis_provider)
):
    """
    환율 예측 (간단한 트렌드 기반)
    
    - **currency_code**: 대상 통화 코드
    - **days**: 예측 일수 (1-30일)
    - **base**: 기준 통화 코드
    """
    try:
        # 파라미터 검증
        currency_code = ValidationUtils.validate_currency_code(currency_code)
        base = ValidationUtils.validate_currency_code(base)
        
        # 환율 예측
        forecast_data = await provider.get_exchange_rate_forecast(
            target_currency=currency_code,
            base_currency=base,
            forecast_days=days
        )
        
        return SuccessResponse(data=forecast_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exchange rate forecast: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate exchange rate forecast")


# AWS Lambda 핸들러 (배포 시 사용)
def lambda_handler(event, context):
    """
    AWS Lambda 핸들러
    
    AWS 배포 시 수정 필요사항:
    1. Mangum 설치: pip install mangum
    2. Aurora 클러스터 접근 권한 설정
    3. VPC 설정 (Aurora, Redis 접근용)
    4. Parameter Store에서 DB 비밀번호 조회 로직 추가
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
    port = int(os.getenv("PORT", "8003"))  # History Service는 8003 포트
    
    logger.info(f"Starting History Service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"
    )