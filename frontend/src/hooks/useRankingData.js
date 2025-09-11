import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

// 랭킹 데이터를 관리하는 커스텀 훅
const useRankingData = () => {
  const [rankings, setRankings] = useState(() => {
    try {
      const cached = localStorage.getItem('ranking_cache_daily');
      if (cached) return JSON.parse(cached);
      // Fallback: rebuild from local click counts
      const countsRaw = localStorage.getItem('ranking_local_counts');
      if (countsRaw) {
        const counts = JSON.parse(countsRaw);
        const entries = Object.entries(counts).filter(([_, v]) => v > 0);
        if (entries.length) {
          const ranking = entries
            .sort((a,b) => b[1]-a[1])
            .map(([code, count], idx) => ({
              country_code: code,
              country_name: code,
              selection_count: count,
              rank: idx + 1
            }));
          return {
            period: 'daily',
            total_selections: ranking.reduce((s,it)=>s+it.selection_count,0),
            last_updated: new Date().toISOString(),
            ranking
          };
        }
      }
    } catch {}
    return null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 랭킹 데이터 가져오기 (위로 올려 useEffect에서 참조 가능하게)
  const fetchRankings = useCallback(async (period = 'daily', limit = 10, offset = 0) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getRankings(period, limit, offset);
      const newData = response.data;
  setRankings(prev => {
        // If server returned empty ranking but we already have data, keep previous
        if (prev && prev.ranking && prev.ranking.length > 0 && (!newData.ranking || newData.ranking.length === 0)) {
          console.debug('[Ranking] Skip overwrite with empty result; keeping existing data');
          return prev;
        }
        return newData;
      });
      // persist only if non-empty
      if (period === 'daily' && newData.ranking && newData.ranking.length > 0) {
        try { localStorage.setItem('ranking_cache_daily', JSON.stringify(newData)); } catch {}
      }
      return newData;
    } catch (err) {
      const errorMessage = err.message || '랭킹 데이터를 가져오는데 실패했습니다.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // 최초 마운트시 캐시 보여주고 비동기 새로고침
  useEffect(() => {
    const t = setTimeout(() => {
      fetchRankings('daily', 10, 0).catch(()=>{});
    }, 50);
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
          // persist optimistic
          try { localStorage.setItem('ranking_cache_daily', JSON.stringify(prev)); } catch {}
          return { ...prev };
        });
        // also persist raw counts map
        try {
          const countsRaw = localStorage.getItem('ranking_local_counts');
          const counts = countsRaw ? JSON.parse(countsRaw) : {};
            counts[countryCode] = (counts[countryCode] || 0) + 1;
          localStorage.setItem('ranking_local_counts', JSON.stringify(counts));
        } catch {}
      }

      const response = await apiService.recordSelection(selectionData);
      console.log('사용자 선택 기록 완료:', response);
      
      if (!options.deferRefresh) {
        await new Promise(r => setTimeout(r, 120));
        await fetchRankings('daily', 10, 0);
      }
      
      return response;
    } catch (err) {
      console.error('사용자 선택 기록 실패:', err);
      throw err; // 선택 기록 실패를 상위로 전파
    }
  }, [fetchRankings]);

  // 여러 국가 한 번에 기록 (배치)
  const recordMultipleSelections = useCallback(async (countryCodes = [], userId='anonymous') => {
    const sessionId = `session_${Date.now()}`;
    const successCodes = [];
    for (const code of countryCodes) {
      try {
  // 선택 단계에서는 카운트( optimistic ) 반영 안 하고 검색 실행 시에만 반영
  await recordUserSelection(code, userId, sessionId, { deferRefresh: true, deferOptimistic: true });
        successCodes.push(code);
      } catch (e) {
        console.error('배치 기록 실패:', code, e);
      }
    }
    if (successCodes.length === 0) {
      console.warn('[Ranking] 모든 선택 기록 실패 (서버 다운 가능).');
  // 서버 응답 실패 시 사용자에게 알려주기 위한 에러 상태 설정
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
        try { localStorage.setItem('ranking_cache_daily', JSON.stringify(next)); } catch {}
        try {
          const countsRaw = localStorage.getItem('ranking_local_counts');
          const counts = countsRaw ? JSON.parse(countsRaw) : {};
          successCodes.forEach(code => { counts[code] = (counts[code] || 0) + 1; });
          localStorage.setItem('ranking_local_counts', JSON.stringify(counts));
        } catch {}
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

