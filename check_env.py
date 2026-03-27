"""
.env 파일 및 환경 변수 확인 스크립트
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

print("=" * 60)
print("환경 변수 확인")
print("=" * 60)

# .env 파일 존재 여부
env_file = ".env"
if os.path.exists(env_file):
    print(f"[OK] .env 파일이 존재합니다: {os.path.abspath(env_file)}")
else:
    print(f"[ERROR] .env 파일이 없습니다!")
    print(f"  프로젝트 루트에 .env 파일을 생성하세요.")
    print()

# 환경 설정
svr = os.getenv('KIS_SVR', 'prod')
print(f"\n환경 설정: {svr} ({'실전투자' if svr == 'prod' else '모의투자'})")

# API 키 확인
if svr == 'prod':
    app_key = os.getenv('KIS_APP_KEY')
    app_secret = os.getenv('KIS_APP_SECRET')
    key_name = "KIS_APP_KEY (실전투자)"
    secret_name = "KIS_APP_SECRET (실전투자)"
else:
    app_key = os.getenv('KIS_PAPER_APP_KEY')
    app_secret = os.getenv('KIS_PAPER_APP_SECRET')
    key_name = "KIS_PAPER_APP_KEY (모의투자)"
    secret_name = "KIS_PAPER_APP_SECRET (모의투자)"

print(f"\n{key_name}:")
if app_key:
    masked_key = app_key[:4] + "*" * (len(app_key) - 8) + app_key[-4:] if len(app_key) > 8 else "*" * len(app_key)
    print(f"  [OK] 설정됨 ({masked_key})")
else:
    print(f"  [ERROR] 설정되지 않음")

print(f"\n{secret_name}:")
if app_secret:
    masked_secret = app_secret[:4] + "*" * (len(app_secret) - 8) + app_secret[-4:] if len(app_secret) > 8 else "*" * len(app_secret)
    print(f"  [OK] 설정됨 ({masked_secret})")
else:
    print(f"  [ERROR] 설정되지 않음")

# 기타 설정
account_no = os.getenv('KIS_ACCOUNT_NO')
account_product = os.getenv('KIS_ACCOUNT_PRODUCT', '01')

print(f"\n계좌 정보:")
if account_no:
    print(f"  [OK] 계좌번호: {account_no}")
else:
    print(f"  [-] 계좌번호: 설정되지 않음 (OHLCV 조회에는 필수 아님)")

print(f"  [OK] 계좌상품: {account_product}")

print("\n" + "=" * 60)
print("확인 완료")
print("=" * 60)

if not app_key or not app_secret:
    print("\n[WARNING] API 키 또는 시크릿이 설정되지 않았습니다!")
    print("   .env 파일에 올바른 값을 입력하세요.")

