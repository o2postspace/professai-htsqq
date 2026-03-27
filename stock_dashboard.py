"""
ProfessAI - 한국투자증권 주식 분석 웹 대시보드
=============================================
기능:
  - 기술적 분석 (RSI, MACD, OBV) 기반 종목 추천
  - 실시간 가격 조회
  - KOSPI 벤치마크 대비 차트 비교
  - 뉴스 분석 + DCF/밸류에이션
  - 매수/매도 주문
  - API 키 설정 페이지 (최초 1회)

사용법:
  python run.py
  -> 브라우저에서 http://localhost:5000 접속
"""
import os
import sys
import re
import json
import time
import numpy as np
import pandas as pd
import requests as http_requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# Flask 앱 설정
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = "professai_stock_2026"

CONFIG_FILE = os.path.join(BASE_DIR, "kis_devlp.yaml")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# 전역 캐시
_cache = {
    "recommendations": None,
    "recommendations_time": 0,
    "news": {},
    "news_time": {},
    "chart": {},
    "chart_time": {},
    "kospi": None,
    "kospi_time": 0,
}
CACHE_TTL_REC = 300
CACHE_TTL_NEWS = 600
CACHE_TTL_CHART = 300

# 뉴스 밸류에이션 유의성 기준 (시총 대비 %)
NEWS_SIG_RATIO = 1.0  # 최소 1% 이상이어야 재평가급


def calc_news_score_bonus(top_val):
    """재평가급 뉴스의 점수 보너스 (-15 ~ +15)"""
    if not top_val:
        return 0
    ratio = top_val.get('ratio_pct', 0)
    upside = top_val.get('upside_pct', 0)
    if ratio < NEWS_SIG_RATIO:
        return 0
    # 규모에 따라 보너스 차등
    if ratio >= 10:
        mag = 15  # 시총 10%+ → 대형 이벤트
    elif ratio >= 5:
        mag = 10  # 시총 5%+ → 유의미
    else:
        mag = 5   # 시총 1%+ → 주목
    return mag if upside > 0 else -mag if upside < 0 else 0

# ============================================================
# 종목명 딕셔너리
# ============================================================
STOCK_NAMES = {
    "005930": "삼성전자", "000660": "SK하이닉스", "035420": "NAVER",
    "035720": "카카오", "051910": "LG화학", "006400": "삼성SDI",
    "005380": "현대차", "028260": "삼성물산", "105560": "KB금융",
    "096770": "SK이노베이션", "066570": "LG전자", "003550": "LG",
    "005490": "POSCO홀딩스", "012330": "현대모비스", "034730": "SK",
    "055550": "신한지주", "000270": "기아", "017670": "SK텔레콤",
    "323410": "카카오뱅크", "207940": "삼성바이오로직스",
    "068270": "셀트리온", "036570": "엔씨소프트",
    "259960": "크래프톤", "086790": "하나금융지주",
    "003670": "포스코퓨처엠", "035760": "CJ ENM",
    "036460": "한국가스공사", "196170": "알테오젠",
    "066970": "엘앤에프", "373220": "LG에너지솔루션",
    "000810": "삼성화재", "030200": "KT", "032640": "LG유플러스",
    "009150": "삼성전기", "010130": "고려아연", "003490": "대한항공",
    "002790": "아모레퍼시픽", "034020": "두산에너빌리티",
    "011200": "HMM", "009540": "한국조선해양", "329180": "HD현대중공업",
    "042700": "한미반도체",
}
TARGET_CODES = list(STOCK_NAMES.keys())

# KOSPI ETF (벤치마크용)
KOSPI_ETF = "069500"  # KODEX 200


# ============================================================
# 설정 관리
# ============================================================
def is_configured():
    """API 키가 설정되어 있는지 확인"""
    # 환경변수 체크 (Vercel 배포 환경)
    env_key = os.environ.get('KIS_APP_KEY', '')
    if env_key and len(env_key) > 10:
        return True
    if os.path.exists(CONFIG_FILE):
        try:
            import yaml
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            if cfg and cfg.get('my_app') and cfg.get('my_sec'):
                val = str(cfg['my_app'])
                if '여기에' not in val and '입력' not in val and len(val) > 10:
                    return True
        except:
            pass
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, 'r') as f:
                content = f.read()
            if 'KIS_APP_KEY=' in content:
                for line in content.split('\n'):
                    if line.startswith('KIS_APP_KEY=') and len(line.split('=', 1)[1].strip()) > 10:
                        return True
        except:
            pass
    return False


