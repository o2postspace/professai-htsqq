# kospi_code.mst 기반 OHLCV 데이터 수집

`kospi_code.mst` 파일에서 종목 코드를 추출하여 모든 코스피 종목의 OHLCV 데이터를 수집합니다.

## 사용 방법

### 1. 기본 실행

```bash
python get_ohlcv_from_mst.py
```

### 2. 옵션 사용

```bash
# 출력 디렉토리 지정
python get_ohlcv_from_mst.py --output kospi_data

# 일봉 데이터 200개 조회
python get_ohlcv_from_mst.py --count 200

# API 호출 간 지연 시간 조정 (초)
python get_ohlcv_from_mst.py --delay 0.2

# 주봉 데이터 조회
python get_ohlcv_from_mst.py --period W
```

## 예상 소요 시간

- 종목 수: 약 2,000개
- 지연 시간: 0.1초/종목 (기본값)
- 예상 시간: 약 3-4분 (2,000개 × 0.1초 = 200초)

## 출력 파일

- 개별 종목 파일: `ohlcv_data/{종목코드}.csv`
- 통합 파일: `ohlcv_data/all_kospi_ohlcv_{날짜}.csv`
- 실패한 종목: `ohlcv_data/failed_codes_{날짜}.txt`

## 주의사항

1. **API 호출 제한**: 한국투자증권 Open API는 초당 호출 제한이 있습니다. 
   - 기본 지연 시간(0.1초)을 사용하는 것을 권장합니다.
   - 너무 빠르게 호출하면 제한에 걸릴 수 있습니다.

2. **대량 데이터**: 약 2,000개 종목을 조회하므로 시간이 걸릴 수 있습니다.
   - 진행 상황은 100개마다 출력됩니다.
   - 중간에 중단되면 실패한 종목 목록을 확인하여 재시도할 수 있습니다.

3. **토큰 만료**: 접근 토큰은 24시간마다 갱신됩니다. 코드가 자동으로 토큰을 갱신합니다.

## 테스트 실행

먼저 소수의 종목만 테스트하려면:

```python
from parse_kospi_mst import get_stock_codes_from_mst
from get_ohlcv import get_ohlcv_data
import kis_auth as ka

# 인증
ka.auth()

# 종목 코드 추출 (처음 10개만)
stock_codes = get_stock_codes_from_mst()[:10]

# 테스트
for code in stock_codes:
    df = get_ohlcv_data(code, period="D", count=10)
    print(f"{code}: {len(df)}개 데이터")
```








