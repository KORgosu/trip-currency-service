import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import useCurrencyData from '../../hooks/useCurrencyData';

const CardContainer = styled.div`
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  transition: transform 0.3s, box-shadow 0.3s;
  
  &:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
  }
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
`;

const CountryFlag = styled.span`
  font-size: 2rem;
`;

const CountryInfo = styled.div`
  flex: 1;
`;

const CountryName = styled.h3`
  margin: 0;
  color: #2c3e50;
  font-size: 1.2rem;
`;

const CountryCode = styled.p`
  margin: 0;
  color: #666;
  font-size: 0.9rem;
`;

const ChartIcon = styled.button`
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  
  &:hover {
    background-color: #f8f9fa;
    color: #2c3e50;
    transform: scale(1.1);
  }
  
  &:active {
    transform: scale(0.95);
  }
  
  svg {
    width: 20px;
    height: 20px;
  }
`;

const DataGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
`;

const DataItem = styled.div`
  text-align: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
`;

const DataLabel = styled.div`
  font-size: 0.8rem;
  color: #666;
  margin-bottom: 0.5rem;
`;

const DataValue = styled.div`
  font-size: 1.2rem;
  font-weight: bold;
  color: #2c3e50;
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ErrorText = styled.div`
  color: #e74c3c;
  font-size: 0.9rem;
`;

const LastUpdated = styled.div`
  font-size: 0.7rem;
  color: #666;
  text-align: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
`;