def save_config(app_key, app_secret, account_no, account_prod='01',
                paper_app='', paper_sec='', paper_acct=''):
    """설정 저장"""
    import yaml
    config = {
        'my_app': app_key,
        'my_sec': app_secret,
        'my_acct_stock': account_no,
        'my_prod': account_prod or '01',
        'my_htsid': '사용자 HTS ID',
        'my_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    if paper_app:
        config['paper_app'] = paper_app
    if paper_sec:
        config['paper_sec'] = paper_sec
    if paper_acct:
        config['my_paper_stock'] = paper_acct

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    # .env도 동시에 저장
    env_lines = [
        f"KIS_APP_KEY={app_key}",
        f"KIS_APP_SECRET={app_secret}",
        f"KIS_ACCOUNT_NO={account_no}",
        f"KIS_ACCOUNT_PRODUCT={account_prod or '01'}",
        "KIS_SVR=prod",
    ]
    with open(ENV_FILE, 'w') as f:
        f.write('\n'.join(env_lines) + '\n')

    return True


# ============================================================
# KIS API 초기화
# ============================================================
_auth_obj = None

def get_auth():
    global _auth_obj
    if _auth_obj is None:
        import kis_auth as ka
        _auth_obj = ka.auth()
    return _auth_obj


def reset_auth():
    global _auth_obj
    _auth_obj = None


# ============================================================
# 기술적 지표
# ============================================================
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def calc_obv(close, volume):
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i - 1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i - 1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)


def score_stock(df):
    if df is None or len(df) < 30:
        return None
    close = df['종가']
    volume = df['거래량']

    rsi = calc_rsi(close)
    current_rsi = rsi.iloc[-1]
    macd_line, signal_line, histogram = calc_macd(close)
    current_hist = histogram.iloc[-1]
    prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0
    obv = calc_obv(close, volume)
    obv_sma20 = obv.rolling(20).mean()

    # RSI 점수 (40)
    if 30 <= current_rsi <= 50: rsi_score = 40
    elif 50 < current_rsi <= 60: rsi_score = 30
    elif 20 <= current_rsi < 30: rsi_score = 25
    elif 60 < current_rsi <= 70: rsi_score = 15
    elif current_rsi > 70: rsi_score = 5
    else: rsi_score = 10

    # MACD 점수 (35)
    macd_score = 0
    if macd_line.iloc[-1] > signal_line.iloc[-1]: macd_score += 15
    if current_hist > 0: macd_score += 10
    if current_hist > prev_hist: macd_score += 10

    # OBV 점수 (25)
    obv_score = 0
    if len(obv_sma20.dropna()) > 0 and not np.isnan(obv_sma20.iloc[-1]):
        if obv.iloc[-1] > obv_sma20.iloc[-1]: obv_score += 15
        if len(obv) >= 5 and obv.iloc[-1] > obv.iloc[-5]: obv_score += 10

    total = rsi_score + macd_score + obv_score

    # 해석
    rsi_comment = "과매도 반등" if current_rsi < 30 else "매수 유리" if current_rsi < 50 else "중립" if current_rsi < 70 else "과매수 주의"
    if macd_line.iloc[-1] > signal_line.iloc[-1] and current_hist > 0:
        macd_comment = "골든크로스+상승"
    elif macd_line.iloc[-1] > signal_line.iloc[-1]:
        macd_comment = "골든크로스"
    elif current_hist > prev_hist:
        macd_comment = "하락 둔화"
    else:
        macd_comment = "하락 모멘텀"
    obv_comment = "거래량 강세" if obv_score >= 20 else "소폭 증가" if obv_score >= 10 else "거래량 약세"

    if total >= 75: signal, signal_class = "강력매수", "strong-buy"
    elif total >= 60: signal, signal_class = "매수고려", "buy"
    elif total >= 40: signal, signal_class = "관망", "hold"
    else: signal, signal_class = "주의", "caution"

    return {
        'total_score': total, 'rsi_score': rsi_score, 'macd_score': macd_score, 'obv_score': obv_score,
        'rsi': round(float(current_rsi), 2),
        'macd': round(float(macd_line.iloc[-1]), 2),
        'macd_signal': round(float(signal_line.iloc[-1]), 2),
        'macd_hist': round(float(current_hist), 2),
        'close': int(close.iloc[-1]), 'volume': int(volume.iloc[-1]),
        'rsi_comment': rsi_comment, 'macd_comment': macd_comment, 'obv_comment': obv_comment,
        'signal': signal, 'signal_class': signal_class,
    }


