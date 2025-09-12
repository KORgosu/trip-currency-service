import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

// 랭킹 데이터를 관리하는 커스텀 훅
const useRankingData = () => {
  const [rankings, setRankings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 랭킹 데이터 가져오기
  const fetchRankings = useCallback(async (period = 'daily', limit = 10, offset = 0) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getRankings(period, limit, offset);
      setRankings(response.data);
      return response.data;
    } catch (err) {
      const errorMessage = err.message || '랭킹 데이터를 가져오는데 실패했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 사용자 선택 기록
  const recordUserSelection = useCallback(async (countryCode, userId = 'anonymous', sessionId = null) => {
    try {
      const selectionData = {
        country_code: countryCode,
        user_id: userId,
        session_id: sessionId || `session_${Date.now()}`,
        referrer: window.location.href
      };

      const response = await apiService.recordSelection(selectionData);
      console.log('사용자 선택 기록 완료:', response);
      return response;
    } catch (err) {
      console.error('사용자 선택 기록 실패:', err);
      // 선택 기록 실패는 치명적이지 않으므로 에러를 던지지 않음
    }
  }, []);

  // 국가별 통계 조회
  const fetchCountryStats = useCallback(async (countryCode, period = '7d') => {
    try {
      const response = await apiService.getCountryStats(countryCode, period);
      return response.data;
    } catch (err) {
      console.error(`국가 통계 조회 실패 (${countryCode}):`, err);
      throw err;
    }
  }, []);

  // 랭킹 계산 트리거 (관리자용)
  const triggerRankingCalculation = useCallback(async (period = 'daily') => {
    try {
      const response = await apiService.triggerRankingCalculation(period);
      return response.data;
    } catch (err) {
      console.error('랭킹 계산 트리거 실패:', err);
      throw err;
    }
  }, []);

  // 데이터 초기화
  const clearData = useCallback(() => {
    setRankings(null);
    setError(null);
  }, []);

  return {
    rankings,
    loading,
    error,
    fetchRankings,
    recordUserSelection,
    fetchCountryStats,
    triggerRankingCalculation,
    clearData,
  };
};

export default useRankingData;