const CountryCard = ({ country, onChartClick }) => {
  const { exchangeRates, priceIndices, loading, error, fetchExchangeRates, fetchPriceIndex } = useCurrencyData();
  const [localData, setLocalData] = useState({
    exchangeRate: null,
    priceIndex: null,
    lastUpdated: null
  });

  const countryInfo = {
    US: { name: '미국', flag: '🇺🇸', currency: 'USD' },
    JP: { name: '일본', flag: '🇯🇵', currency: 'JPY' },
    GB: { name: '영국', flag: '🇬🇧', currency: 'GBP' },
    CN: { name: '중국', flag: '🇨🇳', currency: 'CNY' },
    DE: { name: '독일', flag: '🇩🇪', currency: 'EUR' },
    FR: { name: '프랑스', flag: '🇫🇷', currency: 'EUR' },
    IT: { name: '이탈리아', flag: '🇮🇹', currency: 'EUR' },
    ES: { name: '스페인', flag: '🇪🇸', currency: 'EUR' },
    CA: { name: '캐나다', flag: '🇨🇦', currency: 'CAD' },
    AU: { name: '호주', flag: '🇦🇺', currency: 'AUD' },
    KR: { name: '한국', flag: '🇰🇷', currency: 'KRW' },
    SG: { name: '싱가포르', flag: '🇸🇬', currency: 'SGD' },
    TH: { name: '태국', flag: '🇹🇭', currency: 'THB' },
    MY: { name: '말레이시아', flag: '🇲🇾', currency: 'MYR' },
    ID: { name: '인도네시아', flag: '🇮🇩', currency: 'IDR' },
    PH: { name: '필리핀', flag: '🇵🇭', currency: 'PHP' },
    VN: { name: '베트남', flag: '🇻🇳', currency: 'VND' },
    IN: { name: '인도', flag: '🇮🇳', currency: 'INR' },
    BR: { name: '브라질', flag: '🇧🇷', currency: 'BRL' },
    MX: { name: '멕시코', flag: '🇲🇽', currency: 'MXN' },
    AR: { name: '아르헨티나', flag: '🇦🇷', currency: 'ARS' },
    CH: { name: '스위스', flag: '🇨🇭', currency: 'CHF' },
    NL: { name: '네덜란드', flag: '🇳🇱', currency: 'EUR' },
    BE: { name: '벨기에', flag: '🇧🇪', currency: 'EUR' },
    AT: { name: '오스트리아', flag: '🇦🇹', currency: 'EUR' },
    SE: { name: '스웨덴', flag: '🇸🇪', currency: 'SEK' },
    NO: { name: '노르웨이', flag: '🇳🇴', currency: 'NOK' },
    DK: { name: '덴마크', flag: '🇩🇰', currency: 'DKK' },
    FI: { name: '핀란드', flag: '🇫🇮', currency: 'EUR' },
    PL: { name: '폴란드', flag: '🇵🇱', currency: 'PLN' },
    RU: { name: '러시아', flag: '🇷🇺', currency: 'RUB' },
    TR: { name: '터키', flag: '🇹🇷', currency: 'TRY' },
    ZA: { name: '남아프리카', flag: '🇿🇦', currency: 'ZAR' },
    EG: { name: '이집트', flag: '🇪🇬', currency: 'EGP' },
    NG: { name: '나이지리아', flag: '🇳🇬', currency: 'NGN' },
    KE: { name: '케냐', flag: '🇰🇪', currency: 'KES' },
    MA: { name: '모로코', flag: '🇲🇦', currency: 'MAD' },
    NZ: { name: '뉴질랜드', flag: '🇳🇿', currency: 'NZD' },
    IL: { name: '이스라엘', flag: '🇮🇱', currency: 'ILS' },
    AE: { name: '아랍에미리트', flag: '🇦🇪', currency: 'AED' },
    SA: { name: '사우디아라비아', flag: '🇸🇦', currency: 'SAR' },
  };

  const info = countryInfo[country] || { name: country, flag: '🌍', currency: country };

  // 차트 아이콘 클릭 핸들러
  const handleChartClick = () => {
    if (onChartClick) {
      onChartClick(country);
    }
  };

  // 실제 빅맥 가격 데이터 (2024년 최신 데이터)
  const bigMacPrices = {
    "CH": { bigmac_usd: 8.07, currency: "CHF" },  // 스위스 (가장 비싼 국가)
    "UY": { bigmac_usd: 7.07, currency: "UYU" },  // 우루과이
    "NO": { bigmac_usd: 6.77, currency: "NOK" },  // 노르웨이
    "AR": { bigmac_usd: 6.55, currency: "ARS" },  // 아르헨티나
    "GB": { bigmac_usd: 5.9, currency: "GBP" },   // 영국
    "US": { bigmac_usd: 5.69, currency: "USD" },  // 미국
    "DK": { bigmac_usd: 5.66, currency: "DKK" },  // 덴마크
    "CR": { bigmac_usd: 5.62, currency: "CRC" },  // 코스타리카
    "SE": { bigmac_usd: 5.6, currency: "SEK" },   // 스웨덴
    "CA": { bigmac_usd: 5.52, currency: "CAD" },  // 캐나다
    "PL": { bigmac_usd: 5.27, currency: "PLN" },  // 폴란드
    "LB": { bigmac_usd: 5.14, currency: "LBP" },  // 레바논
    "MX": { bigmac_usd: 5.1, currency: "MXN" },   // 멕시코
    "SA": { bigmac_usd: 5.06, currency: "SAR" },  // 사우디아라비아
    "AU": { bigmac_usd: 5.06, currency: "AUD" },  // 호주
    "NZ": { bigmac_usd: 4.99, currency: "NZD" },  // 뉴질랜드
    "VE": { bigmac_usd: 4.97, currency: "VES" },  // 베네수엘라
    "SG": { bigmac_usd: 4.97, currency: "SGD" },  // 싱가포르
    "CO": { bigmac_usd: 4.9, currency: "COP" },   // 콜롬비아
    "AE": { bigmac_usd: 4.9, currency: "AED" },   // 아랍에미리트
    "TR": { bigmac_usd: 4.68, currency: "TRY" },  // 터키
    "CZ": { bigmac_usd: 4.63, currency: "CZK" },  // 체코
    "KW": { bigmac_usd: 4.58, currency: "KWD" },  // 쿠웨이트
    "PE": { bigmac_usd: 4.55, currency: "PEN" },  // 페루
    "CL": { bigmac_usd: 4.54, currency: "CLP" },  // 칠레
    "IL": { bigmac_usd: 4.52, currency: "ILS" },  // 이스라엘
    "BH": { bigmac_usd: 4.51, currency: "BHD" },  // 바레인
    "NI": { bigmac_usd: 4.34, currency: "NIO" },  // 니카라과
    "BR": { bigmac_usd: 4.23, currency: "BRL" },  // 브라질
    "HN": { bigmac_usd: 4.11, currency: "HNL" },  // 온두라스
    "GT": { bigmac_usd: 4.0, currency: "GTQ" },   // 과테말라
    "KR": { bigmac_usd: 3.99, currency: "KRW" },  // 한국
    "OM": { bigmac_usd: 3.97, currency: "OMR" },  // 오만
    "HU": { bigmac_usd: 3.9, currency: "HUF" },   // 헝가리
    "QA": { bigmac_usd: 3.85, currency: "QAR" },  // 카타르
    "PK": { bigmac_usd: 3.82, currency: "PKR" },  // 파키스탄
    "TH": { bigmac_usd: 3.79, currency: "THB" },  // 태국
    "AZ": { bigmac_usd: 3.62, currency: "AZN" },  // 아제르바이잔
    "MD": { bigmac_usd: 3.57, currency: "MDL" },  // 몰도바
    "CN": { bigmac_usd: 3.53, currency: "CNY" },  // 중국
    "RO": { bigmac_usd: 3.53, currency: "RON" },  // 루마니아
    "JO": { bigmac_usd: 3.53, currency: "JOD" },  // 요르단
    "JP": { bigmac_usd: 3.19, currency: "JPY" },  // 일본
    "VN": { bigmac_usd: 3.01, currency: "VND" },  // 베트남
    "HK": { bigmac_usd: 2.94, currency: "HKD" },  // 홍콩
    "UA": { bigmac_usd: 2.87, currency: "UAH" },  // 우크라이나
    "PH": { bigmac_usd: 2.86, currency: "PHP" },  // 필리핀
    "MY": { bigmac_usd: 2.86, currency: "MYR" },  // 말레이시아
    "ZA": { bigmac_usd: 2.85, currency: "ZAR" },  // 남아프리카
    "IN": { bigmac_usd: 2.75, currency: "INR" },  // 인도
    "EG": { bigmac_usd: 2.47, currency: "EGP" },  // 이집트
    "ID": { bigmac_usd: 2.46, currency: "IDR" },  // 인도네시아
    "TW": { bigmac_usd: 2.28, currency: "TWD" }   // 대만
  };

  // 빅맥 가격 데이터 가져오기
  const getBigMacPrice = (countryCode) => {
    return bigMacPrices[countryCode] || null;
  };

  // 스타벅스 가격 계산 (빅맥 가격의 90%)
  const getStarbucksPrice = (countryCode) => {
    const bigMacData = getBigMacPrice(countryCode);
    if (bigMacData) {
      return {
        starbucks_usd: bigMacData.bigmac_usd * 0.9,
        currency: bigMacData.currency
      };
    }
    return null;
  };

  // 데이터 로드
  useEffect(() => {
    const loadData = async () => {
      try {
        // 환율 데이터만 로드 (빅맥/스타벅스는 하드코딩된 데이터 사용)
        const ratesData = await fetchExchangeRates(info.currency, 'KRW');
        if (ratesData && ratesData.rates && ratesData.rates[info.currency]) {
          // 현재 시간을 마지막 업데이트 시간으로 설정
          const currentTime = new Date().toISOString();
          setLocalData(prev => ({
            ...prev,
            exchangeRate: ratesData.rates[info.currency],
            lastUpdated: currentTime
          }));
        }
      } catch (error) {
        console.error(`환율 데이터 로드 실패 (${country}):`, error);
      }
    };

    loadData();
  }, [country, info.currency, fetchExchangeRates]);

  return (
    <CardContainer>
      <CardHeader>
        <CountryFlag>{info.flag}</CountryFlag>
        <CountryInfo>
          <CountryName>{info.name}</CountryName>
          <CountryCode>{info.currency}</CountryCode>
        </CountryInfo>
        <ChartIcon onClick={handleChartClick} title="환율 차트 보기">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 13h2v8H3v-8zm4-6h2v14H7V7zm4-4h2v18h-2V3zm4 8h2v10h-2V11zm4-2h2v12h-2V9z"/>
          </svg>
        </ChartIcon>
      </CardHeader>

      <DataGrid>
        <DataItem>
          <DataLabel>환율 (KRW)</DataLabel>
          <DataValue>
            {loading ? (
              <LoadingSpinner />
            ) : localData.exchangeRate ? (
              `${localData.exchangeRate.toLocaleString()}원`
            ) : error ? (
              <ErrorText>오류</ErrorText>
            ) : (
              '데이터 없음'
            )}
          </DataValue>
        </DataItem>

        <DataItem>
          <DataLabel>빅맥 지수</DataLabel>
          <DataValue>
            {loading ? (
              <LoadingSpinner />
            ) : (() => {
              const bigMacData = getBigMacPrice(country);
              return bigMacData ? `$${bigMacData.bigmac_usd}` : 'N/A';
            })()}
          </DataValue>
        </DataItem>

        <DataItem>
          <DataLabel>스타벅스 지수</DataLabel>
          <DataValue>
            {loading ? (
              <LoadingSpinner />
            ) : (() => {
              const starbucksData = getStarbucksPrice(country);
              return starbucksData ? `$${starbucksData.starbucks_usd.toFixed(2)}` : 'N/A';
            })()}
          </DataValue>
        </DataItem>

        <DataItem>
          <DataLabel>구매력 지수</DataLabel>
          <DataValue>
            {loading ? (
              <LoadingSpinner />
            ) : (() => {
              const bigMacData = getBigMacPrice(country);
              const koreaData = getBigMacPrice('KR');
              if (bigMacData && koreaData) {
                // 한국 대비 구매력 지수 계산 (한국이 기준 100%)
                const purchasingPower = Math.round((koreaData.bigmac_usd / bigMacData.bigmac_usd) * 100);
                return `${purchasingPower}%`;
              }
              return 'N/A';
            })()}
          </DataValue>
        </DataItem>
      </DataGrid>

      {localData.lastUpdated && (
        <LastUpdated>
          마지막 업데이트: {new Date(localData.lastUpdated).toLocaleString('ko-KR')}
        </LastUpdated>
      )}
    </CardContainer>
  );
};

export default CountryCard;
