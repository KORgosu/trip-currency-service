import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import useRankingData from '../../hooks/useRankingData';

const SelectorContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
`;

const SearchContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
`;

const SearchInput = styled.input`
  flex: 1;
  padding: 1rem;
  border: 2px solid #e1e8ed;
  border-radius: 8px;
  font-size: 1rem;
  background-color: white;
  color: #000000;
  transition: border-color 0.3s;
  
  &::placeholder {
    color: #000000;
  }
  
  &:focus {
    outline: none;
    border-color: #667eea;
  }
  
  @media (max-width: 480px) {
    padding: 0.75rem;
    font-size: 0.9rem;
  }
`;

const SearchButton = styled.button`
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #5a6fd8;
  }
  
  @media (max-width: 480px) {
    width: 45px;
    height: 45px;
  }
`;

const SelectedCountries = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: flex-start;
  width: 100%;
`;

const CountryTag = styled.div`
  display: flex;
  align-items: center;
  background-color: #f8f9fa;
  border: 2px solid #8e44ad;
  border-radius: 20px;
  padding: 0.5rem 1rem;
  font-size: 1.1rem;
`;

const RemoveButton = styled.button`
  background: none;
  border: none;
  color: #666;
  cursor: pointer;
  margin-left: 0.5rem;
  font-size: 1.2rem;
  
  &:hover {
    color: #e74c3c;
  }
`;

const DropdownContainer = styled.div`
  position: relative;
  width: 100%;
`;

const CountryList = styled.div`
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  margin-top: 4px;
`;

const CountryItem = styled.button`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border: none;
  background: ${props => {
    if (props.$isClicked) return '#e8f5e8';
    if (props.$isActive) return '#f0f4ff';
    return 'white';
  }};
  cursor: pointer;
  text-align: left;
  transition: all 0.3s ease;
  width: 100%;
  border-bottom: 1px solid #f5f5f5;
  color: ${props => props.$isClicked ? '#2e7d32' : '#333333'};
  
  &:hover {
    background-color: ${props => props.$isClicked ? '#d4edda' : '#e3f2fd'};
    color: ${props => props.$isClicked ? '#2e7d32' : '#1976d2'};
  }
  
  &:last-child {
    border-bottom: none;
  }
  
  &.highlighted {
    background-color: #e3f2fd;
    color: #1976d2;
  }
`;

const CountryFlag = styled.span`
  font-size: 1.2rem;
