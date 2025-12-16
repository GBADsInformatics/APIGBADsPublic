from typing import List, Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    """
    User creation schema for DPM - creates a user in Cognito.
    """
    username: str
    email: str
    temporary_password: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    send_invitation: bool = False

    # Custom attributes (must be defined in your Cognito User Pool)
    custom_country: Optional[str] = None
    custom_language: Optional[str] = None
    custom_role: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.username = self.username.strip()
        self.email = self.email.strip()
        if self.given_name:
            self.given_name = self.given_name.strip()
        if self.family_name:
            self.family_name = self.family_name.strip()
        if self.custom_country:
            self.custom_country = self.custom_country.strip()
        if self.custom_language:
            self.custom_language = self.custom_language.strip()
        if self.custom_role:
            self.custom_role = self.custom_role.strip()


class User(BaseModel):
    """
    User schema for DPM - represents a Cognito user.
    """
    user_id: str  # Cognito user ID (sub)
    username: str  # Cognito username
    email: str
    email_verified: bool = False
    enabled: bool = True
    user_status: str  # CONFIRMED, UNCONFIRMED, FORCE_CHANGE_PASSWORD, etc.
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    groups: List[str] = []
    created_date: Optional[str] = None
    last_modified_date: Optional[str] = None

    # Custom attributes (if you have them in Cognito)
    custom_country: Optional[str] = None
    custom_language: Optional[str] = None
    custom_role: Optional[str] = None


class UserModel(BaseModel):
    """
    User model schema for DPM.
    """
    user_id: str  # Cognito user ID (sub)
    name: str
    status: str
    file_inputs: List[str] = []
    file_outputs: List[str] = []
    date_created: str
    date_completed: Optional[str] = None
    run_times: List[float] = []
