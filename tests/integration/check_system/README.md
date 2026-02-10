# Check system - Service Mock

To adhere to the way other CLI commands work, the `dell-ai utils check-system` CLI command also requests the SKU platform information from the Huggingface endpoint. Since we are adding the system information to the tested platforms for this feature, how it is being handled here is altering the response of the `/skus` endpoint.

This folder contains a mock of how the service will behave for the `/skus` endpoint. For this, we have a service here that just handles these requests. The following API changes have been made


## API Documentation

-------------------------------


<details>
<summary> <code>GET</code> <code>/skus</code> (Gets the SKUs by reading out the folder structure)</summary> 

##### Parameters
> None

##### Response
> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`        |    `{"skus": ["r760xa-nvidia-l40s", "xe9680-nvidia-h200"]}`                                |
> | `400`         | `application/json`                | `{"code":"400","message":"Bad Request"}`                            |

##### Example
```bash
curl -X GET http://localhost:8000/skus -H "Content-Type: application/json"
```

##### Description
This endpoint returns the list of SKUs available in the system. For this it reads the folder structure as shown below, and populates the names according to the folders

```bash
❯ tree resources

resources
├── r760xa
│   └── nvidia
│       └── l40s
│           ├── cuda128.json
│           └── cuda130.json
├── sysinfo.json
└── xe9680
    └── nvidia
        └── h200
            └── cuda128.json

7 directories, 4 files
```

</details>

-------------------------------

<details>
<summary> <code>GET</code> <code>/skus/{sku_id}</code> (Gets the SKU platform information by ID)</summary> 

##### Parameters
> | name              |  type     | data type      | description                         |
> |-------------------|-----------|----------------|-------------------------------------|
> | `sku_id` |  required | str   | The specific SKU string id        |

##### Response
> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`        |    `{"name": "R760xa Nvidia L40s", "server": "r760xa", "vendor": "NVIDIA", "gputype": "L40S", "gpuram": "46068", "totalgpucount": 4}`                                |
> | `400`         | `application/json`                | `{"code":"400","message":"Bad Request"}`                            |

##### Example
```bash
curl -X GET http://localhost:8000/skus/r760xa-nvidia-l40s -H "Content-Type: application/json"
```

##### Description
This endpoint returns the platform info of the SKU from the first file in the relevant folder, since the platform information is same for every file that is present. 

</details>

----------------

<details>
<summary> <code>GET</code> <code>/skus/{sku_id}/sysinfo</code> (Gets the SKU platform system information by ID)</summary> 

##### Parameters
> | name              |  type     | data type      | description                         |
> |-------------------|-----------|----------------|-------------------------------------|
> | `sku_id` |  required | str   | The specific SKU string id        |

##### Response
> | http code     | content-type                      | response                                                            |
> |---------------|-----------------------------------|---------------------------------------------------------------------|
> | `200`         | `application/json`        |    `{"os": ..., "software": ..., "hardware": ... }`                                |
> | `400`         | `application/json`                | `{"code":"400","message":"Bad Request"}`                            |

##### Example
```bash
curl -X GET http://localhost:8000/skus/r760xa-nvidia-l40s/sysinfo -H "Content-Type: application/json"
```

##### Description
This endpoint returns the system info list of all validated system info present in the relevant folder. Each file should have only one validated system info. 

</details>

----------------

Check the [`service.py`](./service.py) file for the implementation of the service.

## Testing the API

You need `uvicorn` or `fastapi[standard]` present to run the service. If you have run `uv sync --all-extras`, this package would be installed, otherwise you can perform a pip install of `fastapi[standard]`

To run the service, you can run the following command
```bash
cd tests/integration/check_system
python -m uvicorn service:app
```

This starts the service on local port 8000 by default. You can configure the port by passing a `--port` argument to the uvicorn command.

To ensure that `dell-ai` CLI interacts with this service, you can set the `DELL_AI_API_BASE_URL` environment variable to `http://localhost:8000`

```bash
export DELL_AI_API_BASE_URL=http://localhost:8000
export HF_TOKEN="FAKE_TOKEN"
dell-ai utils check-system
```

> Note that these variables would only enable the `check-system` CLI tool. The other API calls will not work. 

> Also note that you need to disable SSL verification in the CLI tool for this to work. To disable verification yourself, you can navigate to [dell_ai/client.py](../../../dell_ai/client.py) , line 87 or in the `DellAIClient._make_request` function, add `verify=False` as an argument to the `self.session.request` method, and then do a pip install or editable install. Note that this is only a requirement for local development. For production, SSL verification should be enabled.