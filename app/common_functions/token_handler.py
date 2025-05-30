from datetime import datetime, timedelta
import jwt
from fastapi import status
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = 'pe0RHpCHH8yWEIQvlfxG7Q=='
ALGORITHM = 'HS256'


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=401, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=401, detail="Invalid authorization code.")

    @staticmethod
    def verify_jwt(jwt_token: str) -> bool:
        is_token_valid: bool = False

        try:
            payload = JWTBearer.verify_token(jwt_token)
        except:
            payload = None

        if payload:
            is_token_valid = True
        return is_token_valid

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    @staticmethod
    def token_generator(data: dict):
        payload = {
            "data": data,
            "exp": datetime.now() + timedelta(hours=5)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
