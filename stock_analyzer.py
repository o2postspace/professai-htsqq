"""
한국투자증권 API를 이용한 기술적 분석 종목 추천 시스템
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- OBV (On Balance Volume)
"""
import os
import sys
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kis_auth as ka
from get_ohlcv import get_ohlcv_data


# ============================================================
# 기술적 지표 계산 함수
# ============================================================

def calc_rsi(series, period=14):
    """RSI 계산"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(series, fast=12, slow=26, signal=9):
    """MACD 계산 -> (macd_line, signal_line, histogram)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_obv(close, volume):
    """OBV 계산"""
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)


# ============================================================
# 종목별 기술적 점수 산정
# ============================================================

def score_stock(df):
    """
    기술적 지표 기반 종목 점수 산정 (0~100)

    점수 기준:
    - RSI (40점): 과매도 반등 구간(30~50) 최고점, 과매수(>70) 감점
    - MACD (35점): 골든크로스 + 히스토그램 상승 시 가점
    - OBV (25점): OBV 상승 추세 시 가점
    """
    if df is None or len(df) < 30:
        return None

    close = df['종가']
    volume = df['거래량']

    # RSI
    rsi = calc_rsi(close)
    current_rsi = rsi.iloc[-1]

    # MACD
    macd_line, signal_line, histogram = calc_macd(close)
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_hist = histogram.iloc[-1]
    prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0

    # OBV
    obv = calc_obv(close, volume)
    obv_sma20 = obv.rolling(20).mean()

    # ---------- RSI 점수 (40점 만점) ----------
    rsi_score = 0
    if 30 <= current_rsi <= 50:
        rsi_score = 40  # 과매도 반등 구간 -> 최고
    elif 50 < current_rsi <= 60:
        rsi_score = 30
    elif 20 <= current_rsi < 30:
        rsi_score = 25  # 과매도(매수 기회지만 리스크)
    elif 60 < current_rsi <= 70:
        rsi_score = 15
    elif current_rsi > 70:
        rsi_score = 5   # 과매수 -> 감점
    elif current_rsi < 20:
        rsi_score = 10  # 극단적 과매도

    # ---------- MACD 점수 (35점 만점) ----------
    macd_score = 0
    # 골든크로스 (MACD > Signal)
    if current_macd > current_signal:
        macd_score += 15
    # 히스토그램 양수 & 상승 중
    if current_hist > 0:
        macd_score += 10
    if current_hist > prev_hist:
        macd_score += 10

    # ---------- OBV 점수 (25점 만점) ----------
    obv_score = 0
    if len(obv_sma20.dropna()) > 0:
        current_obv = obv.iloc[-1]
        current_obv_sma = obv_sma20.iloc[-1]
        if not np.isnan(current_obv_sma):
            # OBV가 20일 이평선 위
            if current_obv > current_obv_sma:
                obv_score += 15
            # OBV 최근 5일 상승 추세
            if len(obv) >= 5:
                recent_obv = obv.iloc[-5:]
                if recent_obv.iloc[-1] > recent_obv.iloc[0]:
                    obv_score += 10

    total = rsi_score + macd_score + obv_score

    return {
        'total_score': total,
        'rsi_score': rsi_score,
        'macd_score': macd_score,
        'obv_score': obv_score,
        'rsi': round(current_rsi, 2),
        'macd': round(current_macd, 2),
        'macd_signal': round(current_signal, 2),
        'macd_hist': round(current_hist, 2),
        'close': int(close.iloc[-1]),
        'volume': int(volume.iloc[-1]),
    }


# ============================================================
# 종목명 딕셔너리 (주요 종목)
# ============================================================

STOCK_NAMES = {
    "005930": "삼성전자", "000660": "SK하이닉스", "035420": "NAVER",
    "035720": "카카오", "051910": "LG화학", "006400": "삼성SDI",
    "005380": "현대차", "028260": "삼성물산", "105560": "KB금융",
    "096770": "SK이노베이션", "066570": "LG전자", "003550": "LG",
    "005490": "POSCO홀딩스", "012330": "현대모비스", "034730": "SK",
    "055550": "신한지주", "000270": "기아", "017670": "SK텔레콤",
    "323410": "카카오뱅크", "207940": "삼성바이오로직스",
    "251270": "넷마블", "068270": "셀트리온", "036570": "엔씨소프트",
    "035900": "JYP Ent.", "259960": "크래프톤", "086790": "하나금융지주",
    "003670": "포스코퓨처엠", "067160": "아프리카TV", "078340": "컴투스",
    "035760": "CJ ENM", "214420": "토니모리", "263750": "펄어비스",
    "036460": "한국가스공사", "196170": "알테오젠", "214150": "클래시스",
    "066970": "엘앤에프", "263720": "디앤씨미디어", "225570": "넥슨게임즈",
    "950210": "프레스티지바이오파마",
    "373220": "LG에너지솔루션", "000810": "삼성화재", "030200": "KT",
    "032640": "LG유플러스", "009150": "삼성전기", "010130": "고려아연",
    "003490": "대한항공", "002790": "아모레퍼시픽", "090430": "아모레G",
    "034020": "두산에너빌리티", "011200": "HMM", "009540": "한국조선해양",
    "329180": "HD현대중공업", "042700": "한미반도체",
}


