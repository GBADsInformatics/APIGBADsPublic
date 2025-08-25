from typing import Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    User creation schema for DPM.
    """
    user_firstname: str
    user_lastname: Optional[str] = None
    user_email: str
    user_country: str
    user_language: str
    user_role: Optional[str] = None


class User(BaseModel):
    """
    User schema for DPM.
    """
    user_id: int
    user_firstname: str
    user_lastname: Optional[str] = None
    user_email: str
    user_country: str
    user_language: str
    user_role: Optional[str] = None
