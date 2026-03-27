"""
설정 파일 확인 스크립트 (YAML 및 .env)
"""
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("설정 파일 확인")
print("=" * 60)

# YAML 파일 확인
yaml_file = "kis_devlp.yaml"
if os.path.exists(yaml_file):
    print(f"[OK] YAML 파일이 존재합니다: {os.path.abspath(yaml_file)}")
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config:
                print("\nYAML 설정 내용:")
                print(f"  my_app (실전투자 앱키): {yaml_config.get('my_app', '설정 안됨')}")
                print(f"  my_sec (실전투자 앱시크릿): {'*' * 20 if yaml_config.get('my_sec') else '설정 안됨'}")
                print(f"  paper_app (모의투자 앱키): {yaml_config.get('paper_app', '설정 안됨')}")
                print(f"  paper_sec (모의투자 앱시크릿): {'*' * 20 if yaml_config.get('paper_sec') else '설정 안됨'}")
                print(f"  my_acct_stock (계좌번호): {yaml_config.get('my_acct_stock', '설정 안됨')}")
                print(f"  my_prod (계좌상품): {yaml_config.get('my_prod', '01')}")
    except Exception as e:
        print(f"[ERROR] YAML 파일 읽기 오류: {e}")
else:
    print(f"[INFO] YAML 파일이 없습니다: {yaml_file}")

# .env 파일 확인
env_file = ".env"
if os.path.exists(env_file):
    print(f"\n[OK] .env 파일이 존재합니다: {os.path.abspath(env_file)}")
    print("\n.env 설정 내용:")
    print(f"  KIS_APP_KEY: {os.getenv('KIS_APP_KEY', '설정 안됨')}")
    print(f"  KIS_APP_SECRET: {'*' * 20 if os.getenv('KIS_APP_SECRET') else '설정 안됨'}")
    print(f"  KIS_PAPER_APP_KEY: {os.getenv('KIS_PAPER_APP_KEY', '설정 안됨')}")
    print(f"  KIS_PAPER_APP_SECRET: {'*' * 20 if os.getenv('KIS_PAPER_APP_SECRET') else '설정 안됨'}")
    print(f"  KIS_SVR: {os.getenv('KIS_SVR', 'prod')}")
else:
    print(f"\n[INFO] .env 파일이 없습니다: {env_file}")

print("\n" + "=" * 60)
print("확인 완료")
print("=" * 60)
print("\n사용 우선순위: YAML 파일 > .env 파일")








