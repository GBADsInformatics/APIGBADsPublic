# Author: Matthew Szurkowski
# Last updated: May 2023

from fastapi.testclient import TestClient
from APIGBADsPublic.main import router

client = TestClient(router)


def test_dataportal_endpoint():
    response = client.get("/dataportal/")
    assert response.status_code == 200
