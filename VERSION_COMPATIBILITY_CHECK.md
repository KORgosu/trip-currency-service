# 버전 호환성 체크 가이드

## 📋 현재 버전 상태

### ✅ 핵심 의존성 버전
```
Python: 3.11+
FastAPI: 0.104.1
Pydantic: 2.5.0
aioredis: 2.0.1
aiomysql: 0.2.0
boto3: 1.34.0
aiokafka: 0.9.0
```

## 🔍 호환성 매트릭스

### Python 버전 호환성
| Python | FastAPI | Pydantic | aioredis | aiomysql | 상태 |
|--------|---------|----------|----------|----------|------|
| 3.11   | 0.104.1 | 2.5.0    | 2.0.1    | 0.2.0    | ✅ 권장 |
| 3.10   | 0.104.1 | 2.5.0    | 2.0.1    | 0.2.0    | ✅ 지원 |
| 3.9    | 0.104.1 | 2.5.0    | 2.0.1    | 0.2.0    | ⚠️ 제한적 |
| 3.8    | 0.104.1 | 2.5.0    | 2.0.1    | 0.2.0    | ❌ 미지원 |

### 주요 라이브러리 호환성

#### FastAPI + Pydantic
```
✅ FastAPI 0.104.1 + Pydantic 2.5.0 (완전 호환)
⚠️ FastAPI 0.100.x + Pydantic 2.x (부분 호환)
❌ FastAPI 0.9x.x + Pydantic 2.x (호환 불가)
```

#### aioredis 버전 변경사항
```python
# aioredis 1.x (구버전)
import aioredis
redis = await aioredis.create_redis_pool('redis://localhost')

# aioredis 2.x (현재 사용)
import aioredis
redis = aioredis.from_url('redis://localhost')
```

## 🔧 마이그레이션 가이드

### 1. aioredis 1.x → 2.x 마이그레이션

#### 연결 방식 변경
```python
# 기존 (1.x)
import aioredis
redis = await aioredis.create_redis_pool('redis://localhost:6379')

# 신규 (2.x)
import aioredis
redis = aioredis.from_url('redis://localhost:6379', decode_responses=True)
```

#### 명령어 API 변경
```python
# 기존 (1.x)
await redis.set('key', 'value')
await redis.expire('key', 60)

# 신규 (2.x)
await redis.set('key', 'value', ex=60)  # TTL을 set 명령어에 포함
```

#### 해시 명령어 변경
```python
# 기존 (1.x)
await redis.hmset('hash_key', {'field1': 'value1', 'field2': 'value2'})

# 신규 (2.x)
await redis.hset('hash_key', mapping={'field1': 'value1', 'field2': 'value2'})
```

### 2. Pydantic 1.x → 2.x 마이그레이션

#### 설정 클래스 변경
```python
# 기존 (1.x)
from pydantic import BaseModel

class MyModel(BaseModel):
    name: str
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 신규 (2.x)
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    name: str
```

#### 검증자 변경
```python
# 기존 (1.x)
from pydantic import validator

class MyModel(BaseModel):
    name: str
    
    @validator('name')
    def validate_name(cls, v):
        if not v:
            raise ValueError('Name is required')
        return v

# 신규 (2.x)
from pydantic import field_validator

class MyModel(BaseModel):
    name: str
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v:
            raise ValueError('Name is required')
        return v
```

## 🚨 알려진 호환성 이슈

### 1. aiokafka 버전 이슈
```
문제: aiokafka 0.8.x와 Python 3.11 호환성 문제
해결: aiokafka 0.9.0+ 사용 필수
```

### 2. MySQL 드라이버 이슈
```
문제: mysql-connector-python과 aiomysql 충돌
해결: aiomysql만 사용, mysql-connector-python 제거
```

### 3. Boto3 버전 이슈
```
문제: 구버전 boto3에서 일부 AWS 서비스 미지원
해결: boto3 1.34.0+ 사용 권장
```

## 🔄 업그레이드 절차

### 1. 단계별 업그레이드
```bash
# 1단계: 테스트 환경에서 업그레이드
pip install --upgrade fastapi pydantic aioredis

# 2단계: 테스트 실행
python -m pytest tests/ -v

# 3단계: 호환성 확인
python scripts/check_compatibility.py

# 4단계: 프로덕션 배포
```

### 2. 롤백 계획
```bash
# 이전 버전으로 롤백
pip install fastapi==0.100.1 pydantic==1.10.12

# 또는 requirements.txt 고정
pip install -r requirements-stable.txt
```

