import React from 'react';
import styled from 'styled-components';
import RankingItem from './RankingItem';

const RankingContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
`;

const LoadingContainer = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
`;

const ErrorContainer = styled.div`
  text-align: center;
  padding: 2rem;
  color: #e74c3c;
`;

const RefreshButton = styled.button`
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
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

const LastUpdated = styled.div`
  font-size: 0.8rem;
  color: #666;
  margin-top: 1rem;
  text-align: center;
`;

const RankingList = ({ rankings, loading, error, onRefresh }) => {
  // 로딩 상태
  if (loading) {
    return (
      <RankingContainer>
        <LoadingContainer>
          <div>📊 랭킹 데이터를 불러오는 중...</div>
        </LoadingContainer>
      </RankingContainer>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <RankingContainer>
        <ErrorContainer>
          <div>❌ 랭킹 데이터를 불러올 수 없습니다.</div>
          <div style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>{error}</div>
          {onRefresh && (
            <RefreshButton onClick={onRefresh}>
              🔄 다시 시도
            </RefreshButton>
          )}
        </ErrorContainer>
      </RankingContainer>
    );
  }

  // 랭킹 데이터가 없는 경우
  if (!rankings || !rankings.ranking || rankings.ranking.length === 0) {
    return (
      <RankingContainer>
        <LoadingContainer>
          <div>📊 아직 클릭된 국가가 없습니다.</div>
          {onRefresh && (
            <RefreshButton onClick={onRefresh}>
              🔄 새로고침
            </RefreshButton>
          )}
        </LoadingContainer>
      </RankingContainer>
    );
  }

  // 클릭 수를 기준으로 정렬 (score 또는 selection_count 사용)
  const sortedRankings = [...rankings.ranking].sort((a, b) => {
    const scoreA = a.score || a.selection_count || 0;
    const scoreB = b.score || b.selection_count || 0;
    return scoreB - scoreA;
  });

  return (
    <RankingContainer>
      {sortedRankings.map((ranking) => (
        <RankingItem
          key={ranking.country_code}
          ranking={{
            countryCode: ranking.country_code,
            selection_count: ranking.score || ranking.selection_count || 0,
          }}
          position={ranking.rank || ranking.position || ranking._rank || ranking.temp_rank || 0}
          countryName={ranking.country_name}
        />
      ))}
      
      {rankings.last_updated && (
        <LastUpdated>
          마지막 업데이트: {new Date(rankings.last_updated).toLocaleString('ko-KR')}
        </LastUpdated>
      )}
      
      {onRefresh && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <RefreshButton onClick={onRefresh} disabled={loading}>
            🔄 새로고침
          </RefreshButton>
        </div>
      )}
    </RankingContainer>
  );
};

export default RankingList;
