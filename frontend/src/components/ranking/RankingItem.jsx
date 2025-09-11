import React from 'react';
import styled from 'styled-components';

const ItemContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  transition: transform 0.3s;
  width: 100%;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  @media (max-width: 480px) {
    padding: 1rem;
    gap: 0.75rem;
  }
`;

const RankNumber = styled.div`
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
  min-width: 2rem;
  
  @media (max-width: 480px) {
    font-size: 1.2rem;
    min-width: 1.5rem;
  }
`;

const TrendIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.8rem;
  font-weight: bold;
  
  &.up {
    color: #e74c3c;
  }
  
  &.down {
    color: #3498db;
  }
  
  &.same {
    color: #95a5a6;
  }
`;

const CountryInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
`;

const CountryFlag = styled.span`
  font-size: 1.5rem;
`;

const CountryName = styled.div`
  font-weight: 500;
  color: #2c3e50;
`;

const ScoreContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const Score = styled.div`
  background-color: #f8f9fa;
  padding: 0.5rem 1rem;
  border-radius: 15px;
  font-weight: bold;
  color: #2c3e50;
  font-size: 0.9rem;
`;

const RankingItem = ({ ranking, position, countryName }) => {
  const getTrendIcon = () => '—';  // 트렌드 아이콘은 일단 중립으로 고정

  const getTrendClass = (trend) => {
    switch (trend) {
      case 'up':
        return 'up';
      case 'down':
        return 'down';
      default:
        return 'same';
    }
  };

  const countryInfo = {
    US: { name: '미국', flag: '🇺🇸' },
    JP: { name: '일본', flag: '🇯🇵' },
    GB: { name: '영국', flag: '🇬🇧' },
    CN: { name: '중국', flag: '🇨🇳' },
    DE: { name: '독일', flag: '🇩🇪' },
    FR: { name: '프랑스', flag: '🇫🇷' },
    IT: { name: '이탈리아', flag: '🇮🇹' },
    ES: { name: '스페인', flag: '🇪🇸' },
    CA: { name: '캐나다', flag: '🇨🇦' },
    AU: { name: '호주', flag: '🇦🇺' },
    KR: { name: '한국', flag: '🇰🇷' },
    SG: { name: '싱가포르', flag: '🇸🇬' },
    TH: { name: '태국', flag: '🇹🇭' },
    MY: { name: '말레이시아', flag: '🇲🇾' },
    ID: { name: '인도네시아', flag: '🇮🇩' },
    PH: { name: '필리핀', flag: '🇵🇭' },
    VN: { name: '베트남', flag: '🇻🇳' },
    IN: { name: '인도', flag: '🇮🇳' },
    BR: { name: '브라질', flag: '🇧🇷' },
    MX: { name: '멕시코', flag: '🇲🇽' },
    AR: { name: '아르헨티나', flag: '🇦🇷' },
    CH: { name: '스위스', flag: '🇨🇭' },
    NL: { name: '네덜란드', flag: '🇳🇱' },
    BE: { name: '벨기에', flag: '🇧🇪' },
    AT: { name: '오스트리아', flag: '🇦🇹' },
    SE: { name: '스웨덴', flag: '🇸🇪' },
    NO: { name: '노르웨이', flag: '🇳🇴' },
    DK: { name: '덴마크', flag: '🇩🇰' },
    FI: { name: '핀란드', flag: '🇫🇮' },
    PL: { name: '폴란드', flag: '🇵🇱' },
    RU: { name: '러시아', flag: '🇷🇺' },
    TR: { name: '터키', flag: '🇹🇷' },
    ZA: { name: '남아프리카', flag: '🇿🇦' },
    EG: { name: '이집트', flag: '🇪🇬' },
    NG: { name: '나이지리아', flag: '🇳🇬' },
    KE: { name: '케냐', flag: '🇰🇪' },
    MA: { name: '모로코', flag: '🇲🇦' },
    NZ: { name: '뉴질랜드', flag: '🇳🇿' },
    IL: { name: '이스라엘', flag: '🇮🇱' },
    AE: { name: '아랍에미리트', flag: '🇦🇪' },
    SA: { name: '사우디아라비아', flag: '🇸🇦' },
  };

  // countryName이 전달되면 사용하고, 없으면 기본 countryInfo에서 찾기
  const info = countryName ? 
    { name: countryName, flag: countryInfo[ranking.countryCode]?.flag || '🌍' } :
    countryInfo[ranking.countryCode] || { 
      name: ranking.countryCode, 
      flag: '🌍' 
    };

  return (
    <ItemContainer>
      <RankNumber>{position}</RankNumber>
      
      <CountryInfo>
        <CountryFlag>{info.flag}</CountryFlag>
        <CountryName>{info.name}</CountryName>
      </CountryInfo>
      
      <ScoreContainer>
        <Score>{ranking.selection_count}회 클릭</Score>
      </ScoreContainer>
    </ItemContainer>
  );
};

export default RankingItem;
