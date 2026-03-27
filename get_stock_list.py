"""
한국 주식 종목 목록 조회
"""
import os
import pandas as pd

def get_stock_list_from_file(file_path="stock_codes.txt"):
    """
    파일에서 종목 코드 목록 읽기
    
    Args:
        file_path: 종목 코드가 한 줄에 하나씩 적혀있는 텍스트 파일 경로
    
    Returns:
        DataFrame: 종목 코드가 포함된 데이터프레임
    """
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            codes = [line.strip() for line in f if line.strip()]
        stocks = [{"종목코드": code} for code in codes]
        return pd.DataFrame(stocks)
    return pd.DataFrame()

def get_major_stock_codes():
    """
    주요 종목 코드 반환 (코스피 + 코스닥)
    """
    # 코스피 주요 종목
    kospi_codes = [
        "005930", "000660", "035420", "035720", "051910", "006400", "005380", 
        "028260", "105560", "096770", "066570", "003550", "005490", "012330",
        "034730", "055550", "000270", "017670", "323410", "207940"
    ]
    
    # 코스닥 주요 종목
    kosdaq_codes = [
        "035720", "251270", "068270", "036570", "035900", "259960", "086790",
        "003670", "067160", "078340", "035760", "214420", "263750", "036460",
        "196170", "214150", "066970", "263720", "225570", "950210"
    ]
    
    all_codes = kospi_codes + kosdaq_codes
    stocks = [{"종목코드": code} for code in all_codes]
    return pd.DataFrame(stocks)

def get_all_stock_codes(use_file=True, file_path="stock_codes.txt"):
    """
    모든 주식 종목 코드 조회
    
    Args:
        use_file: 파일에서 종목 코드를 읽을지 여부
        file_path: 종목 코드 파일 경로
    
    Returns:
        DataFrame: 종목 코드가 포함된 데이터프레임
    """
    # 파일이 없거나 비어있는 경우 주요 종목 코드 사용
    if not use_file:
        print("주요 종목 코드를 사용합니다.")
        return get_major_stock_codes()
    
    try:
        df = get_stock_list_from_file(file_path)
        if not df.empty:
            print(f"파일에서 {len(df)}개 종목 코드를 읽었습니다.")
            return df
        else:
            print("파일이 비어있습니다. 주요 종목 코드를 사용합니다.")
            return get_major_stock_codes()
    except Exception as e:
        print(f"파일 읽기 오류 (무시하고 기본 종목 사용): {e}")
        print("주요 종목 코드를 사용합니다.")
        return get_major_stock_codes()

if __name__ == "__main__":
    # 종목 목록 조회
    print("종목 목록 조회 중...")
    stock_list = get_all_stock_codes()
    print(f"총 {len(stock_list)}개 종목")
    print(stock_list.head(20))

