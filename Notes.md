# Notes

## Certificate error

While running `uv sync` you might get an error like the following

```bash
❯ uv sync
error: Request failed after 3 retries
  Caused by: Failed to download https://github.com/astral-sh/python-build-standalone/releases/download/20251120/cpython-3.10.19%2B20251120-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz
  Caused by: error sending request for url (https://github.com/astral-sh/python-build-standalone/releases/download/20251120/cpython-3.10.19%2B20251120-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz)
  Caused by: client error (Connect)
  Caused by: invalid peer certificate: UnknownIssuer
```

To circumvent this, run

```bash
uv sync --allow-insecure-host github.com --allow-insecure-host pypi.org --allow-insecure-host files.pythonhosted.org       
```

To install test dependencies add `--all-extras` to the above command and run.

------

## Local Setup

The following are the steps to have the CLI ready. This can help you run `dell-ai utils describe-system`

```bash
cd /home/ankitm.dell/
source .venv/bin/activate
cd dell-ai-internal/
export PATH="$PATH:$(pwd)/.venv/bin"
uv sync --all-extras
dell-ai utils describe-system
```

Now to run the `check-system` util, I am mocking the dell-ai API. It needs some more steps

```bash
# on a separate terminal
# same as before
cd /home/ankitm.dell/
source .venv/bin/activate
cd dell-ai-internal/
export PATH="$PATH:$(pwd)/.venv/bin"
uvicorn service:app
```

```bash
# back to the main shell
export DELL_AI_API_BASE_URL=http://localhost:8000
export HF_TOKEN="FAKE_TOKEN"
# please note that I have disabled SSL verification in my copy on the machine, otherwise you will get SSL verification errors
dell-ai utils check-system
```

> For posterity, to disable verification yourself, you can navigate to [dell-ai-internal/dell_ai/client.py](./dell_ai/client.py) , line 87 or in the `DellAIClient._make_request` function, add `verify=False` as an argument to the `self.session.request` method. Note that this is only a requirement for local development. For production, SSL verification should be enabled.
