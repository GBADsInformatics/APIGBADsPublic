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
from app.api.v1 import dpm_endpoints, engine_endpoints, comments_endpoints, tail_endpoints, metadata_endpoints

BASE_URL = os.environ.get("BASE_URL", "")


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

app = FastAPI(
    docs_url=f"{BASE_URL}/docs",
    openapi_url=f"{BASE_URL}/openapi.json",
    title="GBADs Public API",
    description="This is our API for accessing GBADs public database tables and related functionalities.\n\n" \
                "See the [GBADs Knowledge Engine](https://gbadske.org) for more information about the project.\n\n" \
                "The Knowledge Engine endpoints are public, but the DPM and comments endpoints require authentication.",
    version="1.0.0",
    contact={
        "name": "GBADs Informatics Team",
        "url": "https://gbadske.org/about/"
    },
    swagger_ui_parameters={"syntaxHighlight": {"theme": "obsidian"}}
)


# Add middleware to suppress logging for the root endpoint
app.add_middleware(SuppressRootLoggingMiddleware, root_path=f"{BASE_URL}")

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
