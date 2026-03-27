"""
kosdaq_code.mst 기반 증분 OHLCV 데이터 수집
기존 데이터와 병합하여 이어서 가져옵니다 (1997년부터 현재까지, 코스닥 전용)
"""
import os
import time
import pandas as pd
from datetime import datetime, timedelta
import kis_auth as ka
from parse_kosdaq_mst import get_stock_codes_from_mst_kosdaq
from get_ohlcv import get_ohlcv_data


def get_existing_data_info(output_dir, stock_code):
    """
    기존에 저장된 데이터의 날짜 범위 확인

    Args:
        output_dir: 데이터 저장 디렉토리
        stock_code: 종목 코드

    Returns:
        tuple: (가장 오래된 날짜, 가장 최신 날짜, 기존 DataFrame) 또는 (None, None, None)
    """
    output_file = os.path.join(output_dir, f"{stock_code}.csv")

    if os.path.exists(output_file):
        try:
            df = pd.read_csv(output_file, encoding="utf-8-sig")
            if not df.empty and "날짜" in df.columns:
                df["날짜"] = pd.to_datetime(df["날짜"])
                first_date = df["날짜"].min()
                last_date = df["날짜"].max()
                return first_date, last_date, df
        except Exception as e:
            print(f"  경고: 기존 파일 읽기 오류 ({stock_code}): {e}")

    return None, None, None


