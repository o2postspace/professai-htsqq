"""
ProfessAI 주식 분석 대시보드 - 원클릭 실행
===========================================
사용법: python run.py (또는 ProfessAI.bat 더블클릭)
-> 자동으로 필요 패키지 설치
-> OHLCV 데이터 증분 업데이트
-> 서버 시작 + 브라우저 자동 열기
"""
import subprocess
import sys
import os
import webbrowser
import time
import threading


def install_packages():
    """필요 패키지 자동 설치"""
    required = ['flask', 'pandas', 'numpy', 'requests', 'pyyaml', 'python-dotenv']
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_').split('_')[0] if pkg != 'python-dotenv' else 'dotenv')
        except ImportError:
            print(f"  Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])


def update_ohlcv_data():
    """OHLCV 데이터 증분 업데이트 (추가된 데이터만)"""
    try:
        from update_ohlcv import update_all
        update_all()
    except Exception as e:
        print(f"  OHLCV update warning: {e}")
        print("  -> Dashboard will use existing data")


def open_browser():
    """서버 시작 후 브라우저 자동 열기"""
    time.sleep(2)
    webbrowser.open('http://localhost:8050')


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print()
    print("  ==========================================")
    print("       ProfessAI - Stock Analysis Dashboard")
    print("  ==========================================")
    print()

    # 1) 패키지 확인
    print("  [1/4] Checking packages...")
    install_packages()
    print("  [1/4] Packages ready!")
    print()

    # 2) API 인증 확인
    print("  [2/4] Checking API auth...")
    from stock_dashboard import app, is_configured, get_auth

    if is_configured():
        try:
            get_auth()
            print("  [2/4] Auth OK!")
            print()

            # 3) OHLCV 데이터 증분 업데이트
            print("  [3/4] Updating stock data (new data only)...")
            update_ohlcv_data()
            print()
        except Exception as e:
            print(f"  [2/4] Auth failed: {e}")
            print("  [3/4] Skipped (auth required)")
            print("  -> Setup page will open in browser")
            print()
    else:
        print("  [2/4] No API key configured")
        print("  [3/4] Skipped (auth required)")
        print("  -> Setup page will open in browser")
        print()

    # 4) 서버 시작
    print("  [4/4] Starting server...")
    print()
    print("  ==========================================")
    print("   http://localhost:8050")
    print("   Press Ctrl+C to stop")
    print("  ==========================================")
    print()

    # 브라우저 자동 열기
    threading.Thread(target=open_browser, daemon=True).start()

    app.run(host='0.0.0.0', port=8050, debug=False)


if __name__ == '__main__':
    main()
