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

    def __init__(self, **data):
        super().__init__(**data)
        self.user_firstname = self.user_firstname.strip()
        if self.user_lastname:
            self.user_lastname = self.user_lastname.strip()
        self.user_email = self.user_email.strip()
        self.user_country = self.user_country.strip()
        if self.user_language:
            self.user_language = self.user_language.strip()
        if self.user_role:
            self.user_role = self.user_role.strip()


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
