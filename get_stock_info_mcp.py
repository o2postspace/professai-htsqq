"""
MCP를 사용한 주식 시세 조회
한국투자증권 Open API MCP를 활용하여 주가 정보를 가져옵니다.
"""
import kis_auth as ka
import pandas as pd

def get_stock_info(code):
    """
    삼성전자 주가 정보를 가져오는 함수 (MCP 기반)
    
    Args:
        code: 종목 코드 (예: "005930" - 삼성전자)
    
    Returns:
        dict: 주가 정보 딕셔너리
    """
    auth = ka.get_auth()
    
    # 주식현재가 시세 조회 API (MCP에서 추천한 API)
    path = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",  # J: 주식, Q: 코스닥
        "FID_INPUT_ISCD": code  # 종목코드
    }
    
    try:
        result = auth.api_call(path, tr_id, params)
        
        if result['rt_cd'] == '0':
            output = result.get('output', {})
            
            # 주가 정보 정리 (문자열을 숫자로 안전하게 변환)
            def safe_int(value, default=0):
                try:
                    return int(float(str(value).replace(',', '')))
                except (ValueError, TypeError):
                    return default
            
            def safe_float(value, default=0.0):
                try:
                    return float(str(value).replace(',', ''))
                except (ValueError, TypeError):
                    return default
            
            stock_info = {
                '종목코드': code,
                '종목명': output.get('hts_kor_isnm', ''),
                '현재가': safe_int(output.get('stck_prpr', 0)),
                '전일대비': safe_int(output.get('prdy_vrss', 0)),
                '전일대비율': safe_float(output.get('prdy_ctrt', 0)),
                '시가': safe_int(output.get('stck_oprc', 0)),
                '고가': safe_int(output.get('stck_hgpr', 0)),
                '저가': safe_int(output.get('stck_lwpr', 0)),
                '거래량': safe_int(output.get('acml_vol', 0)),
                '거래대금': safe_int(output.get('acml_tr_pbmn', 0)),
                '시가총액': safe_int(output.get('hts_avls', 0)),
                'PER': safe_float(output.get('per', 0)),
                'EPS': safe_int(output.get('eps', 0)),
                'PBR': safe_float(output.get('pbr', 0)),
                '업종명': output.get('hts_kor_isnm', ''),
            }
            
            return stock_info
        else:
            print(f"오류 발생: {result.get('msg1', '알 수 없는 오류')}")
            return None
            
    except Exception as e:
        print(f"주가 정보 조회 실패: {e}")
        return None

def get_stock_info_pretty(code):
    """
    주가 정보를 보기 좋게 출력
    
    Args:
        code: 종목 코드
    """
    info = get_stock_info(code)
    
    if info:
        print("=" * 60)
        print(f"종목명: {info['종목명']} ({info['종목코드']})")
        print("=" * 60)
        print(f"현재가: {info['현재가']:,}원")
        
        change = info['전일대비']
        change_rate = info['전일대비율']
        if change > 0:
            print(f"전일대비: +{change:,}원 (+{change_rate:.2f}%)")
        elif change < 0:
            print(f"전일대비: {change:,}원 ({change_rate:.2f}%)")
        else:
            print(f"전일대비: {change:,}원 ({change_rate:.2f}%)")
        
        print(f"\n시가: {info['시가']:,}원")
        print(f"고가: {info['고가']:,}원")
        print(f"저가: {info['저가']:,}원")
        print(f"\n거래량: {info['거래량']:,}주")
        print(f"거래대금: {info['거래대금']:,}원")
        print(f"시가총액: {info['시가총액']:,}원")
        print(f"\nPER: {info['PER']:.2f}")
        print(f"EPS: {info['EPS']:,}원")
        print(f"PBR: {info['PBR']:.2f}")
        print("=" * 60)
        
        return info
    else:
        print("주가 정보를 가져올 수 없습니다.")
        return None

if __name__ == "__main__":
    # 인증
    print("인증 중...")
    ka.auth()
    
    # 삼성전자 주가 정보 조회
    print("\n삼성전자 주가 정보 조회 중...")
    get_stock_info_pretty("005930")
    
    # 다른 종목도 테스트
    print("\n\nSK하이닉스 주가 정보 조회 중...")
    get_stock_info_pretty("000660")

