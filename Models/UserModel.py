from pydantic import BaseModel, EmailStr


class UserRequestModel(BaseModel):
    email: EmailStr
