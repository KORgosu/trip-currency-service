"""
History Provider - 환율 이력 데이터 제공 서비스
Aurora DB에서 환율 이력 조회 및 차트 데이터 생성
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
import json

from shared.database import RedisHelper, MySQLHelper
import logging
from shared.models import HistoryDataPoint, HistoryStatistics
from shared.exceptions import (
    DatabaseError, NotFoundError, InvalidPeriodError,
    handle_database_exception
)

logger = logging.getLogger(__name__)


class HistoryProvider:
    """환율 이력 데이터 제공자"""
    
    # TODO: 실시간 서비스 변경 - mock 데이터 생성 대신 data-ingestor의 실제 환율 이력 사용
    # - _generate_mock_history_data: 제거, 실제 DB 쿼리만 사용 (data-ingestor 매 5분 업데이트)
    # - _fetch_history_from_db: 파티셔닝 테이블 사용으로 대용량 쿼리 최적화 (월별 파티션)
    # AWS 연결: Aurora Global Database로 멀티 리전 읽기, ElastiCache Redis 캐싱 (TTL 기간별 다름)
    
    def __init__(self):
        self.redis_helper = RedisHelper()
        self.mysql_helper = MySQLHelper()
        self.cache_ttl = {
            "1w": 900,   # 15분
            "1m": 1800,  # 30분
            "6m": 3600   # 1시간
        }
    
    async def get_exchange_rate_history(
        self,
        period: str,
        target_currency: str,
        base_currency: str = "KRW",
        interval: str = "daily"
    ) -> Dict[str, Any]:
        """
        환율 이력 데이터 조회
        
        Args:
            period: 조회 기간 (1w, 1m, 6m)
            target_currency: 대상 통화
            base_currency: 기준 통화
            interval: 데이터 간격 (daily, hourly)
            
        Returns:
            환율 이력 데이터
        """
        try:
            # 캐시 키 생성
            cache_key = f"chart:{period}:{base_currency}:{target_currency}:{interval}"
            
            # 캐시에서 먼저 조회
            cached_data = await self.redis_helper.get_json(cache_key)
            if cached_data:
                logger.info(f"History cache hit for {target_currency}")
                return cached_data
            
            # 기간 계산
            start_date, end_date = self._calculate_date_range(period)
            
            # 데이터베이스에서 이력 데이터 조회
            raw_data = await self._fetch_history_from_db(
                target_currency, start_date, end_date, interval
            )
            
            # TODO: 실시간 서비스 변경 - mock 데이터 제거, 실제 데이터 없으면 에러 또는 최근 데이터 사용
            # - data-ingestor가 매 5분 업데이트하므로 데이터 부재 시 에러 발생 또는 최근 24시간 데이터
            # - 에러 시 fallback to S3 또는 Redis 최근 데이터
            if not raw_data:
                # 데이터가 없으면 모의 데이터 생성
                raw_data = self._generate_mock_history_data(
                    target_currency, start_date, end_date, interval
                )
            
            # 데이터 처리 및 분석
            processed_data = self._process_history_data(raw_data, period, target_currency, base_currency, interval)
            
            # 캐시에 저장
            ttl = self.cache_ttl.get(period, 1800)
            await self.redis_helper.set_json(cache_key, processed_data, ttl)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to get exchange rate history for {target_currency}: {e}")
            raise handle_database_exception(e, "get_exchange_rate_history")
    
    def _calculate_date_range(self, period: str) -> tuple:
        """기간에 따른 날짜 범위 계산"""
        end_date = datetime.utcnow()
        
        if period == "1w":
            start_date = end_date - timedelta(weeks=1)
        elif period == "1m":
            start_date = end_date - timedelta(days=30)
        elif period == "6m":
            start_date = end_date - timedelta(days=180)
        else:
            raise InvalidPeriodError(period, ["1w", "1m", "6m"])
        
        return start_date, end_date
    
    async def _fetch_history_from_db(
        self,
        currency_code: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[Dict[str, Any]]:
        """데이터베이스에서 환율 이력 조회"""
        # TODO: AWS 연결 - Aurora MySQL 쿼리 최적화
        # - 파티션 테이블 사용: PARTITION BY RANGE (YEAR(recorded_at)*100 + MONTH(recorded_at))
        # - 커버링 인덱스: idx_currency_date (currency_code, recorded_at DESC, deal_base_rate)
        # - 6m 기간 이상 시 집계 테이블 daily_exchange_rates 사용
        try:
            if interval == "daily":
                # 일별 집계 데이터 사용 (성능 최적화)
                query = """
                    SELECT
                        trade_date as date,
                        close_rate as rate,
                        (close_rate - open_rate) as `change`,
                        ((close_rate - open_rate) / open_rate * 100) as change_percent,
                        data_points as volume
                    FROM daily_exchange_rates
                    WHERE currency_code = %s
                        AND trade_date BETWEEN %s AND %s
                    ORDER BY trade_date ASC
                """
                params = (currency_code, start_date.date(), end_date.date())
            else:
                # 시간별 데이터 (원본 데이터에서 집계)
                query = """
                    SELECT
                        DATE(recorded_at) as date,
                        HOUR(recorded_at) as hour,
                        AVG(deal_base_rate) as rate,
                        COUNT(*) as volume
                    FROM exchange_rate_history
                    WHERE currency_code = %s
                        AND recorded_at BETWEEN %s AND %s
                    GROUP BY DATE(recorded_at), HOUR(recorded_at)
                    ORDER BY date ASC, hour ASC
                """
                params = (currency_code, start_date, end_date)
            
            result = await self.mysql_helper.execute_query(query, params)
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch history from DB for {currency_code}: {e}")
            return []
    
    def _generate_mock_history_data(
        self,
        currency_code: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[Dict[str, Any]]:
        """모의 환율 이력 데이터 생성"""
        try:
            # 기본 환율 설정
            base_rates = {
                "USD": 1350.0,
                "JPY": 9.2,
                "EUR": 1450.0,
                "GBP": 1650.0,
                "CNY": 185.0
            }
            
            base_rate = base_rates.get(currency_code, 1000.0)
            current_rate = base_rate
            
            mock_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # 랜덤한 변동 생성 (±2% 범위)
                import random
                change_percent = random.uniform(-2.0, 2.0)
                change = current_rate * (change_percent / 100)
                current_rate += change
                
                mock_data.append({
                    "date": current_date.date(),
                    "rate": round(current_rate, 4),
                    "change": round(change, 4),
                    "change_percent": round(change_percent, 4),
                    "volume": random.randint(10, 50)
                })
                
                # 다음 날짜로 이동
                if interval == "daily":
                    current_date += timedelta(days=1)
                else:
                    current_date += timedelta(hours=1)
            
            return mock_data
            
        except Exception as e:
            logger.error(f"Failed to generate mock history data for {currency_code}: {e}")
            return []
    
    def _process_history_data(
        self,
        raw_data: List[Dict[str, Any]],
        period: str,
        target_currency: str,
        base_currency: str,
        interval: str
    ) -> Dict[str, Any]:
        """환율 이력 데이터 처리 및 분석"""
        try:
            if not raw_data:
                return {
                    "base": base_currency,
                    "target": target_currency,
                    "period": period,
                    "interval": interval,
                    "data_points": 0,
                    "results": [],
                    "statistics": {
                        "average": 0.0,
                        "min": 0.0,
                        "max": 0.0,
                        "volatility": 0.0,
                        "trend": "stable",
                        "data_points": 0
                    }
                }
            
            # 데이터 포인트 처리
            results = []
            rates = []
            
            for i, data_point in enumerate(raw_data):
                rate = float(data_point["rate"])
                rates.append(rate)
                
                # 변동률 계산 (이전 데이터와 비교)
                if i > 0:
                    prev_rate = float(raw_data[i-1]["rate"])
                    change = rate - prev_rate
                    change_percent = (change / prev_rate) * 100 if prev_rate != 0 else 0
                else:
                    change = 0
                    change_percent = 0
                
                results.append({
                    "date": data_point["date"].strftime('%Y-%m-%d') if hasattr(data_point["date"], 'strftime') else str(data_point["date"]),
                    "rate": rate,
                    "change": round(change, 4),
                    "change_percent": round(change_percent, 4),
                    "volume": data_point.get("volume", 0)
                })
            
            # 통계 계산
            statistics = self._calculate_statistics(rates)
            
            return {
                "base": base_currency,
                "target": target_currency,
                "period": period,
                "interval": interval,
                "data_points": len(results),
                "results": results,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"Failed to process history data: {e}")
            raise
    
    def _calculate_statistics(self, rates: List[float]) -> Dict[str, Any]:
        """환율 통계 계산"""
        try:
            if not rates:
                return {
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "volatility": 0.0,
                    "trend": "stable",
                    "data_points": 0
                }
            
            # 기본 통계
            average = sum(rates) / len(rates)
            min_rate = min(rates)
            max_rate = max(rates)
            
            # 변동성 계산 (표준편차)
            if len(rates) > 1:
                variance = sum((rate - average) ** 2 for rate in rates) / (len(rates) - 1)
                volatility = variance ** 0.5
            else:
                volatility = 0.0
            
            # 트렌드 계산 (선형 회귀 기울기)
            trend = self._calculate_trend(rates)
            
            return {
                "average": round(average, 4),
                "min": round(min_rate, 4),
                "max": round(max_rate, 4),
                "volatility": round(volatility, 4),
                "trend": trend,
                "data_points": len(rates)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {
                "average": 0.0,
                "min": 0.0,
                "max": 0.0,
                "volatility": 0.0,
                "trend": "stable",
                "data_points": 0
            }
    
    def _calculate_trend(self, rates: List[float]) -> str:
        """트렌드 방향 계산"""
        try:
            if len(rates) < 2:
                return "stable"
            
            # 간단한 선형 회귀 (최소제곱법)
            n = len(rates)
            x_values = list(range(n))
            
            # 기울기 계산
            x_mean = sum(x_values) / n
            y_mean = sum(rates) / n
            
            numerator = sum((x_values[i] - x_mean) * (rates[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return "stable"
            
            slope = numerator / denominator
            
            # 트렌드 판단 (기울기 기준)
            if slope > 0.1:
                return "upward"
            elif slope < -0.1:
                return "downward"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"Failed to calculate trend: {e}")
            return "stable"