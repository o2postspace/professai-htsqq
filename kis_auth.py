"""
한국투자증권 Open API 인증 모듈
"""
import os
import json
import time
import requests
import yaml
from datetime import datetime
from dotenv import load_dotenv
from runtime_config import CONFIG_FILE, ENV_FILE

# .env 파일 로드
load_dotenv(dotenv_path=ENV_FILE)

def load_config():
    """설정 파일 로드 (YAML 우선, 없으면 .env)"""
    config = {}
    
    # YAML 파일 먼저 시도
    yaml_file = CONFIG_FILE
    if os.path.exists(yaml_file):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    # YAML 키를 환경 변수 형식으로 변환
                    # 값이 없거나 예제 텍스트인 경우 빈 문자열로 처리
                    def clean_value(value, default=''):
                        if not value:
                            return default
                        value_str = str(value).strip('"')
                        # 예제 텍스트인 경우 빈 문자열 반환
                        if any(keyword in value_str for keyword in ['여기에', '입력', '사용자', '8자리', '선물옵션계좌', '모의투자']):
                            return default
                        return value_str if value_str else default
                    
                    config['KIS_APP_KEY'] = clean_value(yaml_config.get('my_app'))
                    config['KIS_APP_SECRET'] = clean_value(yaml_config.get('my_sec'))
                    config['KIS_PAPER_APP_KEY'] = clean_value(yaml_config.get('paper_app'))
                    config['KIS_PAPER_APP_SECRET'] = clean_value(yaml_config.get('paper_sec'))
                    config['KIS_ACCOUNT_NO'] = clean_value(yaml_config.get('my_acct_stock'))
                    config['KIS_ACCOUNT_PRODUCT'] = clean_value(yaml_config.get('my_prod'), '01')
                    config['KIS_HTS_ID'] = clean_value(yaml_config.get('my_htsid'))
                    # svr은 기본값 사용 (prod)
                    config['KIS_SVR'] = os.getenv('KIS_SVR', 'prod')
        except Exception as e:
            print(f"YAML 파일 읽기 오류: {e}")
    
    # .env 파일에서 값 가져오기 (YAML에 없거나 빈 값인 경우)
    for key in ['KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_PAPER_APP_KEY', 'KIS_PAPER_APP_SECRET', 
                'KIS_ACCOUNT_NO', 'KIS_ACCOUNT_PRODUCT', 'KIS_HTS_ID', 'KIS_SVR']:
        if key not in config or not config[key]:
            env_value = os.getenv(key)
            if env_value:
                config[key] = env_value
    
    # 기본값 설정
    if 'KIS_SVR' not in config or not config['KIS_SVR']:
        config['KIS_SVR'] = 'prod'
    if 'KIS_ACCOUNT_PRODUCT' not in config or not config['KIS_ACCOUNT_PRODUCT']:
        config['KIS_ACCOUNT_PRODUCT'] = '01'
    
    return config

