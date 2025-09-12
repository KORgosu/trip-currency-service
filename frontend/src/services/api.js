// API 서비스 레이어
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const RANKING_API_BASE_URL = import.meta.env.VITE_RANKING_API_BASE_URL || 'http://localhost:8002';
const HISTORY_API_BASE_URL = import.meta.env.VITE_HISTORY_API_BASE_URL || 'http://localhost:8003';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.rankingBaseURL = RANKING_API_BASE_URL;
    this.historyBaseURL = HISTORY_API_BASE_URL;
  }

  // 기본 HTTP 요청 메서드
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': this.generateCorrelationId(),
      },
    };

    const config = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error?.message || 'API 요청 실패');
      }
      
      return data;
    } catch (error) {
      console.error('API 요청 실패:', error);
      
      // 마이크로서비스가 실행되지 않을 때 Mock 데이터 반환
      if (error.message.includes('Failed to fetch') || error.message.includes('ERR_CONNECTION_REFUSED')) {
        console.warn('마이크로서비스가 실행되지 않음. Mock 데이터를 사용합니다.');
        return this.getMockData(endpoint);
      }
      
      throw error;
    }
  }

  // 랭킹 서비스 전용 요청 메서드
  async rankingRequest(endpoint, options = {}) {
    const url = `${this.rankingBaseURL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': this.generateCorrelationId(),
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
      },
    };

    const config = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      console.log(`[Ranking API] 요청: ${url}`, config);
      const response = await fetch(url, config);
      
      if (!response.ok) {
        console.error(`[Ranking API] HTTP 에러: ${response.status} ${response.statusText}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log(`[Ranking API] 성공 응답:`, data);
      
      // Accept multiple response shapes from the ranking service:
      // - raw array: [ { country, count } ]
      // - wrapped: { success: true, data: { ranking: [...] } }
      // - legacy: { ranking: [...] } or { data: [...] }
      if (Array.isArray(data)) return data;
      if (data && typeof data === 'object') {
        if (data.success === true) return data;
        if (data.data) return data;
        if (Array.isArray(data.ranking)) return data;
      }

      // fallback: error
      throw new Error(data.error?.message || '랭킹 API 요청 실패');
    } catch (error) {
      console.error('랭킹 API 요청 실패:', error);
      
      // 개발 환경에서는 목업 데이터 사용 안 함 - 실제 에러를 보여줌
      throw error; // 목업 데이터 폴백 완전 제거
    }
  }

  // History Service 전용 요청 메서드
  async historyRequest(endpoint, options = {}) {
    const url = `${this.historyBaseURL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        'X-Correlation-ID': this.generateCorrelationId(),
      },
    };

    const config = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error?.message || 'History API 요청 실패');
      }
      
      return data;
    } catch (error) {
      console.error('History API 요청 실패:', error);
      
      // History 서비스가 실행되지 않을 때 Mock 데이터 반환
      if (error.message.includes('Failed to fetch') || error.message.includes('ERR_CONNECTION_REFUSED')) {
        console.warn('History 서비스가 실행되지 않음. Mock 데이터를 사용합니다.');
        return this.getHistoryMockData(endpoint);
      }
      
      throw error;
    }
  }

  // 상관관계 ID 생성
  generateCorrelationId() {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  }

  // Mock 데이터 반환 (마이크로서비스가 실행되지 않을 때)
  getMockData(endpoint) {
    if (endpoint.includes('/currencies/latest')) {
      return {
        success: true,
        data: {
          base: 'KRW',
          rates: {
            'USD': 1350.50,
            'JPY': 9.25,
            'EUR': 1480.75,
            'GBP': 1720.30,
            'CNY': 190.45
          },
          timestamp: new Date().toISOString(),
          cache_hit: false
        }
      };
    }
    
    if (endpoint.includes('/price-index')) {
      return {
        success: true,
        data: {
          country_code: 'US',
          big_mac_index: 5.81,
          starbucks_index: 4.45,
          timestamp: new Date().toISOString()
        }
      };
    }
    
    if (endpoint.includes('/health')) {
      return {
        success: true,
        data: {
          status: 'healthy',
          service: 'currency-service-mock',
          version: '1.0.0-mock'
        }
      };
    }
    
    // 기본 Mock 응답
    return {
      success: true,
      data: { message: 'Mock data - 서비스가 실행되지 않음' }
    };
  }

  // 랭킹 서비스 Mock 데이터 반환 (완전 비활성화)
  getRankingMockData(endpoint) {
    console.warn('[API] 목업 데이터가 호출되었습니다. 실제 서비스 연결을 확인하세요.');
    throw new Error('목업 데이터 사용 금지 - 실제 랭킹 서비스에 연결하세요.');
  }

  // History Service Mock 데이터 반환
  getHistoryMockData(endpoint) {
    if (endpoint.includes('/api/v1/history')) {
      // URL에서 파라미터 추출
      const url = new URL(endpoint, this.historyBaseURL);
      const target = url.searchParams.get('target') || 'USD';
      const period = url.searchParams.get('period') || '1w';
      
      // Mock 환율 이력 데이터 생성
      const mockData = this.generateMockHistoryData(target, period);
      
      return {
        success: true,
        data: mockData
      };
    }
    
    if (endpoint.includes('/api/v1/history/stats')) {
      return {
        success: true,
        data: {
          base: 'KRW',
          target: 'USD',
          period: '6m',
          statistics: {
            average: 1350.25,
            min: 1280.50,
            max: 1420.75,
            volatility: 45.30,
            trend: 'upward',
            data_points: 180
          }
        }
      };
    }
    
    // 기본 History Mock 응답
    return {
      success: true,
      data: { message: 'Mock history data - History 서비스가 실행되지 않음' }
    };
  }

  // Mock 환율 이력 데이터 생성
  generateMockHistoryData(currency, period) {
    const baseRates = {
      'USD': 1350.0,
      'JPY': 9.2,
      'EUR': 1450.0,
      'GBP': 1650.0,
      'CNY': 185.0
    };
    
    const baseRate = baseRates[currency] || 1000.0;
    const days = period === '1w' ? 7 : period === '1m' ? 30 : period === '3m' ? 90 : 180;
    
    const results = [];
    let currentRate = baseRate;
    
    for (let i = 0; i < days; i++) {
      const date = new Date();
      date.setDate(date.getDate() - (days - i - 1));
      
      // 랜덤 변동 (±2% 범위)
      const changePercent = (Math.random() - 0.5) * 4; // -2% ~ +2%
      const change = currentRate * (changePercent / 100);
      currentRate += change;
      
      results.push({
        date: date.toISOString().split('T')[0],
        rate: Math.round(currentRate * 100) / 100,
        change: Math.round(change * 100) / 100,
        change_percent: Math.round(changePercent * 100) / 100,
        volume: Math.floor(Math.random() * 50) + 10
      });
    }
    
    return {
      base: 'KRW',
      target: currency,
      period: period,
      interval: 'daily',
      data_points: results.length,
      results: results,
      statistics: {
        average: Math.round((results.reduce((sum, item) => sum + item.rate, 0) / results.length) * 100) / 100,
        min: Math.min(...results.map(item => item.rate)),
        max: Math.max(...results.map(item => item.rate)),
        volatility: Math.round(Math.random() * 50 + 20),
        trend: Math.random() > 0.5 ? 'upward' : 'downward',
        data_points: results.length
      }
    };
  }

  // 환율 조회
  async getExchangeRates(symbols = 'USD,JPY,EUR,GBP,CNY', base = 'KRW') {
    const symbolsParam = Array.isArray(symbols) ? symbols.join(',') : symbols;
    return this.request(`/api/v1/currencies/latest?symbols=${symbolsParam}&base=${base}`);
  }

  // 물가 지수 조회
  async getPriceIndex(country, baseCountry = 'KR') {
    return this.request(`/api/v1/price-index?country=${country}&base_country=${baseCountry}`);
  }

  // 통화 정보 조회
  async getCurrencyInfo(currencyCode) {
    return this.request(`/api/v1/currencies/${currencyCode}`);
  }

  // 헬스 체크
  async healthCheck() {
    return this.request('/health');
  }

  // 랭킹 서비스 API 메서드들
  
  // 랭킹 조회
  async getRankings(period = 'daily', limit = 10, offset = 0, decay = 0.9) {
    // map period to ranking service endpoints
    // Normalize various response shapes from the ranking service:
    // - raw array: [ { country, count } ]
    // - wrapped: { success: true, data: { ranking: [...] } }
    // - legacy object: { ranking: [...] }
    const normalize = (resp) => {
      if (!resp) return [];
      if (Array.isArray(resp)) return resp;
      if (resp.success && resp.data) {
        if (Array.isArray(resp.data)) return resp.data;
        if (Array.isArray(resp.data.ranking)) return resp.data.ranking;
      }
      if (Array.isArray(resp.ranking)) return resp.ranking;
      if (Array.isArray(resp.data)) return resp.data;
      return [];
    };

    try {
      // Get rankings from our FastAPI backend with strong cache busting
      const url = `/api/v1/rankings?period=${period}&_=${Date.now()}`;
      
      console.log('[getRankings] 요청 URL:', `${this.rankingBaseURL}${url}`);
      
      const resp = await this.rankingRequest(url);
      console.log('[getRankings] rankingRequest 결과:', resp);
      
      // 데이터 추출 로직 개선
      let data, items;
      
      if (resp.success && resp.data) {
        // 표준 응답: { success: true, data: { ranking: [...] } }
        data = resp.data;
        items = data.ranking || [];
        
        // 직접 API 호출 결과와 같은 구조 확인
        console.log('[getRankings] data.ranking:', data.ranking);
        console.log('[getRankings] data.ranking 타입:', typeof data.ranking);
        console.log('[getRankings] data.ranking 길이:', Array.isArray(data.ranking) ? data.ranking.length : 'Not Array');
        
      } else if (resp.data && resp.data.ranking) {
        // 중첩 응답: { data: { ranking: [...] } }
        data = resp.data;
        items = data.ranking || [];
      } else if (Array.isArray(resp.ranking)) {
        // 직접 응답: { ranking: [...] }
        data = resp;
        items = resp.ranking || [];
      } else if (Array.isArray(resp)) {
        // 배열 응답: [...]
        data = { ranking: resp };
        items = resp;
      } else {
        // 예외 처리
        console.warn('[getRankings] 예상치 못한 응답 구조:', resp);
        data = { ranking: [] };
        items = [];
      }
      
      console.log('[getRankings] 추출된 data:', data);
      console.log('[getRankings] 추출된 items:', items);
      console.log('[getRankings] items 길이:', items.length);
      console.log('[getRankings] items 상세:', JSON.stringify(items, null, 2));
      
      // 1) 기본 정규화 (서버 rank 보존)
      let rankingItems = items
        .map(it => ({
          country_code: it.country_code,
          country_name: it.country_name,
          selection_count: it.score ?? it.selection_count ?? 0,
          rank: it.rank // 서버에서 온 rank (dense)
        }))
        .filter(it => it.selection_count > 0); // 필터링을 나중에 수행

      console.log('[getRankings] 정규화된 rankingItems:', rankingItems);

      // 2) 점수 순으로 정렬 (표시 일관성)
      rankingItems.sort((a,b)=> b.selection_count - a.selection_count);

      // 3) 서버가 rank 안준 경우에만 dense fallback 계산
      const missingRank = rankingItems.some(r => r.rank == null);
      if (missingRank) {
        let prevScore = null; let currentRank = 0;
        rankingItems.forEach(row => {
          if (row.selection_count !== prevScore) { currentRank += 1; prevScore = row.selection_count; }
          row.rank = currentRank;
        });
      }

      return {
        success: true,
        data: {
          period: data.period || period || 'daily',
          total_selections: data.total_selections || 0,
          last_updated: data.last_updated || new Date().toISOString(),
          ranking: rankingItems
        }
      };
    } catch (err) {
      // bubble up to rankingRequest which will return mock data if service is down
      throw err;
    }
  }

  // 사용자 선택 기록
  async recordSelection(selectionData) {
    // send a click event to the ranking service
    // backend expects { user_id, country_code, session_id, referrer }
    const payload = {
      user_id: selectionData.user_id || 'anonymous',
      country_code: selectionData.country_code || selectionData.country,
      session_id: selectionData.session_id,
      referrer: selectionData.referrer
    };

    try {
      return await this.rankingRequest('/api/v1/rankings/selections', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error('선택 기록 실패:', error);
      // 에러를 상위로 전파하여 처리
      throw error;
    }
  }

  // 국가별 통계 조회
  async getCountryStats(countryCode, period = '7d') {
    return this.rankingRequest(`/api/v1/rankings/stats/${countryCode}?period=${period}`);
  }

  // 랭킹 계산 트리거 (관리자용)
  async triggerRankingCalculation(period) {
    return this.rankingRequest(`/api/v1/rankings/calculate?period=${period}`, {
      method: 'POST'
    });
  }

  // History Service API 메서드들
  
  // 환율 이력 조회
  async getExchangeRateHistory(period, target, base = 'KRW', interval = 'daily') {
    return this.historyRequest(`/api/v1/history?period=${period}&target=${target}&base=${base}&interval=${interval}`);
  }

  // 환율 통계 조회
  async getExchangeRateStats(target, period = '6m', base = 'KRW') {
    return this.historyRequest(`/api/v1/history/stats?target=${target}&period=${period}&base=${base}`);
  }

  // 환율 비교 분석
  async compareCurrencies(targets, period = '1m', base = 'KRW') {
    const targetsParam = Array.isArray(targets) ? targets.join(',') : targets;
    return this.historyRequest(`/api/v1/history/compare?targets=${targetsParam}&period=${period}&base=${base}`);
  }

  // 환율 예측
  async getExchangeRateForecast(currencyCode, days = 7, base = 'KRW') {
    return this.historyRequest(`/api/v1/history/forecast/${currencyCode}?days=${days}&base=${base}`);
  }

  // History Service 헬스 체크
  async historyHealthCheck() {
    return this.historyRequest('/health');
  }
}

// 싱글톤 인스턴스 생성
const apiService = new ApiService();

export default apiService;
