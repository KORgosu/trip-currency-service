"""
Data Processor - 수집된 데이터 처리 및 저장
데이터 정제, 변환, 저장 및 메시징 처리
"""
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional

import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, 'shared')

sys.path.insert(0, parent_dir)
sys.path.insert(0, shared_dir)

from shared.database import MySQLHelper, RedisHelper, get_db_manager
from shared.logging import get_logger
from shared.models import CollectionResult, RawExchangeRateData, ExchangeRate
from shared.exceptions import DatabaseError, DataProcessingError
from shared.utils import DateTimeUtils, DataUtils, PerformanceUtils, SecurityUtils
from shared.messaging import send_exchange_rate_update

logger = get_logger(__name__)


class DataProcessor:
    """데이터 처리자"""
    
    def __init__(self):
        self.mysql_helper = MySQLHelper()
        self.redis_helper = RedisHelper()
        self.batch_size = 100
        self.duplicate_check_enabled = True
    
    async def initialize(self):
        """처리자 초기화"""
        try:
            logger.info("Data processor initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize data processor", error=e)
            raise
    
    @PerformanceUtils.measure_time
    async def process_exchange_rate_data(self, collection_result: CollectionResult):
        """환율 데이터 처리"""
        if not collection_result.success or not collection_result.raw_data:
            logger.warning("No data to process", source=collection_result.source)
            return
        
        logger.info(
            "Processing exchange rate data",
            source=collection_result.source,
            data_count=len(collection_result.raw_data)
        )
        
        try:
            # 데이터 정제 및 변환
            processed_data = await self._clean_and_transform_data(
                collection_result.raw_data, 
                collection_result.source
            )
            
            if not processed_data:
                logger.warning("No valid data after cleaning", source=collection_result.source)
                return
            
            # 중복 데이터 체크 및 필터링
            if self.duplicate_check_enabled:
                processed_data = await self._filter_duplicates(processed_data)
            
            # 데이터베이스에 저장
            saved_count = await self._save_to_database(processed_data)
            
            # Redis 캐시 업데이트
            await self._update_cache(processed_data)
            
            # 메시징 시스템으로 이벤트 전송
            await self._send_update_events(processed_data)
            
            logger.info(
                "Data processing completed",
                source=collection_result.source,
                processed_count=len(processed_data),
                saved_count=saved_count
            )
            
        except Exception as e:
            logger.error("Failed to process exchange rate data", error=e, source=collection_result.source)
            raise DataProcessingError(
                f"Failed to process data from {collection_result.source}",
                data_type="exchange_rate",
                processing_step="processing"
            )
    
    async def _clean_and_transform_data(
        self, 
        raw_data: List[RawExchangeRateData], 
        source: str
    ) -> List[ExchangeRate]:
        """데이터 정제 및 변환"""
        processed_data = []
        
        for raw_item in raw_data:
            try:
                # 환율 값 정규화
                base_rate = DataUtils.safe_decimal(raw_item.rate, 4)
                
                # TTS/TTB 계산 (송금 시 수수료 적용)
                tts = base_rate * Decimal('1.02')  # 송금 보낼 때 2% 수수료
                ttb = base_rate * Decimal('0.98')  # 받을 때 2% 할인
                
                # 통화명 매핑
                currency_name = self._get_currency_name(raw_item.currency_code)
                
                # ExchangeRate 객체 생성
                exchange_rate = ExchangeRate(
                    currency_code=raw_item.currency_code,
                    currency_name=currency_name,
                    deal_base_rate=base_rate,
                    tts=tts,
                    ttb=ttb,
                    source=source,
                    recorded_at=raw_item.timestamp
                )
                
                processed_data.append(exchange_rate)
                
            except Exception as e:
                logger.warning(
                    "Failed to process raw data item",
                    currency=raw_item.currency_code,
                    error=str(e),
                    source=source
                )
                continue
        
        logger.debug(
            "Data cleaning completed",
            source=source,
            original_count=len(raw_data),
            processed_count=len(processed_data)
        )
        
        return processed_data
    
    def _get_currency_name(self, currency_code: str) -> str:
        """통화 코드에서 통화명 반환"""
        currency_names = {
            "USD": "미국 달러",
            "JPY": "일본 엔",
            "EUR": "유럽연합 유로",
            "GBP": "영국 파운드",
            "CNY": "중국 위안",
            "AUD": "호주 달러",
            "CAD": "캐나다 달러",
            "CHF": "스위스 프랑",
            "HKD": "홍콩 달러",
            "SGD": "싱가포르 달러"
        }
        return currency_names.get(currency_code, currency_code)
    
    async def _filter_duplicates(self, processed_data: List[ExchangeRate]) -> List[ExchangeRate]:
        """중복 데이터 필터링"""
        if not processed_data:
            return []
        
        try:
            # 최근 1시간 내 동일 통화의 데이터가 있는지 확인
            one_hour_ago = DateTimeUtils.utc_now() - timedelta(hours=1)
            
            filtered_data = []
            
            for item in processed_data:
                # 중복 체크 쿼리
                query = """
                    SELECT COUNT(*) as count
                    FROM exchange_rate_history
                    WHERE currency_code = %s 
                        AND source = %s
                        AND recorded_at > %s
                        AND ABS(deal_base_rate - %s) < 0.01
                """
                
                result = await self.mysql_helper.execute_query(
                    query, 
                    (item.currency_code, item.source, one_hour_ago, float(item.deal_base_rate))
                )
                
                if result and result[0]['count'] == 0:
                    # 중복이 아닌 경우만 추가
                    filtered_data.append(item)
                else:
                    logger.debug(
                        "Duplicate data filtered",
                        currency=item.currency_code,
                        source=item.source,
                        rate=float(item.deal_base_rate)
                    )
            
            logger.debug(
                "Duplicate filtering completed",
                original_count=len(processed_data),
                filtered_count=len(filtered_data)
            )
            
            return filtered_data
            
        except Exception as e:
            logger.warning("Duplicate filtering failed, proceeding with all data", error=e)
            return processed_data
    
    async def _save_to_database(self, processed_data: List[ExchangeRate]) -> int:
        """데이터베이스에 저장"""
        if not processed_data:
            return 0
        
        try:
            saved_count = 0
            
            # 배치 단위로 저장
            for i in range(0, len(processed_data), self.batch_size):
                batch = processed_data[i:i + self.batch_size]
                
                for item in batch:
                    try:
                        # INSERT 쿼리 실행
                        query = """
                            INSERT INTO exchange_rate_history 
                            (currency_code, currency_name, deal_base_rate, tts, ttb, source, recorded_at, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        await self.mysql_helper.execute_insert(
                            query,
                            (
                                item.currency_code,
                                item.currency_name,
                                float(item.deal_base_rate),
                                float(item.tts) if item.tts else None,
                                float(item.ttb) if item.ttb else None,
                                item.source,
                                item.recorded_at,
                                DateTimeUtils.utc_now()
                            )
                        )
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(
                            "Failed to save individual record",
                            currency=item.currency_code,
                            error=str(e)
                        )
                        continue
                
                # 배치 간 짧은 대기
                if i + self.batch_size < len(processed_data):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Database save completed",
                total_records=len(processed_data),
                saved_records=saved_count
            )
            
            return saved_count
            
        except Exception as e:
            logger.error("Failed to save to database", error=e)
            raise DatabaseError(
                "Failed to save exchange rate data",
                operation="batch_insert",
                table="exchange_rate_history"
            )
    
    async def _update_cache(self, processed_data: List[ExchangeRate]):
        """Redis 캐시 업데이트"""
        try:
            cache_updates = 0
            
            for item in processed_data:
                try:
                    # 캐시 키 생성
                    cache_key = f"rate:{item.currency_code}"
                    
                    # 캐시 데이터 구성
                    cache_data = {
                        'currency_name': item.currency_name,
                        'deal_base_rate': str(item.deal_base_rate),
                        'tts': str(item.tts) if item.tts else '',
                        'ttb': str(item.ttb) if item.ttb else '',
                        'source': item.source,
                        'last_updated_at': DateTimeUtils.to_iso_string(item.recorded_at)
                    }
                    
                    # Redis에 저장 (TTL: 1시간)
                    await self.redis_helper.set_hash(cache_key, cache_data, 3600)
                    cache_updates += 1
                    
                except Exception as e:
                    logger.warning(
                        "Failed to update cache for currency",
                        currency=item.currency_code,
                        error=str(e)
                    )
                    continue
            
            logger.debug(
                "Cache update completed",
                total_items=len(processed_data),
                cache_updates=cache_updates
            )
            
        except Exception as e:
            # 캐시 업데이트 실패는 로그만 남기고 계속 진행
            logger.warning("Cache update failed", error=e)
    
    async def _send_update_events(self, processed_data: List[ExchangeRate]):
        """업데이트 이벤트 전송"""
        try:
            events_sent = 0
            
            for item in processed_data:
                try:
                    # 이벤트 데이터 구성
                    event_data = {
                        "currency_code": item.currency_code,
                        "currency_name": item.currency_name,
                        "deal_base_rate": float(item.deal_base_rate),
                        "tts": float(item.tts) if item.tts else None,
                        "ttb": float(item.ttb) if item.ttb else None,
                        "source": item.source,
                        "recorded_at": DateTimeUtils.to_iso_string(item.recorded_at),
                        "updated_at": DateTimeUtils.to_iso_string(DateTimeUtils.utc_now())
                    }
                    
                    # 메시징 시스템으로 전송
                    success = await send_exchange_rate_update(event_data)
                    
                    if success:
                        events_sent += 1
                    
                except Exception as e:
                    logger.warning(
                        "Failed to send update event",
                        currency=item.currency_code,
                        error=str(e)
                    )
                    continue
            
            logger.debug(
                "Update events sent",
                total_items=len(processed_data),
                events_sent=events_sent
            )
            
        except Exception as e:
            # 이벤트 전송 실패는 로그만 남기고 계속 진행
            logger.warning("Failed to send update events", error=e)
    
    async def process_price_index_data(self, price_data: Dict[str, Any]):
        """물가 지수 데이터 처리 (향후 확장용)"""
        logger.info("Processing price index data")
        
        try:
            # TODO: 물가 지수 데이터 처리 로직 구현
            # 현재는 로그만 남김
            logger.info("Price index data processing not implemented yet")
            
        except Exception as e:
            logger.error("Failed to process price index data", error=e)
            raise DataProcessingError(
                "Failed to process price index data",
                data_type="price_index",
                processing_step="processing"
            )
    
    async def cleanup_old_data(self, retention_days: int = 365):
        """오래된 데이터 정리"""
        logger.info("Starting data cleanup", retention_days=retention_days)
        
        try:
            cutoff_date = DateTimeUtils.utc_now() - timedelta(days=retention_days)
            
            # 오래된 이력 데이터 삭제
            delete_query = """
                DELETE FROM exchange_rate_history
                WHERE recorded_at < %s
            """
            
            deleted_count = await self.mysql_helper.execute_update(delete_query, (cutoff_date,))
            
            logger.info(
                "Data cleanup completed",
                cutoff_date=DateTimeUtils.to_iso_string(cutoff_date),
                deleted_records=deleted_count
            )
            
        except Exception as e:
            logger.error("Failed to cleanup old data", error=e)
            raise DatabaseError(
                "Failed to cleanup old exchange rate data",
                operation="delete",
                table="exchange_rate_history"
            )
    
    async def generate_daily_aggregates(self, target_date: datetime = None):
        """일별 집계 데이터 생성"""
        if target_date is None:
            target_date = DateTimeUtils.utc_now() - timedelta(days=1)  # 어제 데이터
        
        logger.info("Generating daily aggregates", target_date=DateTimeUtils.get_date_string(target_date))
        
        try:
            # 일별 집계 쿼리
            aggregate_query = """
                INSERT INTO daily_exchange_rates 
                (currency_code, trade_date, open_rate, close_rate, high_rate, low_rate, avg_rate, volume, volatility, created_at)
                SELECT 
                    currency_code,
                    DATE(recorded_at) as trade_date,
                    (SELECT deal_base_rate FROM exchange_rate_history h2 
                     WHERE h2.currency_code = h1.currency_code 
                     AND DATE(h2.recorded_at) = DATE(h1.recorded_at)
                     ORDER BY h2.recorded_at ASC LIMIT 1) as open_rate,
                    (SELECT deal_base_rate FROM exchange_rate_history h2 
                     WHERE h2.currency_code = h1.currency_code 
                     AND DATE(h2.recorded_at) = DATE(h1.recorded_at)
                     ORDER BY h2.recorded_at DESC LIMIT 1) as close_rate,
                    MAX(deal_base_rate) as high_rate,
                    MIN(deal_base_rate) as low_rate,
                    AVG(deal_base_rate) as avg_rate,
                    COUNT(*) as volume,
                    STDDEV(deal_base_rate) as volatility,
                    NOW() as created_at
                FROM exchange_rate_history h1
                WHERE DATE(recorded_at) = %s
                GROUP BY currency_code, DATE(recorded_at)
                ON DUPLICATE KEY UPDATE
                    close_rate = VALUES(close_rate),
                    high_rate = VALUES(high_rate),
                    low_rate = VALUES(low_rate),
                    avg_rate = VALUES(avg_rate),
                    volume = VALUES(volume),
                    volatility = VALUES(volatility),
                    created_at = VALUES(created_at)
            """
            
            affected_rows = await self.mysql_helper.execute_update(
                aggregate_query, 
                (target_date.date(),)
            )
            
            logger.info(
                "Daily aggregates generated",
                target_date=DateTimeUtils.get_date_string(target_date),
                affected_rows=affected_rows
            )
            
        except Exception as e:
            logger.error("Failed to generate daily aggregates", error=e)
            raise DatabaseError(
                "Failed to generate daily aggregates",
                operation="aggregate",
                table="daily_exchange_rates"
            )
    
    async def close(self):
        """리소스 정리"""
        logger.info("Data processor closed")