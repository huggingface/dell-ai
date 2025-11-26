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
