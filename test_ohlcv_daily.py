"""
일봉 데이터 테스트
"""
import kis_auth as ka
from get_ohlcv import get_ohlcv_data
from datetime import datetime, timedelta

# 인증
print("인증 중...")
ka.auth()

# 삼성전자 일봉 데이터 테스트
print("\n삼성전자 일봉 데이터 조회 테스트")
print("=" * 60)

# 최근 10일 데이터
print("\n1. 최근 10일 일봉 데이터:")
df = get_ohlcv_data("005930", period="D", count=10)
if not df.empty:
    print(f"   데이터 개수: {len(df)}개")
    print(f"   날짜 범위: {df['날짜'].min().strftime('%Y-%m-%d')} ~ {df['날짜'].max().strftime('%Y-%m-%d')}")
    print("\n   최근 5일 데이터:")
    print(df[['날짜', '시가', '고가', '저가', '종가', '거래량']].head())
else:
    print("   데이터 없음")

# 100개 이상 데이터 (배치 처리 테스트)
print("\n2. 최근 150일 일봉 데이터 (배치 처리):")
df2 = get_ohlcv_data("005930", period="D", count=150)
if not df2.empty:
    print(f"   데이터 개수: {len(df2)}개")
    print(f"   날짜 범위: {df2['날짜'].min().strftime('%Y-%m-%d')} ~ {df2['날짜'].max().strftime('%Y-%m-%d')}")
    print("\n   처음 5일 데이터:")
    print(df2[['날짜', '시가', '고가', '저가', '종가', '거래량']].head())
    print("\n   마지막 5일 데이터:")
    print(df2[['날짜', '시가', '고가', '저가', '종가', '거래량']].tail())
else:
    print("   데이터 없음")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)