# ============================================================
# 포트폴리오 조회
# ============================================================

def get_portfolio(auth_obj):
    """계좌 잔고 조회"""
    path = "/uapi/domestic-stock/v1/trading/inquire-balance"
    tr_id = "TTTC8434R" if auth_obj.svr == 'prod' else "VTTC8434R"

    params = {
        "CANO": auth_obj.account_no,
        "ACNT_PRDT_CD": auth_obj.account_product,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    try:
        result = auth_obj.api_call(path, tr_id, params)
        if result.get('rt_cd') == '0':
            return result
        else:
            print(f"포트폴리오 조회 실패: {result.get('msg1', '알 수 없는 오류')}")
            return None
    except Exception as e:
        print(f"포트폴리오 조회 오류: {e}")
        return None


def display_portfolio(portfolio_data):
    """포트폴리오 출력"""
    if not portfolio_data:
        print("포트폴리오 데이터가 없습니다.")
        return

    print("\n" + "=" * 80)
    print("  나의 포트폴리오 (계좌 잔고)")
    print("=" * 80)

    # 보유 종목
    holdings = portfolio_data.get('output1', [])
    if holdings:
        print(f"\n{'종목명':<16} {'종목코드':<10} {'보유수량':>8} {'매입평균가':>12} "
              f"{'현재가':>10} {'평가손익':>14} {'수익률':>8}")
        print("-" * 80)

        for item in holdings:
            hldg_qty = int(item.get('hldg_qty', 0))
            if hldg_qty == 0:
                continue
            name = item.get('prdt_name', '?')
            code = item.get('pdno', '?')
            avg_price = int(item.get('pchs_avg_pric', 0).split('.')[0]) if '.' in str(item.get('pchs_avg_pric', 0)) else int(item.get('pchs_avg_pric', 0))
            current_price = int(item.get('prpr', 0))
            eval_pl = int(item.get('evlu_pfls_amt', 0))
            pl_rate = float(item.get('evlu_pfls_rt', 0))

            pl_sign = "+" if eval_pl >= 0 else ""
            print(f"{name:<16} {code:<10} {hldg_qty:>8,} {avg_price:>12,}원 "
                  f"{current_price:>10,}원 {pl_sign}{eval_pl:>13,}원 {pl_sign}{pl_rate:>6.2f}%")

    else:
        print("\n  보유 종목이 없습니다.")

    # 계좌 요약
    output2 = portfolio_data.get('output2', [])
    if output2:
        summary = output2[0] if isinstance(output2, list) else output2
        total_eval = int(summary.get('tot_evlu_amt', 0))
        total_purchase = int(summary.get('pchs_amt_smtl_amt', 0))
        total_pl = int(summary.get('evlu_pfls_smtl_amt', 0))
        deposit = int(summary.get('dnca_tot_amt', 0))

        print("\n" + "-" * 80)
        print(f"  예수금(현금):       {deposit:>15,}원")
        print(f"  총 매입금액:        {total_purchase:>15,}원")
        print(f"  총 평가금액:        {total_eval:>15,}원")
        pl_sign = "+" if total_pl >= 0 else ""
        print(f"  총 평가손익:        {pl_sign}{total_pl:>14,}원")
        if total_purchase > 0:
            total_rate = (total_pl / total_purchase) * 100
            print(f"  총 수익률:          {pl_sign}{total_rate:>14.2f}%")
    print("=" * 80)


# ============================================================
# 현재가 조회
# ============================================================

def get_current_price(auth_obj, stock_code):
    """현재가 조회"""
    path = "/uapi/domestic-stock/v1/quotations/inquire-price"
    tr_id = "FHKST01010100"
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
    }
    try:
        result = auth_obj.api_call(path, tr_id, params)
        if result.get('rt_cd') == '0':
            output = result.get('output', {})
            return {
                'name': output.get('hts_kor_isnm', STOCK_NAMES.get(stock_code, stock_code)),
                'price': int(output.get('stck_prpr', 0)),
                'change': int(output.get('prdy_vrss', 0)),
                'change_rate': float(output.get('prdy_ctrt', 0)),
                'volume': int(output.get('acml_vol', 0)),
                'market_cap': int(output.get('hts_avls', 0)),  # 시가총액(억)
            }
    except Exception:
        pass
    return None