def get_ohlcv_data_incremental(stock_code, output_dir, period="D", delay=0.1):
    """
    증분 방식으로 OHLCV 데이터 조회 (기존 데이터와 병합)
    1997년부터 현재까지 데이터를 가져오되, 기존 데이터가 있으면 이어서 가져옵니다.

    Args:
        stock_code: 종목 코드
        output_dir: 데이터 저장 디렉토리
        period: 기간 구분 (D: 일봉)
        delay: API 호출 간 지연 시간

    Returns:
        tuple: (성공 여부, 가져온 데이터 개수)
    """
    # 1997년 1월 1일부터 시작
    start_date_1997 = datetime(1997, 1, 1)
    end_date_today = datetime.now()

    # 기존 데이터 확인
    first_date, last_date, existing_df = get_existing_data_info(output_dir, stock_code)

    try:
        all_new_data = []

        if first_date is None:
            # 기존 데이터가 없으면 1997년 1월 1일부터 시작
            current_start = start_date_1997
            print(f"  신규 종목, 1997-01-01부터 데이터 조회 시작")
        else:
            # 기존 데이터가 있으면 가장 오래된 날짜 이전부터 가져오기
            current_start = start_date_1997
            print(
                f"  기존 데이터 있음 (범위: {first_date.strftime('%Y-%m-%d')} ~ {last_date.strftime('%Y-%m-%d')})"
            )
            print(f"  {first_date.strftime('%Y-%m-%d')} 이전 데이터부터 이어서 조회")

        # 1997년부터 기존 데이터의 시작일자까지 (또는 현재까지) 순차적으로 가져오기
        target_end_date = first_date if first_date else end_date_today

        # API 제한: 한 번에 최대 100개
        max_per_call = 100
        batch_days = max_per_call
        max_iterations = 1000  # 무한 루프 방지
        iteration = 0

        print(
            f"    목표 날짜 범위: {current_start.strftime('%Y-%m-%d')} ~ {target_end_date.strftime('%Y-%m-%d')}"
        )

        while current_start < target_end_date and iteration < max_iterations:
            iteration += 1

            # 이번 배치의 종료일자
            batch_end = min(current_start + timedelta(days=batch_days - 1), target_end_date)

            # 시작일자가 종료일자와 같거나 넘어가면 중단
            if current_start >= target_end_date:
                break

            print(
                f"    [{iteration}] 배치 조회: {current_start.strftime('%Y-%m-%d')} ~ {batch_end.strftime('%Y-%m-%d')}"
            )

            # 배치 데이터 조회
            try:
                batch_df = get_ohlcv_data(
                    stock_code,
                    period=period,
                    count=batch_days,
                    start_date=current_start,
                    end_date=batch_end,
                    from_oldest=True,
                )
            except Exception as e:
                print(f"    오류 발생: {e}")
                break

            if batch_df.empty:
                # 데이터가 없으면 다음 배치로
                print(f"    데이터 없음, 다음 배치로 이동")
                current_start = batch_end + timedelta(days=1)
                # 더 이상 진행할 수 없으면 중단
                if current_start >= target_end_date:
                    break
                continue

            print(f"    가져온 데이터: {len(batch_df)}개")
            all_new_data.append(batch_df)

            # 다음 배치 시작일자 (가장 최신 날짜 다음날)
            if not batch_df.empty:
                batch_max_date = batch_df["날짜"].max()
                next_start = batch_max_date + timedelta(days=1)

                # 날짜가 진행되지 않으면 중단 (무한 루프 방지)
                if next_start <= current_start:
                    print(f"    경고: 날짜가 진행되지 않음, 중단")
                    break

                current_start = next_start
                print(f"    다음 시작일자: {current_start.strftime('%Y-%m-%d')}")
            else:
                current_start = batch_end + timedelta(days=1)

            # API 제한을 위한 지연
            time.sleep(delay)

            # 진행 상황 출력 (100일마다)
            days_fetched = (current_start - start_date_1997).days
            if days_fetched % 100 == 0:
                print(f"    진행: {days_fetched}일 수집 완료...")

        if iteration >= max_iterations:
            print(f"    경고: 최대 반복 횟수({max_iterations})에 도달했습니다.")

        # 기존 데이터 이후의 최신 데이터도 가져오기
        if last_date:
            days_since_last = (end_date_today - last_date).days
            if days_since_last > 1:
                print(f"  최신 데이터 업데이트: {last_date.strftime('%Y-%m-%d')} 이후 {days_since_last}일")
                latest_df = get_ohlcv_data(
                    stock_code,
                    period=period,
                    count=days_since_last + 10,
                    start_date=last_date + timedelta(days=1),
                    end_date=end_date_today,
                    from_oldest=True,
                )
                if not latest_df.empty:
                    all_new_data.append(latest_df)

        # 모든 데이터 병합
        if all_new_data:
            new_df = pd.concat(all_new_data, ignore_index=True)
            new_df = new_df.drop_duplicates(subset=["날짜"], keep="last")
            new_df = new_df.sort_values("날짜", ascending=True).reset_index(drop=True)
        else:
            return True, 0  # 새 데이터 없음

        # 기존 데이터와 병합
        if existing_df is not None and not existing_df.empty:
            # 중복 제거 (날짜 기준)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=["날짜"], keep="last")
            combined_df = combined_df.sort_values("날짜", ascending=True).reset_index(
                drop=True
            )  # 오래된 것부터
        else:
            combined_df = new_df

        # 파일 저장
        os.makedirs(output_dir, exist_ok=True)  # 디렉토리 생성
        output_file = os.path.join(output_dir, f"{stock_code}.csv")
        combined_df.to_csv(output_file, index=False, encoding="utf-8-sig")

        new_count = len(new_df)
        total_count = len(combined_df)
        return True, new_count

    except Exception as e:
        print(f"  오류: {e}")
        return False, 0


