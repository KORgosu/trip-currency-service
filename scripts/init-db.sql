-- Currency Travel Service Database Schema
-- MySQL/Aurora 호환 스키마

-- 데이터베이스 생성 (필요시)
CREATE DATABASE IF NOT EXISTS currency_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE currency_db;

-- 통화 마스터 테이블
CREATE TABLE IF NOT EXISTS currencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL UNIQUE,
    currency_name_ko VARCHAR(100) NOT NULL,
    currency_name_en VARCHAR(100) NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    country_name_ko VARCHAR(100) NOT NULL,
    country_name_en VARCHAR(100) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    decimal_places INT DEFAULT 2,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 999,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_currency_code (currency_code),
    INDEX idx_country_code (country_code),
    INDEX idx_active_order (is_active, display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 환율 이력 테이블 (메인 데이터)
CREATE TABLE IF NOT EXISTS exchange_rate_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    currency_name VARCHAR(100) NOT NULL,
    deal_base_rate DECIMAL(18, 4) NOT NULL,
    tts DECIMAL(18, 4) NULL COMMENT '송금 보낼 때',
    ttb DECIMAL(18, 4) NULL COMMENT '받을 때',
    source VARCHAR(50) NOT NULL,
    recorded_at DATETIME NOT NULL COMMENT '환율 기준 시점',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '데이터 생성 시점',
    
    INDEX idx_currency_date (currency_code, recorded_at DESC),
    INDEX idx_recorded_at (recorded_at DESC),
    INDEX idx_currency_source (currency_code, source),
    INDEX idx_created_at (created_at DESC),
    
    FOREIGN KEY (currency_code) REFERENCES currencies(currency_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 일별 집계 테이블 (성능 최적화용)
CREATE TABLE IF NOT EXISTS daily_exchange_rates (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    open_rate DECIMAL(18, 4) NOT NULL COMMENT '시가',
    close_rate DECIMAL(18, 4) NOT NULL COMMENT '종가',
    high_rate DECIMAL(18, 4) NOT NULL COMMENT '고가',
    low_rate DECIMAL(18, 4) NOT NULL COMMENT '저가',
    avg_rate DECIMAL(18, 4) NOT NULL COMMENT '평균가',
    volume INT DEFAULT 0 COMMENT '데이터 포인트 수',
    volatility DECIMAL(10, 6) NULL COMMENT '변동성',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_currency_date (currency_code, trade_date),
    INDEX idx_trade_date (trade_date DESC),
    INDEX idx_currency_date (currency_code, trade_date DESC),
    
    FOREIGN KEY (currency_code) REFERENCES currencies(currency_code) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 물가 지수 테이블 (향후 확장용)
CREATE TABLE IF NOT EXISTS price_indices (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    index_type VARCHAR(50) NOT NULL COMMENT 'bigmac, starbucks, composite',
    index_value DECIMAL(10, 2) NOT NULL,
    base_country VARCHAR(10) DEFAULT 'KR',
    price_data JSON NULL COMMENT '원본 가격 데이터',
    recorded_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_country_type_date (country_code, index_type, recorded_date),
    INDEX idx_recorded_date (recorded_date DESC),
    INDEX idx_country_type (country_code, index_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 데이터 수집 로그 테이블
CREATE TABLE IF NOT EXISTS collection_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    correlation_id VARCHAR(100) NOT NULL,
    source VARCHAR(50) NOT NULL,
    status ENUM('SUCCESS', 'FAILED', 'PARTIAL') NOT NULL,
    currency_count INT DEFAULT 0,
    error_message TEXT NULL,
    processing_time_ms INT DEFAULT 0,
    collected_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_collected_at (collected_at DESC),
    INDEX idx_source_status (source, status),
    INDEX idx_correlation_id (correlation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기본 통화 데이터 삽입
INSERT INTO currencies (currency_code, currency_name_ko, currency_name_en, country_code, country_name_ko, country_name_en, symbol, display_order) VALUES
('USD', '미국 달러', 'US Dollar', 'US', '미국', 'United States', '$', 1),
('JPY', '일본 엔', 'Japanese Yen', 'JP', '일본', 'Japan', '¥', 2),
('EUR', '유럽연합 유로', 'Euro', 'EU', '유럽연합', 'European Union', '€', 3),
('GBP', '영국 파운드', 'British Pound', 'GB', '영국', 'United Kingdom', '£', 4),
('CNY', '중국 위안', 'Chinese Yuan', 'CN', '중국', 'China', '¥', 5),
('AUD', '호주 달러', 'Australian Dollar', 'AU', '호주', 'Australia', 'A$', 6),
('CAD', '캐나다 달러', 'Canadian Dollar', 'CA', '캐나다', 'Canada', 'C$', 7),
('CHF', '스위스 프랑', 'Swiss Franc', 'CH', '스위스', 'Switzerland', 'CHF', 8),
('HKD', '홍콩 달러', 'Hong Kong Dollar', 'HK', '홍콩', 'Hong Kong', 'HK$', 9),
('SGD', '싱가포르 달러', 'Singapore Dollar', 'SG', '싱가포르', 'Singapore', 'S$', 10),
('KRW', '한국 원', 'Korean Won', 'KR', '한국', 'South Korea', '₩', 11)
ON DUPLICATE KEY UPDATE
    currency_name_ko = VALUES(currency_name_ko),
    currency_name_en = VALUES(currency_name_en),
    country_name_ko = VALUES(country_name_ko),
    country_name_en = VALUES(country_name_en),
    symbol = VALUES(symbol),
    display_order = VALUES(display_order);

-- 샘플 환율 데이터 삽입 (테스트용)
INSERT INTO exchange_rate_history (currency_code, currency_name, deal_base_rate, tts, ttb, source, recorded_at) VALUES
('USD', '미국 달러', 1392.40, 1420.85, 1363.95, 'sample', NOW() - INTERVAL 1 HOUR),
('JPY', '일본 엔', 9.46, 9.65, 9.27, 'sample', NOW() - INTERVAL 1 HOUR),
('EUR', '유럽연합 유로', 1456.80, 1486.94, 1426.66, 'sample', NOW() - INTERVAL 1 HOUR),
('GBP', '영국 파운드', 1678.50, 1712.07, 1644.93, 'sample', NOW() - INTERVAL 1 HOUR),
('CNY', '중국 위안', 192.30, 196.15, 188.45, 'sample', NOW() - INTERVAL 1 HOUR)
ON DUPLICATE KEY UPDATE
    deal_base_rate = VALUES(deal_base_rate),
    tts = VALUES(tts),
    ttb = VALUES(ttb),
    recorded_at = VALUES(recorded_at);

-- 파티셔닝 설정 (대용량 데이터 처리용)
-- 주의: 파티셔닝은 기존 데이터가 있으면 적용할 수 없으므로 초기 설정 시에만 사용
-- ALTER TABLE exchange_rate_history 
-- PARTITION BY RANGE (YEAR(recorded_at)) (
--     PARTITION p2023 VALUES LESS THAN (2024),
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );

-- 성능 최적화를 위한 추가 인덱스
CREATE INDEX idx_exchange_rate_latest ON exchange_rate_history (currency_code, recorded_at DESC, deal_base_rate);
CREATE INDEX idx_daily_rates_latest ON daily_exchange_rates (currency_code, trade_date DESC, close_rate);

-- 뷰 생성: 최신 환율 조회용
CREATE OR REPLACE VIEW latest_exchange_rates AS
SELECT 
    h.currency_code,
    c.currency_name_ko as currency_name,
    c.symbol,
    h.deal_base_rate,
    h.tts,
    h.ttb,
    h.source,
    h.recorded_at,
    h.created_at
FROM exchange_rate_history h
INNER JOIN currencies c ON h.currency_code = c.currency_code
INNER JOIN (
    SELECT currency_code, MAX(recorded_at) as max_recorded_at
    FROM exchange_rate_history 
    GROUP BY currency_code
) latest ON h.currency_code = latest.currency_code 
         AND h.recorded_at = latest.max_recorded_at
WHERE c.is_active = TRUE
ORDER BY c.display_order;

-- 프로시저: 일별 집계 데이터 생성
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS GenerateDailyAggregates(IN target_date DATE)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    INSERT INTO daily_exchange_rates 
    (currency_code, trade_date, open_rate, close_rate, high_rate, low_rate, avg_rate, volume, volatility)
    SELECT 
        currency_code,
        DATE(recorded_at) as trade_date,
        (SELECT deal_base_rate FROM exchange_rate_history h2 
         WHERE h2.currency_code = h1.currency_code 
         AND DATE(h2.recorded_at) = target_date
         ORDER BY h2.recorded_at ASC LIMIT 1) as open_rate,
        (SELECT deal_base_rate FROM exchange_rate_history h2 
         WHERE h2.currency_code = h1.currency_code 
         AND DATE(h2.recorded_at) = target_date
         ORDER BY h2.recorded_at DESC LIMIT 1) as close_rate,
        MAX(deal_base_rate) as high_rate,
        MIN(deal_base_rate) as low_rate,
        AVG(deal_base_rate) as avg_rate,
        COUNT(*) as volume,
        STDDEV(deal_base_rate) as volatility
    FROM exchange_rate_history h1
    WHERE DATE(recorded_at) = target_date
    GROUP BY currency_code
    ON DUPLICATE KEY UPDATE
        open_rate = VALUES(open_rate),
        close_rate = VALUES(close_rate),
        high_rate = VALUES(high_rate),
        low_rate = VALUES(low_rate),
        avg_rate = VALUES(avg_rate),
        volume = VALUES(volume),
        volatility = VALUES(volatility),
        updated_at = CURRENT_TIMESTAMP;
    
    COMMIT;
END //
DELIMITER ;

-- 함수: 환율 변화율 계산
DELIMITER //
CREATE FUNCTION IF NOT EXISTS CalculateChangePercent(current_rate DECIMAL(18,4), previous_rate DECIMAL(18,4))
RETURNS DECIMAL(10,4)
READS SQL DATA
DETERMINISTIC
BEGIN
    IF previous_rate IS NULL OR previous_rate = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN ((current_rate - previous_rate) / previous_rate) * 100;
END //
DELIMITER ;

-- 데이터 정리를 위한 이벤트 스케줄러 (선택사항)
-- SET GLOBAL event_scheduler = ON;
-- 
-- CREATE EVENT IF NOT EXISTS cleanup_old_exchange_rates
-- ON SCHEDULE EVERY 1 DAY
-- STARTS CURRENT_TIMESTAMP
-- DO
--   DELETE FROM exchange_rate_history 
--   WHERE recorded_at < DATE_SUB(NOW(), INTERVAL 2 YEAR);

COMMIT;