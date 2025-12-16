import io
import os
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError
from app.models.schemas import User, UserModel
from app.models.auth import CognitoUser
from app.adapters.rds_adapter import RDSAdapter
from app.adapters.s3_adapter import S3Adapter
from app.adapters.cognito_adapter import CognitoAdapter
from app.utils.dependencies import get_rds_adapter, get_s3_adapter, get_cognito_adapter
from app.utils.auth import CognitoVerifier

router = APIRouter()


def verify_user_access(authenticated_user: CognitoUser, target_user_id: str) -> None:
    """
    Verify that the authenticated user has access to the target user's data.
    Admins can access any user's data. Regular users can only access their own data.

    Args:
        authenticated_user: The authenticated user from the token
        target_user_id: The user ID being accessed

    Raises:
        HTTPException: If user doesn't have permission
    """
    # Admins can access any user's data
    if "Admin" in authenticated_user.groups:
        return

    # Regular users can only access their own data
    if authenticated_user.user_id != target_user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this user's data"
        )


@router.post("/upload")
async def upload_file(
    bucket_name: str,
    object_name: str,
    file: UploadFile = File(...),
    current_user: CognitoUser = Depends(CognitoVerifier()),
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    Upload a file to S3.
    Regular users can upload to their own user folder (dpm/user_{user_id}/).
    Admins can upload anywhere.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        file (UploadFile): The file to upload.
        current_user (CognitoUser): The authenticated user.

    Returns:
        dict: Success message or raises HTTPException on failure.
    """
    try:
        # Extract user_id from the object path if present (e.g., dpm/user_123/file.yaml)
        if object_name.startswith("dpm/user_"):
            parts = object_name.split("/")
            if len(parts) >= 2:
                folder_user_id = parts[1].replace("user_", "")
                # Verify user has access to this folder
                verify_user_access(current_user, folder_user_id)
        elif "Admin" not in current_user.groups:
            # Non-admins can only upload to their own user folder
            raise HTTPException(
                status_code=403,
                detail="Regular users must upload to their own user folder (dpm/user_{user_id}/)"
            )

        s3_adapter.upload(bucket_name, object_name, fileobj=file.file)
        return {"message": "File uploaded successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/download")
async def download_file(
    bucket_name: str,
    object_name: str,
    current_user: CognitoUser = Depends(CognitoVerifier()),
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    Download a file from S3.
    Regular users can download from their own user folder.
    Admins can download from anywhere.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        current_user (CognitoUser): The authenticated user.

    Returns:
        StreamingResponse: A streaming response to download the file.

    Raises:
        HTTPException: For file not found or internal server errors.
    """
    try:
        # Extract user_id from the object path if present
        if object_name.startswith("dpm/user_"):
            parts = object_name.split("/")
            if len(parts) >= 2:
                folder_user_id = parts[1].replace("user_", "")
                verify_user_access(current_user, folder_user_id)
        elif "Admin" not in current_user.groups:
            raise HTTPException(
                status_code=403,
                detail="Regular users can only download from their own user folder"
            )

        file_content = s3_adapter.download(bucket_name, object_name)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found or empty")
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={object_name}"}
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/list", response_model = List[str])
async def list_files(
    bucket_name: str,
    prefix: str = "",  # Optional folder path
    current_user: CognitoUser = Depends(CognitoVerifier()),
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    List all filenames in a specified S3 bucket folder.
    Regular users can only list files in their own user folder.
    Admins can list files anywhere.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str, optional): The folder path inside the bucket. Defaults to root ("").
        current_user (CognitoUser): The authenticated user.

    Returns:
        List[str]: A list of filenames in the specified folder.
    """
    try:
        # Extract user_id from the prefix if present
        if prefix.startswith("dpm/user_"):
            parts = prefix.split("/")
            if len(parts) >= 2:
                folder_user_id = parts[1].replace("user_", "")
                verify_user_access(current_user, folder_user_id)
        elif "Admin" not in current_user.groups:
            raise HTTPException(
                status_code=403,
                detail="Regular users can only list files in their own user folder"
            )

        files = s3_adapter.list_files(bucket_name=bucket_name, prefix=prefix)
        return files
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/delete")
async def delete_file(
    bucket_name: str,
    object_name: str,
    current_user: CognitoUser = Depends(CognitoVerifier()),
    s3_adapter: S3Adapter = Depends(get_s3_adapter)
):
    """
    Delete a file from S3.
    Regular users can delete files from their own user folder.
    Admins can delete files from anywhere.

    Args:
        bucket_name (str): The name of the S3 bucket.
        object_name (str): The name of the object in S3.
        current_user (CognitoUser): The authenticated user.

    Returns:
        dict: Success message or raises HTTPException on failure.
    """
    try:
        # Extract user_id from the object path if present
        if object_name.startswith("dpm/user_"):
            parts = object_name.split("/")
            if len(parts) >= 2:
                folder_user_id = parts[1].replace("user_", "")
                verify_user_access(current_user, folder_user_id)
        elif "Admin" not in current_user.groups:
            raise HTTPException(
                status_code=403,
                detail="Regular users can only delete files from their own user folder"
            )

        s3_adapter.delete(bucket_name, object_name)
        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/users", response_model=List[User])
async def list_users(
    current_user: CognitoUser = Depends(CognitoVerifier(required_groups=["Admin"])),
    cognito_adapter: CognitoAdapter = Depends(get_cognito_adapter)
):
    """
    List all users from Cognito.
    Only admins can list all users.
    :return: A list of User objects from Cognito.
    """
    try:
        # Fetch all users from Cognito (may need pagination for large user pools)
        all_users = []
        pagination_token = None

        while True:
            response = cognito_adapter.list_users(limit=60, pagination_token=pagination_token)
            cognito_users = response.get('Users', [])

            for cognito_user in cognito_users:
                # Extract user attributes
                user_attrs = CognitoAdapter.extract_user_attributes(cognito_user)

                # Get user's groups
                try:
                    groups = cognito_adapter.list_groups_for_user(user_attrs['username'])
                    user_attrs['groups'] = groups
                except (KeyError, ClientError):
                    user_attrs['groups'] = []

                # Create User object
                all_users.append(User(**user_attrs))

            # Check if there are more users to fetch
            pagination_token = response.get('PaginationToken')
            if not pagination_token:
                break

        return all_users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users from Cognito: {str(e)}") from e


@router.get("/user/{user_id}", response_model=User)
async def get_user_data(
    user_id: str,
    current_user: CognitoUser = Depends(CognitoVerifier()),
    cognito_adapter: CognitoAdapter = Depends(get_cognito_adapter)
):
    """
    Get user data from Cognito by user ID (sub).
    Admins can get any user's data. Regular users can only get their own data.
    :param user_id: The Cognito user ID (sub) of the user to retrieve.
    :return: A User object with user data from Cognito.
    """
    try:
        # Verify access
        verify_user_access(current_user, user_id)

        # Get user by sub
        cognito_user = cognito_adapter.get_user_by_sub(user_id)

        if not cognito_user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found in Cognito")

        # Extract user attributes
        user_attrs = CognitoAdapter.extract_user_attributes(cognito_user)

        # Get user's groups
        try:
            groups = cognito_adapter.list_groups_for_user(user_attrs['username'])
            user_attrs['groups'] = groups
        except (KeyError, ClientError):
            user_attrs['groups'] = []

        return User(**user_attrs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user from Cognito: {str(e)}") from e


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: str,
    current_user: CognitoUser = Depends(CognitoVerifier()),
    cognito_adapter: CognitoAdapter = Depends(get_cognito_adapter)
):
    """
    Delete user from Cognito.
    Admins can delete any user. Regular users can only delete their own account.
    :param user_id: The Cognito user ID (sub) of the user to delete.
    :return: A success message.
    """
    try:
        # Verify access
        verify_user_access(current_user, user_id)

        # First, get the user to find their username (required for deletion)
        cognito_user = cognito_adapter.get_user_by_sub(user_id)

        if not cognito_user:
            raise HTTPException(status_code=404, detail=f"No user exists with ID {user_id}")

        # Extract username
        username = cognito_user.get('Username')
        if not username:
            raise HTTPException(status_code=500, detail="Could not determine username for deletion")

        # Delete the user from Cognito
        cognito_adapter.delete_user(username)

        return {"message": "User deleted successfully from Cognito"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user from Cognito: {str(e)}") from e


@router.get("/models", response_model=List[UserModel])
async def list_user_models(
    user_id: Optional[str] = Query(None, description="User ID - if not provided, lists your own models (or all models if admin)."),
    current_user: CognitoUser = Depends(CognitoVerifier()),
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_name="dpm",
        db_host=os.getenv("RDS_HOST"),
        db_user=os.getenv("RDS_USER"),
        db_password=os.getenv("RDS_PASS")
    ))
):
    """
    List user models in the database.
    Admins can list all models or filter by user_id.
    Regular users can only list their own models.
    :param user_id: Optional Cognito user ID (sub) to filter models by user.
    :return: A list of UserModel objects.
    """
    try:
        # Determine which user_id to query
        if user_id is None:
            # No user_id provided
            if "Admin" in current_user.groups:
                # Admins can see all models
                query_user_id = None
            else:
                # Regular users see their own models
                query_user_id = current_user.user_id
        else:
            # user_id was explicitly provided - verify access
            verify_user_access(current_user, user_id)
            query_user_id = user_id

        def status_priority(status):
            if status and 'error' in status:
                return 3
            if status and 'in_progress' in status:
                return 2
            if status and status == 'completed':
                return 1
            return 0

        if query_user_id is None:
            models, _, _ = rds_adapter.select(table_name='user_models2')
        else:
            models, _, _ = rds_adapter.select(table_name='user_models2', where="user_id = %s", where_params=(query_user_id,))

        model_dict = {}
        for row in models:
            uid, name, status, file_input, file_outputs, date_created, date_completed, _, run_time = row
            if name not in model_dict:
                model_dict[name] = UserModel(
                    user_id=uid,
                    name=name,
                    status=status,
                    file_inputs=[file_input],
                    file_outputs=file_outputs.split(',') if file_outputs else [],
                    date_created=str(date_created),
                    date_completed=str(date_completed),
                    run_times=[run_time] if run_time else []
                )
            else:
                # Update existing entry
                existing_model = model_dict[name]
                if status_priority(status) > status_priority(existing_model.status):
                    existing_model.status = status
                existing_model.file_inputs.append(file_input)
                existing_model.file_outputs.extend(file_outputs.split(',') if file_outputs else [])
                # Append run time
                if run_time:
                    existing_model.run_times.append(run_time)
        return list(model_dict.values())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}") from e


@router.post("/merge-user")
async def merge_user(
    existing_user_id: str = Query(..., description="The existing user ID to migrate from"),
    new_user_id: str = Query(..., description="The new user ID to migrate to"),
    current_user: CognitoUser = Depends(CognitoVerifier(required_groups=["Admin"])),
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    rds_adapter: RDSAdapter = Depends(get_rds_adapter(
        db_name="dpm",
        db_host=os.getenv("RDS_HOST"),
        db_user=os.getenv("RDS_USER"),
        db_password=os.getenv("RDS_PASS")
    ))
):
    """
    Merge or rename a user by migrating all their data from one user ID to another.
    This endpoint will:
    1. Copy all S3 files from user_{existing_id} to user_{new_id} in inputs, outputs, and storage buckets
       (Lambda functions triggered by S3 events will create new database rows with new user_id)
    2. Update user_id in metadata JSON files in the inputs bucket before uploading
    3. Delete old database rows with the old user_id (new rows already created by Lambda)
    4. Delete old S3 files after successful migration
    
    Only admins can perform this operation.
    
    Args:
        existing_user_id: The current user ID to migrate from
        new_user_id: The new user ID to migrate to
        
    Returns:
        dict: Summary of the migration operation
    """
    try:
        buckets = [
            "gbads-modelling-inputs",
            "gbads-modelling-outputs",
            "gbads-modelling-storage"
        ]
        
        migration_summary = {
            "s3_files_copied": 0,
            "metadata_files_updated": 0,
            "database_rows_deleted": 0,
            "errors": []
        }
        
        # Step 1: Copy S3 files (non-metadata files first, metadata files will be handled separately)
        # This will trigger Lambda functions that create new database rows with the new user_id
        metadata_files = []
        
        for bucket_name in buckets:
            old_prefix = f"dpm/user_{existing_user_id}/"
            new_prefix = f"dpm/user_{new_user_id}/"
            
            try:
                # List all files in the old user folder
                files = s3_adapter.list_files(bucket_name=bucket_name, prefix=old_prefix)
                
                for file_key in files:
                    try:
                        # Calculate new file key
                        new_file_key = file_key.replace(old_prefix, new_prefix, 1)
                        
                        # Skip metadata files for now, we'll handle them after
                        if bucket_name == "gbads-modelling-inputs" and file_key.endswith("_metadata.json"):
                            metadata_files.append((bucket_name, file_key, new_file_key))
                        else:
                            # For non-metadata files, just copy
                            s3_adapter.copy(bucket_name, file_key, new_file_key)
                            migration_summary["s3_files_copied"] += 1
                        
                    except Exception as file_error:
                        error_msg = f"Error copying {file_key}: {str(file_error)}"
                        migration_summary["errors"].append(error_msg)
                        
            except Exception as bucket_error:
                error_msg = f"Error accessing bucket {bucket_name}: {str(bucket_error)}"
                migration_summary["errors"].append(error_msg)
        
        # Step 2: Update and upload metadata files with new user_id
        # This will trigger Lambda to create rows with correct user_id in metadata
        for bucket_name, file_key, new_file_key in metadata_files:
            try:
                # Download the metadata file
                file_content = s3_adapter.download(bucket_name, file_key)
                
                if file_content:
                    # Parse JSON
                    metadata = json.loads(file_content.decode('utf-8'))
                    
                    # Update user_id (convert to string as per requirements)
                    metadata['user_id'] = new_user_id
                    
                    # Upload updated metadata to new location
                    updated_content = json.dumps(metadata, indent=2).encode('utf-8')
                    s3_adapter.upload(bucket_name, new_file_key, fileobj=io.BytesIO(updated_content))
                    
                    migration_summary["metadata_files_updated"] += 1
                    migration_summary["s3_files_copied"] += 1
                else:
                    raise Exception(f"Failed to download metadata file: {file_key}")
                    
            except Exception as file_error:
                error_msg = f"Error updating metadata {file_key}: {str(file_error)}"
                migration_summary["errors"].append(error_msg)
        
        # Step 3: Delete old database rows (Lambda already created new ones with new user_id)
        # We delete old rows instead of updating to avoid conflicts
        
        # Delete from user_models2 table
        try:
            rows_affected = rds_adapter.delete(
                table="user_models2",
                where="user_id = %s",
                params=(existing_user_id,)
            )
            migration_summary["database_rows_deleted"] += rows_affected
        except Exception as db_error:
            error_msg = f"Error deleting old rows from user_models2: {str(db_error)}"
            migration_summary["errors"].append(error_msg)
        
        # Delete from user_dashboards2 table
        try:
            rows_affected = rds_adapter.delete(
                table="user_dashboards2",
                where="user_id = %s",
                params=(existing_user_id,)
            )
            migration_summary["database_rows_deleted"] += rows_affected
        except Exception as db_error:
            error_msg = f"Error deleting old rows from user_dashboards2: {str(db_error)}"
            migration_summary["errors"].append(error_msg)
        
        # Step 3: Delete old S3 files (only if no errors in migration)
        if not migration_summary["errors"]:
            for bucket_name in buckets:
                old_prefix = f"dpm/user_{existing_user_id}/"
                
                try:
                    files = s3_adapter.list_files(bucket_name=bucket_name, prefix=old_prefix)
                    
                    for file_key in files:
                        try:
                            s3_adapter.delete(bucket_name, file_key)
                        except Exception as delete_error:
                            error_msg = f"Error deleting old file {file_key}: {str(delete_error)}"
                            migration_summary["errors"].append(error_msg)
                            
                except Exception as bucket_error:
                    error_msg = f"Error cleaning up bucket {bucket_name}: {str(bucket_error)}"
                    migration_summary["errors"].append(error_msg)
        
        # Return summary
        if migration_summary["errors"]:
            return {
                "status": "completed_with_errors",
                "message": f"User migration completed with some errors. Copied {migration_summary['s3_files_copied']} S3 files, "
                          f"updated {migration_summary['metadata_files_updated']} metadata files, "
                          f"and deleted {migration_summary['database_rows_deleted']} old database rows.",
                "summary": migration_summary
            }
        else:
            return {
                "status": "success",
                "message": f"User migration completed successfully. Copied {migration_summary['s3_files_copied']} S3 files, "
                          f"updated {migration_summary['metadata_files_updated']} metadata files, "
                          f"and deleted {migration_summary['database_rows_deleted']} old database rows.",
                "summary": migration_summary
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during user migration: {str(e)}") from e
