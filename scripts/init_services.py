#!/usr/bin/env python3
"""
서비스 초기화 스크립트
MySQL, Redis, LocalStack 초기 설정 및 데이터 로드
"""
import os
import sys
import asyncio
import time
import json
from datetime import datetime, timedelta
from decimal import Decimal

# 상위 디렉토리의 shared 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services'))

import aiomysql
import redis.asyncio as aioredis
import boto3
from botocore.exceptions import ClientError


class ServiceInitializer:
    """서비스 초기화 클래스"""
    
    def __init__(self):
        self.mysql_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'currency_user'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'db': os.getenv('DB_NAME', 'currency_db')
        }
        
        self.redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'password': os.getenv('REDIS_PASSWORD', '')
        }
        
        self.aws_config = {
            'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566'),
            'region_name': os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-2'),
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
        }
    
    async def initialize_all(self):
        """모든 서비스 초기화"""
        print("🚀 Starting service initialization...")
        
        try:
            # 1. MySQL 초기화
            await self.initialize_mysql()
            
            # 2. Redis 초기화
            await self.initialize_redis()
            
            # 3. LocalStack (DynamoDB, SQS) 초기화
            await self.initialize_localstack()
            
            print("✅ All services initialized successfully!")
            
        except Exception as e:
            print(f"❌ Service initialization failed: {e}")
            raise
    
    async def initialize_mysql(self):
        """MySQL 데이터베이스 초기화"""
        print("📊 Initializing MySQL database...")
        
        try:
            # MySQL 연결 대기
            await self.wait_for_mysql()
            
            # 데이터베이스 연결
            connection = await aiomysql.connect(**self.mysql_config)
            
            try:
                async with connection.cursor() as cursor:
                    # 통화 마스터 데이터 삽입
                    await self.insert_currency_master_data(cursor)
                    
                    # 샘플 환율 데이터 삽입
                    await self.insert_sample_exchange_rates(cursor)
                    
                    # 일별 집계 테이블 데이터 생성
                    await self.generate_daily_aggregates(cursor)
                
                await connection.commit()
                print("✅ MySQL initialization completed")
                
            finally:
                connection.close()
                
        except Exception as e:
            print(f"❌ MySQL initialization failed: {e}")
            raise
    
    async def wait_for_mysql(self, max_retries=30):
        """MySQL 연결 대기"""
        for i in range(max_retries):
            try:
                connection = await aiomysql.connect(**self.mysql_config)
                connection.close()
                print("✅ MySQL is ready")
                return
            except Exception as e:
                print(f"⏳ Waiting for MySQL... ({i+1}/{max_retries})")
                await asyncio.sleep(2)
        
        raise Exception("MySQL connection timeout")
    
    async def insert_currency_master_data(self, cursor):
        """통화 마스터 데이터 삽입"""
        currencies = [
            ('USD', '미국 달러', 'US Dollar', 'US', '미국', 'United States', '$', 2, True, 1),
            ('JPY', '일본 엔', 'Japanese Yen', 'JP', '일본', 'Japan', '¥', 0, True, 2),
            ('EUR', '유로', 'Euro', 'EU', '유럽연합', 'European Union', '€', 2, True, 3),
            ('GBP', '영국 파운드', 'British Pound', 'GB', '영국', 'United Kingdom', '£', 2, True, 4),
            ('CNY', '중국 위안', 'Chinese Yuan', 'CN', '중국', 'China', '¥', 2, True, 5),
            ('AUD', '호주 달러', 'Australian Dollar', 'AU', '호주', 'Australia', 'A$', 2, True, 6),
            ('CAD', '캐나다 달러', 'Canadian Dollar', 'CA', '캐나다', 'Canada', 'C$', 2, True, 7),
            ('CHF', '스위스 프랑', 'Swiss Franc', 'CH', '스위스', 'Switzerland', 'CHF', 2, True, 8),
            ('HKD', '홍콩 달러', 'Hong Kong Dollar', 'HK', '홍콩', 'Hong Kong', 'HK$', 2, True, 9),
            ('SGD', '싱가포르 달러', 'Singapore Dollar', 'SG', '싱가포르', 'Singapore', 'S$', 2, True, 10)
        ]
        
        # 기존 데이터 확인
        await cursor.execute("SELECT COUNT(*) FROM currencies")
        count = await cursor.fetchone()
        
        if count[0] == 0:
            insert_query = """
                INSERT INTO currencies (
                    currency_code, currency_name_ko, currency_name_en,
                    country_code, country_name_ko, country_name_en,
                    symbol, decimal_places, is_active, display_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            await cursor.executemany(insert_query, currencies)
            print(f"✅ Inserted {len(currencies)} currency records")
        else:
            print(f"ℹ️ Currency master data already exists ({count[0]} records)")
    
    async def insert_sample_exchange_rates(self, cursor):
        """샘플 환율 데이터 삽입"""
        # 기존 데이터 확인
        await cursor.execute("SELECT COUNT(*) FROM exchange_rate_history")
        count = await cursor.fetchone()
        
        if count[0] > 0:
            print(f"ℹ️ Exchange rate data already exists ({count[0]} records)")
            return
        
        # 샘플 환율 데이터 생성 (최근 30일)
        base_rates = {
            'USD': 1350.0,
            'JPY': 9.2,
            'EUR': 1450.0,
            'GBP': 1650.0,
            'CNY': 185.0,
            'AUD': 900.0,
            'CAD': 1000.0,
            'CHF': 1500.0,
            'HKD': 175.0,
            'SGD': 1000.0
        }
        
        currency_names = {
            'USD': '미국 달러',
            'JPY': '일본 엔',
            'EUR': '유로',
            'GBP': '영국 파운드',
            'CNY': '중국 위안',
            'AUD': '호주 달러',
            'CAD': '캐나다 달러',
            'CHF': '스위스 프랑',
            'HKD': '홍콩 달러',
            'SGD': '싱가포르 달러'
        }
        
        insert_query = """
            INSERT INTO exchange_rate_history (
                currency_code, currency_name, deal_base_rate, tts, ttb,
                source, recorded_at, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        records = []
        
        for days_ago in range(30, 0, -1):
            record_date = datetime.now() - timedelta(days=days_ago)
            
            for currency_code, base_rate in base_rates.items():
                # 약간의 랜덤 변동 추가
                import random
                variation = random.uniform(-0.02, 0.02)  # ±2% 변동
                current_rate = base_rate * (1 + variation)
                
                # TTS/TTB 계산 (매매기준율 기준 ±2%)
                tts = current_rate * 1.02
                ttb = current_rate * 0.98
                
                records.append((
                    currency_code,
                    currency_names[currency_code],
                    round(current_rate, 4),
                    round(tts, 4),
                    round(ttb, 4),
                    'BOK',  # 한국은행
                    record_date,
                    datetime.now()
                ))
        
        await cursor.executemany(insert_query, records)
        print(f"✅ Inserted {len(records)} exchange rate records")
    
    async def generate_daily_aggregates(self, cursor):
        """일별 집계 데이터 생성"""
        # 기존 데이터 확인
        await cursor.execute("SELECT COUNT(*) FROM daily_exchange_rates")
        count = await cursor.fetchone()
        
        if count[0] > 0:
            print(f"ℹ️ Daily aggregate data already exists ({count[0]} records)")
            return
        
        # 일별 집계 데이터 생성
        aggregate_query = """
            INSERT INTO daily_exchange_rates (
                currency_code, trade_date, open_rate, close_rate,
                high_rate, low_rate, avg_rate, volume
            )
            SELECT 
                currency_code,
                DATE(recorded_at) as trade_date,
                MIN(deal_base_rate) as open_rate,
                MAX(deal_base_rate) as close_rate,
                MAX(deal_base_rate) as high_rate,
                MIN(deal_base_rate) as low_rate,
                AVG(deal_base_rate) as avg_rate,
                COUNT(*) as volume
            FROM exchange_rate_history 
            GROUP BY currency_code, DATE(recorded_at)
        """
        
        await cursor.execute(aggregate_query)
        affected_rows = cursor.rowcount
        print(f"✅ Generated {affected_rows} daily aggregate records")
    
    async def initialize_redis(self):
        """Redis 초기화"""
        print("🔴 Initializing Redis...")
        
        try:
            # Redis 연결
            redis_url = f"redis://{self.redis_config['host']}:{self.redis_config['port']}"
            redis = aioredis.from_url(redis_url, decode_responses=True)
            
            # 연결 테스트
            await redis.ping()
            
            # 샘플 환율 데이터를 Redis에 캐시
            await self.cache_sample_rates(redis)
            
            await redis.close()
            print("✅ Redis initialization completed")
            
        except Exception as e:
            print(f"❌ Redis initialization failed: {e}")
            # Redis 실패는 치명적이지 않으므로 계속 진행
            print("⚠️ Continuing without Redis cache")
    
    async def cache_sample_rates(self, redis):
        """샘플 환율 데이터를 Redis에 캐시"""
        sample_rates = {
            'USD': {'currency_name': '미국 달러', 'deal_base_rate': '1350.0', 'tts': '1377.0', 'ttb': '1323.0'},
            'JPY': {'currency_name': '일본 엔', 'deal_base_rate': '9.2', 'tts': '9.38', 'ttb': '9.02'},
            'EUR': {'currency_name': '유로', 'deal_base_rate': '1450.0', 'tts': '1479.0', 'ttb': '1421.0'},
            'GBP': {'currency_name': '영국 파운드', 'deal_base_rate': '1650.0', 'tts': '1683.0', 'ttb': '1617.0'},
            'CNY': {'currency_name': '중국 위안', 'deal_base_rate': '185.0', 'tts': '188.7', 'ttb': '181.3'}
        }
        
        for currency_code, rate_data in sample_rates.items():
            cache_key = f"rate:{currency_code}"
            rate_data['source'] = 'BOK'
            rate_data['last_updated_at'] = datetime.now().isoformat() + 'Z'
            
            await redis.hset(cache_key, mapping=rate_data)
            await redis.expire(cache_key, 600)  # 10분 TTL
        
        print(f"✅ Cached {len(sample_rates)} exchange rates in Redis")
    
    async def initialize_localstack(self):
        """LocalStack (DynamoDB, SQS) 초기화"""
        print("🌩️ Initializing LocalStack services...")
        
        try:
            # LocalStack 연결 대기
            await self.wait_for_localstack()
            
            # DynamoDB 테이블 생성
            await self.create_dynamodb_tables()
            
            # SQS 큐 생성
            await self.create_sqs_queues()
            
            print("✅ LocalStack initialization completed")
            
        except Exception as e:
            print(f"❌ LocalStack initialization failed: {e}")
            print("⚠️ Continuing without LocalStack services")
    
    async def wait_for_localstack(self, max_retries=10):
        """LocalStack 연결 대기"""
        import requests
        
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.aws_config['endpoint_url']}/_localstack/health", timeout=5)
                if response.status_code == 200:
                    print("✅ LocalStack is ready")
                    return
            except Exception:
                pass
            
            print(f"⏳ Waiting for LocalStack... ({i+1}/{max_retries})")
            await asyncio.sleep(2)
        
        raise Exception("LocalStack connection timeout")
    
    async def create_dynamodb_tables(self):
        """DynamoDB 테이블 생성"""
        dynamodb = boto3.client('dynamodb', **self.aws_config)
        
        # 1. 사용자 선택 기록 테이블
        try:
            table_name = 'travel_destination_selections'
            
            # 테이블 존재 확인
            try:
                dynamodb.describe_table(TableName=table_name)
                print(f"ℹ️ DynamoDB table '{table_name}' already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # 테이블 생성
                    dynamodb.create_table(
                        TableName=table_name,
                        KeySchema=[
                            {'AttributeName': 'selection_date', 'KeyType': 'HASH'},
                            {'AttributeName': 'selection_timestamp_userid', 'KeyType': 'RANGE'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'selection_date', 'AttributeType': 'S'},
                            {'AttributeName': 'selection_timestamp_userid', 'AttributeType': 'S'},
                            {'AttributeName': 'country_code', 'AttributeType': 'S'}
                        ],
                        GlobalSecondaryIndexes=[
                            {
                                'IndexName': 'country-date-index',
                                'KeySchema': [
                                    {'AttributeName': 'country_code', 'KeyType': 'HASH'},
                                    {'AttributeName': 'selection_date', 'KeyType': 'RANGE'}
                                ],
                                'Projection': {'ProjectionType': 'ALL'},
                                'ProvisionedThroughput': {
                                    'ReadCapacityUnits': 5,
                                    'WriteCapacityUnits': 5
                                }
                            }
                        ],
                        BillingMode='PROVISIONED',
                        ProvisionedThroughput={
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    )
                    print(f"✅ Created DynamoDB table '{table_name}'")
                else:
                    raise
            
            # 2. 랭킹 결과 테이블
            table_name = 'RankingResults'
            
            try:
                dynamodb.describe_table(TableName=table_name)
                print(f"ℹ️ DynamoDB table '{table_name}' already exists")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    dynamodb.create_table(
                        TableName=table_name,
                        KeySchema=[
                            {'AttributeName': 'period', 'KeyType': 'HASH'}
                        ],
                        AttributeDefinitions=[
                            {'AttributeName': 'period', 'AttributeType': 'S'}
                        ],
                        BillingMode='PROVISIONED',
                        ProvisionedThroughput={
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 2
                        }
                    )
                    print(f"✅ Created DynamoDB table '{table_name}'")
                else:
                    raise
            
        except Exception as e:
            print(f"❌ Failed to create DynamoDB tables: {e}")
            raise
    
    async def create_sqs_queues(self):
        """SQS 큐 생성"""
        sqs = boto3.client('sqs', **self.aws_config)
        
        queues = [
            'ranking-calculation-queue',
            'data-processing-queue',
            'notification-queue'
        ]
        
        for queue_name in queues:
            try:
                # 큐 존재 확인
                try:
                    response = sqs.get_queue_url(QueueName=queue_name)
                    print(f"ℹ️ SQS queue '{queue_name}' already exists")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                        # 큐 생성
                        sqs.create_queue(
                            QueueName=queue_name,
                            Attributes={
                                'DelaySeconds': '0',
                                'MaxReceiveCount': '3',
                                'MessageRetentionPeriod': '1209600',  # 14일
                                'VisibilityTimeoutSeconds': '300'     # 5분
                            }
                        )
                        print(f"✅ Created SQS queue '{queue_name}'")
                    else:
                        raise
                        
            except Exception as e:
                print(f"❌ Failed to create SQS queue '{queue_name}': {e}")
                # SQS 큐 생성 실패는 치명적이지 않음


async def main():
    """메인 함수"""
    initializer = ServiceInitializer()
    await initializer.initialize_all()


if __name__ == "__main__":
    asyncio.run(main())