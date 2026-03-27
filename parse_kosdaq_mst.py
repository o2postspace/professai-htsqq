"""
코스닥 종목 마스터 파일 파싱
`kis_kosdaq_code_mst.py` 예제를 그대로 사용해 kosdaq_code.mst에서 종목 코드를 추출합니다.
"""
import os
import pandas as pd
from kis_kosdaq_code_mst import get_kosdaq_master_dataframe as _kis_get_kosdaq_master_dataframe


def get_kosdaq_master_dataframe(base_dir: str):
    """
    kosdaq_code.mst 파일을 파싱하여 DataFrame으로 변환

    내부적으로 `kis_kosdaq_code_mst.get_kosdaq_master_dataframe` 를 호출합니다.

    Args:
        base_dir: 파일이 있는 디렉토리 경로

    Returns:
        DataFrame: 종목 정보가 포함된 DataFrame
    """
    return _kis_get_kosdaq_master_dataframe(base_dir)


def get_stock_codes_from_mst_kosdaq(base_dir: str = "."):
    """
    kosdaq_code.mst 파일에서 종목 코드 목록 추출

    Args:
        base_dir: 파일이 있는 디렉토리 경로

    Returns:
        list: 종목 코드 리스트 (예: ['035720', '041510', ...])
    """
    df = get_kosdaq_master_dataframe(base_dir)

    # 단축코드가 6자리인 종목만 필터링 (일반 주식)
    stock_codes = df[df["단축코드"].str.len() == 6]["단축코드"].tolist()

    # 종목 코드를 6자리로 패딩
    stock_codes = [str(code).zfill(6) for code in stock_codes if code]

    return stock_codes


if __name__ == "__main__":
    # 테스트
    base_dir = os.getcwd()
    print(f"현재 디렉토리: {base_dir}")

    try:
        df = get_kosdaq_master_dataframe(base_dir)
        print(f"\n총 {len(df)}개 종목 정보를 읽었습니다.")
        print("\n처음 10개 종목:")
        # 원본 예제 기준 컬럼들만 출력
        print(df[["단축코드", "한글종목명"]].head(10))

        stock_codes = get_stock_codes_from_mst_kosdaq(base_dir)
        print(f"\n총 {len(stock_codes)}개 종목 코드 추출 완료")
        print(f"처음 10개: {stock_codes[:10]}")

    except FileNotFoundError as e:
        print(f"오류: {e}")
        print("kosdaq_code.mst 파일이 현재 디렉토리에 있는지 확인하세요.")


