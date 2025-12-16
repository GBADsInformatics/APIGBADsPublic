import logging
from typing import List, Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError


logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t%(name)s: %(message)s')
logger = logging.getLogger(__name__)


class CognitoAdapter:
    """
    A class to interact with AWS Cognito User Pools using boto3.
    This class provides methods to manage users in Cognito.
    """

    def __init__(self, region: str, user_pool_id: str, access_key: str = None, secret_key: str = None):
        """
        Initialize the Cognito adapter.

        Args:
            region (str): AWS region where the user pool is located
            user_pool_id (str): The Cognito User Pool ID
            access_key (str, optional): AWS access key ID. If not provided, uses default AWS credentials
            secret_key (str, optional): AWS secret access key. If not provided, uses default AWS credentials
        """
        self.user_pool_id = user_pool_id
        self.region = region

        try:
            if access_key and secret_key:
                self.client = boto3.client(
                    'cognito-idp',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                self.client = boto3.client('cognito-idp', region_name=region)
        except Exception as exc:
            logger.error("Error initializing Cognito client: %s", exc)
            raise

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user details from Cognito by username.

        Args:
            username (str): The username to look up

        Returns:
            Optional[Dict[str, Any]]: User details if found, None otherwise
        """
        try:
            response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                logger.info("User %s not found in Cognito", username)
                return None
            logger.error("Error getting user %s: %s", username, e)
            raise

    def get_user_by_sub(self, sub: str) -> Optional[Dict[str, Any]]:
        """
        Get user details from Cognito by sub (user ID).

        Args:
            sub (str): The Cognito user ID (sub claim)

        Returns:
            Optional[Dict[str, Any]]: User details if found, None otherwise
        """
        try:
            # Search for user by sub attribute
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'sub = "{sub}"',
                Limit=1
            )

            if response['Users']:
                return response['Users'][0]
            return None
        except ClientError as e:
            logger.error("Error getting user by sub %s: %s", sub, e)
            raise

    def list_users(self, limit: int = 60, pagination_token: str = None) -> Dict[str, Any]:
        """
        List users in the Cognito User Pool.

        Args:
            limit (int): Maximum number of users to return (max 60)
            pagination_token (str, optional): Token for pagination

        Returns:
            Dict[str, Any]: Response containing users list and pagination token
        """
        try:
            params = {
                'UserPoolId': self.user_pool_id,
                'Limit': min(limit, 60)
            }
            if pagination_token:
                params['PaginationToken'] = pagination_token

            response = self.client.list_users(**params)
            return response
        except ClientError as e:
            logger.error("Error listing users: %s", e)
            raise

    def create_user(
        self,
        username: str,
        email: str,
        temporary_password: str = None,
        email_verified: bool = True,
        send_invitation: bool = False,
        user_attributes: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user in Cognito.

        Args:
            username (str): Username for the new user
            email (str): Email address for the new user
            temporary_password (str, optional): Temporary password. If not provided, user gets email invitation
            email_verified (bool): Whether to mark email as verified (default True)
            send_invitation (bool): Whether to send invitation email (default False)
            user_attributes (Dict[str, str], optional): Additional user attributes

        Returns:
            Dict[str, Any]: Response from Cognito containing user details
        """
        try:
            attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true' if email_verified else 'false'}
            ]

            if user_attributes:
                for key, value in user_attributes.items():
                    attributes.append({'Name': key, 'Value': value})

            params = {
                'UserPoolId': self.user_pool_id,
                'Username': username,
                'UserAttributes': attributes,
                'DesiredDeliveryMediums': ['EMAIL'] if send_invitation else []
            }

            if temporary_password:
                params['TemporaryPassword'] = temporary_password
                params['MessageAction'] = 'SUPPRESS'  # Don't send welcome email if password provided

            response = self.client.admin_create_user(**params)
            logger.info("Created user %s in Cognito", username)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                logger.warning("User %s already exists in Cognito", username)
            logger.error("Error creating user %s: %s", username, e)
            raise

    def delete_user(self, username: str) -> None:
        """
        Delete a user from Cognito.

        Args:
            username (str): Username of the user to delete
        """
        try:
            self.client.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info("Deleted user %s from Cognito", username)
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                logger.warning("User %s not found in Cognito", username)
            else:
                logger.error("Error deleting user %s: %s", username, e)
                raise

    def update_user_attributes(self, username: str, attributes: Dict[str, str]) -> None:
        """
        Update user attributes in Cognito.

        Args:
            username (str): Username of the user to update
            attributes (Dict[str, str]): Dictionary of attributes to update
        """
        try:
            user_attributes = [
                {'Name': key, 'Value': value}
                for key, value in attributes.items()
            ]

            self.client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=user_attributes
            )
            logger.info("Updated attributes for user %s", username)
        except ClientError as e:
            logger.error("Error updating user %s: %s", username, e)
            raise

    def add_user_to_group(self, username: str, group_name: str) -> None:
        """
        Add a user to a Cognito group.

        Args:
            username (str): Username of the user
            group_name (str): Name of the group to add user to
        """
        try:
            self.client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=username,
                GroupName=group_name
            )
            logger.info("Added user %s to group %s", username, group_name)
        except ClientError as e:
            logger.error("Error adding user %s to group %s: %s", username, group_name, e)
            raise

    def remove_user_from_group(self, username: str, group_name: str) -> None:
        """
        Remove a user from a Cognito group.

        Args:
            username (str): Username of the user
            group_name (str): Name of the group to remove user from
        """
        try:
            self.client.admin_remove_user_from_group(
                UserPoolId=self.user_pool_id,
                Username=username,
                GroupName=group_name
            )
            logger.info("Removed user %s from group %s", username, group_name)
        except ClientError as e:
            logger.error("Error removing user %s from group %s: %s", username, group_name, e)
            raise

    def list_groups_for_user(self, username: str) -> List[str]:
        """
        List all groups a user belongs to.

        Args:
            username (str): Username of the user

        Returns:
            List[str]: List of group names
        """
        try:
            response = self.client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except ClientError as e:
            logger.error("Error listing groups for user %s: %s", username, e)
            raise

    def enable_user(self, username: str) -> None:
        """
        Enable a user account.

        Args:
            username (str): Username of the user to enable
        """
        try:
            self.client.admin_enable_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info("Enabled user %s", username)
        except ClientError as e:
            logger.error("Error enabling user %s: %s", username, e)
            raise

    def disable_user(self, username: str) -> None:
        """
        Disable a user account.

        Args:
            username (str): Username of the user to disable
        """
        try:
            self.client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            logger.info("Disabled user %s", username)
        except ClientError as e:
            logger.error("Error disabling user %s: %s", username, e)
            raise

    def get_user_sub(self, username: str) -> Optional[str]:
        """
        Get the sub (user ID) for a given username.

        Args:
            username (str): Username to look up

        Returns:
            Optional[str]: The user's sub (UUID) if found, None otherwise
        """
        user = self.get_user(username)
        if not user:
            return None

        # Extract sub from user attributes
        for attr in user.get('UserAttributes', []):
            if attr['Name'] == 'sub':
                return attr['Value']
        return None

    @staticmethod
    def extract_user_attributes(cognito_user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and parse user attributes from a Cognito user object.

        Args:
            cognito_user (Dict[str, Any]): Raw Cognito user object

        Returns:
            Dict[str, Any]: Parsed user attributes in a flat dictionary
        """
        attributes = {}

        # Extract standard fields
        attributes['username'] = cognito_user.get('Username', '')
        attributes['enabled'] = cognito_user.get('Enabled', True)
        attributes['user_status'] = cognito_user.get('UserStatus', '')
        attributes['created_date'] = str(cognito_user.get('UserCreateDate', ''))
        attributes['last_modified_date'] = str(cognito_user.get('UserLastModifiedDate', ''))

        # Extract attributes
        for attr in cognito_user.get('Attributes', []):
            name = attr['Name']
            value = attr['Value']

            if name == 'sub':
                attributes['user_id'] = value
            elif name == 'email':
                attributes['email'] = value
            elif name == 'email_verified':
                attributes['email_verified'] = value.lower() == 'true'
            elif name == 'given_name':
                attributes['given_name'] = value
            elif name == 'family_name':
                attributes['family_name'] = value
            elif name.startswith('custom:'):
                # Handle custom attributes
                custom_key = 'custom_' + name.replace('custom:', '')
                attributes[custom_key] = value

        # Set defaults for optional fields
        attributes.setdefault('user_id', '')
        attributes.setdefault('email', '')
        attributes.setdefault('email_verified', False)
        attributes.setdefault('given_name', None)
        attributes.setdefault('family_name', None)
        attributes.setdefault('groups', [])
        attributes.setdefault('custom_country', None)
        attributes.setdefault('custom_language', None)
        attributes.setdefault('custom_role', None)

        return attributes
