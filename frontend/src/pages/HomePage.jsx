import React, { useEffect } from 'react';
import styled from 'styled-components';
import CountrySelector from '../components/country/CountrySelector';
import RankingList from '../components/ranking/RankingList';
import useGeolocation from '../hooks/useGeolocation';
import useRankingData from '../hooks/useRankingData';

const HomeContainer = styled.div`
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  
  @media (max-width: 768px) {
    padding: 0;
  }
`;

const ContentWrapper = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 0 2rem;
  
  @media (max-width: 768px) {
    padding: 0 1rem;
  }
`;

const HeaderSection = styled.section`
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
  width: 100%;
`;

const MainTitle = styled.h1`
  font-size: 2rem;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
  
  @media (max-width: 480px) {
    font-size: 1.2rem;
  }
`;

const CurrentLocation = styled.p`
  font-size: 1.1rem;
  color: #666;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
`;

const LocationIcon = styled.span`
  font-size: 1rem;
`;

const RefreshButton = styled.button`
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  transition: all 0.2s;
  
  &:hover {
    background-color: #f0f0f0;
    color: #333;
  }
`;

const SearchSection = styled.section`
  padding: 2rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  width: 100%;
  
  @media (max-width: 768px) {
    padding: 1.5rem;
  }
`;

const RankingSection = styled.section`
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  padding: 2rem;
  width: 100%;
  
  @media (max-width: 768px) {
    padding: 1.5rem;
  }
`;

const RankingHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
`;

const RankingIcon = styled.span`
  font-size: 1.2rem;
`;

const RankingTitle = styled.h2`
  font-size: 1.1rem;
  font-weight: bold;
  color: #2c3e50;
  margin: 0;
`;

const MainContentSection = styled.section`
  display: flex;
  flex-direction: column;
  gap: 2rem;
  width: 100%;
  min-height: auto;
`;

const ContentColumn = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2rem;
`;

const HomePage = () => {
  const { country, loading, error, refreshLocation } = useGeolocation();
  const { rankings, loading: rankingLoading, error: rankingError, fetchRankings } = useRankingData();

  // 컴포넌트 마운트 시 랭킹 데이터 로드
  useEffect(() => {
    fetchRankings('daily', 10, 0);
  }, [fetchRankings]);

  return (
    <HomeContainer>
      <ContentWrapper>
        <HeaderSection>
          <MainTitle>여행하고 싶은 국가를 입력해주세요</MainTitle>
          <CurrentLocation>
            <LocationIcon>📍</LocationIcon>
            현재 위치 : {loading ? '위치 확인 중...' : country}
            <RefreshButton onClick={refreshLocation} title="위치 새로고침">
              🔄
            </RefreshButton>
          </CurrentLocation>
        </HeaderSection>

        <MainContentSection>
          <ContentColumn>
            <SearchSection>
              <CountrySelector />
            </SearchSection>
            
            <RankingSection>
              <RankingHeader>
                <RankingIcon>⚡</RankingIcon>
                <RankingTitle>현재 인기 Top 여행지</RankingTitle>
              </RankingHeader>
              <RankingList 
                rankings={rankings} 
                loading={rankingLoading} 
                error={rankingError}
                onRefresh={() => fetchRankings('daily', 10, 0)}
              />
            </RankingSection>
          </ContentColumn>
        </MainContentSection>
      </ContentWrapper>
    </HomeContainer>
  );
};

export default HomePage;