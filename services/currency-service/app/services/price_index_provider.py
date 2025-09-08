"""
Price Index Provider - 물가 지수 데이터 제공 서비스
빅맥 지수, 스타벅스 지수 등 물가 비교 데이터 제공
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import json

from shared.database import RedisHelper, MySQLHelper
import logging
from shared.models import PriceIndex
from shared.exceptions import (
    NotFoundError, handle_database_exception
)

logger = logging.getLogger(__name__)


class PriceIndexProvider:
    """물가 지수 데이터 제공자"""
    
    # TODO: 실시간 서비스 변경 - mock 데이터 대신 실제 빅맥/스타벅스 API 또는 크롤링 구현
    # - _get_mock_price_data: 외부 API (TheEconomist Big Mac Index API) 또는 웹 스크래핑으로 실제 가격 수집
    # - _get_real_exchange_rate: 실제 환율 API 호출 (BOK, ExchangeRate-API)
    # - 수집된 데이터 DB 저장 (data-ingestor 역할)
    # AWS 연결: ElastiCache Redis 캐싱, Aurora MySQL 물가 테이블 저장
    
    def __init__(self):
        self.redis_helper = RedisHelper()
        self.mysql_helper = MySQLHelper()
        self.cache_ttl = 3600  # 1시간 (물가 데이터는 자주 변경되지 않음)
    
    async def get_price_index(
        self, 
        country_code: str, 
        base_country: str = "KR"
    ) -> Dict[str, Any]:
        """
        물가 지수 조회
        
        Args:
            country_code: 대상 국가 코드
            base_country: 기준 국가 코드
            
        Returns:
            물가 지수 데이터
        """
        try:
            # 캐시 키 생성
            cache_key = f"price_index:{country_code}:{base_country}"
            
            # 캐시에서 먼저 조회
            cached_data = await self.redis_helper.get_json(cache_key)
            if cached_data:
                logger.info(f"Price index cache hit for {country_code}")
                return cached_data
            
            # 캐시 미스 시 계산
            price_index_data = await self._calculate_price_index(country_code, base_country)
            
            # 캐시에 저장
            await self.redis_helper.set_json(cache_key, price_index_data, self.cache_ttl)
            
            return price_index_data
            
        except Exception as e:
            logger.error(f"Failed to get price index for {country_code}: {e}")
            if isinstance(e, NotFoundError):
                raise
            raise handle_database_exception(e, "get_price_index")
    
    async def _calculate_price_index(
        self, 
        country_code: str, 
        base_country: str
    ) -> Dict[str, Any]:
        """물가 지수 계산"""
        try:
            # 국가 정보 조회
            country_info = await self._get_country_info(country_code)
            base_country_info = await self._get_country_info(base_country)
            
            if not country_info:
                raise NotFoundError("country", country_code)
            if not base_country_info:
                raise NotFoundError("country", base_country)
            
            # 현재는 더미 데이터로 구현 (실제로는 외부 API에서 수집)
            # TODO: 실제 빅맥 지수, 스타벅스 가격 데이터 연동
            price_data = await self._get_mock_price_data(country_code, base_country)
            
            # 지수 계산
            bigmac_index = self._calculate_bigmac_index(
                price_data["target_bigmac_price"], 
                price_data["base_bigmac_price"],
                price_data["exchange_rate"]
            )
            
            starbucks_index = self._calculate_starbucks_index(
                price_data["target_starbucks_price"],
                price_data["base_starbucks_price"], 
                price_data["exchange_rate"]
            )
            
            composite_index = (bigmac_index + starbucks_index) / 2
            
            return {
                "country_code": country_code,
                "country_name": country_info["country_name"],
                "base_country": base_country,
                "indices": {
                    "bigmac_index": float(bigmac_index),
                    "starbucks_index": float(starbucks_index),
                    "composite_index": float(composite_index)
                },
                "price_data": {
                    "bigmac_price_local": price_data["target_bigmac_price"],
                    "bigmac_price_usd": price_data["target_bigmac_price"] / price_data["exchange_rate"],
                    "starbucks_latte_local": price_data["target_starbucks_price"],
                    "starbucks_latte_usd": price_data["target_starbucks_price"] / price_data["exchange_rate"]
                },
                "last_updated": datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate price index: {e}")
            raise
    
    async def _get_country_info(self, country_code: str) -> Optional[Dict[str, Any]]:
        """국가 정보 조회"""
        try:
            query = """
                SELECT DISTINCT
                    country_code,
                    country_name_ko as country_name,
                    country_name_en
                FROM currencies 
                WHERE country_code = %s AND is_active = TRUE
                LIMIT 1
            """
            
            result = await self.mysql_helper.execute_query(query, (country_code,))
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Failed to get country info for {country_code}: {e}")
            return None
    
    async def _get_mock_price_data(
        self,
        country_code: str,
        base_country: str
    ) -> Dict[str, Any]:
        """
        실제 환율 데이터 기반 물가 데이터 생성
        """
        # TODO: 실시간 서비스 변경 - 실제 빅맥 지수 API 호출 (TheEconomist GitHub API 또는 공식 API)
        # - aiohttp로 https://raw.githubusercontent.com/TheEconomist/big-mac-data/master/output-data/big-mac-full-index.csv 파싱
        # - 스타벅스 가격: 국가별 Starbucks 웹사이트 크롤링 또는 API (e.g., unofficial API)
        # - 수집된 가격 DB 저장 (price_indices 테이블, Aurora MySQL)
        # 실제 환율 조회
        exchange_rate = await self._get_real_exchange_rate(country_code)
        
        # 실제 빅맥 가격 데이터 (사용자 제공 크롤링 데이터 기반)
        real_bigmac_prices = {
            "US": {"bigmac_usd": 5.50, "currency": "USD"},
            "JP": {"bigmac_usd": 3.12, "currency": "JPY"},  # 실제 크롤링된 데이터
            "KR": {"bigmac_usd": 3.8, "currency": "KRW"},
            "CH": {"bigmac_usd": 7.75, "currency": "CHF"},  # 스위스 (가장 비싼 국가)
            "AU": {"bigmac_usd": 4.90, "currency": "AUD"},
            "CA": {"bigmac_usd": 4.85, "currency": "CAD"},
            "GB": {"bigmac_usd": 4.20, "currency": "GBP"},
            "CN": {"bigmac_usd": 3.05, "currency": "CNY"},
            "SG": {"bigmac_usd": 4.25, "currency": "SGD"},
            "EU": {"bigmac_usd": 4.80, "currency": "EUR"},
            "TH": {"bigmac_usd": 2.85, "currency": "THB"}
        }
        
        # 스타벅스 가격 (추정값)
        starbucks_multiplier = 0.9  # 빅맥 가격의 90% 정도
        
        target_data = real_bigmac_prices.get(country_code, real_bigmac_prices["US"])
        base_data = real_bigmac_prices.get(base_country, real_bigmac_prices["KR"])
        
        # 현지 통화 가격 계산
        target_bigmac_local = target_data["bigmac_usd"] * exchange_rate
        target_starbucks_local = target_bigmac_local * starbucks_multiplier
        
        base_bigmac_local = base_data["bigmac_usd"] * (await self._get_real_exchange_rate(base_country))
        base_starbucks_local = base_bigmac_local * starbucks_multiplier
        
        return {
            "target_bigmac_price": target_bigmac_local,
            "target_starbucks_price": target_starbucks_local,
            "base_bigmac_price": base_bigmac_local,
            "base_starbucks_price": base_starbucks_local,
            "exchange_rate": exchange_rate
        }
    
    async def _get_real_exchange_rate(self, country_code: str) -> float:
        """실제 환율 조회 (사용자 제공 데이터 기반)"""
        # TODO: 실시간 서비스 변경 - mock 하드코딩 대신 BOK 또는 ExchangeRate-API 호출
        # - aiohttp로 https://ecos.bok.or.kr/api/StatisticSearch 또는 https://api.exchangerate-api.com/v4/latest/KRW 호출
        # - API 키 config.external_apis.bok_api_key 또는 backup_api_key 사용
        # - 수집된 환율 DB 저장 (exchange_rate_history 테이블)
        try:
            # 실제 환율 데이터 (사용자 제공)
            real_exchange_rates = {
                "US": 1385.3,    # USD
                "JP": 936.39,    # JPY(100) → JPY 단위로 환산
                "KR": 1.0,       # KRW (기준)
                "EU": 1616.16,   # EUR
                "GB": 1871.12,   # GBP
                "CN": 192.78,    # CNH
                "AU": 899.34,    # AUD
                "CA": 1003.62,   # CAD
                "CH": 1715.65,   # CHF
                "SG": 1078.31,   # SGD
                "HK": 177.16,    # HKD
                "TH": 42.6       # THB
            }
            
            # 국가 코드별 환율 반환
            rate = real_exchange_rates.get(country_code, 1385.3)  # 기본값 USD
            
            # JPY는 100엔 단위이므로 조정
            if country_code == "JP":
                rate = rate / 100  # 100엔 → 1엔 단위
            
            return rate
            
        except Exception as e:
            logger.warning(f"Failed to get real exchange rate for {country_code}: {e}")
            return 1385.3  # USD 기본값
    
    def _calculate_bigmac_index(
        self, 
        target_price: float, 
        base_price: float, 
        exchange_rate: float
    ) -> Decimal:
        """빅맥 지수 계산"""
        try:
            # 구매력 평가 기준 지수 계산
            # 100을 기준으로 상대적 물가 수준 표시
            if base_price == 0:
                return Decimal("100.0")
            
            # 환율을 고려한 상대 가격 비교
            adjusted_target_price = target_price / exchange_rate
            index = (adjusted_target_price / base_price) * 100
            
            return Decimal(str(round(index, 2)))
            
        except Exception as e:
            logger.error(f"Failed to calculate bigmac index: {e}")
            return Decimal("100.0")
    
    def _calculate_starbucks_index(
        self, 
        target_price: float, 
        base_price: float, 
        exchange_rate: float
    ) -> Decimal:
        """스타벅스 지수 계산"""
        try:
            # 빅맥 지수와 동일한 방식으로 계산
            if base_price == 0:
                return Decimal("100.0")
            
            adjusted_target_price = target_price / exchange_rate
            index = (adjusted_target_price / base_price) * 100
            
            return Decimal(str(round(index, 2)))
            
        except Exception as e:
            logger.error(f"Failed to calculate starbucks index: {e}")
            return Decimal("100.0")