"""
코스닥 OHLCV 증분 수집 실행 스크립트

사용법:
    py run_kosdaq_ohlcv.py

출력:
    기본 출력 디렉토리: ./ohlcv_kosdaq
"""
from get_ohlcv_incremental_kosdaq import get_all_kosdaq_ohlcv_incremental


def main():
    # 별도 옵션 없이 고정 경로로 실행
    output_dir = "ohlcv_kosdaq"
    period = "D"  # 일봉
    delay = 0.1

    get_all_kosdaq_ohlcv_incremental(
        output_dir=output_dir,
        period=period,
        delay=delay,
    )


if __name__ == "__main__":
    main()






