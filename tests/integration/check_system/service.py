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
    """
    SKU method implementation to illustrate SKU parsing according to the structure in the resources directory
    """
    sku_list = []
    for file_name in resource_folder.iterdir():
        if file_name.is_dir():
            server = file_name.name
            for framework in (resource_folder / server).iterdir():
                if framework.is_dir():
                    if framework.name in ["intel", "nvidia", "amd"]:
                        for sku_name in (
                            resource_folder / server / framework.name
                        ).iterdir():
                            if sku_name.is_dir():
                                sku_list.append(
                                    f"{server.lower()}-{framework.name.lower()}-{sku_name.name.lower()}"
                                )
    return {"skus": sku_list}


@app.get("/skus/{sku_id}")
def sku(sku_id: str):
    """
    Get SKU from sku_id, should be in the resources folder
    
    :param sku_id: Description
    :type sku_id: str
    """
    server, framework, sku_name = sku_id.split("-")
    made_path = resource_folder / server / framework / sku_name
    assert (
        made_path.exists()
    ), f"Did not find server/framework/sku_name combination for {sku_id}"
    assert made_path.is_dir(), "Path should be a folder"
    for filename in made_path.iterdir():
        if filename.is_file() and filename.name.endswith(".json"):
            with open(filename, "r") as fp:
                return json.load(fp)["platform"]
    raise FileNotFoundError(f"{sku_id} not found")


@app.get("/skus/{sku_id}/sysinfo")
def sysinfo(sku_id: str):
    """
    Get sysinfo for the sku_id
    
    :param sku_id: Description
    :type sku_id: str
    """
    server, framework, sku_name = sku_id.split("-")
    sys_infos = []
    made_path = resource_folder / server / framework / sku_name
    assert (
        made_path.exists()
    ), f"Did not find server/framework/sku_name combination for {sku_id}"
    assert made_path.is_dir(), "Path should be a folder"
    for filename in made_path.iterdir():
        if filename.is_file() and filename.name.endswith(".json"):
            with open(filename, "r") as fp:
                sys_infos.append(json.load(fp)["sysinfo"])
    return sys_infos
