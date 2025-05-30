import time
from fastapi import APIRouter, Response, Depends
from sqlalchemy.orm import Session
from starlette import status
from app.common_functions.helper_functions import users_data_former
from app.common_functions.token_handler import JWTBearer
from app.pydantic_models.userModel import LoginModel, RegisterUser, DeleteUser, EditUser
from app.settings import DB
from app.sql_schemas.models import Users

router = APIRouter()
Time_Format = "%Y-%m-%d %H:%M:%S"


@router.post("/login")
def login(payload: LoginModel, response: Response = None, db: Session = Depends(DB)):
    try:
        payload = dict(payload)
        user = db.query(Users).filter_by(email=payload["email"]).first()
        if (
            user
            and (user := user.as_dict())
            and user["password"] == payload["password"]
        ):
            user.pop("password")
            access_token = JWTBearer.token_generator(payload)
            return {
                "data": user,
                "msg": "logged in successfully",
                "token": access_token,
            }
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"msg": "Invalid login credentials"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/users", dependencies=[Depends(JWTBearer())])
def users(response: Response = None, db: Session = Depends(DB)):
    try:
        users_list = (
            db.query(Users)
            .filter(~Users.is_deleted, ~Users.is_admin)
            .order_by(Users.id.desc())
            .all()
        )
        data = [users_data_former(item) for item in users_list]
        return {"data": data, "msg": "fetch successful"}
    except Exception as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/users/add_user", dependencies=[Depends(JWTBearer())])
def add_user(
    payload: RegisterUser, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = payload.model_dump()
        user_record_exists = (
            db.query(Users)
            .filter_by(email=payload["email"])
            .filter(~Users.is_deleted)
            .first()
        )
        if not user_record_exists:
            payload["timestamp"] = int(time.time())
            user = Users(**payload)
            db.add(user)
            db.commit()
            return {"msg": f"Added user {payload['email']}"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['email']} already exists"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/users/delete_user", dependencies=[Depends(JWTBearer())])
async def add_user(
    payload: DeleteUser, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = dict(payload)
        user_rec = db.query(Users).get({"id": payload["id"]})
        if user_rec:
            user_rec.is_deleted = True
            db.commit()
            return {"msg": f"Deleted user {payload['email']} Successfully"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['email']} doesn't exists"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}


@router.post("/users/edit_user", dependencies=[Depends(JWTBearer())])
async def add_user(
    payload: EditUser, response: Response = None, db: Session = Depends(DB)
):
    try:
        payload = dict(payload)
        user_rec = db.query(Users).get({"id": payload["id"]})
        if user_rec:
            user_rec.password = payload["new_password"]
            db.commit()
            return {"msg": "Password changed successfully"}
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": f"{payload['email']} doesn't exists"}
    except Exception as err:
        db.rollback()
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"msg": str(err)}
