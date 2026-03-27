"""
kospi_code.mst 파일 기반 OHLCV 데이터 수집
"""
import os
import time
import pandas as pd
from datetime import datetime
import kis_auth as ka
from parse_kospi_mst import get_stock_codes_from_mst
from get_ohlcv import get_ohlcv_data

def get_all_kospi_ohlcv(output_dir="ohlcv_data", period="D", count=100, delay=0.1):
    """
    kospi_code.mst 파일의 모든 종목에 대해 OHLCV 데이터 수집
    
    Args:
        output_dir: 데이터 저장 디렉토리
        period: 기간 구분 (D: 일봉, W: 주봉, M: 월봉, Y: 연봉)
        count: 종목당 조회할 데이터 개수
        delay: API 호출 간 지연 시간 (초)
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 인증
    print("인증 중...")
    ka.auth()
    
    # kospi_code.mst에서 종목 코드 추출
    print("kospi_code.mst 파일에서 종목 코드 추출 중...")
    try:
        stock_codes = get_stock_codes_from_mst()
        print(f"총 {len(stock_codes)}개 종목 코드를 추출했습니다.")
    except Exception as e:
        print(f"종목 코드 추출 실패: {e}")
        return
    
    if not stock_codes:
        print("종목 코드를 찾을 수 없습니다.")
        return
    
    print(f"총 {len(stock_codes)}개 종목의 OHLCV 데이터를 수집합니다.")
    print(f"예상 소요 시간: 약 {len(stock_codes) * delay / 60:.1f}분")
    print()
    
    # 전체 데이터를 저장할 리스트
    all_data = []
    success_count = 0
    fail_count = 0
    failed_codes = []
    
    # 각 종목의 OHLCV 데이터 조회
    for idx, stock_code in enumerate(stock_codes, 1):
        print(f"[{idx}/{len(stock_codes)}] {stock_code} 조회 중...", end=" ")
        
        try:
            df = get_ohlcv_data(stock_code, period=period, count=count)
            
            if not df.empty:
                # 종목 코드 추가
                df['종목코드'] = stock_code
                
                # 개별 파일로 저장
                output_file = os.path.join(output_dir, f"{stock_code}.csv")
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                # 전체 데이터에 추가
                all_data.append(df)
                
                success_count += 1
                print(f"✓ ({len(df)}개 데이터)")
            else:
                fail_count += 1
                failed_codes.append(stock_code)
                print("✗ (데이터 없음)")
                
        except Exception as e:
            fail_count += 1
            failed_codes.append(stock_code)
            print(f"✗ (오류: {str(e)[:50]})")
        
        # API 호출 제한을 위한 지연
        if idx < len(stock_codes):
            time.sleep(delay)
        
        # 진행 상황 출력 (100개마다)
        if idx % 100 == 0:
            print(f"\n진행 상황: {idx}/{len(stock_codes)} ({idx/len(stock_codes)*100:.1f}%)")
            print(f"성공: {success_count}, 실패: {fail_count}\n")
    
    # 전체 데이터를 하나의 파일로 저장
    if all_data:
        print("\n전체 데이터 통합 중...")
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = os.path.join(output_dir, f"all_kospi_ohlcv_{datetime.now().strftime('%Y%m%d')}.csv")
        combined_df.to_csv(combined_file, index=False, encoding='utf-8-sig')
        print(f"통합 파일 저장 완료: {combined_file}")
        print(f"총 {len(combined_df)}개 데이터")
    
    # 실패한 종목 코드 저장
    if failed_codes:
        failed_file = os.path.join(output_dir, f"failed_codes_{datetime.now().strftime('%Y%m%d')}.txt")
        with open(failed_file, 'w', encoding='utf-8') as f:
            for code in failed_codes:
                f.write(f"{code}\n")
        print(f"실패한 종목 코드 저장: {failed_file} ({len(failed_codes)}개)")
    
    # 결과 요약
    print("\n" + "="*50)
    print("수집 완료!")
    print(f"성공: {success_count}개 종목")
    print(f"실패: {fail_count}개 종목")
    print(f"데이터 저장 위치: {os.path.abspath(output_dir)}")
    print("="*50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='kospi_code.mst 기반 OHLCV 데이터 수집')
    parser.add_argument('--output', '-o', default='ohlcv_data', help='출력 디렉토리 (기본값: ohlcv_data)')
    parser.add_argument('--period', '-p', default='D', choices=['D', 'W', 'M', 'Y'], 
                       help='기간 구분 (D: 일봉, W: 주봉, M: 월봉, Y: 연봉)')
    parser.add_argument('--count', '-c', type=int, default=100, help='종목당 조회할 데이터 개수 (기본값: 100)')
    parser.add_argument('--delay', '-d', type=float, default=0.1, help='API 호출 간 지연 시간(초) (기본값: 0.1)')
    
    args = parser.parse_args()
    
    get_all_kospi_ohlcv(
        output_dir=args.output,
        period=args.period,
        count=args.count,
        delay=args.delay
    )