class KISAuth:
    def __init__(self):
        # 설정 파일 로드
        config = load_config()
        
        self.svr = config.get('KIS_SVR', 'prod')  # prod: 실전투자, vps: 모의투자
        self.app_key = config.get('KIS_APP_KEY') if self.svr == 'prod' else config.get('KIS_PAPER_APP_KEY')
        self.app_secret = config.get('KIS_APP_SECRET') if self.svr == 'prod' else config.get('KIS_PAPER_APP_SECRET')
        self.account_no = config.get('KIS_ACCOUNT_NO')
        self.account_product = config.get('KIS_ACCOUNT_PRODUCT', '01')
        
        # API URL 설정
        if self.svr == 'prod':
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        
        self.access_token = None
        self.token_expires_at = 0
        # Vercel 환경에서는 /tmp 사용, 로컬에서는 ~/KIS/config 사용
        self.config_root = os.environ.get("KIS_TOKEN_DIR",
                                           os.path.join(os.path.expanduser("~"), "KIS", "config"))
        os.makedirs(self.config_root, exist_ok=True)
        
    def get_access_token(self):
        """접근 토큰 발급"""
        # 저장된 토큰 확인
        token_file = os.path.join(self.config_root, f"token_{self.svr}.json")
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                    saved_token = token_data.get('access_token')
                    expires_at = token_data.get('expires_at', 0)
                    # 토큰이 아직 유효한지 확인 (1시간 여유)
                    if saved_token and time.time() < (expires_at - 3600):
                        self.access_token = saved_token
                        self.token_expires_at = expires_at
                        return self.access_token
            except:
                pass
        
        # 토큰이 아직 유효한지 확인
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        # API 키와 시크릿 확인
        if not self.app_key or not self.app_secret:
            error_msg = "API 키 또는 시크릿이 설정되지 않았습니다.\n"
            error_msg += "다음을 확인하세요:\n"
            error_msg += "1. kis_devlp.yaml 파일이 프로젝트 루트에 있는지 확인\n"
            error_msg += "   또는 .env 파일에 설정이 있는지 확인\n"
            error_msg += f"2. 환경={self.svr} ({'실전투자' if self.svr == 'prod' else '모의투자'})에 맞는 키가 설정되어 있는지 확인\n"
            if self.svr == 'prod':
                error_msg += "   YAML 파일: my_app, my_sec\n"
                error_msg += "   또는 .env: KIS_APP_KEY, KIS_APP_SECRET\n"
            else:
                error_msg += "   YAML 파일: paper_app, paper_sec\n"
                error_msg += "   또는 .env: KIS_PAPER_APP_KEY, KIS_PAPER_APP_SECRET\n"
            raise ValueError(error_msg)
        
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {
            "content-type": "application/json"
        }
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            # 응답 내용 확인
            if response.status_code == 403:
                try:
                    error_detail = response.json()
                    error_code = error_detail.get('error_code', '')
                    error_desc = error_detail.get('error_description', '')
                    
                    # 1분당 1회 제한 오류인 경우
                    if 'EGW00133' in error_code or '1분' in error_desc or '1분당' in error_desc:
                        print("토큰 발급 제한: 1분당 1회 제한입니다. 잠시 후 다시 시도하세요.")
                        # 저장된 토큰이 있으면 사용
                        token_file = os.path.join(self.config_root, f"token_{self.svr}.json")
                        if os.path.exists(token_file):
                            try:
                                with open(token_file, 'r') as f:
                                    token_data = json.load(f)
                                    saved_token = token_data.get('access_token')
                                    if saved_token:
                                        print("저장된 토큰을 사용합니다.")
                                        self.access_token = saved_token
                                        self.token_expires_at = token_data.get('expires_at', time.time() + 3600)
                                        return self.access_token
                            except:
                                pass
                        raise ValueError("토큰 발급 제한: 1분 후 다시 시도하세요.")
                    
                    error_msg = f"403 Forbidden 오류가 발생했습니다.\n"
                    error_msg += f"URL: {url}\n"
                    error_msg += f"환경: {'실전투자' if self.svr == 'prod' else '모의투자'}\n"
                    error_msg += "가능한 원인:\n"
                    error_msg += "1. API 키 또는 시크릿이 잘못되었습니다\n"
                    error_msg += "2. API 키가 해당 환경(실전/모의)에 맞지 않습니다\n"
                    error_msg += "3. API 키가 활성화되지 않았습니다\n"
                    error_msg += f"4. 앱키 앞 4자리: {self.app_key[:4] if len(self.app_key) > 4 else 'N/A'}...\n"
                    error_msg += f"서버 응답: {error_detail}\n"
                    raise ValueError(error_msg)
                except:
                    error_msg = f"403 Forbidden 오류: {response.text}\n"
                    raise ValueError(error_msg)
            
            response.raise_for_status()
            result = response.json()
            
            self.access_token = result['access_token']
            # 토큰 만료 시간 설정 (보통 24시간, 여유있게 23시간으로 설정)
            self.token_expires_at = time.time() + (23 * 60 * 60)
            
            # 토큰 저장
            token_file = os.path.join(self.config_root, f"token_{self.svr}.json")
            with open(token_file, 'w') as f:
                json.dump({
                    'access_token': self.access_token,
                    'expires_at': self.token_expires_at
                }, f)
            
            return self.access_token
        except ValueError:
            raise
        except Exception as e:
            print(f"토큰 발급 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"서버 응답 상세: {error_detail}")
                except:
                    print(f"서버 응답: {e.response.text}")
            raise
    
    def get_headers(self, tr_id=None):
        """API 호출용 헤더 생성"""
        token = self.get_access_token()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id or "",
            "custtype": "P"
        }
        return headers
    
    def api_call(self, path, tr_id, params=None):
        """API 호출 공통 함수"""
        url = f"{self.base_url}{path}"
        headers = self.get_headers(tr_id)
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API 호출 실패: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"응답 내용: {e.response.text}")
            raise

# 전역 인스턴스
_kis_auth = None

def auth(svr=None):
    """인증 초기화"""
    global _kis_auth
    if svr:
        os.environ['KIS_SVR'] = svr
    _kis_auth = KISAuth()
    _kis_auth.get_access_token()
    return _kis_auth

def get_auth():
    """인증 객체 반환"""
    global _kis_auth
    if _kis_auth is None:
        _kis_auth = KISAuth()
        _kis_auth.get_access_token()
    return _kis_auth