# ============================================================
# 로컬 CSV 로딩 (API 호출 최소화)
# ============================================================
OHLCV_DIR = os.environ.get("OHLCV_DIR", os.path.join(BASE_DIR, "ohlcv_data"))
if not os.path.isabs(OHLCV_DIR):
    OHLCV_DIR = os.path.join(BASE_DIR, OHLCV_DIR)


def load_ohlcv_csv(stock_code, days=200):
    """
    로컬 CSV에서 OHLCV 데이터 로딩 (API 호출 없이).
    CSV가 없거나 데이터 부족 시 API 폴백.
    """
    csv_path = os.path.join(OHLCV_DIR, f"{stock_code}.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            if not df.empty and '날짜' in df.columns and '종가' in df.columns:
                df['날짜'] = pd.to_datetime(df['날짜'])
                for col in ['시가', '고가', '저가', '종가', '거래량', '거래대금']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                df = df.sort_values('날짜').tail(days).reset_index(drop=True)
                if len(df) >= 30:
                    return df
        except Exception:
            pass

    # CSV 없거나 부족하면 API 폴백
    from get_ohlcv import get_ohlcv_data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(days * 1.5))
    return get_ohlcv_data(stock_code, period="D", count=days,
                          start_date=start_date, end_date=end_date)


# ============================================================
# 차트 데이터 (종목 vs KOSPI)
# ============================================================
def get_chart_data(stock_code, days=60):
    """종목 + KOSPI 비교 차트 데이터"""
    # 로컬 CSV 우선, API 폴백
    stock_df = load_ohlcv_csv(stock_code, days=days + 10)
    kospi_df = load_ohlcv_csv(KOSPI_ETF, days=days + 10)

    if stock_df is None or kospi_df is None or stock_df.empty or kospi_df.empty:
        return None

    # 날짜 기준으로 merge
    stock_df = stock_df[['날짜', '종가']].rename(columns={'종가': 'stock_price'})
    kospi_df = kospi_df[['날짜', '종가']].rename(columns={'종가': 'kospi_price'})
    merged = pd.merge(stock_df, kospi_df, on='날짜', how='inner').sort_values('날짜')

    if len(merged) < 5:
        return None

    # 100 기준 정규화
    base_stock = merged['stock_price'].iloc[0]
    base_kospi = merged['kospi_price'].iloc[0]

    labels = merged['날짜'].dt.strftime('%m/%d').tolist()
    stock_norm = ((merged['stock_price'] / base_stock) * 100).round(2).tolist()
    kospi_norm = ((merged['kospi_price'] / base_kospi) * 100).round(2).tolist()
    stock_prices = merged['stock_price'].tolist()

    return {
        'labels': labels,
        'stock': stock_norm,
        'kospi': kospi_norm,
        'stock_prices': stock_prices,
        'base_stock': int(base_stock),
        'base_kospi': int(base_kospi),
    }


# ============================================================
# 뉴스 분석 + 밸류에이션
# ============================================================
def extract_amount(text):
    amounts = []
    for v in re.findall(r'(\d+(?:\.\d+)?)\s*조', text):
        amounts.append(float(v) * 10000)
    for v in re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*억', text):
        amounts.append(float(v.replace(',', '')))
    for v in re.findall(r'(\d{1,3}(?:,\d{3})*)\s*만', text):
        val = float(v.replace(',', ''))
        if val >= 1000:
            amounts.append(val / 10000)
    return amounts


def classify_news(headline):
    kw = {
        "수주": ["수주", "계약", "납품", "공급계약", "수출", "대규모", "물량"],
        "실적": ["실적", "매출", "영업이익", "순이익", "흑자", "적자", "분기",
                 "반기", "연결", "연간", "사상 최대", "어닝", "컨센서스", "영업이익률"],
        "자산": ["자산", "인수", "합병", "M&A", "지분", "투자", "설비", "공장",
                 "부지", "증설", "R&D", "연구", "특허"],
        "성장": ["성장", "증가", "확대", "신사업", "신규", "진출", "호황", "호실적",
                 "호조", "급증", "돌파", "사상최고", "최대", "신고가", "랠리", "기대감"],
        "배당": ["배당", "주주환원", "자사주", "소각"],
        "위험": ["하락", "감소", "축소", "손실", "부진", "리스크", "악화", "급락",
                 "폭락", "위기", "적자전환", "하향", "우려"],
    }
    for cat, words in kw.items():
        for w in words:
            if w in headline:
                return cat
    return "기타"