## 📊 성능 영향 분석

### Pydantic 2.x 성능 개선
```
- 검증 속도: 5-50x 향상
- 메모리 사용량: 10-20% 감소
- JSON 직렬화: 2-3x 향상
```

### aioredis 2.x 성능 변화
```
- 연결 성능: 약간 향상
- 메모리 사용량: 유사
- API 일관성: 크게 개선
```

## 🧪 호환성 테스트

### 자동 호환성 체크 스크립트
```python
#!/usr/bin/env python3
"""
버전 호환성 체크 스크립트
"""
import sys
import importlib
from packaging import version

def check_python_version():
    """Python 버전 체크"""
    required = "3.10"
    current = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    if version.parse(current) < version.parse(required):
        print(f"❌ Python {current} < {required} (required)")
        return False
    
    print(f"✅ Python {current} >= {required}")
    return True

def check_package_version(package_name: str, required_version: str):
    """패키지 버전 체크"""
    try:
        pkg = importlib.import_module(package_name)
        current_version = getattr(pkg, '__version__', 'unknown')
        
        if current_version == 'unknown':
            print(f"⚠️ {package_name}: version unknown")
            return True
        
        if version.parse(current_version) >= version.parse(required_version):
            print(f"✅ {package_name}: {current_version} >= {required_version}")
            return True
        else:
            print(f"❌ {package_name}: {current_version} < {required_version}")
            return False
            
    except ImportError:
        print(f"❌ {package_name}: not installed")
        return False

def main():
    """메인 체크 함수"""
    print("🔍 Version Compatibility Check")
    print("=" * 40)
    
    checks = [
        check_python_version(),
        check_package_version("fastapi", "0.104.0"),
        check_package_version("pydantic", "2.5.0"),
        check_package_version("aioredis", "2.0.0"),
        check_package_version("aiomysql", "0.2.0"),
        check_package_version("boto3", "1.34.0"),
        check_package_version("aiokafka", "0.9.0"),
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    print("\n" + "=" * 40)
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All compatibility checks passed!")
        return 0
    else:
        print("⚠️ Some compatibility issues found")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 실행 방법
```bash
# 호환성 체크 실행
python scripts/check_compatibility.py

# 또는 Make 명령어로
make check-compatibility
```

## 🔧 문제 해결 가이드

### 1. ImportError 해결
```python
# 문제: ModuleNotFoundError: No module named 'aioredis'
# 해결:
pip install aioredis==2.0.1

# 문제: ImportError: cannot import name 'create_redis_pool'
# 해결: aioredis 2.x API 사용
redis = aioredis.from_url('redis://localhost')
```

### 2. Pydantic 검증 에러 해결
```python
# 문제: ValidationError in Pydantic 2.x
# 해결: 새로운 검증자 API 사용
from pydantic import field_validator

@field_validator('field_name')
@classmethod
def validate_field(cls, v):
    return v
```

### 3. FastAPI 호환성 에러 해결
```python
# 문제: Pydantic model serialization error
# 해결: model_dump() 사용
# 기존
model.dict()

# 신규
model.model_dump()
```

## 📅 업그레이드 로드맵

### 단기 (1-2주)
- [ ] 현재 버전 호환성 확인
- [ ] 테스트 환경에서 업그레이드 테스트
- [ ] 문제점 파악 및 해결

### 중기 (1개월)
- [ ] 프로덕션 환경 업그레이드
- [ ] 성능 모니터링
- [ ] 안정성 확인

### 장기 (3개월)
- [ ] 최신 버전 추적 시스템 구축
- [ ] 자동 호환성 테스트 구축
- [ ] 정기 업그레이드 프로세스 수립

## 📋 체크리스트

### 업그레이드 전
- [ ] 현재 버전 백업
- [ ] 테스트 환경 준비
- [ ] 롤백 계획 수립
- [ ] 의존성 분석 완료

### 업그레이드 중
- [ ] 단계별 업그레이드 실행
- [ ] 각 단계별 테스트 실행
- [ ] 문제 발생 시 즉시 롤백
- [ ] 로그 모니터링

### 업그레이드 후
- [ ] 전체 기능 테스트
- [ ] 성능 테스트
- [ ] 모니터링 확인
- [ ] 문서 업데이트

이 가이드를 통해 안전하고 체계적인 버전 업그레이드를 수행할 수 있습니다.