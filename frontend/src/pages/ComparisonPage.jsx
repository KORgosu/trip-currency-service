import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import ExchangeRateChart from '../components/country/ExchangeRateChart';
import CountryCard from '../components/country/CountryCard';
import useCurrencyData from '../hooks/useCurrencyData';

const ComparisonContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  background: white;
  min-height: 100vh;
`;

const PageTitle = styled.h1`
  color: #2c3e50;
  margin-bottom: 2rem;
  text-align: center;
`;

const ChartSection = styled.section`
  background: white;
  padding: 2rem;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
  min-height: 500px;
  position: relative;
`;

const SectionTitle = styled.h2`
  color: #2c3e50;
  margin-bottom: 1.5rem;
`;

const CountriesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
`;

const BackButton = styled.button`
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  margin-bottom: 2rem;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #5a6fd8;
  }
`;

const NoCountriesMessage = styled.div`
  text-align: center;
  padding: 3rem;
  color: #666;
  font-size: 1.1rem;
`;

const RefreshButton = styled.button`
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  margin-left: 1rem;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #218838;
  }
  
  &:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }
`;

const HeaderActions = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
`;

const TimeRangeSelector = styled.div`
  display: flex;
  gap: 0.5rem;
  position: absolute;
  top: calc(1rem + 5px);
  right: 1rem;
  z-index: 10;
`;

const TimeButton = styled.button`
  padding: 0.4rem 0.8rem;
  border: 1px solid #e1e8ed;
  background: white;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.3s;
  color: #000000;
  font-size: 0.9rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  
  &:hover {
    background-color: #f8f9fa;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  
  &.active {
    background-color: #667eea;
    color: white;
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  }
`;

const ComparisonPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedCountries, setSelectedCountries] = useState([]);
  const [timeRange, setTimeRange] = useState('1w');
  const [selectedChartCountry, setSelectedChartCountry] = useState(null);
  const { fetchAllData, loading } = useCurrencyData();

  const timeRanges = [
    { value: '1w', label: '1주' },
    { value: '1m', label: '1개월' },
    { value: '3m', label: '3개월' },
    { value: '6m', label: '6개월' }
  ];

  // 국가 코드를 통화 코드로 변환하는 함수
  const getCurrencyCode = (countryCode) => {
    const countryToCurrency = {
      'US': 'USD',
      'JP': 'JPY', 
      'GB': 'GBP',
      'CN': 'CNY',
      'EU': 'EUR',
      'AU': 'AUD',
      'CA': 'CAD',
      'CH': 'CHF',
      'KR': 'KRW'
    };
    return countryToCurrency[countryCode] || 'USD';
  };

  // 차트 클릭 핸들러
  const handleChartClick = (countryCode) => {
    setSelectedChartCountry(countryCode);
  };

  useEffect(() => {
    const countriesParam = searchParams.get('countries');
    if (countriesParam) {
      const countries = countriesParam.split(',').filter(country => country.trim());
      setSelectedCountries(countries);
    } else {
      // URL 파라미터가 없으면 기본 국가들로 설정
      setSelectedCountries(['US', 'JP', 'GB', 'CN']);
    }
  }, [searchParams]);

  const handleBackToHome = () => {
    navigate('/');
  };

  const handleRefreshData = async () => {
    try {
      await fetchAllData();
    } catch (error) {
      console.error('데이터 새로고침 실패:', error);
    }
  };

  return (
    <ComparisonContainer>
      <HeaderActions>
        <BackButton onClick={handleBackToHome}>
          ← 홈으로 돌아가기
        </BackButton>
        
        <RefreshButton onClick={handleRefreshData} disabled={loading}>
          {loading ? '새로고침 중...' : '🔄 데이터 새로고침'}
        </RefreshButton>
      </HeaderActions>
      
      <PageTitle>
        {selectedCountries.length > 0 
          ? `선택된 ${selectedCountries.length}개국 실시간 환율 및 물가 지수 비교`
          : '국가별 실시간 환율 및 물가 지수 비교'
        }
      </PageTitle>
      
      <ChartSection>
        <SectionTitle>
          {selectedChartCountry ? `${selectedChartCountry} 환율 차트` : '환율 차트'}
        </SectionTitle>
        
        <TimeRangeSelector>
          {timeRanges.map(range => (
            <TimeButton
              key={range.value}
              className={timeRange === range.value ? 'active' : ''}
              onClick={() => setTimeRange(range.value)}
            >
              {range.label}
            </TimeButton>
          ))}
        </TimeRangeSelector>
        
        <ExchangeRateChart 
          currencyCode={getCurrencyCode(selectedChartCountry || selectedCountries[0]) || 'USD'} 
          timeRange={timeRange} 
        />
      </ChartSection>

      {selectedCountries.length > 0 ? (
        <CountriesGrid>
          {selectedCountries.map(countryCode => (
            <CountryCard 
              key={countryCode} 
              country={countryCode} 
              onChartClick={handleChartClick}
            />
          ))}
        </CountriesGrid>
      ) : (
        <NoCountriesMessage>
          비교할 국가가 선택되지 않았습니다.
          <br />
          홈페이지에서 국가를 선택한 후 다시 시도해주세요.
        </NoCountriesMessage>
      )}
    </ComparisonContainer>
  );
};

export default ComparisonPage;
