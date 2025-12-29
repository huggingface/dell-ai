import json
from pathlib import Path
from fastapi import FastAPI

app = FastAPI()


@app.get("/auth")
def auth():
    """
    Handles GET requests to the /auth endpoint, returning user authentication information.

    Returns:
        A JSON object containing user details, including username, name, org, canSeeOrg, canSeePrivateRepo, repoSorting, lastLogin, full_name, email, type, id, role, isAnonymous, and isOrganization.
    """
    return {
        "username": "your_username",
        "name": "Your Name",
        "org": None,
        "canSeeOrg": False,
        "canSeePrivateRepo": True,
        "repoSorting": "name",
        "lastLogin": "2023-02-20T14:30:00.000Z",
        "full_name": "Your Full Name",
        "email": "your_email@example.com",
        "type": "user",
        "id": 123456,
        "role": "reader",
        "isAnonymous": False,
        "isOrganization": False,
    }


resource_file = Path(__file__).parent / "resources" / "sysinfo.json"

@app.get("/skus")
def skus():
    with open(resource_file, "r") as fp:
        content = json.load(fp)
        return {"skus": list(content.keys())}

@app.get("/skus/{sku_id}")
def sku(sku_id: str):
    with open(resource_file, "r") as fp:
        content = json.load(fp)
        return content[sku_id]["platform"]


@app.get("/skus/{sku_id}/sysinfo")
def sysinfo(sku_id: str):
    with open(resource_file, "r") as fp:
        content = json.load(fp)
        return content[sku_id]["sysinfo"]