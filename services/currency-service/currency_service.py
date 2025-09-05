"""
Currency Service - 환율 서비스 모듈

이 모듈은 환율 변환 및 관련 기능을 제공합니다.
Jenkins-SonarQube 테스트를 위한 샘플 코드입니다.
"""

import json
import logging
from typing import Dict, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import requests


class CurrencyService:
    """환율 서비스 클래스"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        CurrencyService 초기화
        
        Args:
            api_key: 외부 API 키 (선택사항)
        """
        self.api_key = api_key
        self.exchange_rates: Dict[str, float] = {}
        self.logger = logging.getLogger(__name__)
        
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        두 통화 간의 환율을 조회합니다.
        
        Args:
            from_currency: 원본 통화 코드 (예: 'USD')
            to_currency: 대상 통화 코드 (예: 'KRW')
            
        Returns:
            환율 또는 None (조회 실패 시)
            
        Raises:
            ValueError: 통화 코드가 유효하지 않은 경우
        """
        if not self._is_valid_currency_code(from_currency):
            raise ValueError(f"Invalid currency code: {from_currency}")
        if not self._is_valid_currency_code(to_currency):
            raise ValueError(f"Invalid currency code: {to_currency}")
            
        if from_currency == to_currency:
            return 1.0
            
        # 실제 구현에서는 외부 API를 호출할 수 있습니다
        rate_key = f"{from_currency}_{to_currency}"
        return self.exchange_rates.get(rate_key)
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """
        통화를 변환합니다.
        
        Args:
            amount: 변환할 금액
            from_currency: 원본 통화 코드
            to_currency: 대상 통화 코드
            
        Returns:
            변환된 금액 또는 None (변환 실패 시)
        """
        if amount < 0:
            self.logger.warning(f"Negative amount provided: {amount}")
            return None
            
        rate = self.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            self.logger.error(f"Exchange rate not found: {from_currency} to {to_currency}")
            return None
            
        converted_amount = amount * rate
        # 소수점 둘째 자리까지 반올림
        return round(converted_amount, 2)
    
    def set_exchange_rate(self, from_currency: str, to_currency: str, rate: float) -> bool:
        """
        환율을 설정합니다.
        
        Args:
            from_currency: 원본 통화 코드
            to_currency: 대상 통화 코드
            rate: 환율
            
        Returns:
            설정 성공 여부
        """
        if not self._is_valid_currency_code(from_currency) or not self._is_valid_currency_code(to_currency):
            return False
            
        if rate <= 0:
            self.logger.error(f"Invalid exchange rate: {rate}")
            return False
            
        rate_key = f"{from_currency}_{to_currency}"
        self.exchange_rates[rate_key] = rate
        self.logger.info(f"Exchange rate set: {rate_key} = {rate}")
        return True
    
    def get_supported_currencies(self) -> List[str]:
        """
        지원되는 통화 목록을 반환합니다.
        
        Returns:
            지원되는 통화 코드 목록
        """
        return ['USD', 'EUR', 'JPY', 'KRW', 'GBP', 'CAD', 'AUD', 'CHF']
    
    def _is_valid_currency_code(self, currency_code: str) -> bool:
        """
        통화 코드가 유효한지 확인합니다.
        
        Args:
            currency_code: 확인할 통화 코드
            
        Returns:
            유효성 여부
        """
        if not isinstance(currency_code, str):
            return False
        return len(currency_code) == 3 and currency_code.isalpha()
    
    def calculate_currency_fluctuation(self, currency_pair: str, days: int = 30) -> Optional[Dict]:
        """
        통화 변동률을 계산합니다.
        
        Args:
            currency_pair: 통화 쌍 (예: 'USD_KRW')
            days: 분석 기간 (일)
            
        Returns:
            변동률 정보 또는 None
        """
        if days <= 0:
            return None
            
        # 실제 구현에서는 과거 데이터를 조회할 수 있습니다
        # 여기서는 샘플 데이터를 반환합니다
        return {
            'currency_pair': currency_pair,
            'period_days': days,
            'fluctuation_rate': 2.5,
            'trend': 'increasing',
            'last_updated': datetime.now().isoformat()
        }


class CurrencyConverter:
    """환율 변환기 클래스"""
    
    def __init__(self, currency_service: CurrencyService):
        """
        CurrencyConverter 초기화
        
        Args:
            currency_service: 환율 서비스 인스턴스
        """
        self.currency_service = currency_service
    
    def convert_multiple_currencies(self, amount: float, from_currency: str, 
                                  target_currencies: List[str]) -> Dict[str, Optional[float]]:
        """
        여러 통화로 동시 변환합니다.
        
        Args:
            amount: 변환할 금액
            from_currency: 원본 통화 코드
            target_currencies: 대상 통화 코드 목록
            
        Returns:
            변환 결과 딕셔너리
        """
        results = {}
        for target_currency in target_currencies:
            converted_amount = self.currency_service.convert_currency(
                amount, from_currency, target_currency
            )
            results[target_currency] = converted_amount
        return results


def main():
    """메인 함수 - 테스트용"""
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)
    
    # 서비스 초기화
    service = CurrencyService()
    
    # 샘플 환율 설정
    service.set_exchange_rate('USD', 'KRW', 1300.0)
    service.set_exchange_rate('EUR', 'KRW', 1400.0)
    service.set_exchange_rate('USD', 'EUR', 0.85)
    
    # 변환 테스트
    converter = CurrencyConverter(service)
    
    # 100 USD를 여러 통화로 변환
    amount = 100.0
    target_currencies = ['KRW', 'EUR', 'JPY']
    results = converter.convert_multiple_currencies(amount, 'USD', target_currencies)
    
    print(f"{amount} USD 변환 결과:")
    for currency, converted_amount in results.items():
        if converted_amount:
            print(f"  {currency}: {converted_amount}")
        else:
            print(f"  {currency}: 변환 실패")


if __name__ == "__main__":
    main()