def calc_valuation(headline, news_type, mcap, price, shares):
    amounts = extract_amount(headline)
    if not amounts or mcap <= 0 or shares <= 0:
        return None
    amt = max(amounts)
    r = {"amount_억": amt, "market_cap_억": mcap, "ratio_pct": round((amt / mcap) * 100, 2)}
    dr = 0.08

    if news_type == "수주":
        annual_profit = (amt / 3) * 0.10
        dcf = sum(annual_profit / (1 + dr) ** i for i in range(1, 4))
        ps = (dcf * 1e8) / shares
        r.update(method='현금흐름 할인법 (DCF)',
                 assumption=f'수주 {amt:,.0f}억원, 3년분할, 영업이익률10%, 할인율8%',
                 per_share_impact=round(ps), target_price=round(price + ps),
                 upside_pct=round((ps / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}%")
    elif news_type == "실적":
        eps = (amt * 1e8) / shares
        fv = eps * 15
        r.update(method='PER 배수법',
                 assumption=f'실적 {amt:,.0f}억원, PER 15배',
                 per_share_impact=round(fv), target_price=round(price + fv),
                 upside_pct=round((fv / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}%")
    elif news_type == "자산":
        nav = (amt / mcap) * price
        r.update(method='순자산가치법 (NAV)',
                 assumption=f'자산가치 {amt:,.0f}억원',
                 per_share_impact=round(nav), target_price=round(price + nav),
                 upside_pct=round((nav / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}%")
    elif news_type == "성장":
        gv = amt * 0.15
        dcf = sum(gv / (1 + dr) ** i for i in range(1, 6))
        ps = (dcf * 1e8) / shares
        r.update(method='성장가치 DCF',
                 assumption=f'성장규모 {amt:,.0f}억원, 5년반영, 할인율8%',
                 per_share_impact=round(ps), target_price=round(price + ps),
                 upside_pct=round((ps / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}%")
    elif news_type == "위험":
        loss = -(amt / mcap) * price
        r.update(method='손실 반영',
                 assumption=f'손실 규모 {amt:,.0f}억원',
                 per_share_impact=round(loss), target_price=round(price + loss),
                 upside_pct=round((loss / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}% 리스크")
    elif news_type == "기타" or news_type == "배당":
        # 기타/배당이라도 금액이 있으면 시총 대비 규모 표시
        ratio = (amt / mcap) * price if mcap > 0 else 0
        r.update(method='시가총액 대비 규모 분석',
                 assumption=f'뉴스 언급 금액 {amt:,.0f}억원',
                 per_share_impact=round(ratio * 0.1),  # 보수적 10% 반영
                 target_price=round(price + ratio * 0.1),
                 upside_pct=round((ratio * 0.1 / price) * 100, 2) if price else 0,
                 grade=f"시총 대비 {r['ratio_pct']}%")
    else:
        return None
    return r


def _decode_html_entities(text):
    """HTML 엔티티 디코딩"""
    import html as html_mod
    text = html_mod.unescape(text)
    # 추가로 남는 엔티티 제거
    text = re.sub(r'&[a-z]+;', '', text)
    return text.strip()


def fetch_news(stock_code, stock_name):
    ck = stock_code
    now = time.time()
    if ck in _cache["news"] and (now - _cache["news_time"].get(ck, 0)) < CACHE_TTL_NEWS:
        return _cache["news"][ck]

    news_list = []
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}&page=1&sm=title_entity_id.basic"
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://finance.naver.com/item/news.naver?code={stock_code}",
        }
        resp = http_requests.get(url, headers=hdrs, timeout=8)
        resp.encoding = 'euc-kr'
        html = resp.text

        # <tr> 블록 단위로 파싱 (네이버 금융 뉴스 테이블 구조)
        blocks = html.split('<tr')
        for block in blocks:
            if 'class="tit"' not in block:
                continue
            href_m = re.search(r'href="([^"]+)"[^>]*class="tit"', block)
            title_m = re.search(r'class="tit"[^>]*>(.+?)</a>', block, re.DOTALL)
            date_m = re.search(r'class="date">\s*([\d.]+)', block)
            info_m = re.search(r'class="info">\s*([^<]+)', block)

            if not (href_m and title_m):
                continue

            raw_title = re.sub(r'<[^>]+>', '', title_m.group(1))
            title = _decode_html_entities(raw_title)
            if not title:
                continue

            href = href_m.group(1)
            link = ("https://finance.naver.com" + href) if href.startswith('/') else href
            date = date_m.group(1).strip() if date_m else datetime.now().strftime('%Y.%m.%d')
            source = info_m.group(1).strip() if info_m else ''

            news_list.append({
                'title': title, 'date': date, 'source': source, 'link': link,
                'type': classify_news(title), 'valuation': None,
            })
            if len(news_list) >= 15:
                break

    except Exception as e:
        print(f"뉴스 오류 ({stock_code}): {e}")

    # 네이버 금융에서 못 가져왔으면 검색 뉴스 시도
    if not news_list:
        try:
            import urllib.parse
            q = urllib.parse.quote(stock_name)
            surl = f"https://search.naver.com/search.naver?where=news&query={q}&sm=tab_opt&sort=1&pd=1"
            hdrs = {"User-Agent": "Mozilla/5.0", "Referer": "https://search.naver.com"}
            resp = http_requests.get(surl, headers=hdrs, timeout=5)
            resp.encoding = 'utf-8'
            items = re.findall(r'<a[^>]*class="news_tit"[^>]*href="([^"]*)"[^>]*title="([^"]*)"', resp.text)
            for link, title in items[:10]:
                title = _decode_html_entities(title)
                news_list.append({
                    'title': title, 'date': datetime.now().strftime('%Y.%m.%d'),
                    'source': '', 'link': link,
                    'type': classify_news(title), 'valuation': None,
                })
        except Exception as e:
            print(f"검색뉴스 오류 ({stock_code}): {e}")

    _cache["news"][ck] = news_list
    _cache["news_time"][ck] = now
    return news_list


# ============================================================
# KIS API 래퍼
# ============================================================
def get_realtime_price(auth_obj, stock_code):
    path = "/uapi/domestic-stock/v1/quotations/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": stock_code}
    try:
        result = auth_obj.api_call(path, "FHKST01010100", params)
        if result.get('rt_cd') == '0':
            o = result['output']
            return {
                'code': stock_code,
                'name': o.get('hts_kor_isnm', STOCK_NAMES.get(stock_code, stock_code)),
                'price': int(o.get('stck_prpr', 0)),
                'change': int(o.get('prdy_vrss', 0)),
                'change_rate': float(o.get('prdy_ctrt', 0)),
                'volume': int(o.get('acml_vol', 0)),
                'high': int(o.get('stck_hgpr', 0)),
                'low': int(o.get('stck_lwpr', 0)),
                'open': int(o.get('stck_oprc', 0)),
                'market_cap': int(o.get('hts_avls', 0)),
                'shares': int(o.get('lstn_stcn', 0)),
                'per': float(o.get('per', 0) or 0),
                'pbr': float(o.get('pbr', 0) or 0),
            }
    except Exception as e:
        print(f"현재가 오류 ({stock_code}): {e}")
    return None


def get_portfolio(auth_obj):
    path = "/uapi/domestic-stock/v1/trading/inquire-balance"
    tr_id = "TTTC8434R" if auth_obj.svr == 'prod' else "VTTC8434R"
    params = {
        "CANO": auth_obj.account_no, "ACNT_PRDT_CD": auth_obj.account_product,
        "AFHR_FLPR_YN": "N", "OFL_YN": "", "INQR_DVSN": "02", "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N", "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01", "CTX_AREA_FK100": "", "CTX_AREA_NK100": "",
    }
    try:
        result = auth_obj.api_call(path, tr_id, params)
        if result.get('rt_cd') == '0':
            return result
    except:
        pass
    return None


def get_hashkey(auth_obj, data):
    url = f"{auth_obj.base_url}/uapi/hashkey"
    headers = {"content-type": "application/json", "appkey": auth_obj.app_key, "appsecret": auth_obj.app_secret}
    try:
        return http_requests.post(url, headers=headers, json=data).json().get("HASH", "")
    except:
        return ""


def place_order(auth_obj, stock_code, qty, price, order_type, side):
    path = "/uapi/domestic-stock/v1/trading/order-cash"
    tr_id = ("TTTC0802U" if side == 'buy' else "TTTC0801U") if auth_obj.svr == 'prod' \
        else ("VTTC0802U" if side == 'buy' else "VTTC0801U")
    body = {
        "CANO": auth_obj.account_no, "ACNT_PRDT_CD": auth_obj.account_product,
        "PDNO": stock_code, "ORD_DVSN": order_type,
        "ORD_QTY": str(qty), "ORD_UNPR": str(price if order_type == "00" else 0),
    }
    hashkey = get_hashkey(auth_obj, body)
    headers = auth_obj.get_headers(tr_id)
    headers["hashkey"] = hashkey
    headers["content-type"] = "application/json; charset=utf-8"
    try:
        return http_requests.post(f"{auth_obj.base_url}{path}", headers=headers, json=body).json()
    except Exception as e:
        return {"rt_cd": "-1", "msg1": str(e)}


# ============================================================
# 분석 엔진
# ============================================================
def run_analysis():
    now = time.time()
    if _cache["recommendations"] and (now - _cache["recommendations_time"]) < CACHE_TTL_REC:
        return _cache["recommendations"]

    results = []
    api_fallback_count = 0

    for code in TARGET_CODES:
        name = STOCK_NAMES.get(code, code)
        try:
            df = load_ohlcv_csv(code, days=200)
            if df is not None and len(df) >= 30:
                s = score_stock(df)
                if s:
                    s['code'] = code
                    s['name'] = name
                    results.append(s)
        except:
            pass

    results.sort(key=lambda x: x['total_score'], reverse=True)
    _cache["recommendations"] = results
    _cache["recommendations_time"] = now
    return results


# ============================================================
# Flask 라우트
# ============================================================
@app.route('/')
def index():
    if not is_configured():
        return render_template('setup.html')
    return render_template('dashboard.html')


@app.route('/setup')
def setup_page():
    return render_template('setup.html')


@app.route('/api/save-config', methods=['POST'])
def api_save_config():
    try:
        d = request.json
        save_config(
            d.get('app_key', ''), d.get('app_secret', ''),
            d.get('account_no', ''), d.get('account_prod', '01'),
            d.get('paper_app', ''), d.get('paper_sec', ''), d.get('paper_acct', ''),
        )
        reset_auth()
        # 인증 테스트
        try:
            auth_obj = get_auth()
            return jsonify({"ok": True, "message": "설정 저장 및 인증 성공!"})
        except Exception as e:
            return jsonify({"ok": False, "error": f"설정은 저장되었으나 인증 실패: {e}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/init')
def api_init():
    try:
        auth_obj = get_auth()
        return jsonify({"ok": True, "svr": auth_obj.svr, "account": auth_obj.account_no})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/portfolio')
def api_portfolio():
    try:
        auth_obj = get_auth()
        data = get_portfolio(auth_obj)
        if not data:
            return jsonify({"ok": False, "error": "조회 실패"})
        holdings = []
        for item in data.get('output1', []):
            qty = int(item.get('hldg_qty', 0))
            if qty == 0: continue
            holdings.append({
                'name': item.get('prdt_name', '?'), 'code': item.get('pdno', '?'),
                'qty': qty, 'avg_price': int(float(item.get('pchs_avg_pric', '0'))),
                'current_price': int(item.get('prpr', 0)),
                'eval_pl': int(item.get('evlu_pfls_amt', 0)),
                'pl_rate': float(item.get('evlu_pfls_rt', 0)),
            })
        summary = {}
        o2 = data.get('output2', [])
        if o2:
            s = o2[0] if isinstance(o2, list) else o2
            summary = {
                'deposit': int(s.get('dnca_tot_amt', 0)),
                'total_purchase': int(s.get('pchs_amt_smtl_amt', 0)),
                'total_eval': int(s.get('tot_evlu_amt', 0)),
                'total_pl': int(s.get('evlu_pfls_smtl_amt', 0)),
            }
        return jsonify({"ok": True, "holdings": holdings, "summary": summary})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/recommendations')
def api_recommendations():
    try:
        results = run_analysis()
        return jsonify({"ok": True, "data": results, "updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/price/<code>')
def api_price(code):
    try:
        auth_obj = get_auth()
        d = get_realtime_price(auth_obj, code)
        return jsonify({"ok": True, "data": d}) if d else jsonify({"ok": False})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/chart/<code>')
def api_chart(code):
    """종목 vs KOSPI 비교 차트 데이터"""
    now = time.time()
    ck = code
    if ck in _cache["chart"] and (now - _cache["chart_time"].get(ck, 0)) < CACHE_TTL_CHART:
        return jsonify({"ok": True, "data": _cache["chart"][ck], "name": STOCK_NAMES.get(code, code)})
    try:
        data = get_chart_data(code, days=60)
        if data:
            _cache["chart"][ck] = data
            _cache["chart_time"][ck] = now
            return jsonify({"ok": True, "data": data, "name": STOCK_NAMES.get(code, code)})
        return jsonify({"ok": False, "error": "데이터 부족"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/news/<code>')
def api_news(code):
    try:
        name = STOCK_NAMES.get(code, code)
        news_list = fetch_news(code, name)
        auth_obj = get_auth()
        pd = get_realtime_price(auth_obj, code)
        price = pd['price'] if pd else 0
        mcap = pd['market_cap'] if pd else 0
        shares = pd['shares'] if pd else 0
        for n in news_list:
            # 모든 타입에 대해 밸류에이션 시도 (금액이 있는 경우만 계산됨)
            n['valuation'] = calc_valuation(n['title'], n['type'], mcap, price, shares)
        return jsonify({"ok": True, "news": news_list, "stock_name": name})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/kospi-chart')
def api_kospi_chart():
    """KOSPI 벤치마크 차트 (포트폴리오용)"""
    now = time.time()
    if _cache["kospi"] and (now - _cache["kospi_time"]) < CACHE_TTL_CHART:
        return jsonify({"ok": True, "data": _cache["kospi"]})
    try:
        df = load_ohlcv_csv(KOSPI_ETF, days=60)
        if df is None or df.empty:
            return jsonify({"ok": False, "error": "데이터 없음"})
        df = df.sort_values('날짜')
        labels = df['날짜'].dt.strftime('%m/%d').tolist()
        prices = df['종가'].tolist()
        volumes = df['거래량'].tolist() if '거래량' in df.columns else []
        base = prices[0] if prices else 1
        changes = [round((p / base - 1) * 100, 2) for p in prices]
        data = {
            'labels': labels,
            'prices': prices,
            'volumes': volumes,
            'changes': changes,
            'current': int(prices[-1]) if prices else 0,
            'change_pct': changes[-1] if changes else 0,
        }
        _cache["kospi"] = data
        _cache["kospi_time"] = now
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/portfolio-benchmark')
def api_portfolio_benchmark():
    """포트폴리오 vs KOSPI 벤치마크 (매수 시점 기준 비교)"""
    try:
        auth_obj = get_auth()
        pf_data = get_portfolio(auth_obj)
        if not pf_data:
            return jsonify({"ok": False, "error": "포트폴리오 조회 실패"})

        holdings = []
        for item in pf_data.get('output1', []):
            qty = int(item.get('hldg_qty', 0))
            if qty == 0:
                continue
            holdings.append({
                'code': item.get('pdno', ''),
                'name': item.get('prdt_name', ''),
                'qty': qty,
                'avg_price': float(item.get('pchs_avg_pric', 0)),
                'current_price': int(item.get('prpr', 0)),
                'purchase_amt': qty * float(item.get('pchs_avg_pric', 0)),
            })

        if not holdings:
            return jsonify({"ok": False, "error": "보유 종목 없음"})

        # 1) 각 종목 OHLCV + 매수일 추정 (매입가에 가장 가까운 날짜)
        stock_dfs = {}
        for h in holdings:
            code = h['code']
            df = load_ohlcv_csv(code, days=400)
            if df is not None and not df.empty:
                df = df.sort_values('날짜').reset_index(drop=True)
                df['_diff'] = abs(df['종가'] - h['avg_price'])
                idx = df['_diff'].idxmin()
                h['est_date'] = df.loc[idx, '날짜']
                stock_dfs[code] = df[['날짜', '종가']].copy()

        dates = [h['est_date'] for h in holdings if 'est_date' in h]
        if not dates:
            return jsonify({"ok": False, "error": "매수일 추정 실패"})
        chart_start = min(dates)

        # 2) KOSPI ETF 데이터 (매수일부터)
        kospi_df = load_ohlcv_csv(KOSPI_ETF, days=400)
        if kospi_df is None or kospi_df.empty:
            return jsonify({"ok": False, "error": "KOSPI 데이터 없음"})
        kospi_df = kospi_df[['날짜', '종가']].sort_values('날짜').reset_index(drop=True)
        kospi_df = kospi_df[kospi_df['날짜'] >= chart_start].reset_index(drop=True)

        # 3) 일별 포트폴리오 가치 (KOSPI 거래일 기준)
        trade_dates = kospi_df['날짜'].tolist()
        daily_pf = []
        for dt in trade_dates:
            val = 0
            for h in holdings:
                code = h['code']
                if code not in stock_dfs:
                    continue
                sdf = stock_dfs[code]
                mask = sdf['날짜'] <= dt
                price = sdf[mask].iloc[-1]['종가'] if mask.any() else h['avg_price']
                val += price * h['qty']
            daily_pf.append(val)

        if not daily_pf or daily_pf[0] == 0:
            return jsonify({"ok": False, "error": "가치 계산 실패"})

        # 4) 100 기준 정규화
        pf_base = daily_pf[0]
        k_base = kospi_df['종가'].iloc[0]
        labels = [dt.strftime('%m/%d') for dt in trade_dates]
        pf_norm = [round((v / pf_base) * 100, 2) for v in daily_pf]
        k_norm = [round((p / k_base) * 100, 2) for p in kospi_df['종가'].tolist()]

        pf_ret = round(pf_norm[-1] - 100, 2)
        k_ret = round(k_norm[-1] - 100, 2)
        alpha = round(pf_ret - k_ret, 2)

        # 5) 종목별 alpha
        hold_info = []
        for h in holdings:
            ret = round((h['current_price'] / h['avg_price'] - 1) * 100, 2) if h['avg_price'] > 0 else 0
            est = h.get('est_date')
            k_r = 0
            if est:
                mask = kospi_df['날짜'] >= est
                if mask.any():
                    kp0 = kospi_df[mask].iloc[0]['종가']
                    kp1 = kospi_df.iloc[-1]['종가']
                    k_r = round((kp1 / kp0 - 1) * 100, 2)
            hold_info.append({
                'name': h['name'], 'code': h['code'],
                'return_pct': ret, 'kospi_pct': k_r,
                'alpha_pct': round(ret - k_r, 2),
                'est_date': est.strftime('%Y-%m-%d') if est else '',
            })

        return jsonify({
            "ok": True,
            "pf_return": pf_ret, "kospi_return": k_ret, "alpha": alpha,
            "start_date": chart_start.strftime('%Y-%m-%d'),
            "holdings": hold_info,
            "chart": {"labels": labels, "portfolio": pf_norm, "kospi": k_norm},
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/news-summary/<code>')
def api_news_summary(code):
    """종목 뉴스 밸류에이션 요약 - 재평가급만 필터"""
    try:
        name = STOCK_NAMES.get(code, code)
        news_list = fetch_news(code, name)
        auth_obj = get_auth()
        pd = get_realtime_price(auth_obj, code)
        price = pd['price'] if pd else 0
        mcap = pd['market_cap'] if pd else 0
        shares = pd['shares'] if pd else 0

        # 모든 뉴스 밸류에이션 계산
        sig_vals = []  # 유의미한 밸류에이션만
        for n in news_list:
            v = calc_valuation(n['title'], n['type'], mcap, price, shares)
            if v and v.get('ratio_pct', 0) >= NEWS_SIG_RATIO:
                sig_vals.append({**v, 'title': n['title'], 'news_type': n['type']})

        # 가장 영향력 큰 것 선택
        top_val = None
        if sig_vals:
            sig_vals.sort(key=lambda x: abs(x.get('upside_pct', 0)), reverse=True)
            top_val = sig_vals[0]

        score_bonus = calc_news_score_bonus(top_val)
        significant = top_val is not None

        # 유의성 등급
        grade_label = ''
        if significant:
            ratio = top_val.get('ratio_pct', 0)
            if ratio >= 10:
                grade_label = '대형 이벤트'
            elif ratio >= 5:
                grade_label = '재평가급'
            else:
                grade_label = '주목'

        return jsonify({
            "ok": True, "code": code,
            "news_count": len(news_list),
            "sig_count": len(sig_vals),
            "top": top_val,
            "score_bonus": score_bonus,
            "significant": significant,
            "grade_label": grade_label,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route('/api/order', methods=['POST'])
def api_order():
    try:
        d = request.json
        code, qty = d.get('code'), int(d.get('qty', 0))
        price, ot, side = int(d.get('price', 0)), d.get('order_type', '01'), d.get('side', 'buy')
        if not code or qty <= 0:
            return jsonify({"ok": False, "error": "종목코드와 수량을 확인하세요"})
        auth_obj = get_auth()
        result = place_order(auth_obj, code, qty, price, ot, side)
        if result.get('rt_cd') == '0':
            odno = result.get('output', {}).get('ODNO', '')
            return jsonify({"ok": True, "message": f"{'매수' if side=='buy' else '매도'} 주문 성공! 주문번호: {odno}"})
        return jsonify({"ok": False, "error": result.get('msg1', '주문 실패')})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  ProfessAI 주식 분석 대시보드")
    print("  http://localhost:8050")
    print("=" * 50)
    if is_configured():
        try:
            get_auth()
            print("  API 인증 성공!")
        except Exception as e:
            print(f"  API 인증 실패: {e}")
    else:
        print("  API 키 미설정 -> 설정 페이지로 이동합니다")
    app.run(host='0.0.0.0', port=8050, debug=False)
