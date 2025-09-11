import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import apiService from '../../services/api';

// Chart.js 등록
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const ChartContainer = styled.div`
  width: 100%;
  min-height: 400px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  background-color: #f8f9fa;
  border-radius: 8px;
  position: relative;
`;

const ChartTitle = styled.h3`
  color: #2c3e50;
  margin-bottom: 1rem;
  text-align: center;
`;


const ChartWrapper = styled.div`
  width: 100%;
  height: 250px;
  position: relative;
  margin-bottom: 1rem;
`;

const LoadingContainer = styled.div`
  width: 100%;
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f8f9fa;
  border-radius: 8px;
  color: #666;
  font-size: 1rem;
`;

const ErrorContainer = styled.div`
  width: 100%;
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #ffe6e6;
  border-radius: 8px;
  color: #d63031;
  font-size: 1rem;
`;

const StatsContainer = styled.div`
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  margin-top: 0.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
  position: relative;
  z-index: 1;
`;

const StatItem = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  padding: 0.75rem;
  background-color: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
`;

const StatLabel = styled.div`
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
  margin-bottom: 0.25rem;
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 1rem;
  font-weight: bold;
  color: #2c3e50;
  text-align: center;
`;

const ExchangeRateChart = ({ currencyCode = 'USD', timeRange = '1w' }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statistics, setStatistics] = useState(null);

  useEffect(() => {
    fetchChartData();
  }, [timeRange, currencyCode]);

  const fetchChartData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiService.getExchangeRateHistory(
        timeRange, 
        currencyCode, 
        'KRW', 
        'daily'
      );
      
      if (response.success) {
        const data = response.data;
        
        // 차트 데이터 구성
        setChartData({
          labels: data.results.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('ko-KR', { 
              month: 'short', 
              day: 'numeric' 
            });
          }),
          datasets: [{
            label: `${currencyCode}/KRW`,
            data: data.results.map(item => item.rate),
            borderColor: '#667eea',
            backgroundColor: 'rgba(102, 126, 234, 0.1)',
            borderWidth: 2,
            pointBackgroundColor: '#667eea',
            pointBorderColor: '#667eea',
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.4,
            fill: true
          }]
        });
        
        // 통계 데이터 설정
        setStatistics(data.statistics);
      }
    } catch (error) {
      console.error('차트 데이터 로드 실패:', error);
      setError('차트 데이터를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function(context) {
            return `${currencyCode}/KRW: ${context.parsed.y.toLocaleString()}원`;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: '날짜'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: '환율 (원)'
        },
        beginAtZero: false,
        ticks: {
          callback: function(value) {
            return value.toLocaleString() + '원';
          }
        }
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    }
  };

  return (
    <ChartContainer>
      <ChartTitle>{currencyCode}/KRW 환율 차트</ChartTitle>

      <ChartWrapper>
        {loading ? (
          <LoadingContainer>
            📊 차트 데이터를 불러오는 중...
          </LoadingContainer>
        ) : error ? (
          <ErrorContainer>
            ❌ {error}
          </ErrorContainer>
        ) : chartData ? (
          <Line data={chartData} options={chartOptions} />
        ) : (
          <LoadingContainer>
            📊 차트 데이터가 없습니다.
          </LoadingContainer>
        )}
      </ChartWrapper>

      {statistics && (
        <StatsContainer>
          <StatItem>
            <StatLabel>평균</StatLabel>
            <StatValue>{statistics.average.toLocaleString()}원</StatValue>
          </StatItem>
          <StatItem>
            <StatLabel>최고</StatLabel>
            <StatValue>{statistics.max.toLocaleString()}원</StatValue>
          </StatItem>
          <StatItem>
            <StatLabel>최저</StatLabel>
            <StatValue>{statistics.min.toLocaleString()}원</StatValue>
          </StatItem>
          <StatItem>
            <StatLabel>변동성</StatLabel>
            <StatValue>{statistics.volatility.toFixed(2)}</StatValue>
          </StatItem>
          <StatItem>
            <StatLabel>트렌드</StatLabel>
            <StatValue>
              {statistics.trend === 'upward' ? '📈 상승' : 
               statistics.trend === 'downward' ? '📉 하락' : '➡️ 보합'}
            </StatValue>
          </StatItem>
        </StatsContainer>
      )}
    </ChartContainer>
  );
};

export default ExchangeRateChart;
