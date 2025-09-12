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
      console.log(`[useRankingData] 랭킹 데이터 요청: period=${period}, limit=${limit}, offset=${offset}`);
      
      // 직접 fetch로 시도
      const url = `http://localhost:8002/api/v1/rankings?period=${period}&_=${Date.now()}`;
      console.log(`[useRankingData] 직접 fetch URL: ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const rawData = await response.json();
      console.log(`[useRankingData] 직접 fetch 응답:`, rawData);
      
      const newData = rawData.data || rawData;
      console.log(`[useRankingData] 처리된 데이터:`, newData);
      
      // 항상 새로운 데이터로 업데이트 (빈 데이터라도)
      console.log('[useRankingData] 랭킹 데이터 업데이트:', newData);
      setRankings(newData);
      
      return newData;
    } catch (err) {
      const errorMessage = err.message || '랭킹 데이터를 가져오는데 실패했습니다.';
      console.error('[useRankingData] 랭킹 데이터 요청 실패:', err);
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 최초 마운트시 백엔드에서 최신 데이터 가져오기
  useEffect(() => {
    console.log('[useRankingData] 컴포넌트 마운트 - 최신 데이터 가져오기');
    
    const t = setTimeout(() => {
      fetchRankings('daily', 10, 0).catch((err) => {
        console.error('[useRankingData] 초기 데이터 로드 실패:', err);
      });
    }, 100);
    return () => clearTimeout(t);
  }, [fetchRankings]);

  // 사용자 선택 기록
  const recordUserSelection = useCallback(async (countryCode, userId = 'anonymous', sessionId = null, options = {}) => {
    try {
      const selectionData = {
        country_code: countryCode,
        user_id: userId,
        session_id: sessionId || `session_${Date.now()}`,
        referrer: window.location.href
      };

      if (!options.deferOptimistic) {
        // Optimistic 업데이트: 현재 rankings가 있으면 선택 카운트 +1 반영
        setRankings(prev => {
          if (!prev || !prev.ranking) return prev;
          const found = prev.ranking.find(r => r.country_code === countryCode);
          if (found) {
            found.selection_count += 1;
          } else {
            prev.ranking.push({
              country_code: countryCode,
              country_name: countryCode,
              selection_count: 1,
              rank: prev.ranking.length + 1
            });
          }
          prev.ranking = [...prev.ranking]
            .sort((a,b) => b.selection_count - a.selection_count)
            .map((it, idx) => ({ ...it, rank: idx + 1 }));
          return { ...prev };
        });
      }

      const response = await fetch('http://localhost:8002/api/v1/rankings/selections', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(selectionData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('사용자 선택 기록 완료:', result);
      
      if (!options.deferRefresh) {
        await new Promise(r => setTimeout(r, 500));
        await fetchRankings('daily', 10, 0);
      }
      
      return result;
    } catch (err) {
      console.error('사용자 선택 기록 실패:', err);
      throw err;
    }
  }, [fetchRankings]);

  // 여러 국가 한 번에 기록 (배치)
  const recordMultipleSelections = useCallback(async (countryCodes = [], userId='anonymous') => {
    const sessionId = `session_${Date.now()}`;
    const successCodes = [];
    for (const code of countryCodes) {
      try {
        await recordUserSelection(code, userId, sessionId, { deferRefresh: true, deferOptimistic: true });
        successCodes.push(code);
      } catch (e) {
        console.error('배치 기록 실패:', code, e);
      }
    }
    if (successCodes.length === 0) {
      console.warn('[Ranking] 모든 선택 기록 실패 (서버 다운 가능).');
      setError('선택 기록 서버에 연결되지 않아 랭킹이 갱신되지 않았습니다. 랭킹 서비스(포트 8002)가 실행 중인지 확인하세요.');
    } else {
      // 성공한 것들만 낙관적 1회 반영
      setRankings(prev => {
        if (!prev || !prev.ranking) return prev;
        const map = new Map(prev.ranking.map(r => [r.country_code, r]));
        successCodes.forEach(code => {
          const item = map.get(code);
          if (item) {
            item.selection_count += 1;
          } else {
            map.set(code, {
              country_code: code,
              country_name: code,
              selection_count: 1,
              rank: map.size + 1
            });
          }
        });
        const updated = Array.from(map.values())
          .sort((a,b) => b.selection_count - a.selection_count)
          .map((it, idx) => ({ ...it, rank: idx + 1 }));
        const next = { ...prev, ranking: updated };
        return next;
      });
    }
    // 서버 반영 여유 시간 후 실제 랭킹 재조회
    await new Promise(r => setTimeout(r, 220));
    try { await fetchRankings('daily', 10, 0); } catch {}
  }, [recordUserSelection, fetchRankings]);

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
    recordMultipleSelections,
    clearData,
  };
};

export default useRankingData;

