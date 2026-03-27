"""
증분 수집 테스트
"""
import os
import pandas as pd
from datetime import datetime
from get_ohlcv_incremental import get_ohlcv_data_incremental

# 테스트용 디렉토리
test_dir = "test_ohlcv"

# 기존 데이터 확인
stock_code = "000020"
output_file = os.path.join(test_dir, f"{stock_code}.csv")

if os.path.exists(output_file):
    df = pd.read_csv(output_file, encoding='utf-8-sig')
    df['날짜'] = pd.to_datetime(df['날짜'])
    print(f"기존 데이터:")
    print(f"  파일: {output_file}")
    print(f"  데이터 개수: {len(df)}개")
    print(f"  날짜 범위: {df['날짜'].min().strftime('%Y-%m-%d')} ~ {df['날짜'].max().strftime('%Y-%m-%d')}")
    print(f"  가장 오래된 날짜: {df['날짜'].min().strftime('%Y-%m-%d')}")
    print(f"  가장 최신 날짜: {df['날짜'].max().strftime('%Y-%m-%d')}")
else:
    print(f"기존 데이터 없음: {output_file}")

print("\n증분 수집 테스트 시작...")
success, new_count = get_ohlcv_data_incremental(stock_code, test_dir, period="D", delay=0.1)

if success:
    print(f"\n성공! 새로 추가된 데이터: {new_count}개")
    
    # 결과 확인
    if os.path.exists(output_file):
        df_new = pd.read_csv(output_file, encoding='utf-8-sig')
        df_new['날짜'] = pd.to_datetime(df_new['날짜'])
        print(f"\n업데이트된 데이터:")
        print(f"  데이터 개수: {len(df_new)}개")
        print(f"  날짜 범위: {df_new['날짜'].min().strftime('%Y-%m-%d')} ~ {df_new['날짜'].max().strftime('%Y-%m-%d')}")
        print(f"  가장 오래된 날짜: {df_new['날짜'].min().strftime('%Y-%m-%d')}")
        print(f"  가장 최신 날짜: {df_new['날짜'].max().strftime('%Y-%m-%d')}")
else:
    print("\n실패")








