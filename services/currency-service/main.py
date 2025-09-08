"""
Currency Service - 실시간 환율 조회 서비스
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
    LatestRatesResponse, CurrencyInfo, PriceIndex, 
    CurrencyCode, CountryCode, SuccessResponse, ErrorResponse
)
from shared.exceptions import (
    BaseServiceException, InvalidCurrencyCodeError, 
    InvalidCountryCodeError, get_http_status_code
)
from shared.utils import SecurityUtils

from app.services.currency_provider import CurrencyProvider
from app.services.price_index_provider import PriceIndexProvider

# 로거 초기화
logger = logging.getLogger(__name__)

# 전역 변수
currency_provider: Optional[CurrencyProvider] = None
price_index_provider: Optional[PriceIndexProvider] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global currency_provider, price_index_provider
    
    try:
        # 설정 초기화
        config = init_config("currency-service")
        logger.info("Currency Service starting", version=config.service_version)
        
        # 데이터베이스 초기화
        await init_database()
        logger.info("Database connections initialized")
        
        # 서비스 프로바이더 초기화
        currency_provider = CurrencyProvider()
        price_index_provider = PriceIndexProvider()
        
        logger.info("Currency Service started successfully")
        yield
        
    except Exception as e:
        logger.error("Failed to start Currency Service", error=e)
        raise
    finally:
        # 정리 작업
        db_manager = get_db_manager()
        await db_manager.close()
        logger.info("Currency Service stopped")


# FastAPI 앱 생성
app = FastAPI(
    title="Currency Service",
    description="실시간 환율 조회 서비스",
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
def get_currency_provider() -> CurrencyProvider:
    """Currency Provider 의존성"""
    if currency_provider is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return currency_provider


def get_price_index_provider() -> PriceIndexProvider:
    """Price Index Provider 의존성"""
    if price_index_provider is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return price_index_provider


# 미들웨어
@app.middleware("http")
async def logging_middleware(request, call_next):
    """로깅 미들웨어"""
    # 상관관계 ID 설정
    correlation_id = request.headers.get("X-Correlation-ID") or SecurityUtils.generate_correlation_id()
    set_correlation_id(correlation_id)
    
    # 요청 ID 설정 (Lambda에서는 AWS Request ID 사용)
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
    
    from datetime import datetime
    return JSONResponse(
        status_code=get_http_status_code(exc),
        content={
            "success": False,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "version": "v1",
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
            "service": "currency-service",
            "version": get_config().service_version
        }
    )


@app.get("/api/v1/currencies/latest", response_model=LatestRatesResponse)
async def get_latest_rates(
    symbols: Optional[str] = Query(None, description="쉼표로 구분된 통화 코드"),
    base: str = Query("KRW", description="기준 통화 코드"),
    provider: CurrencyProvider = Depends(get_currency_provider)
):
    """
    최신 환율 정보 조회
    
    - **symbols**: 조회할 통화 코드들 (예: USD,JPY,EUR)
    - **base**: 기준 통화 코드 (기본값: KRW)
    """
    try:
        # 파라미터 파싱
        currency_codes = []
        if symbols:
            currency_codes = [code.strip().upper() for code in symbols.split(",")]
            # 통화 코드 검증
            for code in currency_codes:
                if code not in [c.value for c in CurrencyCode]:
                    raise InvalidCurrencyCodeError(code)
        
        # 기준 통화 검증
        if base.upper() not in [c.value for c in CurrencyCode]:
            raise InvalidCurrencyCodeError(base)
        
        # 환율 데이터 조회
        rates_data = await provider.get_latest_rates(currency_codes, base.upper())
        
        return LatestRatesResponse(data=rates_data)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exchange rates")


@app.get("/api/v1/price-index", response_model=SuccessResponse)
async def get_price_index(
    country: str = Query(..., description="국가 코드"),
    base_country: str = Query("KR", description="기준 국가 코드"),
    provider: PriceIndexProvider = Depends(get_price_index_provider)
):
    """
    물가 지수 조회

    - **country**: 대상 국가 코드 (예: JP)
    - **base_country**: 기준 국가 코드 (기본값: KR)
    """
    # TODO: 실시간 서비스 변경 - /api/v1/price-index 경로로 변경하여 {currency_code} 라우트 충돌 방지
    # - CountryCode enum에 추가 국가 지원
    # - 실제 물가 데이터로 계산 (빅맥/스타벅스 API 연동)
    try:
        # 국가 코드 검증
        country = country.upper()
        base_country = base_country.upper()
        
        if country not in [c.value for c in CountryCode]:
            raise InvalidCountryCodeError(country)
        if base_country not in [c.value for c in CountryCode]:
            raise InvalidCountryCodeError(base_country)
        
        # 물가 지수 조회
        price_index = await provider.get_price_index(country, base_country)
        
        return SuccessResponse(data=price_index)
        
    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get price index for {country}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve price index")


@app.get("/api/v1/currencies/{currency_code}", response_model=SuccessResponse)
async def get_currency_info(
    currency_code: str,
    country: Optional[str] = Query(None, description="국가 코드 (price-index 전용)"),
    base_country: str = Query("KR", description="기준 국가 코드 (price-index 전용)"),
    currency_provider: CurrencyProvider = Depends(get_currency_provider),
    price_provider: PriceIndexProvider = Depends(get_price_index_provider)
):
    """
    통화별 상세 정보 조회 또는 물가 지수 조회

    - **currency_code**: 3자리 통화 코드 (예: USD) 또는 "price-index"
    - **country**: 물가 지수 조회 시 대상 국가 코드 (예: JP)
    - **base_country**: 물가 지수 조회 시 기준 국가 코드 (기본값: KR)
    """
    try:
        # 통화 코드 검증
        currency_code = currency_code.upper()

        # price-index 특별 처리
        if currency_code == "PRICE-INDEX":
            if not country:
                raise HTTPException(status_code=400, detail="country parameter is required for price-index")

            # 국가 코드 검증
            country = country.upper()
            base_country = base_country.upper()

            if country not in [c.value for c in CountryCode]:
                raise InvalidCountryCodeError(country)
            if base_country not in [c.value for c in CountryCode]:
                raise InvalidCountryCodeError(base_country)

            # 물가 지수 조회
            price_index = await price_provider.get_price_index(country, base_country)
            return SuccessResponse(data=price_index)

        # 일반 통화 정보 조회
        if currency_code not in [c.value for c in CurrencyCode]:
            raise InvalidCurrencyCodeError(currency_code)

        # 통화 정보 조회
        currency_info = await currency_provider.get_currency_info(currency_code)

        return SuccessResponse(data=currency_info)

    except BaseServiceException:
        raise
    except Exception as e:
        logger.error(f"Failed to get info for {currency_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve information")


# AWS Lambda 핸들러 (배포 시 사용)
def lambda_handler(event, context):
    """
    AWS Lambda 핸들러
    
    AWS 배포 시 수정 필요사항:
    1. Mangum 설치: pip install mangum
    2. 아래 코드 주석 해제 및 수정
    3. Lambda 환경변수 설정
    4. VPC 설정 (Aurora, ElastiCache 접근용)
    5. IAM 역할 권한 설정
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
    port = int(os.getenv("PORT", "8001"))  # Currency Service는 8001 포트
    
    logger.info(f"Starting Currency Service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"
    )