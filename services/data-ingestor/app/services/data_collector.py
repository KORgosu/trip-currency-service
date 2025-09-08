"""
Data Collector - 외부 API에서 환율 데이터 수집
다중 소스에서 데이터를 수집하고 검증
"""
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, 'shared')

sys.path.insert(0, parent_dir)
sys.path.insert(0, shared_dir)

from shared.models import CollectionResult, RawExchangeRateData
from shared.exceptions import ExternalAPIError, DataValidationError
from shared.utils import HTTPUtils, DateTimeUtils, ValidationUtils, PerformanceUtils

def get_logger_safe():
    """안전한 로거 가져오기"""
    try:
        from shared.logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

# 전역 로거 초기화 (지연 로딩)
logger = get_logger_safe()


class DataCollector:
    """외부 데이터 수집자"""
    
    # TODO: 실시간 서비스 변경 - mock API 호출 대신 실제 BOK, Fed, ECB API 키 사용
    # - config.external_apis.bok_api_key 등 실제 키 로드 (Parameter Store)
    # - _collect_from_bok: 실제 BOK API 호출 및 응답 파싱 (매 5분 EventBridge 트리거)
    # - 다중 소스 병렬 호출로 실시간성 확보, 실패 시 SQS 폴백
    # AWS 연결: Lambda (data-ingestor-lambda) 또는 EKS CronJob 실행, S3 원본 저장, MSK 스트리밍
    
    def __init__(self):
        self.config = None  # 초기화 시점에서 로드
        self.session = None
        self.api_sources = {}  # 초기화 시점에서 로드
    
    async def initialize(self):
        """수집자 초기화"""
        try:
            # 설정 로드
            from shared.config import get_config
            self.config = get_config()
            
            # API 소스 초기화
            self.api_sources = self._initialize_api_sources()
            
            # HTTP 세션 생성
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Data collector initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize data collector", error=e)
            raise
    
    def _initialize_api_sources(self) -> Dict[str, Dict[str, Any]]:
        """API 소스 설정 초기화"""
        # TODO: AWS 연결 - 실제 API 키 Parameter Store에서 로드 (e.g., /data-ingestor/bok-api-key)
        # - bok_api_key: 실제 키 설정, 무료 한도 초과 시 유료 플랜
        # - exchangerate_api, fixer: 백업으로 사용, 실제 엔드포인트 확인
        return {
            "bok": {  # 한국은행
                "name": "Bank of Korea",
                "base_url": "https://ecos.bok.or.kr/api/StatisticSearch",
                "api_key": self.config.external_apis.bok_api_key,
                "currencies": ["USD", "JPY", "EUR", "GBP", "CNY"],
                "timeout": 15,
                "priority": 1,
                "active": bool(self.config.external_apis.bok_api_key)
            },
            "exchangerate_api": {  # 백업 API
                "name": "ExchangeRate-API",
                "base_url": "https://api.exchangerate-api.com/v4/latest/KRW",
                "api_key": self.config.external_apis.backup_api_key,
                "currencies": ["USD", "JPY", "EUR", "GBP", "CNY", "AUD", "CAD", "CHF"],
                "timeout": 10,
                "priority": 2,
                "active": True  # API 키 불필요
            },
            "fixer": {  # 추가 백업 API
                "name": "Fixer.io",
                "base_url": "http://data.fixer.io/api/latest",
                "api_key": "",  # 무료 버전
                "currencies": ["USD", "JPY", "EUR", "GBP"],
                "timeout": 10,
                "priority": 3,
                "active": True
            }
        }
    
    @PerformanceUtils.measure_time
    async def collect_all_data(self) -> List[CollectionResult]:
        """모든 소스에서 데이터 수집"""
        logger.info("Starting data collection from all sources")
        
        collection_tasks = []
        
        # 활성화된 소스들에 대해 병렬 수집
        for source_id, source_config in self.api_sources.items():
            if source_config.get("active", False):
                task = self._collect_from_source(source_id, source_config)
                collection_tasks.append(task)
        
        # 모든 수집 작업 실행
        results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # 결과 처리
        collection_results = []
        for i, result in enumerate(results):
            source_id = list(self.api_sources.keys())[i]
            
            if isinstance(result, Exception):
                # 예외 발생한 경우
                collection_results.append(
                    CollectionResult(
                        source=source_id,
                        success=False,
                        error_message=str(result),
                        collection_time=DateTimeUtils.utc_now(),
                        processing_time_ms=0
                    )
                )
            else:
                collection_results.append(result)
        
        # 수집 결과 로깅
        successful = sum(1 for r in collection_results if r.success)
        failed = len(collection_results) - successful
        
        logger.info(
            "Data collection completed",
            total_sources=len(collection_results),
            successful=successful,
            failed=failed
        )
        
        return collection_results
    
    async def _collect_from_source(
        self, 
        source_id: str, 
        source_config: Dict[str, Any]
    ) -> CollectionResult:
        """특정 소스에서 데이터 수집"""
        start_time = datetime.utcnow()
        
        logger.info(
            "Collecting data from source",
            source=source_id,
            source_name=source_config["name"]
        )
        
        try:
            # 소스별 수집 메서드 호출
            if source_id == "bok":
                raw_data = await self._collect_from_bok(source_config)
            elif source_id == "exchangerate_api":
                raw_data = await self._collect_from_exchangerate_api(source_config)
            elif source_id == "fixer":
                raw_data = await self._collect_from_fixer(source_config)
            else:
                raise ValueError(f"Unknown source: {source_id}")
            
            # 데이터 검증
            validated_data = self._validate_collected_data(raw_data, source_id)
            
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(
                "Data collection successful",
                source=source_id,
                currency_count=len(validated_data),
                processing_time_ms=processing_time
            )
            
            return CollectionResult(
                source=source_id,
                success=True,
                currency_count=len(validated_data),
                collection_time=end_time,
                processing_time_ms=processing_time,
                raw_data=validated_data
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds() * 1000)
            
            logger.error(
                "Data collection failed",
                source=source_id,
                error=e,
                processing_time_ms=processing_time
            )
            
            return CollectionResult(
                source=source_id,
                success=False,
                error_message=str(e),
                collection_time=end_time,
                processing_time_ms=processing_time
            )
    
    async def _collect_from_bok(self, config: Dict[str, Any]) -> List[RawExchangeRateData]:
        """한국은행 API에서 데이터 수집"""
        # TODO: 실시간 서비스 변경 - 실제 BOK API 호출로 mock 파라미터 제거
        # - statCode: 실제 환율 코드 확인 (e.g., 001Y001 for daily rates)
        # - API 키 Parameter Store에서 로드 (/data-ingestor/bok-api-key)
        # - 응답 에러 핸들링 강화 (rate limit, quota 초과)
        if not config.get("api_key"):
            raise ExternalAPIError("BOK API key not configured", "bok")
        
        # 한국은행 API 파라미터 구성
        today = DateTimeUtils.get_date_string().replace('-', '')
        
        params = {
            "service": "StatisticSearch",
            "authKey": config["api_key"],
            "requestType": "json",
            "language": "kr",
            "startCount": "1",
            "endCount": "10",
            "statCode": "731Y001",  # 환율 통계 코드
            "cycleType": "DD",      # 일별
            "startDate": today,
            "endDate": today,
            "dataType": "json"
        }
        
        try:
            async with self.session.get(config["base_url"], params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                # BOK API 응답 파싱
                raw_data = []
                
                if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                    for item in data["StatisticSearch"]["row"]:
                        currency_code = self._parse_bok_currency_code(item.get("STAT_NAME", ""))
                        rate_value = item.get("DATA_VALUE")
                        
                        if currency_code and rate_value:
                            raw_data.append(RawExchangeRateData(
                                currency_code=currency_code,
                                rate=float(rate_value),
                                source="bok",
                                timestamp=DateTimeUtils.utc_now(),
                                metadata={
                                    "stat_code": item.get("STAT_CODE"),
                                    "unit": item.get("UNIT_NAME"),
                                    "original_name": item.get("STAT_NAME")
                                }
                            ))
                
                return raw_data
                
        except Exception as e:
            raise ExternalAPIError(f"BOK API request failed: {str(e)}", "bok")
    
    async def _collect_from_exchangerate_api(self, config: Dict[str, Any]) -> List[RawExchangeRateData]:
        """ExchangeRate-API에서 데이터 수집"""
        try:
            async with self.session.get(config["base_url"]) as response:
                response.raise_for_status()
                data = await response.json()
                
                raw_data = []
                
                if "rates" in data:
                    for currency_code, rate in data["rates"].items():
                        if currency_code in config["currencies"]:
                            # KRW 기준이므로 역수 계산
                            krw_rate = 1 / rate if rate > 0 else 0
                            
                            raw_data.append(RawExchangeRateData(
                                currency_code=currency_code,
                                rate=krw_rate,
                                source="exchangerate_api",
                                timestamp=DateTimeUtils.utc_now(),
                                metadata={
                                    "base_currency": data.get("base", "KRW"),
                                    "date": data.get("date")
                                }
                            ))
                
                return raw_data
                
        except Exception as e:
            raise ExternalAPIError(f"ExchangeRate-API request failed: {str(e)}", "exchangerate_api")
    
    async def _collect_from_fixer(self, config: Dict[str, Any]) -> List[RawExchangeRateData]:
        """Fixer.io API에서 데이터 수집"""
        params = {
            "access_key": config.get("api_key", ""),
            "base": "EUR",  # 무료 버전은 EUR 기준
            "symbols": ",".join(config["currencies"] + ["KRW"])
        }
        
        try:
            async with self.session.get(config["base_url"], params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
                raw_data = []
                
                if "rates" in data and "KRW" in data["rates"]:
                    krw_to_eur = data["rates"]["KRW"]
                    
                    for currency_code, eur_rate in data["rates"].items():
                        if currency_code in config["currencies"] and currency_code != "KRW":
                            # EUR -> KRW 환산
                            krw_rate = krw_to_eur / eur_rate if eur_rate > 0 else 0
                            
                            raw_data.append(RawExchangeRateData(
                                currency_code=currency_code,
                                rate=krw_rate,
                                source="fixer",
                                timestamp=DateTimeUtils.utc_now(),
                                metadata={
                                    "base_currency": "EUR",
                                    "date": data.get("date"),
                                    "via_eur": True
                                }
                            ))
                
                return raw_data
                
        except Exception as e:
            raise ExternalAPIError(f"Fixer.io API request failed: {str(e)}", "fixer")
    
    def _parse_bok_currency_code(self, stat_name: str) -> Optional[str]:
        """한국은행 통계명에서 통화 코드 추출"""
        currency_mapping = {
            "미국": "USD",
            "일본": "JPY", 
            "유럽연합": "EUR",
            "영국": "GBP",
            "중국": "CNY"
        }
        
        for country, currency in currency_mapping.items():
            if country in stat_name:
                return currency
        
        return None
    
    def _validate_collected_data(
        self, 
        raw_data: List[RawExchangeRateData], 
        source: str
    ) -> List[RawExchangeRateData]:
        """수집된 데이터 검증"""
        validated_data = []
        
        for item in raw_data:
            try:
                # 통화 코드 검증
                ValidationUtils.validate_currency_code(item.currency_code)
                
                # 환율 값 검증
                rate_value = float(item.rate)
                if rate_value <= 0 or rate_value > 10000:
                    logger.warning(
                        "Invalid exchange rate value",
                        currency=item.currency_code,
                        rate=rate_value,
                        source=source
                    )
                    continue
                
                # 타임스탬프 검증
                if not item.timestamp:
                    item.timestamp = DateTimeUtils.utc_now()
                
                validated_data.append(item)
                
            except Exception as e:
                logger.warning(
                    "Data validation failed",
                    currency=item.currency_code,
                    error=str(e),
                    source=source
                )
                continue
        
        logger.debug(
            "Data validation completed",
            source=source,
            original_count=len(raw_data),
            validated_count=len(validated_data)
        )
        
        return validated_data
    
    async def test_api_connectivity(self) -> Dict[str, bool]:
        """API 연결성 테스트"""
        logger.info("Testing API connectivity")
        
        connectivity_results = {}
        
        for source_id, config in self.api_sources.items():
            if not config.get("active", False):
                connectivity_results[source_id] = False
                continue
            
            try:
                # 간단한 연결 테스트
                if source_id == "exchangerate_api":
                    async with self.session.get(config["base_url"]) as response:
                        connectivity_results[source_id] = response.status == 200
                else:
                    # 다른 API들은 기본 URL 테스트
                    async with self.session.get(config["base_url"].split('?')[0]) as response:
                        connectivity_results[source_id] = response.status in [200, 400]  # 400도 연결은 됨
                        
            except Exception as e:
                logger.warning(f"Connectivity test failed for {source_id}", error=e)
                connectivity_results[source_id] = False
        
        logger.info("API connectivity test completed", results=connectivity_results)
        return connectivity_results
    
    async def close(self):
        """리소스 정리"""
        if self.session:
            await self.session.close()
        
        logger.info("Data collector closed")