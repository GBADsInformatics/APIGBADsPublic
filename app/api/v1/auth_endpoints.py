from fastapi import APIRouter, Depends
from app.utils.auth import CognitoVerifier
from app.models.auth import CognitoUser

router = APIRouter()


@router.get("/profile", response_model=CognitoUser)
async def get_profile(
    user: CognitoUser = Depends(CognitoVerifier()),
) -> CognitoUser:
    """
    Endpoint to retrieve the authenticated user's profile information.
    Returns:
        CognitoUser: The authenticated user's profile information.
    """
    return user


# @router.get("/admin")
# async def admin_endpoint(
#     user: CognitoUser = Depends(CognitoVerifier(required_groups=["Admin"])),
# ):
#     """
#     Endpoint to retrieve the authenticated user's profile information.
#     Returns:
#         CognitoUser: The authenticated user's profile information.
#     """
#     return {"message": "Admin access granted"}
