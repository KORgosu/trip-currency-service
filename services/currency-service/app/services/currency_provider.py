"""
Currency Provider - 환율 데이터 제공 서비스
Redis 캐시 우선 조회, Aurora DB 폴백
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import json

from shared.database import RedisHelper, MySQLHelper
import logging
from shared.models import ExchangeRate, CurrencyInfo
from shared.exceptions import (
    DatabaseError, CacheError, NotFoundError, 
    handle_database_exception, handle_cache_exception
)

logger = logging.getLogger(__name__)


class CurrencyProvider:
    """환율 데이터 제공자"""
    
    # TODO: 실시간 서비스 변경 - mock DB 데이터 대신 data-ingestor의 실제 환율 수집 데이터 사용
    # - _get_rate_from_db: Aurora DB의 exchange_rate_history 테이블에서 실제 최신 환율 조회
    # - data-ingestor에서 BOK API 호출로 실시간 업데이트
    # AWS 연결: ElastiCache Redis 캐싱 (TTL 10분), Aurora MySQL 폴백
    
    def __init__(self):
        self.redis_helper = RedisHelper()
        self.mysql_helper = MySQLHelper()
        self.cache_ttl = 600  # 10분
    
    async def get_latest_rates(
        self, 
        currency_codes: List[str] = None, 
        base_currency: str = "KRW"
    ) -> Dict[str, Any]:
        """
        최신 환율 조회
        
        Args:
            currency_codes: 조회할 통화 코드 리스트
            base_currency: 기준 통화
            
        Returns:
            환율 데이터 딕셔너리
        """
        try:
            # 기본 통화 목록 설정
            if not currency_codes:
                currency_codes = ["USD", "JPY", "EUR", "GBP", "CNY"]
            
            rates = {}
            cache_hits = 0
            
            # Redis에서 캐시된 환율 조회
            for currency_code in currency_codes:
                try:
                    cached_rate = await self._get_cached_rate(currency_code)
                    if cached_rate:
                        rates[currency_code] = float(cached_rate["deal_base_rate"])
                        cache_hits += 1
                    else:
                        # 캐시 미스 시 DB에서 조회
                        db_rate = await self._get_rate_from_db(currency_code)
                        if db_rate:
                            rates[currency_code] = float(db_rate["deal_base_rate"])
                            # 캐시에 저장
                            await self._cache_rate(currency_code, db_rate)
                        else:
                            logger.warning(f"No rate found for {currency_code}")
                
                except Exception as e:
                    logger.error(f"Failed to get rate for {currency_code}: {e}")
                    continue
            
            return {
                "base": base_currency,
                "timestamp": int(datetime.utcnow().timestamp()),
                "rates": rates,
                "source": "redis_cache" if cache_hits > 0 else "database",
                "cache_hit": cache_hits > 0,
                "cache_hit_ratio": cache_hits / len(currency_codes) if currency_codes else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get latest rates: {e}")
            raise handle_database_exception(e, "get_latest_rates")
    
    async def get_currency_info(self, currency_code: str) -> Dict[str, Any]:
        """
        통화 상세 정보 조회
        
        Args:
            currency_code: 통화 코드
            
        Returns:
            통화 정보 딕셔너리
        """
        try:
            # 캐시에서 먼저 조회
            cache_key = f"currency_info:{currency_code}"
            cached_info = await self.redis_helper.get_json(cache_key)
            
            if cached_info:
                return cached_info
            
            # DB에서 통화 정보 조회
            query = """
                SELECT 
                    c.currency_code,
                    c.currency_name_ko as currency_name,
                    c.country_code,
                    c.country_name_ko as country_name,
                    c.symbol,
                    h.deal_base_rate as current_rate,
                    h.tts,
                    h.ttb,
                    h.recorded_at as last_updated,
                    h.source
                FROM currencies c
                LEFT JOIN exchange_rate_history h ON c.currency_code = h.currency_code
                WHERE c.currency_code = %s 
                    AND c.is_active = TRUE
                    AND h.recorded_at = (
                        SELECT MAX(recorded_at) 
                        FROM exchange_rate_history 
                        WHERE currency_code = c.currency_code
                    )
            """
            
            result = await self.mysql_helper.execute_query(query, (currency_code,))
            
            if not result:
                raise NotFoundError("currency", currency_code)
            
            currency_info = result[0]
            
            # 응답 데이터 구성
            response_data = {
                "currency_code": currency_info["currency_code"],
                "currency_name": currency_info["currency_name"],
                "country_code": currency_info["country_code"],
                "country_name": currency_info["country_name"],
                "symbol": currency_info["symbol"],
                "current_rate": float(currency_info["current_rate"]) if currency_info["current_rate"] else None,
                "tts": float(currency_info["tts"]) if currency_info["tts"] else None,
                "ttb": float(currency_info["ttb"]) if currency_info["ttb"] else None,
                "last_updated": currency_info["last_updated"].isoformat() + 'Z' if currency_info["last_updated"] else None,
                "source": currency_info["source"]
            }
            
            # 캐시에 저장 (1시간)
            await self.redis_helper.set_json(cache_key, response_data, 3600)
            
            return response_data
            
        except Exception as e:
            logger.error(f"Failed to get currency info for {currency_code}: {e}")
            if isinstance(e, NotFoundError):
                raise
            raise handle_database_exception(e, "get_currency_info", "currencies")
    
    async def _get_cached_rate(self, currency_code: str) -> Optional[Dict[str, Any]]:
        """Redis에서 캐시된 환율 조회"""
        try:
            cache_key = f"rate:{currency_code}"
            cached_data = await self.redis_helper.get_hash(cache_key)
            
            if cached_data and "deal_base_rate" in cached_data:
                return {
                    "currency_code": currency_code,
                    "currency_name": cached_data.get("currency_name", ""),
                    "deal_base_rate": cached_data["deal_base_rate"],
                    "tts": cached_data.get("tts"),
                    "ttb": cached_data.get("ttb"),
                    "source": cached_data.get("source", "cache"),
                    "last_updated_at": cached_data.get("last_updated_at")
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache lookup failed for {currency_code}", error=e)
            return None
    
    async def _get_rate_from_db(self, currency_code: str) -> Optional[Dict[str, Any]]:
        """데이터베이스에서 최신 환율 조회"""
        # TODO: 실시간 서비스 변경 - data-ingestor에서 수집된 실제 환율 데이터 사용
        # - exchange_rate_history 테이블에 매 5분마다 업데이트 (data_processor.process_exchange_rate_data 호출)
        # - 쿼리 최적화: 인덱스 idx_currency_date (currency_code, recorded_at DESC) 사용
        try:
            query = """
                SELECT
                    currency_code,
                    currency_name,
                    deal_base_rate,
                    tts,
                    ttb,
                    source,
                    recorded_at
                FROM exchange_rate_history
                WHERE currency_code = %s
                ORDER BY recorded_at DESC
                LIMIT 1
            """
            
            result = await self.mysql_helper.execute_query(query, (currency_code,))
            
            if result:
                rate_data = result[0]
                return {
                    "currency_code": rate_data["currency_code"],
                    "currency_name": rate_data["currency_name"],
                    "deal_base_rate": str(rate_data["deal_base_rate"]),
                    "tts": str(rate_data["tts"]) if rate_data["tts"] else None,
                    "ttb": str(rate_data["ttb"]) if rate_data["ttb"] else None,
                    "source": rate_data["source"],
                    "last_updated_at": rate_data["recorded_at"].isoformat() + 'Z'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Database lookup failed for {currency_code}: {e}")
            raise handle_database_exception(e, "get_rate_from_db", "exchange_rate_history")
    
    async def _cache_rate(self, currency_code: str, rate_data: Dict[str, Any]):
        """환율 데이터를 Redis에 캐시"""
        # TODO: AWS 연결 - ElastiCache Redis 클러스터 사용
        # - set_hash: 실제 클러스터 엔드포인트로 캐싱
        # - TTL 10분으로 실시간성 유지
        try:
            cache_key = f"rate:{currency_code}"
            
            cache_data = {
                "currency_name": rate_data["currency_name"],
                "deal_base_rate": rate_data["deal_base_rate"],
                "tts": rate_data.get("tts", ""),
                "ttb": rate_data.get("ttb", ""),
                "source": rate_data["source"],
                "last_updated_at": rate_data["last_updated_at"]
            }
            
            await self.redis_helper.set_hash(cache_key, cache_data, self.cache_ttl)
            
        except Exception as e:
            logger.warning(f"Failed to cache rate for {currency_code}", error=e)
            # 캐시 실패는 치명적이지 않으므로 예외를 발생시키지 않음