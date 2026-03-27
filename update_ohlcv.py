"""
OHLCV 데이터 경량 증분 업데이트
================================
- 기존 CSV의 마지막 날짜 이후 데이터만 API로 가져와서 추가
- 대시보드 분석 대상 종목 우선 업데이트
- 전체 CSV 업데이트도 지원 (--all-csv)

사용법:
  python update_ohlcv.py              # 대시보드 42개 종목만 업데이트
  python update_ohlcv.py --all-csv    # ohlcv_data 내 모든 CSV 업데이트
  python update_ohlcv.py --codes 005930 000660  # 특정 종목만
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kis_auth as ka
from get_ohlcv import get_ohlcv_data

# 대시보드 분석 대상 종목 (stock_dashboard.py의 TARGET_CODES와 동일)
TARGET_CODES = [
    "005930", "000660", "035420", "035720", "051910",
    "006400", "005380", "028260", "105560", "096770",
    "066570", "003550", "005490", "012330", "034730",
    "055550", "000270", "017670", "323410", "207940",
    "068270", "036570", "259960", "086790", "003670",
    "035760", "036460", "196170", "066970", "373220",
    "000810", "030200", "032640", "009150", "010130",
    "003490", "002790", "034020", "011200", "009540",
    "329180", "042700",
]


def get_last_date(csv_path):
    """CSV 파일의 마지막 날짜 반환"""
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig', usecols=['날짜'])
        if not df.empty:
            df['날짜'] = pd.to_datetime(df['날짜'])
            return df['날짜'].max()
    except Exception:
        pass
    return None


def update_stock(stock_code, output_dir="ohlcv_data"):
    """
    한 종목의 OHLCV 데이터 증분 업데이트

    Returns:
        tuple: (추가된 건수, 상태 메시지)
    """
    csv_path = os.path.join(output_dir, f"{stock_code}.csv")
    today = datetime.now()

    last_date = get_last_date(csv_path)

    if last_date is None:
        # CSV 없으면 최근 약 200거래일(300일) 데이터 가져오기
        start_date = today - timedelta(days=300)
        print(f"  신규: {start_date.strftime('%Y-%m-%d')}부터 수집")
    else:
        days_gap = (today - last_date).days
        if days_gap <= 0:
            return 0, "최신"
        # 주말/공휴일 고려: 갭이 1일(토요일 데이터가 금요일)이면 스킵
        # 월요일 아침에는 갭이 2-3일이지만 업데이트 필요
        if days_gap == 1 and today.weekday() == 6:  # 일요일이면 스킵
            return 0, "최신(주말)"
        start_date = last_date + timedelta(days=1)
        print(f"  갭: {days_gap}일 ({last_date.strftime('%Y-%m-%d')} → 오늘)")

    # API로 새 데이터 가져오기
    new_df = get_ohlcv_data(
        stock_code, period="D",
        count=500,
        start_date=start_date,
        end_date=today,
        from_oldest=True
    )

    if new_df is None or new_df.empty:
        return 0, "새 데이터 없음"

    # 기존 CSV와 병합
    if os.path.exists(csv_path):
        try:
            existing_df = pd.read_csv(csv_path, encoding='utf-8-sig')
            existing_df['날짜'] = pd.to_datetime(existing_df['날짜'])
            original_cols = existing_df.columns.tolist()
            prev_count = len(existing_df)

            # 기존 CSV 컬럼 기준으로 새 데이터에서 공통 컬럼만 선택
            common_cols = [c for c in original_cols if c in new_df.columns]

            combined = pd.concat(
                [existing_df[common_cols], new_df[common_cols]],
                ignore_index=True
            )
            combined = combined.drop_duplicates(subset=['날짜'], keep='last')
            combined = combined.sort_values('날짜').reset_index(drop=True)

            actually_added = len(combined) - prev_count
        except Exception as e:
            print(f"  기존 CSV 병합 오류: {e}, 새 데이터로 덮어씁니다")
            combined = new_df.sort_values('날짜').reset_index(drop=True)
            actually_added = len(combined)
    else:
        combined = new_df.sort_values('날짜').reset_index(drop=True)
        actually_added = len(combined)

    # 실제 새 데이터가 없으면 스킵
    if actually_added <= 0:
        return 0, "최신"

    # 저장
    os.makedirs(output_dir, exist_ok=True)
    combined.to_csv(csv_path, index=False, encoding='utf-8-sig')

    return actually_added, "업데이트 완료"


def update_all(stock_codes=None, output_dir="ohlcv_data", delay=0.1):
    """
    여러 종목 증분 업데이트

    Args:
        stock_codes: 종목 코드 리스트 (None이면 TARGET_CODES 사용)
        output_dir: 데이터 저장 디렉토리
        delay: API 호출 간 지연 시간 (초)
    """
    if stock_codes is None:
        stock_codes = TARGET_CODES

    print("KIS API 인증 중...")
    ka.auth()

    total = len(stock_codes)
    print(f"\n총 {total}개 종목 증분 업데이트 시작")
    print(f"데이터 디렉토리: {os.path.abspath(output_dir)}")
    print("=" * 55)

    updated = 0
    skipped = 0
    failed = 0
    total_added = 0

    for idx, code in enumerate(stock_codes, 1):
        code = str(code).zfill(6)
        print(f"[{idx}/{total}] {code}", end=" ")

        try:
            count, status = update_stock(code, output_dir)
            if count > 0:
                updated += 1
                total_added += count
                print(f"[OK] +{count}건")
            else:
                skipped += 1
                print(f"[SKIP] {status}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {e}")

        if idx < total:
            time.sleep(delay)

    print("\n" + "=" * 55)
    print(f"완료!")
    print(f"  업데이트: {updated}개 종목 (+{total_added}건)")
    print(f"  스킵(최신): {skipped}개 종목")
    print(f"  실패: {failed}개 종목")
    print("=" * 55)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='OHLCV 경량 증분 업데이트')
    parser.add_argument('--output', '-o', default='ohlcv_data',
                        help='데이터 디렉토리 (기본: ohlcv_data)')
    parser.add_argument('--all-csv', action='store_true',
                        help='ohlcv_data 내 모든 기존 CSV 업데이트')
    parser.add_argument('--codes', nargs='+',
                        help='특정 종목 코드만 업데이트 (예: 005930 000660)')
    parser.add_argument('--delay', '-d', type=float, default=0.1,
                        help='API 호출 간 지연 (초, 기본: 0.1)')

    args = parser.parse_args()

    if args.codes:
        codes = [c.zfill(6) for c in args.codes]
    elif args.all_csv:
        # 기존 CSV 파일에서 종목코드 추출
        codes = []
        if os.path.isdir(args.output):
            for f in os.listdir(args.output):
                if f.endswith('.csv') and len(f) == 10:  # 000000.csv
                    codes.append(f[:6])
        codes.sort()
        if not codes:
            print("업데이트할 CSV 파일이 없습니다.")
            sys.exit(1)
        print(f"기존 CSV {len(codes)}개 종목 전체 업데이트")
    else:
        codes = TARGET_CODES

    update_all(stock_codes=codes, output_dir=args.output, delay=args.delay)
