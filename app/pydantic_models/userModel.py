from pydantic import BaseModel, EmailStr


class LoginModel(BaseModel):
    email: EmailStr
    password: str


class RegisterUser(BaseModel):
    first_name: str
    second_name: str
    email: EmailStr
    role: str
    rule: str
    password: str


class DeleteUser(BaseModel):
    id: int
    email: EmailStr


class EditUser(BaseModel):
    id: int
    password: str
    new_password: str
