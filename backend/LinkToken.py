from fastapi import APIRouter, HTTPException
import requests
import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import uuid
from pydantic import BaseModel

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app을 APIRouter로 변경
router = APIRouter()

# 환경 변수 로드
env_path = Path(__file__).parents[1] / '.env'
load_dotenv(dotenv_path=env_path)

# 환경 변수 검증
def validate_env_vars():
    required_vars = ["PLAID_CLIENT_ID", "PLAID_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# 앱 시작 시 환경 변수 검증
validate_env_vars()

# 환경 변수에서 Plaid 인증 정보 가져오기
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = "sandbox"
PLAID_BASE_URL = "https://sandbox.plaid.com"

class PublicTokenRequest(BaseModel):
    public_token: str

@router.post("/create_link_token")
async def create_link_token():
    try:
        logger.info("Creating Plaid Link token")
        url = f"{PLAID_BASE_URL}/link/token/create"
        
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "client_name": "California Property Mortgage",
            "products": ["auth", "transactions"],
            "country_codes": ["US"],
            "language": "en",
            "user": {
                "client_user_id": str(uuid.uuid4())
            }
        }
        
        logger.info(f"Sending request to Plaid: {url}")
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        logger.info(f"Plaid response status: {response.status_code}")
        logger.info(f"Plaid response: {response.text}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Plaid API error: {response.text}"
            )
            
        return response.json()

    except Exception as e:
        logger.error(f"Error creating link token: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exchange_token")
async def exchange_token(request: PublicTokenRequest):
    try:
        logger.info("Exchanging public token for access token")
        url = f"{PLAID_BASE_URL}/item/public_token/exchange"
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "client_id": PLAID_CLIENT_ID,
                "secret": PLAID_SECRET,
                "public_token": request.public_token
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Token exchange failed: {response.text}"
            )
            
        # Sandbox 테스트 데이터 추가
        return {
            "access_token": response.json().get("access_token"),
            "accounts": [],
            # 테스트용 더미 데이터
            "income": 120000,  # 연봉 $120,000
            "debt": 15000,    # 부채 $15,000
            "credit_score": 720  # 신용점수 720
        }

    except Exception as e:
        logger.error(f"Token exchange error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/accounts/{access_token}")
async def get_accounts(access_token: str):
    try:
        logger.info("Fetching account information")
        response = requests.post(
            f"https://{PLAID_ENV}.plaid.com/accounts/balance/get",
            headers={"Content-Type": "application/json"},
            json={
                "client_id": PLAID_CLIENT_ID,
                "secret": PLAID_SECRET,
                "access_token": access_token
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Account fetch failed: {response.text}")
            raise HTTPException(status_code=400, detail="계좌 정보 조회 실패")
            
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching accounts: {str(e)}")
        raise HTTPException(status_code=503, detail="Plaid 서비스 연결 실패")
    except Exception as e:
        logger.error(f"Account fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail="내부 서버 오류")