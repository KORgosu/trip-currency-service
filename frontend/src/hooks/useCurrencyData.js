import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

// 환율 데이터를 관리하는 커스텀 훅
const useCurrencyData = () => {
  const [exchangeRates, setExchangeRates] = useState(null);
  const [priceIndices, setPriceIndices] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 환율 데이터 가져오기
  const fetchExchangeRates = useCallback(async (symbols = 'USD,JPY,EUR,GBP,CNY', base = 'KRW') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.getExchangeRates(symbols, base);
      setExchangeRates(response.data);
      return response.data;
    } catch (err) {
      const errorMessage = err.message || '환율 데이터를 가져오는데 실패했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 물가 지수 데이터 가져오기
  const fetchPriceIndex = useCallback(async (country, baseCountry = 'KR') => {
    try {
      const response = await apiService.getPriceIndex(country, baseCountry);
      setPriceIndices(prev => ({
        ...prev,
        [country]: response.data
      }));
      return response.data;
    } catch (err) {
      console.error(`물가 지수 조회 실패 (${country}):`, err);
      throw err;
    }
  }, []);

  // 여러 국가의 물가 지수를 한번에 가져오기
  const fetchMultiplePriceIndices = useCallback(async (countries, baseCountry = 'KR') => {
    setLoading(true);
    setError(null);
    
    try {
      const promises = countries.map(country => 
        apiService.getPriceIndex(country, baseCountry)
          .then(response => ({ country, data: response.data }))
          .catch(err => {
            console.error(`물가 지수 조회 실패 (${country}):`, err);
            return { country, data: null, error: err.message };
          })
      );
      
      const results = await Promise.all(promises);
      const priceData = {};
      
      results.forEach(({ country, data, error }) => {
        if (data) {
          priceData[country] = data;
        }
      });
      
      setPriceIndices(priceData);
      return priceData;
    } catch (err) {
      const errorMessage = err.message || '물가 지수 데이터를 가져오는데 실패했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 전체 데이터 가져오기 (환율 + 물가 지수)
  const fetchAllData = useCallback(async (symbols = 'USD,JPY,EUR,GBP,CNY', base = 'KRW') => {
    setLoading(true);
    setError(null);
    
    try {
      // 환율과 물가 지수를 동시에 가져오기
      const [ratesResponse, ...priceResponses] = await Promise.all([
        apiService.getExchangeRates(symbols, base),
        apiService.getPriceIndex('US', 'KR'),
        apiService.getPriceIndex('JP', 'KR'),
        apiService.getPriceIndex('GB', 'KR'),
        apiService.getPriceIndex('CN', 'KR')
      ]);
      
      setExchangeRates(ratesResponse.data);
      
      const priceData = {};
      const countryMap = { 'USD': 'US', 'JPY': 'JP', 'GBP': 'GB', 'CNY': 'CN' };
      
      priceResponses.forEach((response, index) => {
        const currency = symbols.split(',')[index + 1] || Object.keys(countryMap)[index];
        const country = countryMap[currency];
        if (country && response.data) {
          priceData[country] = response.data;
        }
      });
      
      setPriceIndices(priceData);
      
      return {
        exchangeRates: ratesResponse.data,
        priceIndices: priceData
      };
    } catch (err) {
      const errorMessage = err.message || '데이터를 가져오는데 실패했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 헬스 체크
  const checkHealth = useCallback(async () => {
    try {
      const response = await apiService.healthCheck();
      return response.data;
    } catch (err) {
      console.error('헬스 체크 실패:', err);
      throw err;
    }
  }, []);

  // 데이터 초기화
  const clearData = useCallback(() => {
    setExchangeRates(null);
    setPriceIndices({});
    setError(null);
  }, []);

  return {
    // 상태
    exchangeRates,
    priceIndices,
    loading,
    error,
    
    // 액션
    fetchExchangeRates,
    fetchPriceIndex,
    fetchMultiplePriceIndices,
    fetchAllData,
    checkHealth,
    clearData
  };
};

export default useCurrencyData;