# ============================================================
# 메인 분석 로직
# ============================================================

def analyze_stocks():
    """주요 종목 기술적 분석 실행"""

    print("=" * 80)
    print("  한국투자증권 기술적 분석 종목 추천 시스템")
    print("  지표: RSI + MACD + OBV")
    print(f"  분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1) 인증
    print("\n[1/4] 한국투자증권 API 인증 중...")
    try:
        auth_obj = ka.auth()
        print("  인증 성공!")
    except Exception as e:
        print(f"  인증 실패: {e}")
        return

    # 2) 포트폴리오 조회
    print("\n[2/4] 포트폴리오 조회 중...")
    portfolio = get_portfolio(auth_obj)
    display_portfolio(portfolio)

    # 3) 종목 분석
    print("\n[3/4] 주요 종목 기술적 분석 중...")

    # 분석 대상 종목 (코스피 + 코스닥 주요 50개)
    target_codes = [
        "005930", "000660", "035420", "035720", "051910",
        "006400", "005380", "028260", "105560", "096770",
        "066570", "003550", "005490", "012330", "034730",
        "055550", "000270", "017670", "323410", "207940",
        "068270", "036570", "259960", "086790", "003670",
        "035760", "036460", "196170", "066970",
        "373220", "000810", "030200", "032640", "009150",
        "010130", "003490", "002790", "034020", "011200",
        "009540", "329180", "042700",
    ]

    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=250)  # 약 200 거래일

    for idx, code in enumerate(target_codes, 1):
        name = STOCK_NAMES.get(code, code)
        print(f"  [{idx}/{len(target_codes)}] {name}({code}) 분석 중...", end="")

        try:
            df = get_ohlcv_data(code, period="D", count=200,
                                start_date=start_date, end_date=end_date)

            if df is not None and len(df) >= 30:
                score_data = score_stock(df)
                if score_data:
                    score_data['code'] = code
                    score_data['name'] = name
                    results.append(score_data)
                    print(f" 점수: {score_data['total_score']}")
                else:
                    print(" (데이터 부족)")
            else:
                print(" (데이터 없음)")
        except Exception as e:
            print(f" 오류: {e}")

        # API 호출 제한 방지
        time.sleep(0.15)

    if not results:
        print("\n분석 가능한 종목이 없습니다.")
        return

    # 결과 정렬
    results.sort(key=lambda x: x['total_score'], reverse=True)

    # 4) 결과 출력
    print("\n[4/4] 분석 결과")

    # -- 전체 종목 순위 --
    print("\n" + "=" * 80)
    print("  전체 종목 기술적 분석 순위")
    print("=" * 80)
    print(f"{'순위':>4} {'종목명':<16} {'코드':<8} {'총점':>4} "
          f"{'RSI점수':>7} {'MACD점수':>8} {'OBV점수':>7} "
          f"{'RSI':>6} {'현재가':>10}")
    print("-" * 80)

    for rank, r in enumerate(results, 1):
        print(f"{rank:>4} {r['name']:<16} {r['code']:<8} {r['total_score']:>4} "
              f"{r['rsi_score']:>7} {r['macd_score']:>8} {r['obv_score']:>7} "
              f"{r['rsi']:>6.1f} {r['close']:>10,}원")

    # -- TOP 추천 종목 --
    top_n = min(10, len(results))
    top_stocks = results[:top_n]

    print("\n" + "=" * 80)
    print(f"  TOP {top_n} 추천 종목 (기술적 지표 기반)")
    print("=" * 80)

    for rank, r in enumerate(top_stocks, 1):
        print(f"\n  #{rank} {r['name']} ({r['code']})  -  총점: {r['total_score']}/100")
        print(f"      현재가: {r['close']:,}원 | 거래량: {r['volume']:,}")
        print(f"      RSI: {r['rsi']:.1f} (점수: {r['rsi_score']}/40)")

        # RSI 해석
        if r['rsi'] < 30:
            rsi_comment = "과매도 구간 - 반등 가능성 주시"
        elif r['rsi'] < 50:
            rsi_comment = "매수 유리 구간"
        elif r['rsi'] < 70:
            rsi_comment = "중립~약간 과열"
        else:
            rsi_comment = "과매수 주의"
        print(f"        -> {rsi_comment}")

        print(f"      MACD: {r['macd']:.2f} | Signal: {r['macd_signal']:.2f} | "
              f"Histogram: {r['macd_hist']:.2f} (점수: {r['macd_score']}/35)")

        # MACD 해석
        if r['macd'] > r['macd_signal'] and r['macd_hist'] > 0:
            macd_comment = "골든크로스 + 상승 모멘텀 -> 매수 시그널"
        elif r['macd'] > r['macd_signal']:
            macd_comment = "골든크로스 발생 중"
        elif r['macd_hist'] > 0:
            macd_comment = "히스토그램 양수 전환"
        else:
            macd_comment = "하락 모멘텀 주의"
        print(f"        -> {macd_comment}")

        print(f"      OBV 점수: {r['obv_score']}/25")
        if r['obv_score'] >= 20:
            obv_comment = "거래량 강한 상승 추세 -> 매수 동력 확인"
        elif r['obv_score'] >= 10:
            obv_comment = "거래량 소폭 증가"
        else:
            obv_comment = "거래량 약세"
        print(f"        -> {obv_comment}")

    # -- 포트폴리오 기반 추천 --
    if portfolio:
        holdings = portfolio.get('output1', [])
        held_codes = [item.get('pdno', '') for item in holdings if int(item.get('hldg_qty', 0)) > 0]

        if held_codes:
            print("\n" + "=" * 80)
            print("  보유 종목 기술적 분석 & 추천")
            print("=" * 80)

            for item in holdings:
                code = item.get('pdno', '')
                qty = int(item.get('hldg_qty', 0))
                if qty == 0:
                    continue

                name = item.get('prdt_name', '?')
                eval_pl = int(item.get('evlu_pfls_amt', 0))
                pl_rate = float(item.get('evlu_pfls_rt', 0))

                # 분석 결과에서 찾기
                stock_result = next((r for r in results if r['code'] == code), None)

                print(f"\n  {name} ({code}) | 보유: {qty:,}주 | 평가손익: {eval_pl:+,}원 ({pl_rate:+.2f}%)")

                if stock_result:
                    score = stock_result['total_score']
                    rsi_val = stock_result['rsi']

                    # 종합 추천
                    if score >= 70 and pl_rate < 0:
                        recommendation = "추가 매수 고려 (기술적 반등 시그널 + 현재 손실 상태)"
                    elif score >= 70:
                        recommendation = "보유 유지 (강한 상승 시그널)"
                    elif score >= 50 and pl_rate > 10:
                        recommendation = "일부 차익 실현 고려"
                    elif score >= 50:
                        recommendation = "보유 유지"
                    elif score < 30 and pl_rate < -10:
                        recommendation = "손절 검토 (기술적 하락 신호 + 큰 손실)"
                    elif score < 30:
                        recommendation = "관망 (하락 모멘텀)"
                    else:
                        recommendation = "보유 유지하되 주시"

                    print(f"    기술 점수: {score}/100 | RSI: {rsi_val:.1f}")
                    print(f"    -> 추천: {recommendation}")
                else:
                    print(f"    (분석 대상 외 종목)")

    # -- 종합 투자 전략 --
    print("\n" + "=" * 80)
    print("  종합 투자 전략 가이드")
    print("=" * 80)

    strong_buy = [r for r in results if r['total_score'] >= 75]
    buy = [r for r in results if 60 <= r['total_score'] < 75]
    hold = [r for r in results if 40 <= r['total_score'] < 60]
    caution = [r for r in results if r['total_score'] < 40]

    if strong_buy:
        print(f"\n  [강력 매수 시그널] (75점 이상)")
        for s in strong_buy:
            print(f"    - {s['name']}({s['code']}): {s['total_score']}점 / RSI {s['rsi']:.1f}")

    if buy:
        print(f"\n  [매수 고려] (60~74점)")
        for s in buy:
            print(f"    - {s['name']}({s['code']}): {s['total_score']}점 / RSI {s['rsi']:.1f}")

    if hold:
        print(f"\n  [관망/보유 유지] (40~59점)")
        for s in hold:
            print(f"    - {s['name']}({s['code']}): {s['total_score']}점 / RSI {s['rsi']:.1f}")

    if caution:
        print(f"\n  [주의/매도 고려] (40점 미만)")
        for s in caution:
            print(f"    - {s['name']}({s['code']}): {s['total_score']}점 / RSI {s['rsi']:.1f}")

    print("\n" + "-" * 80)
    print("  [투자 참고사항]")
    print("  1. 기술적 지표는 과거 데이터 기반이므로 미래를 보장하지 않습니다.")
    print("  2. RSI 30 이하 과매도 종목은 반등 가능성이 높지만 하락 추세일 수도 있습니다.")
    print("  3. MACD 골든크로스 + OBV 상승 = 가장 강력한 매수 신호입니다.")
    print("  4. 분산 투자를 권장합니다. 한 종목에 30% 이상 집중하지 마세요.")
    print("  5. 반드시 본인의 판단과 리스크 허용 범위 내에서 투자하세요.")
    print("-" * 80)
    print(f"\n  분석 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  * 본 분석은 투자 참고용이며 투자 책임은 본인에게 있습니다.\n")


if __name__ == "__main__":
    analyze_stocks()
