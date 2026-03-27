"""
종목 목록 조회 테스트
"""
import get_stock_list as gsl

print("=" * 50)
print("종목 목록 조회 테스트")
print("=" * 50)

# 파일에서 읽기 테스트
print("\n1. 파일에서 종목 코드 읽기 테스트")
stock_list = gsl.get_all_stock_codes(use_file=True, file_path="stock_codes.txt")
print(f"결과: {len(stock_list)}개 종목")
if not stock_list.empty:
    print(stock_list.head())

# 주요 종목 코드 테스트
print("\n2. 주요 종목 코드 테스트")
stock_list = gsl.get_all_stock_codes(use_file=False)
print(f"결과: {len(stock_list)}개 종목")
if not stock_list.empty:
    print(stock_list.head())

print("\n테스트 완료!")








