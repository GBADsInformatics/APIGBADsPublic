"""
This module sets up the FastAPI application for the GBADs public API.

The application architecture includes endpoints, adapters, and utilities for database interactions.

It includes the following components:
- `engine_endpoints`: Handles queries to the GBADs public database.
- `dpm_endpoints`: Manages endpoints related to the Dynamic Population Model.
- `comments_endpoints`: Facilitates dashboard comments via Slack.
- `tail_endpoints`: Manages endpoints related to the TAIL dashboard.

Authors:
    William Fitzjohn
    Matthew Szurkowski
    Deborah Stacey
    Ian McKechnie
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.openapi.utils import get_openapi
from app.api.v1 import auth_endpoints, dpm_endpoints, engine_endpoints, comments_endpoints, tail_endpoints, metadata_endpoints

BASE_URL = os.environ.get("BASE_URL", "")

# Cognito configuration
COGNITO_REGION = os.environ.get("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_DOMAIN = os.environ.get("COGNITO_DOMAIN", "")  # e.g., "myapp-dev-auth"
COGNITO_CLIENT_ID_SWAGGER = os.environ.get("COGNITO_CLIENT_ID_SWAGGER", "")


# Helper to determine the Cognito host to use for OAuth URLs.
def _cognito_host(domain: str, region: str) -> str:
    """
    Accepts either a Cognito domain prefix (e.g. "myapp-dev-auth") or a full custom domain
    (e.g. "login.gbadske.org" or "https://login.gbadske.org") and returns the host to use
    in OAuth URLs.
    """
    if not domain:
        return ""
    # If user provided a full URL, extract the host
    try:
        from urllib.parse import urlparse
        parsed = urlparse(domain)
        if parsed.netloc:
            return parsed.netloc
    except Exception:
        # fall back to simple checks below
        pass

    # If domain contains a dot, treat it as a full domain (custom domain)
    if "." in domain:
        return domain

    # Otherwise assume it's a Cognito user pool domain prefix
    return f"{domain}.auth.{region}.amazoncognito.com"


# Build Cognito URLs
COGNITO_HOST = _cognito_host(COGNITO_DOMAIN, COGNITO_REGION)
COGNITO_AUTHORIZATION_URL = f"https://{COGNITO_HOST}/oauth2/authorize" if COGNITO_HOST else ""
COGNITO_TOKEN_URL = f"https://{COGNITO_HOST}/oauth2/token" if COGNITO_HOST else ""


class SuppressRootLoggingMiddleware:
    """
    Middleware to suppress logging for requests to the root endpoint.
    """
    def __init__(self, inner_app, root_path):
        self.app = inner_app
        self.root_path = root_path.rstrip('/') + '/'

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and (scope["path"] == self.root_path or scope["path"] == self.root_path.rstrip('/')):
            # Temporarily suppress logging for this request
            logger = logging.getLogger("uvicorn.access")
            prev_level = logger.level
            logger.setLevel(logging.CRITICAL)
            try:
                await self.app(scope, receive, send)
            finally:
                logger.setLevel(prev_level)
        else:
            await self.app(scope, receive, send)


# OAuth2 scheme for Swagger UI (only if Cognito is configured)
oauth2_scheme = None
if COGNITO_DOMAIN and COGNITO_CLIENT_ID_SWAGGER:
    oauth2_scheme = OAuth2AuthorizationCodeBearer(
        authorizationUrl=COGNITO_AUTHORIZATION_URL,
        tokenUrl=COGNITO_TOKEN_URL,
        scopes={
            "openid": "OpenID Connect",
            "email": "Email address",
            "profile": "User profile information"
        }
    )

app = FastAPI(
    docs_url=f"{BASE_URL}/docs",
    openapi_url=f"{BASE_URL}/openapi.json",
    title="GBADs Public API",
    description="This is our API for accessing GBADs public database tables and related functionalities.\n\n" \
                "See the [GBADs Knowledge Engine](https://gbadske.org) for more information about the project.\n\n" \
                "The Knowledge Engine endpoints are public, but the DPM and comments endpoints require authentication.\n\n" \
                "## Authentication\n" \
                "- **Legacy Token**: Use `Bearer <token>` in the Authorization header\n" \
                "- **Cognito OAuth2**: Click the 'Authorize' button and log in with your Cognito credentials",
    version="1.0.0",
    contact={
        "name": "GBADs Informatics Team",
        "url": "https://gbadske.org/about/"
    },
    swagger_ui_parameters={
        "syntaxHighlight": {"theme": "obsidian"}
    },
    swagger_ui_oauth2_redirect_url=f"{BASE_URL}/docs/oauth2-redirect",
    # Swagger UI OAuth2 configuration (only if Cognito is configured)
    swagger_ui_init_oauth={
        "clientId": COGNITO_CLIENT_ID_SWAGGER,
        "appName": "GBADs Public API - Swagger UI",
        "scopes": "openid email profile",
        "usePkceWithAuthorizationCodeGrant": False  # Disable PKCE for implicit flow
    } if COGNITO_DOMAIN and COGNITO_CLIENT_ID_SWAGGER else None
)


# Manually add OAuth2 security scheme to OpenAPI if Cognito is configured
def custom_openapi():
    """
    Generate custom OpenAPI schema with Cognito OAuth2 security scheme if configured.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add Cognito OAuth2 security scheme if configured
    if COGNITO_DOMAIN and COGNITO_CLIENT_ID_SWAGGER:
        openapi_schema["components"]["securitySchemes"]["CognitoOAuth2"] = {
            "type": "oauth2",
            "flows": {
                "implicit": {
                    "authorizationUrl": COGNITO_AUTHORIZATION_URL,
                    "scopes": {
                        "openid": "OpenID Connect",
                        "email": "Email address",
                        "profile": "User profile information"
                    }
                }
            }
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to suppress logging for the root endpoint
app.add_middleware(SuppressRootLoggingMiddleware, root_path=f"{BASE_URL}")

app.include_router(auth_endpoints.router, prefix=f"{BASE_URL}/auth", tags=["User Authentication"])
app.include_router(engine_endpoints.router, prefix=f"{BASE_URL}", tags=["Knowledge Engine"])
app.include_router(dpm_endpoints.router, prefix=f"{BASE_URL}/dpm", tags=["Dynamic Population Model"])
app.include_router(comments_endpoints.router, prefix=f"{BASE_URL}/slack", tags=["Dashboard Comments"])
app.include_router(tail_endpoints.router, prefix=f"{BASE_URL}/tail", tags=["TAIL Backend"])
app.include_router(metadata_endpoints.router, prefix=f"{BASE_URL}/meta-api", tags=["Metadata API"])

@app.get(f"{BASE_URL}/", include_in_schema=False)
@app.head(f"{BASE_URL}/", include_in_schema=False)
async def root():
    """
    Root endpoint for the API.
    """
    return {"message": "Welcome to the public GBADs database tables!"}