def get_all_kosdaq_ohlcv_incremental(output_dir="ohlcv_kosdaq", period="D", delay=0.1):
    """
    kosdaq_code.mst 파일의 모든 코스닥 종목에 대해 증분 OHLCV 데이터 수집

    Args:
        output_dir: 데이터 저장 디렉토리
        period: 기간 구분 (D: 일봉)
        delay: API 호출 간 지연 시간 (초)
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    # 인증
    print("인증 중...")
    ka.auth()

    # kosdaq_code.mst에서 종목 코드 추출
    print("kosdaq_code.mst 파일에서 코스닥 종목 코드 추출 중...")
    try:
        stock_codes = get_stock_codes_from_mst_kosdaq(".")
        print(f"총 {len(stock_codes)}개 코스닥 종목 코드를 추출했습니다.")
    except Exception as e:
        print(f"종목 코드 추출 실패: {e}")
        return

    if not stock_codes:
        print("종목 코드를 찾을 수 없습니다.")
        return

    print(f"\n총 {len(stock_codes)}개 코스닥 종목의 OHLCV 데이터를 증분 수집합니다.")
    print("기존 데이터가 있으면 마지막 날짜 이후부터, 없으면 1997년부터 가져옵니다.")
    print()

    # 통계
    success_count = 0
    fail_count = 0
    skip_count = 0
    new_data_count = 0
    failed_codes = []

    # 각 종목의 OHLCV 데이터 조회
    for idx, stock_code in enumerate(stock_codes, 1):
        print(f"[{idx}/{len(stock_codes)}] {stock_code}", end=" ")

        success, new_count = get_ohlcv_data_incremental(
            stock_code, output_dir, period=period, delay=0
        )

        if success:
            if new_count == 0:
                skip_count += 1
                print("✓ (스킵 - 최신 데이터)")
            else:
                success_count += 1
                new_data_count += new_count
                print(f"✓ ({new_count}개 새 데이터 추가)")
        else:
            fail_count += 1
            failed_codes.append(stock_code)
            print("✗ (실패)")

        # API 호출 제한을 위한 지연
        if idx < len(stock_codes):
            time.sleep(delay)

        # 진행 상황 출력 (100개마다)
        if idx % 100 == 0:
            print(f"\n진행 상황: {idx}/{len(stock_codes)} ({idx/len(stock_codes)*100:.1f}%)")
            print(
                f"성공: {success_count}, 스킵: {skip_count}, 실패: {fail_count}, 새 데이터: {new_data_count}개\n"
            )

    # 통합 파일 생성
    print("\n전체 데이터 통합 중...")
    all_data = []
    for stock_code in stock_codes:
        output_file = os.path.join(output_dir, f"{stock_code}.csv")
        if os.path.exists(output_file):
            try:
                df = pd.read_csv(output_file, encoding="utf-8-sig")
                if not df.empty:
                    all_data.append(df)
            except:
                pass

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_file = os.path.join(
            output_dir, f"all_kosdaq_ohlcv_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        combined_df.to_csv(combined_file, index=False, encoding="utf-8-sig")
        print(f"통합 파일 저장 완료: {combined_file}")
        print(f"총 {len(combined_df)}개 데이터")

    # 실패한 종목 코드 저장
    if failed_codes:
        failed_file = os.path.join(
            output_dir, f"failed_codes_kosdaq_{datetime.now().strftime('%Y%m%d')}.txt"
        )
        with open(failed_file, "w", encoding="utf-8") as f:
            for code in failed_codes:
                f.write(f"{code}\n")
        print(f"실패한 종목 코드 저장: {failed_file} ({len(failed_codes)}개)")

    # 결과 요약
    print("\n" + "=" * 60)
    print("코스닥 수집 완료!")
    print(f"성공: {success_count}개 종목 (새 데이터 추가)")
    print(f"스킵: {skip_count}개 종목 (이미 최신)")
    print(f"실패: {fail_count}개 종목")
    print(f"새로 추가된 데이터: {new_data_count}개")
    print(f"데이터 저장 위치: {os.path.abspath(output_dir)}")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="kosdaq_code.mst 기반 코스닥 증분 OHLCV 데이터 수집 (1997년부터)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="ohlcv_kosdaq",
        help="출력 디렉토리 (기본값: ohlcv_kosdaq)",
    )
    parser.add_argument(
        "--period",
        "-p",
        default="D",
        choices=["D", "W", "M", "Y"],
        help="기간 구분 (D: 일봉, W: 주봉, M: 월봉, Y: 연봉)",
    )
    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=0.1,
        help="API 호출 간 지연 시간(초) (기본값: 0.1)",
    )

    args = parser.parse_args()

    get_all_kosdaq_ohlcv_incremental(
        output_dir=args.output,
        period=args.period,
        delay=args.delay,
    )






