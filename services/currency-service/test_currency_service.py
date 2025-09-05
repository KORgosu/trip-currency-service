"""
Currency Service 단위 테스트

Jenkins-SonarQube 테스트를 위한 테스트 케이스들입니다.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from decimal import Decimal

from currency_service import CurrencyService, CurrencyConverter


class TestCurrencyService:
    """CurrencyService 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.service = CurrencyService()
        self.service.set_exchange_rate('USD', 'KRW', 1300.0)
        self.service.set_exchange_rate('EUR', 'KRW', 1400.0)
        self.service.set_exchange_rate('USD', 'EUR', 0.85)
    
    def test_get_exchange_rate_success(self):
        """환율 조회 성공 테스트"""
        rate = self.service.get_exchange_rate('USD', 'KRW')
        assert rate == 1300.0
    
    def test_get_exchange_rate_same_currency(self):
        """같은 통화 간 환율 테스트"""
        rate = self.service.get_exchange_rate('USD', 'USD')
        assert rate == 1.0
    
    def test_get_exchange_rate_invalid_currency(self):
        """잘못된 통화 코드 테스트"""
        with pytest.raises(ValueError):
            self.service.get_exchange_rate('INVALID', 'KRW')
        
        with pytest.raises(ValueError):
            self.service.get_exchange_rate('USD', 'INVALID')
    
    def test_get_exchange_rate_not_found(self):
        """존재하지 않는 환율 조회 테스트"""
        rate = self.service.get_exchange_rate('JPY', 'KRW')
        assert rate is None
    
    def test_convert_currency_success(self):
        """통화 변환 성공 테스트"""
        result = self.service.convert_currency(100.0, 'USD', 'KRW')
        assert result == 130000.0
    
    def test_convert_currency_negative_amount(self):
        """음수 금액 변환 테스트"""
        result = self.service.convert_currency(-100.0, 'USD', 'KRW')
        assert result is None
    
    def test_convert_currency_zero_amount(self):
        """0원 변환 테스트"""
        result = self.service.convert_currency(0.0, 'USD', 'KRW')
        assert result == 0.0
    
    def test_convert_currency_rate_not_found(self):
        """환율이 없는 경우 변환 테스트"""
        result = self.service.convert_currency(100.0, 'JPY', 'KRW')
        assert result is None
    
    def test_set_exchange_rate_success(self):
        """환율 설정 성공 테스트"""
        success = self.service.set_exchange_rate('GBP', 'KRW', 1600.0)
        assert success is True
        
        rate = self.service.get_exchange_rate('GBP', 'KRW')
        assert rate == 1600.0
    
    def test_set_exchange_rate_invalid_currency(self):
        """잘못된 통화 코드로 환율 설정 테스트"""
        success = self.service.set_exchange_rate('INVALID', 'KRW', 1600.0)
        assert success is False
    
    def test_set_exchange_rate_negative_rate(self):
        """음수 환율 설정 테스트"""
        success = self.service.set_exchange_rate('GBP', 'KRW', -100.0)
        assert success is False
    
    def test_set_exchange_rate_zero_rate(self):
        """0 환율 설정 테스트"""
        success = self.service.set_exchange_rate('GBP', 'KRW', 0.0)
        assert success is False
    
    def test_get_supported_currencies(self):
        """지원 통화 목록 테스트"""
        currencies = self.service.get_supported_currencies()
        assert isinstance(currencies, list)
        assert 'USD' in currencies
        assert 'KRW' in currencies
        assert 'EUR' in currencies
    
    def test_is_valid_currency_code(self):
        """통화 코드 유효성 검사 테스트"""
        # 유효한 코드
        assert self.service._is_valid_currency_code('USD') is True
        assert self.service._is_valid_currency_code('KRW') is True
        
        # 무효한 코드
        assert self.service._is_valid_currency_code('US') is False  # 너무 짧음
        assert self.service._is_valid_currency_code('USDD') is False  # 너무 김
        assert self.service._is_valid_currency_code('US1') is False  # 숫자 포함
        assert self.service._is_valid_currency_code('') is False  # 빈 문자열
        assert self.service._is_valid_currency_code(None) is False  # None
        assert self.service._is_valid_currency_code(123) is False  # 숫자
    
    def test_calculate_currency_fluctuation_success(self):
        """통화 변동률 계산 성공 테스트"""
        result = self.service.calculate_currency_fluctuation('USD_KRW', 30)
        
        assert result is not None
        assert 'currency_pair' in result
        assert 'period_days' in result
        assert 'fluctuation_rate' in result
        assert 'trend' in result
        assert 'last_updated' in result
        assert result['currency_pair'] == 'USD_KRW'
        assert result['period_days'] == 30
    
    def test_calculate_currency_fluctuation_invalid_days(self):
        """잘못된 기간으로 변동률 계산 테스트"""
        result = self.service.calculate_currency_fluctuation('USD_KRW', -1)
        assert result is None
        
        result = self.service.calculate_currency_fluctuation('USD_KRW', 0)
        assert result is None


