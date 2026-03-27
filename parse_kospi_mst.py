"""
코스피 종목 마스터 파일 파싱
kospi_code.mst 파일에서 종목 코드를 추출합니다.
"""
import os
import pandas as pd

def get_kospi_master_dataframe(base_dir):
    """
    kospi_code.mst 파일을 파싱하여 DataFrame으로 변환
    
    Args:
        base_dir: 파일이 있는 디렉토리 경로
    
    Returns:
        DataFrame: 종목 정보가 포함된 DataFrame
    """
    file_name = os.path.join(base_dir, "kospi_code.mst")
    
    if not os.path.exists(file_name):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_name}")
    
    tmp_fil1 = os.path.join(base_dir, "kospi_code_part1.tmp")
    tmp_fil2 = os.path.join(base_dir, "kospi_code_part2.tmp")

    wf1 = open(tmp_fil1, mode="w", encoding="utf-8")
    wf2 = open(tmp_fil2, mode="w", encoding="utf-8")

    with open(file_name, mode="r", encoding="cp949") as f:
        for row in f:
            rf1 = row[0:len(row) - 228]
            rf1_1 = rf1[0:9].rstrip()
            rf1_2 = rf1[9:21].rstrip()
            rf1_3 = rf1[21:].strip()
            wf1.write(rf1_1 + ',' + rf1_2 + ',' + rf1_3 + '\n')
            rf2 = row[-228:]
            wf2.write(rf2)

    wf1.close()
    wf2.close()

    part1_columns = ['단축코드', '표준코드', '한글명']
    df1 = pd.read_csv(tmp_fil1, header=None, names=part1_columns, encoding='utf-8')

    field_specs = [2, 1, 4, 4, 4,
                   1, 1, 1, 1, 1,
                   1, 1, 1, 1, 1,
                   1, 1, 1, 1, 1,
                   1, 1, 1, 1, 1,
                   1, 1, 1, 1, 1,
                   1, 9, 5, 5, 1,
                   1, 1, 2, 1, 1,
                   1, 2, 2, 2, 3,
                   1, 3, 12, 12, 8,
                   15, 21, 2, 7, 1,
                   1, 1, 1, 1, 9,
                   9, 9, 5, 9, 8,
                   9, 3, 1, 1, 1
                   ]

    part2_columns = ['그룹코드', '시가총액규모', '지수업종대분류', '지수업종중분류', '지수업종소분류',
                     '제조업', '저유동성', '지배구조지수종목', 'KOSPI200섹터업종', 'KOSPI100',
                     'KOSPI50', 'KRX', 'ETP', 'ELW발행', 'KRX100',
                     'KRX자동차', 'KRX반도체', 'KRX바이오', 'KRX은행', 'SPAC',
                     'KRX에너지화학', 'KRX철강', '단기과열', 'KRX미디어통신', 'KRX건설',
                     'Non1', 'KRX증권', 'KRX선박', 'KRX섹터_보험', 'KRX섹터_운송',
                     'SRI', '기준가', '매매수량단위', '시간외수량단위', '거래정지',
                     '정리매매', '관리종목', '시장경고', '경고예고', '불성실공시',
                     '우회상장', '락구분', '액면변경', '증자구분', '증거금비율',
                     '신용가능', '신용기간', '전일거래량', '액면가', '상장일자',
                     '상장주수', '자본금', '결산월', '공모가', '우선주',
                     '공매도과열', '이상급등', 'KRX300', 'KOSPI', '매출액',
                     '영업이익', '경상이익', '당기순이익', 'ROE', '기준년월',
                     '시가총액', '그룹사코드', '회사신용한도초과', '담보대출가능', '대주가능'
                     ]

    df2 = pd.read_fwf(tmp_fil2, widths=field_specs, names=part2_columns)

    df = pd.merge(df1, df2, how='outer', left_index=True, right_index=True)

    # 임시 파일 삭제
    if os.path.exists(tmp_fil1):
        os.remove(tmp_fil1)
    if os.path.exists(tmp_fil2):
        os.remove(tmp_fil2)
    
    return df

def get_stock_codes_from_mst(base_dir="."):
    """
    kospi_code.mst 파일에서 종목 코드 목록 추출
    
    Args:
        base_dir: 파일이 있는 디렉토리 경로
    
    Returns:
        list: 종목 코드 리스트 (예: ['005930', '000660', ...])
    """
    df = get_kospi_master_dataframe(base_dir)
    
    # 단축코드가 6자리인 종목만 필터링 (일반 주식)
    stock_codes = df[df['단축코드'].str.len() == 6]['단축코드'].tolist()
    
    # 종목 코드를 6자리로 패딩
    stock_codes = [str(code).zfill(6) for code in stock_codes if code]
    
    return stock_codes

if __name__ == "__main__":
    # 테스트
    base_dir = os.getcwd()
    print(f"현재 디렉토리: {base_dir}")
    
    try:
        df = get_kospi_master_dataframe(base_dir)
        print(f"\n총 {len(df)}개 종목 정보를 읽었습니다.")
        print("\n처음 10개 종목:")
        print(df[['단축코드', '한글명', 'KRX', '기준가']].head(10))
        
        stock_codes = get_stock_codes_from_mst(base_dir)
        print(f"\n총 {len(stock_codes)}개 종목 코드 추출 완료")
        print(f"처음 10개: {stock_codes[:10]}")
        
    except FileNotFoundError as e:
        print(f"오류: {e}")
        print("kospi_code.mst 파일이 현재 디렉토리에 있는지 확인하세요.")








