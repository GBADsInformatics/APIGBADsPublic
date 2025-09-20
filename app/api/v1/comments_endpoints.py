import json
import datetime
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from app.utils.auth import SlackJWTVerifier
from app.utils.dependencies import get_rds_adapter, get_s3_adapter
from app.adapters.s3_adapter import S3Adapter
from app.adapters.rds_adapter import RDSAdapter


router = APIRouter()


@router.post("/approve/{comment_id}")
async def approve_comment(
    comment_id: str,
    _: dict = Depends(
        SlackJWTVerifier(
            key_filename="app/public/keys/slackbot_comments_move_approve_key.pub",
            desired_app="slackbot_comments_move",
            desired_task="approve"
        )
    ),
    reviewer: Optional[str] = None,
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
    rds_adapter: RDSAdapter = Depends(
        get_rds_adapter(
            db_name="public_data",
            db_host=os.getenv("RDS_HOST"),
            db_user=os.getenv("RDS_USER"),
            db_password=os.getenv("RDS_PASS")
        )
    )
):
    """
    Approve a comment and move it to the approved folder.\n
    :param comment_id: The ID of the comment to approve.\n
    :param authorization_token: The JWT token for authorization.\n
    :param reviewer: Optional name of the reviewer approving the comment.\n
    :return: A message indicating success or failure.
    """
    try:
        comment_file = s3_adapter.download(
            bucket="gbads-comments",
            object_name=f"underreview/{comment_id}"
        )

        # Process the comment data
        json_data = json.loads(comment_file.decode('utf-8'))
        created = str(json_data["created"])[0:19]
        approved = str(datetime.datetime.now())[0:19]
        dashboard = str(json_data["dashboard"])
        table = str(json_data["table"])
        subject = str(json_data["subject"])
        message = str(json_data["message"])
        is_public = str(json_data["isPublic"]).upper()
        if is_public == "FALSE":
            name = "NULL"
            email = "NULL"
        else:
            name = str(json_data["name"])
            email = str(json_data["email"])
        if not reviewer:
            reviewer = "Unknown"

        # Insert into the database
        rds_adapter.insert(
            table="gbads_comments",
            values=(
                created, approved, dashboard, table, subject,
                message, name, email, is_public, reviewer
            )
        )

        # Move the comment file to the approved folder
        s3_adapter.move(
            bucket="gbads-comments",
            source_object_name=f"underreview/{comment_id}",
            destination_object_name=f"approved/{comment_id}"
        )

        return {"message": "Comment approved successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/deny/{comment_id}")
async def deny_comment(
    comment_id: str,
    _: dict = Depends(
        SlackJWTVerifier(
            key_filename="app/public/keys/slackbot_comments_move_deny_key.pub",
            desired_app="slackbot_comments_move",
            desired_task="deny"
        )
    ),
    s3_adapter: S3Adapter = Depends(get_s3_adapter),
):
    """
    Deny a comment and move it to the denied folder.\n
    :param comment_id: The ID of the comment to deny.\n
    :param authorization_token: The JWT token for authorization.\n
    :return: A message indicating success or failure.
    """
    try:
        # Move the comment file to the denied folder
        s3_adapter.move(
            bucket="gbads-comments",
            source_object_name=f"underreview/{comment_id}",
            destination_object_name=f"notapproved/{comment_id}"
        )
        return {"message": "Comment denied successfully"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