class TestCurrencyConverter:
    """CurrencyConverter 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.service = CurrencyService()
        self.service.set_exchange_rate('USD', 'KRW', 1300.0)
        self.service.set_exchange_rate('USD', 'EUR', 0.85)
        self.converter = CurrencyConverter(self.service)
    
    def test_convert_multiple_currencies_success(self):
        """여러 통화 변환 성공 테스트"""
        results = self.converter.convert_multiple_currencies(
            100.0, 'USD', ['KRW', 'EUR']
        )
        
        assert 'KRW' in results
        assert 'EUR' in results
        assert results['KRW'] == 130000.0
        assert results['EUR'] == 85.0
    
    def test_convert_multiple_currencies_with_invalid_currency(self):
        """잘못된 통화가 포함된 여러 통화 변환 테스트"""
        results = self.converter.convert_multiple_currencies(
            100.0, 'USD', ['KRW', 'JPY', 'EUR']
        )
        
        assert 'KRW' in results
        assert 'JPY' in results
        assert 'EUR' in results
        assert results['KRW'] == 130000.0
        assert results['JPY'] is None  # 환율이 설정되지 않음
        assert results['EUR'] == 85.0
    
    def test_convert_multiple_currencies_empty_list(self):
        """빈 통화 목록으로 변환 테스트"""
        results = self.converter.convert_multiple_currencies(
            100.0, 'USD', []
        )
        
        assert results == {}


class TestCurrencyServiceIntegration:
    """통합 테스트 클래스"""
    
    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 서비스 초기화
        service = CurrencyService()
        
        # 환율 설정
        assert service.set_exchange_rate('USD', 'KRW', 1300.0) is True
        assert service.set_exchange_rate('USD', 'EUR', 0.85) is True
        
        # 환율 조회
        usd_krw_rate = service.get_exchange_rate('USD', 'KRW')
        assert usd_krw_rate == 1300.0
        
        # 통화 변환
        converted_amount = service.convert_currency(100.0, 'USD', 'KRW')
        assert converted_amount == 130000.0
        
        # 변동률 계산
        fluctuation = service.calculate_currency_fluctuation('USD_KRW', 30)
        assert fluctuation is not None
    
    @patch('currency_service.requests.get')
    def test_external_api_integration(self, mock_get):
        """외부 API 통합 테스트 (모킹)"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.json.return_value = {'rates': {'KRW': 1300.0}}
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        service = CurrencyService(api_key='test_key')
        
        # 실제 API 호출이 있다면 여기서 테스트
        # 현재는 샘플 구현이므로 기본 기능만 테스트
        assert service.api_key == 'test_key'


class TestLogging:
    """로깅 테스트 클래스"""
    
    def test_logging_setup(self, caplog):
        """로깅 설정 테스트"""
        with caplog.at_level(logging.INFO):
            service = CurrencyService()
            service.set_exchange_rate('USD', 'KRW', 1300.0)
            
            # 로그 메시지 확인
            assert "Exchange rate set: USD_KRW = 1300.0" in caplog.text
    
    def test_warning_logging(self, caplog):
        """경고 로깅 테스트"""
        with caplog.at_level(logging.WARNING):
            service = CurrencyService()
            service.convert_currency(-100.0, 'USD', 'KRW')
            
            # 경고 로그 메시지 확인
            assert "Negative amount provided: -100.0" in caplog.text


# 픽스처 정의
@pytest.fixture
def currency_service():
    """CurrencyService 픽스처"""
    service = CurrencyService()
    service.set_exchange_rate('USD', 'KRW', 1300.0)
    service.set_exchange_rate('EUR', 'KRW', 1400.0)
    return service


@pytest.fixture
def currency_converter(currency_service):
    """CurrencyConverter 픽스처"""
    return CurrencyConverter(currency_service)


# 픽스처를 사용한 테스트
def test_with_fixtures(currency_service, currency_converter):
    """픽스처를 사용한 테스트"""
    result = currency_converter.convert_multiple_currencies(
        50.0, 'USD', ['KRW', 'EUR']
    )
    
    assert result['KRW'] == 65000.0
    assert result['EUR'] == 42.5


# 파라미터화된 테스트
@pytest.mark.parametrize("amount,from_currency,to_currency,expected", [
    (100.0, 'USD', 'KRW', 130000.0),
    (200.0, 'USD', 'KRW', 260000.0),
    (50.0, 'USD', 'EUR', 42.5),
    (0.0, 'USD', 'KRW', 0.0),
])
def test_convert_currency_parametrized(amount, from_currency, to_currency, expected):
    """파라미터화된 통화 변환 테스트"""
    service = CurrencyService()
    service.set_exchange_rate('USD', 'KRW', 1300.0)
    service.set_exchange_rate('USD', 'EUR', 0.85)
    
    result = service.convert_currency(amount, from_currency, to_currency)
    assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
