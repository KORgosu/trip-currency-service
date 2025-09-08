"""
Currency Service 테스트
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# 테스트를 위한 경로 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 환경 변수 설정 (테스트용)
os.environ['ENVIRONMENT'] = 'local'
os.environ['DB_HOST'] = 'localhost'
os.environ['REDIS_HOST'] = 'localhost'


class TestCurrencyService:
    """Currency Service 테스트 클래스"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock 데이터베이스 매니저"""
        with patch('services.shared.database.db_manager') as mock:
            mock_manager = MagicMock()
            mock_manager.get_redis_client.return_value = AsyncMock()
            mock.return_value = mock_manager
            yield mock_manager
    
    @pytest.fixture
    def mock_redis_helper(self):
        """Mock Redis Helper"""
        with patch('services.currency_service.app.services.currency_provider.RedisHelper') as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_mysql_helper(self):
        """Mock MySQL Helper"""
        with patch('services.currency_service.app.services.currency_provider.MySQLHelper') as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def client(self, mock_db_manager):
        """테스트 클라이언트"""
        # 설정 초기화 모킹
        with patch('shared.config.init_config') as mock_init_config, \
             patch('shared.database.init_database') as mock_init_db:
            
            # Mock 설정 반환
            mock_config = MagicMock()
            mock_config.service_version = "1.0.0-test"
            mock_config.cors_origins = ["http://localhost:3000"]
            mock_init_config.return_value = mock_config
            
            # Mock 데이터베이스 초기화
            mock_init_db.return_value = None
            
            # FastAPI 앱 import 및 클라이언트 생성
            from services.currency_service.main import app
            
            with TestClient(app) as test_client:
                yield test_client
    
    def test_health_check(self, client):
        """헬스 체크 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["status"] == "healthy"
        assert data["data"]["service"] == "currency-service"
    
    @pytest.mark.asyncio
    async def test_currency_provider_get_latest_rates_cache_hit(self, mock_redis_helper, mock_mysql_helper):
        """환율 조회 - 캐시 히트 테스트"""
        from services.currency_service.app.services.currency_provider import CurrencyProvider
        
        # Mock Redis 응답 (캐시 히트)
        mock_redis_helper.get_hash.return_value = {
            'deal_base_rate': '1392.4',
            'currency_name': '미국 달러',
            'tts': '1420.85',
            'ttb': '1363.95',
            'source': 'BOK',
            'last_updated_at': '2025-09-05T10:30:00Z'
        }
        
        provider = CurrencyProvider()
        provider.redis_helper = mock_redis_helper
        provider.mysql_helper = mock_mysql_helper
        
        result = await provider.get_latest_rates(['USD'], 'KRW')
        
        # 검증
        assert result['base'] == 'KRW'
        assert 'USD' in result['rates']
        assert result['rates']['USD'] == 1392.4
        assert result['source'] == 'redis_cache'
        assert result['cache_hit'] is True
        assert result['cache_stats']['hits'] == 1
        assert result['cache_stats']['misses'] == 0
        
        # Redis가 호출되었는지 확인
        mock_redis_helper.get_hash.assert_called()
        # DB는 호출되지 않았는지 확인
        mock_mysql_helper.execute_query.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_currency_provider_get_latest_rates_cache_miss(self, mock_redis_helper, mock_mysql_helper):
        """환율 조회 - 캐시 미스 테스트"""
        from services.currency_service.app.services.currency_provider import CurrencyProvider
        
        # Mock Redis 응답 (캐시 미스)
        mock_redis_helper.get_hash.return_value = {}
        
        # Mock MySQL 응답
        mock_mysql_helper.execute_query.return_value = [
            {
                'currency_code': 'USD',
                'currency_name': '미국 달러',
                'deal_base_rate': 1392.4,
                'tts': 1420.85,
                'ttb': 1363.95,
                'source': 'BOK',
                'recorded_at': '2025-09-05T10:30:00'
            }
        ]
        
        provider = CurrencyProvider()
        provider.redis_helper = mock_redis_helper
        provider.mysql_helper = mock_mysql_helper
        
        result = await provider.get_latest_rates(['USD'], 'KRW')
        
        # 검증
        assert result['base'] == 'KRW'
        assert 'USD' in result['rates']
        assert result['rates']['USD'] == 1392.4
        assert result['source'] == 'database'
        assert result['cache_hit'] is False
        assert result['cache_stats']['hits'] == 0
        assert result['cache_stats']['misses'] == 1
        
        # Redis와 MySQL 모두 호출되었는지 확인
        mock_redis_helper.get_hash.assert_called()
        mock_mysql_helper.execute_query.assert_called()
    
    @pytest.mark.asyncio
    async def test_currency_provider_get_currency_info(self, mock_redis_helper, mock_mysql_helper):
        """통화 정보 조회 테스트"""
        from services.currency_service.app.services.currency_provider import CurrencyProvider
        
        # Mock Redis 응답 (캐시 미스)
        mock_redis_helper.get_hash.return_value = {}
        
        # Mock MySQL 응답
        mock_mysql_helper.execute_query.return_value = [
            {
                'currency_code': 'USD',
                'currency_name': '미국 달러',
                'country_code': 'US',
                'country_name': '미국',
                'symbol': '$',
                'deal_base_rate': 1392.4,
                'tts': 1420.85,
                'ttb': 1363.95,
                'source': 'BOK',
                'last_updated': '2025-09-05T10:30:00'
            }
        ]
        
        provider = CurrencyProvider()
        provider.redis_helper = mock_redis_helper
        provider.mysql_helper = mock_mysql_helper
        
        result = await provider.get_currency_info('USD')
        
        # 검증
        assert result['currency_code'] == 'USD'
        assert result['currency_name'] == '미국 달러'
        assert result['country_code'] == 'US'
        assert result['country_name'] == '미국'
        assert result['symbol'] == '$'
        assert result['current_rate'] == 1392.4
        assert result['source'] == 'BOK'
    
    @pytest.mark.asyncio
    async def test_price_index_provider_get_price_index(self, mock_redis_helper):
        """물가 지수 조회 테스트"""
        from services.currency_service.app.services.price_index_provider import PriceIndexProvider
        
        # Mock Redis 응답 (캐시 미스)
        mock_redis_helper.get_json.return_value = None
        mock_redis_helper.set_json.return_value = None
        
        provider = PriceIndexProvider()
        provider.redis_helper = mock_redis_helper
        
        result = await provider.get_price_index('JP', 'KR')
        
        # 검증
        assert result['country_code'] == 'JP'
        assert result['country_name'] == '일본'
        assert result['base_country'] == 'KR'
        assert 'indices' in result
        assert 'bigmac_index' in result['indices']
        assert 'starbucks_index' in result['indices']
        assert 'composite_index' in result['indices']
        assert 'price_data' in result
        
        # 캐시 저장이 호출되었는지 확인
        mock_redis_helper.set_json.assert_called()
    
    def test_api_get_latest_rates_success(self, client):
        """API - 최신 환율 조회 성공 테스트"""
        with patch('services.currency_service.main.currency_provider') as mock_provider:
            # Mock provider 응답
            mock_provider.get_latest_rates.return_value = {
                'base': 'KRW',
                'timestamp': 1725525000,
                'rates': {'USD': 1392.4, 'JPY': 9.46},
                'source': 'redis_cache',
                'cache_hit': True
            }
            
            response = client.get("/api/v1/currencies/latest?symbols=USD,JPY")
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'data' in data
            assert data['data']['base'] == 'KRW'
            assert 'USD' in data['data']['rates']
            assert 'JPY' in data['data']['rates']
    
    def test_api_get_latest_rates_invalid_currency(self, client):
        """API - 잘못된 통화 코드 테스트"""
        response = client.get("/api/v1/currencies/latest?symbols=INVALID")
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert data['error']['code'] == 'INVALID_CURRENCY_CODE'
    
    def test_api_get_currency_info_success(self, client):
        """API - 통화 정보 조회 성공 테스트"""
        with patch('services.currency_service.main.currency_provider') as mock_provider:
            # Mock provider 응답
            mock_provider.get_currency_info.return_value = {
                'currency_code': 'USD',
                'currency_name': '미국 달러',
                'country_code': 'US',
                'current_rate': 1392.4
            }
            
            response = client.get("/api/v1/currencies/USD")
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['currency_code'] == 'USD'
    
    def test_api_get_currency_info_invalid_currency(self, client):
        """API - 잘못된 통화 코드로 통화 정보 조회 테스트"""
        response = client.get("/api/v1/currencies/INVALID")
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_CURRENCY_CODE'
    
    def test_api_get_price_index_success(self, client):
        """API - 물가 지수 조회 성공 테스트"""
        with patch('services.currency_service.main.price_index_provider') as mock_provider:
            # Mock provider 응답
            mock_provider.get_price_index.return_value = {
                'country_code': 'JP',
                'country_name': '일본',
                'base_country': 'KR',
                'indices': {
                    'bigmac_index': 85.2,
                    'starbucks_index': 92.1,
                    'composite_index': 88.1
                }
            }
            
            response = client.get("/api/v1/currencies/price-index?country=JP")
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['country_code'] == 'JP'
            assert 'indices' in data['data']
    
    def test_api_get_price_index_invalid_country(self, client):
        """API - 잘못된 국가 코드로 물가 지수 조회 테스트"""
        response = client.get("/api/v1/currencies/price-index?country=INVALID")
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_COUNTRY_CODE'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])