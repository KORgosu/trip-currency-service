"""
Data Ingestor Service - 외부 데이터 수집 및 처리 서비스
CronJob으로 실행되는 배치 작업 (로컬에서는 스케줄러로 실행)
"""
import os
import sys
import asyncio
import signal
import platform
from datetime import datetime, timedelta
from typing import Optional

# Windows 운영체제일 경우, asyncio 정책을 변경하여 SelectorEventLoop를 사용하도록 설정
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 상위 디렉토리의 shared 모듈 import를 위한 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
shared_dir = os.path.join(parent_dir, 'shared')

# 프로젝트 루트 경로 추가 (app 폴더를 찾기 위해)
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

sys.path.insert(0, parent_dir)
sys.path.insert(0, shared_dir)
sys.path.append(os.path.join(current_dir, 'app'))

from shared.config import init_config, get_config
from shared.database import init_database, get_db_manager
from shared.utils import SecurityUtils
from shared.exceptions import BaseServiceException

# config 초기화 (import 전에 해야 함)
config = init_config("data-ingestor")

# TODO: import 경로 문제 해결 - PYTHONPATH 설정 또는 sys.path 추가
# - app 디렉토리 경로 추가: sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
# - services/data-ingestor/app/services/data_processor.py 존재 확인
import sys
import os

# 절대 경로를 사용하여 import
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, 'app')
services_dir = os.path.join(app_dir, 'services')

# 경로 추가
sys.path.insert(0, current_dir)
sys.path.insert(0, app_dir)
sys.path.insert(0, services_dir)

# import 시도
try:
    from app.services.data_collector import DataCollector
    from app.services.data_processor import DataProcessor
    from app.scheduler import DataIngestionScheduler
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"App directory: {app_dir}")
    print(f"Services directory: {services_dir}")
    print(f"Python path: {sys.path}")

    # 파일 존재 확인
    data_collector_path = os.path.join(services_dir, 'data_collector.py')
    data_processor_path = os.path.join(services_dir, 'data_processor.py')
    scheduler_path = os.path.join(app_dir, 'scheduler.py')

    print(f"Data collector exists: {os.path.exists(data_collector_path)}")
    print(f"Data processor exists: {os.path.exists(data_processor_path)}")
    print(f"Scheduler exists: {os.path.exists(scheduler_path)}")

    raise

# 전역 변수
data_collector: Optional[DataCollector] = None
data_processor: Optional[DataProcessor] = None
scheduler: Optional[DataIngestionScheduler] = None
running = True


async def initialize_services():
    """서비스 초기화"""
    global data_collector, data_processor, scheduler
    
    try:
        # 설정 초기화
        config = init_config("data-ingestor")
        
        # 로거 초기화 (설정 후)
        from shared.logging import get_logger, set_correlation_id
        logger = get_logger(__name__)
        
        logger.info("Data Ingestor Service starting", version=config.service_version)
        
        # 데이터베이스 초기화
        await init_database()
        logger.info("Database connections initialized")
        
        # 서비스 초기화
        data_collector = DataCollector()
        data_processor = DataProcessor()
        scheduler = DataIngestionScheduler(data_collector, data_processor)
        
        await data_collector.initialize()
        await data_processor.initialize()
        
        logger.info("Data Ingestor Service initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize Data Ingestor Service", error=e)
        raise


async def cleanup_services():
    """서비스 정리"""
    global data_collector, data_processor, scheduler

    try:
        if scheduler:
            await scheduler.stop()

        if data_collector:
            await data_collector.close()

        if data_processor:
            await data_processor.close()

        db_manager = get_db_manager()
        await db_manager.close()

        # 로거가 정의되지 않은 경우를 대비하여 print 사용
        try:
            from shared.logging import get_logger
            logger = get_logger(__name__)
            logger.info("Data Ingestor Service stopped")
        except:
            print("Data Ingestor Service stopped")

    except Exception as e:
        try:
            from shared.logging import get_logger
            logger = get_logger(__name__)
            logger.error("Error during cleanup", error=e)
        except:
            print(f"Error during cleanup: {e}")


def signal_handler(signum, frame):
    """시그널 핸들러"""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


async def run_single_collection():
    """단일 데이터 수집 실행 (테스트용)"""
    from shared.logging import get_logger, set_correlation_id
    logger = get_logger(__name__)
    
    correlation_id = SecurityUtils.generate_correlation_id()
    set_correlation_id(correlation_id)
    
    logger.info("Starting single data collection run", correlation_id=correlation_id)
    
    try:
        await initialize_services()
        
        # 데이터 수집 실행
        collection_results = await data_collector.collect_all_data()
        
        # 데이터 처리
        for result in collection_results:
            if result.success:
                await data_processor.process_exchange_rate_data(result)
            else:
                logger.warning("Collection failed", source=result.source, error=result.error_message)
        
        logger.info("Single data collection completed successfully")
        
    except Exception as e:
        logger.error("Single data collection failed", error=e)
        raise
    finally:
        await cleanup_services()


async def run_scheduler():
    """스케줄러 실행 (지속적 실행)"""
    logger.info("Starting Data Ingestor Scheduler")
    
    try:
        await initialize_services()
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 스케줄러 시작
        await scheduler.start()
        
        # 메인 루프
        while running:
            await asyncio.sleep(1)
        
        logger.info("Scheduler shutdown requested")
        
    except Exception as e:
        logger.error("Scheduler execution failed", error=e)
        raise
    finally:
        await cleanup_services()


async def run_kubernetes_cronjob():
    """Kubernetes CronJob 실행 (한 번 실행 후 종료)"""
    correlation_id = SecurityUtils.generate_correlation_id()
    set_correlation_id(correlation_id)
    
    logger.info("Starting Kubernetes CronJob execution", correlation_id=correlation_id)
    
    try:
        await initialize_services()
        
        # 데이터 수집 및 처리
        start_time = datetime.utcnow()
        
        collection_results = await data_collector.collect_all_data()
        
        successful_collections = 0
        failed_collections = 0
        
        for result in collection_results:
            if result.success:
                try:
                    await data_processor.process_exchange_rate_data(result)
                    successful_collections += 1
                except Exception as e:
                    logger.error("Failed to process data", source=result.source, error=e)
                    failed_collections += 1
            else:
                failed_collections += 1
                logger.warning("Collection failed", 
                             source=result.source, 
                             error=result.error_message)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(
            "CronJob execution completed",
            duration_seconds=duration,
            successful_collections=successful_collections,
            failed_collections=failed_collections,
            correlation_id=correlation_id
        )
        
        # 성공/실패에 따른 종료 코드 설정
        if successful_collections > 0:
            sys.exit(0)  # 성공
        else:
            sys.exit(1)  # 실패
        
    except Exception as e:
        logger.error("CronJob execution failed", error=e, correlation_id=correlation_id)
        sys.exit(1)
    finally:
        await cleanup_services()


def main():
    """메인 함수"""
    # 실행 모드 결정
    mode = os.getenv("EXECUTION_MODE", "single")  # single, scheduler, cronjob
    
    if mode == "single":
        # 단일 실행 (테스트용)
        asyncio.run(run_single_collection())
    elif mode == "scheduler":
        # 지속적 스케줄러 실행 (로컬 개발용)
        asyncio.run(run_scheduler())
    elif mode == "cronjob":
        # Kubernetes CronJob 실행
        asyncio.run(run_kubernetes_cronjob())
    else:
        logger.error(f"Unknown execution mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()