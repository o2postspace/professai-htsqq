# 한국 주식 OHLCV 데이터 수집

한국투자증권 Open API를 사용하여 한국 주식의 OHLCV(Open, High, Low, Close, Volume) 데이터를 수집하는 프로젝트입니다.

## 설치 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

**방법 1: YAML 파일 사용 (권장)**

`kis_devlp.yaml` 파일을 생성하고 다음 정보를 입력하세요:

```yaml
# 실전투자
my_app: "여기에 실전투자 앱키 입력"
my_sec: "여기에 실전투자 앱시크릿 입력"

# 모의투자
paper_app: "여기에 모의투자 앱키 입력"
paper_sec: "여기에 모의투자 앱시크릿 입력"

# HTS ID(KIS Developers 고객 ID) - 선택사항
my_htsid: "사용자 HTS ID"

# 계좌번호 앞 8자리
my_acct_stock: "증권계좌 8자리"
my_acct_future: "선물옵션계좌 8자리"
my_paper_stock: "모의투자 증권계좌 8자리"
my_paper_future: "모의투자 선물옵션계좌 8자리"

# 계좌번호 뒤 2자리
my_prod: "01" # 종합계좌
# my_prod: "03" # 국내선물옵션 계좌
# my_prod: "08" # 해외선물옵션 계좌
# my_prod: "22" # 연금저축 계좌
# my_prod: "29" # 퇴직연금 계좌

# User-Agent(기본값 사용 권장, 변경 불필요)
my_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

**방법 2: .env 파일 사용**

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# 한국투자증권 Open API 설정
# 실전투자
KIS_APP_KEY=your_real_app_key_here
KIS_APP_SECRET=your_real_app_secret_here

# 모의투자
KIS_PAPER_APP_KEY=your_paper_app_key_here
KIS_PAPER_APP_SECRET=your_paper_app_secret_here

# 계좌 정보
KIS_ACCOUNT_NO=your_account_number_here
KIS_ACCOUNT_PRODUCT=01

# HTS ID (선택사항)
KIS_HTS_ID=your_hts_id_here

# 환경 설정 (prod: 실전투자, vps: 모의투자)
KIS_SVR=prod
```

**참고**: YAML 파일이 있으면 YAML 파일을 우선 사용하고, 없으면 .env 파일을 사용합니다.

## 사용 방법

### 기본 사용법

모든 주식 종목의 OHLCV 데이터를 수집:

```bash
python get_ohlcv.py
```

### 옵션 사용

```bash
# 출력 디렉토리 지정
python get_ohlcv.py --output my_data

# 일봉 데이터 200개 조회
python get_ohlcv.py --count 200

# API 호출 간 지연 시간 조정 (초)
python get_ohlcv.py --delay 0.2

# 주봉 데이터 조회
python get_ohlcv.py --period W
```

### 개별 종목 조회

Python 코드에서 직접 사용:

```python
import kis_auth as ka
from get_ohlcv import get_ohlcv_data

# 인증
ka.auth()

# 삼성전자 일봉 데이터 조회 (최근 100일)
df = get_ohlcv_data("005930", period="D", count=100)
print(df)
```

## 출력 파일

- 개별 종목 파일: `ohlcv_data/{종목코드}.csv`
- 통합 파일: `ohlcv_data/all_stocks_ohlcv_{날짜}.csv`

각 CSV 파일에는 다음 컬럼이 포함됩니다:
- 날짜
- 시가 (Open)
- 고가 (High)
- 저가 (Low)
- 종가 (Close)
- 거래량 (Volume)
- 거래대금
- 종목코드

## 주의사항

1. **API 호출 제한**: 한국투자증권 Open API는 초당 호출 제한이 있습니다. `--delay` 옵션을 사용하여 적절한 지연 시간을 설정하세요.

2. **토큰 만료**: 접근 토큰은 24시간마다 갱신됩니다. 코드가 자동으로 토큰을 갱신합니다.

3. **모의투자 vs 실전투자**: `.env` 파일의 `KIS_SVR` 값을 변경하여 모의투자(`vps`) 또는 실전투자(`prod`) 환경을 선택할 수 있습니다.

## 문제 해결

### 설정 파일 확인
```bash
# 설정 파일 확인
python check_config.py
```

### 토큰 오류
```python
import kis_auth as ka
ka.auth()  # 토큰 재발급
```

### 종목 목록 조회 실패
- API 키와 시크릿이 올바른지 확인하세요.
- `kis_devlp.yaml` 또는 `.env` 파일의 설정이 올바른지 확인하세요.
- 실전투자/모의투자 환경에 맞는 키를 사용하고 있는지 확인하세요.

## 참고 자료

- [한국투자증권 Open API 개발자센터](https://apiportal.koreainvestment.com/)
- [GitHub 저장소](https://github.com/koreainvestment/open-trading-api)

