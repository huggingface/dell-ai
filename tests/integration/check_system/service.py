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
    return {}


resource_file = Path(__file__).parent / "resources" / "sysinfo.json"
resource_folder = Path(__file__).parent / "resources"

@app.get("/skus")
def skus():
    sku_list = []
    for file_name in resource_folder.iterdir():
        if file_name.is_dir():
            server = file_name.name
            for framework in (resource_folder / server).iterdir():
                if framework.is_dir():
                    assert framework.name in ["intel", "nvidia", "amd"], "Not a valid framework"
                    for sku_name in (resource_folder / server / framework.name).iterdir():
                        if sku_name.is_dir():
                            sku_list.append(f"{server.lower()}-{framework.name.lower()}-{sku_name.name.lower()}")
    return sku_list



@app.get("/skus/{sku_id}")
def sku(sku_id: str):
    server, framework, sku_name = sku_id.split("-")
    for files in (resource_folder / server / framework / sku_name).iterdir():
        if files.is_file():
            with open(files, "r") as fp:
                return json.load(fp)["platform"]
    raise FileNotFoundError(f"{sku_id} not found")


@app.get("/skus/{sku_id}/sysinfo")
def sysinfo(sku_id: str):
    server, framework, sku_name = sku_id.split("-")
    sys_infos = []
    for files in (resource_folder / server / framework / sku_name).iterdir():
        if files.is_file():
            with open(files, "r") as fp:
                sys_infos.append(json.load(fp)["sysinfo"])
    return sys_infos
