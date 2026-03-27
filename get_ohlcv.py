"""
한국 주식 OHLCV 데이터 수집
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import kis_auth as ka

def get_ohlcv_data(stock_code, period="D", count=100, start_date=None, end_date=None, from_oldest=True):
    """
    주식 OHLCV 데이터 조회 (일봉)
    
    API 문서: https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
    - 한 번의 호출에 최대 100건까지 확인 가능
    - FID_INPUT_DATE_1: 조회 시작일자
    - FID_INPUT_DATE_2: 조회 종료일자
    
    Args:
        stock_code: 종목 코드 (6자리)
        period: 기간 구분 (D: 일봉, W: 주봉, M: 월봉, Y: 연봉) - 기본값: D(일봉)
        count: 조회할 데이터 개수 (최대 100개, 초과 시 자동으로 배치 처리)
        start_date: 시작 날짜 (datetime 객체, None이면 오늘부터)
        end_date: 종료 날짜 (datetime 객체, None이면 오늘)
        from_oldest: True면 오래된 것부터, False면 최신 것부터 (기본값: True)
    
    Returns:
        DataFrame: OHLCV 데이터 (날짜 오름차순 정렬)
    """
    auth = ka.get_auth()
    
    # 주식 일봉 차트 조회 API
    path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    tr_id = "FHKST03010100"
    
    # 날짜 설정
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date
    
    # API 제한: 한 번에 최대 100개
    max_per_call = 100
    all_data = []
    
    # 100개 이상이면 배치로 나눠서 가져오기
    remaining_count = count
    
    if from_oldest:
        # 오래된 것부터 순차적으로 가져오기
        current_start_date = start_date
        current_end_date = min(start_date + timedelta(days=max_per_call - 1), end_date)
    else:
        # 최신 것부터 역순으로 가져오기 (기존 방식)
        current_end_date = end_date
        current_start_date = max(end_date - timedelta(days=max_per_call - 1), start_date)
    
    max_iterations = 1000  # 무한 루프 방지
    iteration = 0
    
    while remaining_count > 0 and len(all_data) < count and iteration < max_iterations:
        iteration += 1
        
        # 이번 배치에서 가져올 개수
        batch_count = min(remaining_count, max_per_call)
        
        if from_oldest:
            # 오래된 것부터: 시작일자부터 100일씩
            batch_start = current_start_date
            batch_end = min(current_start_date + timedelta(days=batch_count - 1), end_date)
            
            # 다음 배치를 위한 시작일자 업데이트
            current_start_date = batch_end + timedelta(days=1)
        else:
            # 최신 것부터: 종료일자로부터 역산
            batch_end = current_end_date
            batch_start = max(current_end_date - timedelta(days=batch_count - 1), start_date)
            
            # 다음 배치를 위한 종료일자 업데이트
            current_end_date = batch_start - timedelta(days=1)
        
        # 날짜 형식 변환
        date_1 = batch_start.strftime("%Y%m%d")  # 조회 시작일자
        date_2 = batch_end.strftime("%Y%m%d")  # 조회 종료일자
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식시장
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": date_1,  # 조회 시작일자
            "FID_INPUT_DATE_2": date_2,  # 조회 종료일자
            "FID_PERIOD_DIV_CODE": period,  # D: 일봉
            "FID_ORG_ADJ_PRC": "0"  # 0: 수정주가, 1: 원주가
        }
    
        try:
            result = auth.api_call(path, tr_id, params)
            
            if result['rt_cd'] == '0':
                output = result.get('output2', [])
                if output:
                    df = pd.DataFrame(output)
                    
                    # 컬럼명 변경 및 데이터 타입 변환
                    if len(df) > 0:
                        df = df.rename(columns={
                            'stck_bsop_date': '날짜',
                            'stck_oprc': '시가',
                            'stck_hgpr': '고가',
                            'stck_lwpr': '저가',
                            'stck_clpr': '종가',
                            'acml_vol': '거래량',
                            'acml_tr_pbmn': '거래대금'
                        })
                        
                        # 날짜 형식 변환
                        df['날짜'] = pd.to_datetime(df['날짜'], format='%Y%m%d')
                        
                        # 숫자 형식 변환
                        numeric_cols = ['시가', '고가', '저가', '종가', '거래량', '거래대금']
                        for col in numeric_cols:
                            if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                        all_data.append(df)
                        remaining_count -= len(df)
                        
                        # 더 이상 가져올 데이터가 없으면 중단
                        if len(df) < batch_count:
                            break
                    else:
                        break
                else:
                    break
            else:
                print(f"오류 발생 ({stock_code}): {result.get('msg1', '알 수 없는 오류')}")
                break
                
        except Exception as e:
            print(f"OHLCV 데이터 조회 실패 ({stock_code}): {e}")
            break
        
        # 시작일자가 종료일자를 넘어가면 중단
        if from_oldest and current_start_date > end_date:
            break
        elif not from_oldest and current_end_date < start_date:
            break
    
    # 모든 배치 데이터 병합
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        # 중복 제거
        combined_df = combined_df.drop_duplicates(subset=['날짜'], keep='last')
        
        # 날짜 순으로 정렬 (오래된 것부터)
        combined_df = combined_df.sort_values('날짜', ascending=True).reset_index(drop=True)
        
        # 요청한 개수만큼만 반환
        if count > 0:
            combined_df = combined_df.head(count)
        
        return combined_df
    else:
        return pd.DataFrame()

def get_all_stocks_ohlcv(output_dir="ohlcv_data", period="D", count=100, delay=0.1, stock_file="stock_codes.txt", use_file=True):
    """
    모든 주식 종목의 OHLCV 데이터 수집
    
    Args:
        output_dir: 데이터 저장 디렉토리
        period: 기간 구분 (D: 일봉)
        count: 종목당 조회할 데이터 개수
        delay: API 호출 간 지연 시간 (초)
        stock_file: 종목 코드 파일 경로
        use_file: 파일에서 종목 코드를 읽을지 여부
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 인증
    print("인증 중...")
    ka.auth()
    
    # 종목 목록 조회
    print("종목 목록 조회 중...")
    stock_codes = None
    
    try:
        from get_stock_list import get_all_stock_codes as gsl_get_all
        stock_list = gsl_get_all(use_file=use_file, file_path=stock_file)
        
        if stock_list.empty:
            print("경고: 종목 목록이 비어있습니다. 주요 종목 코드를 사용합니다.")
            stock_codes = None
        elif '종목코드' in stock_list.columns:
            stock_codes = stock_list['종목코드'].tolist()
            print(f"종목 목록 조회 완료: {len(stock_codes)}개 종목")
        else:
            print(f"경고: '종목코드' 컬럼을 찾을 수 없습니다.")
            print(f"사용 가능한 컬럼: {stock_list.columns.tolist()}")
            stock_codes = None
    except Exception as e:
        import traceback
        print(f"종목 목록 조회 중 오류 발생: {e}")
        print("주요 종목 코드를 사용합니다.")
        traceback.print_exc()
        stock_codes = None
    
    # 종목 코드가 없으면 기본 종목 사용
    if stock_codes is None or len(stock_codes) == 0:
        print("주요 종목 코드를 사용합니다.")
        stock_codes = [
            "005930", "000660", "035420", "035720", "051910", "006400", "005380", 
            "028260", "105560", "096770", "066570", "003550", "005490", "012330",
            "034730", "055550", "000270", "017670", "323410", "207940",
            "251270", "068270", "036570", "035900", "259960", "086790",
            "003670", "067160", "078340", "035760", "214420", "263750", "036460",
            "196170", "214150", "066970", "263720", "225570", "950210"
        ]
    
    print(f"총 {len(stock_codes)}개 종목의 OHLCV 데이터를 수집합니다.")
    
    # 전체 데이터를 저장할 리스트
    all_data = []
    success_count = 0
    fail_count = 0
    
    # 각 종목의 OHLCV 데이터 조회
    for idx, stock_code in enumerate(stock_codes, 1):
        # 종목 코드를 6자리 문자열로 변환
        stock_code_str = str(stock_code).zfill(6)
        
        print(f"[{idx}/{len(stock_codes)}] {stock_code_str} 조회 중...", end=" ")
        
        try:
            df = get_ohlcv_data(stock_code_str, period=period, count=count)
            
            if not df.empty:
                # 종목 코드 추가
                df['종목코드'] = stock_code_str
                
                # 개별 파일로 저장
                output_file = os.path.join(output_dir, f"{stock_code_str}.csv")
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                # 전체 데이터에 추가
                all_data.append(df)
                
                success_count += 1
                print(f"✓ ({len(df)}개 데이터)")
            else:
                fail_count += 1
                print("✗ (데이터 없음)")
                
        except Exception as e:
            fail_count += 1
            print(f"✗ (오류: {e})")
        
        # API 호출 제한을 위한 지연
        if idx < len(stock_codes):
            time.sleep(delay)
    
    # 전체 데이터를 하나의 파일로 저장
    if all_data:
        print("\n전체 데이터 통합 중...")
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = os.path.join(output_dir, f"all_stocks_ohlcv_{datetime.now().strftime('%Y%m%d')}.csv")
        combined_df.to_csv(combined_file, index=False, encoding='utf-8-sig')
        print(f"통합 파일 저장 완료: {combined_file}")
        print(f"총 {len(combined_df)}개 데이터")
    
    # 결과 요약
    print("\n" + "="*50)
    print("수집 완료!")
    print(f"성공: {success_count}개 종목")
    print(f"실패: {fail_count}개 종목")
    print(f"데이터 저장 위치: {os.path.abspath(output_dir)}")
    print("="*50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='한국 주식 OHLCV 데이터 수집')
    parser.add_argument('--output', '-o', default='ohlcv_data', help='출력 디렉토리 (기본값: ohlcv_data)')
    parser.add_argument('--period', '-p', default='D', choices=['D', 'W', 'M', 'Y'], 
                       help='기간 구분 (D: 일봉, W: 주봉, M: 월봉, Y: 연봉)')
    parser.add_argument('--count', '-c', type=int, default=100, help='종목당 조회할 데이터 개수 (기본값: 100)')
    parser.add_argument('--delay', '-d', type=float, default=0.1, help='API 호출 간 지연 시간(초) (기본값: 0.1)')
    parser.add_argument('--stock-file', '-f', default='stock_codes.txt', help='종목 코드 파일 경로 (기본값: stock_codes.txt)')
    parser.add_argument('--no-file', action='store_true', help='파일을 사용하지 않고 주요 종목만 조회')
    
    args = parser.parse_args()
    
    get_all_stocks_ohlcv(
        output_dir=args.output,
        period=args.period,
        count=args.count,
        delay=args.delay,
        stock_file=args.stock_file,
        use_file=not args.no_file
    )

