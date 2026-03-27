"""
간단한 테스트 - 한 종목만
"""
import kis_auth as ka
from get_ohlcv_incremental import get_ohlcv_data_incremental

print("인증 중...")
ka.auth()

print("\n삼성전자 증분 수집 테스트 (5개 배치만)")
print("=" * 60)

# 테스트: 작은 배치만
success, new_count = get_ohlcv_data_incremental(
    "005930", 
    "test_ohlcv", 
    period="D", 
    delay=0.1
)

print(f"\n결과: 성공={success}, 새 데이터={new_count}개")








