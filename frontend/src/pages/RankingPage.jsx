import React from 'react';
import styled from 'styled-components';
import RankingList from '../components/ranking/RankingList';

const RankingContainer = styled.div`
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

const RankingSection = styled.section`
  background: white;
  padding: 2rem;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
`;

const SectionTitle = styled.h2`
  color: #2c3e50;
  margin-bottom: 1.5rem;
`;

const RankingPage = () => {
  return (
    <RankingContainer>
      <PageTitle>여행지 인기 랭킹</PageTitle>
      
      <RankingSection>
        <SectionTitle>현재 인기 Top 여행지</SectionTitle>
        <RankingList />
      </RankingSection>
    </RankingContainer>
  );
};

export default RankingPage;