`;

const CountrySelector = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCountries, setSelectedCountries] = useState(['US', 'JP', 'GB']);
  const [showList, setShowList] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
  const [clickedItem, setClickedItem] = useState(null);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();
  const { recordUserSelection } = useRankingData();

  // 확장된 국가 데이터
  const countries = [
    { code: 'US', name: '미국', flag: '🇺🇸', nameEn: 'United States' },
    { code: 'JP', name: '일본', flag: '🇯🇵', nameEn: 'Japan' },
    { code: 'GB', name: '영국', flag: '🇬🇧', nameEn: 'United Kingdom' },
    { code: 'CN', name: '중국', flag: '🇨🇳', nameEn: 'China' },
    { code: 'DE', name: '독일', flag: '🇩🇪', nameEn: 'Germany' },
    { code: 'FR', name: '프랑스', flag: '🇫🇷', nameEn: 'France' },
    { code: 'IT', name: '이탈리아', flag: '🇮🇹', nameEn: 'Italy' },
    { code: 'ES', name: '스페인', flag: '🇪🇸', nameEn: 'Spain' },
    { code: 'CA', name: '캐나다', flag: '🇨🇦', nameEn: 'Canada' },
    { code: 'AU', name: '호주', flag: '🇦🇺', nameEn: 'Australia' },
    { code: 'KR', name: '한국', flag: '🇰🇷', nameEn: 'South Korea' },
    { code: 'SG', name: '싱가포르', flag: '🇸🇬', nameEn: 'Singapore' },
    { code: 'TH', name: '태국', flag: '🇹🇭', nameEn: 'Thailand' },
    { code: 'MY', name: '말레이시아', flag: '🇲🇾', nameEn: 'Malaysia' },
    { code: 'ID', name: '인도네시아', flag: '🇮🇩', nameEn: 'Indonesia' },
    { code: 'PH', name: '필리핀', flag: '🇵🇭', nameEn: 'Philippines' },
    { code: 'VN', name: '베트남', flag: '🇻🇳', nameEn: 'Vietnam' },
    { code: 'IN', name: '인도', flag: '🇮🇳', nameEn: 'India' },
    { code: 'BR', name: '브라질', flag: '🇧🇷', nameEn: 'Brazil' },
    { code: 'MX', name: '멕시코', flag: '🇲🇽', nameEn: 'Mexico' },
    { code: 'AR', name: '아르헨티나', flag: '🇦🇷', nameEn: 'Argentina' },
    { code: 'CH', name: '스위스', flag: '🇨🇭', nameEn: 'Switzerland' },
    { code: 'NL', name: '네덜란드', flag: '🇳🇱', nameEn: 'Netherlands' },
    { code: 'BE', name: '벨기에', flag: '🇧🇪', nameEn: 'Belgium' },
    { code: 'AT', name: '오스트리아', flag: '🇦🇹', nameEn: 'Austria' },
    { code: 'SE', name: '스웨덴', flag: '🇸🇪', nameEn: 'Sweden' },
    { code: 'NO', name: '노르웨이', flag: '🇳🇴', nameEn: 'Norway' },
    { code: 'DK', name: '덴마크', flag: '🇩🇰', nameEn: 'Denmark' },
    { code: 'FI', name: '핀란드', flag: '🇫🇮', nameEn: 'Finland' },
    { code: 'PL', name: '폴란드', flag: '🇵🇱', nameEn: 'Poland' },
    { code: 'RU', name: '러시아', flag: '🇷🇺', nameEn: 'Russia' },
    { code: 'TR', name: '터키', flag: '🇹🇷', nameEn: 'Turkey' },
    { code: 'ZA', name: '남아프리카', flag: '🇿🇦', nameEn: 'South Africa' },
    { code: 'EG', name: '이집트', flag: '🇪🇬', nameEn: 'Egypt' },
    { code: 'NG', name: '나이지리아', flag: '🇳🇬', nameEn: 'Nigeria' },
    { code: 'KE', name: '케냐', flag: '🇰🇪', nameEn: 'Kenya' },
    { code: 'MA', name: '모로코', flag: '🇲🇦', nameEn: 'Morocco' },
    { code: 'NZ', name: '뉴질랜드', flag: '🇳🇿', nameEn: 'New Zealand' },
    { code: 'IL', name: '이스라엘', flag: '🇮🇱', nameEn: 'Israel' },
    { code: 'AE', name: '아랍에미리트', flag: '🇦🇪', nameEn: 'United Arab Emirates' },
    { code: 'SA', name: '사우디아라비아', flag: '🇸🇦', nameEn: 'Saudi Arabia' },
  ];

  // 디바운싱 효과
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  // 개선된 필터링 (한국어, 영어, 코드 모두 검색 가능 + 이미 선택된 국가 제외)
  const filteredCountries = countries.filter(country => {
    // 이미 선택된 국가는 제외
    if (selectedCountries.includes(country.code)) {
      return false;
    }
    
    const searchLower = debouncedSearchTerm.toLowerCase();
    return (
      country.name.toLowerCase().includes(searchLower) ||
      country.nameEn.toLowerCase().includes(searchLower) ||
      country.code.toLowerCase().includes(searchLower)
    );
  }).sort((a, b) => {
    // 검색어와 정확히 일치하는 것을 우선순위로 정렬
    const searchLower = debouncedSearchTerm.toLowerCase();
    const aExactMatch = a.name.toLowerCase() === searchLower || a.nameEn.toLowerCase() === searchLower;
    const bExactMatch = b.name.toLowerCase() === searchLower || b.nameEn.toLowerCase() === searchLower;
    
    if (aExactMatch && !bExactMatch) return -1;
    if (!aExactMatch && bExactMatch) return 1;
    
    // 그 다음으로 시작하는 것을 우선순위로
    const aStartsWith = a.name.toLowerCase().startsWith(searchLower) || a.nameEn.toLowerCase().startsWith(searchLower);
    const bStartsWith = b.name.toLowerCase().startsWith(searchLower) || b.nameEn.toLowerCase().startsWith(searchLower);
    
    if (aStartsWith && !bStartsWith) return -1;
    if (!aStartsWith && bStartsWith) return 1;
    
    return a.name.localeCompare(b.name);
  });

  const handleCountrySelect = async (country) => {
    if (!selectedCountries.includes(country.code)) {
      // 클릭 애니메이션 효과 시작
      setClickedItem(country.code);
      
      // 0.5초 후 애니메이션 효과 제거
      setTimeout(() => {
        setClickedItem(null);
      }, 500);
      
      setSelectedCountries([...selectedCountries, country.code]);
      
      // 랭킹 서비스에 사용자 선택 기록
      try {
        await recordUserSelection(country.code, 'anonymous', `session_${Date.now()}`);
        console.log(`국가 선택 기록 완료: ${country.name} (${country.code})`);
      } catch (error) {
        console.error('국가 선택 기록 실패:', error);
        // 기록 실패는 사용자 경험에 영향을 주지 않음
      }
    }
    setSearchTerm('');
    setShowList(false);
    setHighlightedIndex(-1);
    inputRef.current?.focus();
  };

  const handleCountryRemove = (countryCode) => {
    setSelectedCountries(selectedCountries.filter(code => code !== countryCode));
  };

  const getCountryInfo = (code) => {
    return countries.find(country => country.code === code);
  };

  // 검색 실행 함수
  const handleSearch = () => {
    if (selectedCountries.length === 0) {
      alert('비교할 국가를 최소 1개 이상 선택해주세요.');
      return;
    }
    
    // 선택된 국가들을 URL 파라미터로 전달
    const countriesParam = selectedCountries.join(',');
    navigate(`/comparison?countries=${countriesParam}`);
  };

  // 키보드 네비게이션 핸들러
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !showList) {
      // 드롭다운이 열려있지 않을 때 Enter키를 누르면 검색 실행
      e.preventDefault();
      handleSearch();
      return;
    }

    if (!showList || filteredCountries.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev < filteredCountries.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev > 0 ? prev - 1 : filteredCountries.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < filteredCountries.length) {
          handleCountrySelect(filteredCountries[highlightedIndex]);
        }
        break;
      case 'Escape':
        setShowList(false);
        setHighlightedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (listRef.current && !listRef.current.contains(event.target) && 
          inputRef.current && !inputRef.current.contains(event.target)) {
        setShowList(false);
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <SelectorContainer>
      <SearchContainer>
        <DropdownContainer>
        <SearchInput
            ref={inputRef}
          type="text"
            placeholder="국가를 검색하세요 (한국어/영어/코드)"
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setShowList(true);
              setHighlightedIndex(-1);
          }}
          onFocus={() => setShowList(true)}
            onKeyDown={handleKeyDown}
          />
          
          {showList && debouncedSearchTerm && (
            <CountryList ref={listRef}>
              {filteredCountries.length > 0 ? (
                filteredCountries.map((country, index) => (
                  <CountryItem
                    key={country.code}
                    $isActive={index === highlightedIndex}
                    $isClicked={clickedItem === country.code}
                    className={index === highlightedIndex ? 'highlighted' : ''}
                    onClick={() => handleCountrySelect(country)}
                  >
                    <CountryFlag>{country.flag}</CountryFlag>
                    <div>
                      <div>{country.name}</div>
                      <div style={{ fontSize: '0.8rem', color: '#666' }}>
                        {country.nameEn}
                      </div>
                    </div>
                  </CountryItem>
                ))
              ) : (
                <div style={{ padding: '1rem', textAlign: 'center', color: '#666' }}>
                  검색 결과가 없습니다
                </div>
              )}
            </CountryList>
          )}
        </DropdownContainer>
        
        <SearchButton onClick={handleSearch} title="선택된 국가들 비교하기">
          🔍
        </SearchButton>
      </SearchContainer>

      <SelectedCountries>
        {selectedCountries.map(countryCode => {
          const country = getCountryInfo(countryCode);
          return (
            <CountryTag key={countryCode}>
              <CountryFlag>{country?.flag}</CountryFlag>
              <span>{country?.name}</span>
              <RemoveButton onClick={() => handleCountryRemove(countryCode)}>
                ×
              </RemoveButton>
            </CountryTag>
          );
        })}
      </SelectedCountries>
    </SelectorContainer>
  );
};

export default CountrySelector;
