"""Environment variable management for the Dell AI SDK."""

import json
import os
from pathlib import Path
from typing import Dict, Optional

# Name of the per-directory (local) environment variables file
LOCAL_ENV_FILENAME = ".dell-ai-env.json"


def get_global_env_path() -> Path:
    """Get the path to the global environment variables file."""
    return Path.home() / ".config" / "dell-ai" / "env.json"


def get_local_env_path() -> Path:
    """Get the path to the local (current working directory) env file."""
    return Path.cwd() / LOCAL_ENV_FILENAME


def load_env_file(path: Path) -> Dict[str, str]:
    """
    Load environment variables from a JSON file.

    Args:
        path: Path to the JSON env file

    Returns:
        A dictionary containing the environment variables
    """
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_env_file(path: Path, env_vars: Dict[str, str]) -> None:
    """
    Save environment variables to a JSON file.

    Args:
        path: Path to the JSON env file
        env_vars: Dictionary of environment variables to save
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(env_vars, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save env file at {path}: {str(e)}")


def set_env_var(key: str, value: str, is_global: bool = False) -> None:
    """
    Set an environment variable locally or globally.

    Args:
        key: The environment variable key
        value: The environment variable value
        is_global: If True, set globally; otherwise set in the current directory
    """
    path = get_global_env_path() if is_global else get_local_env_path()
    env_vars = load_env_file(path)
    env_vars[key] = value
    save_env_file(path, env_vars)
    # Also set in active environment process
    os.environ[key] = value


def get_env_var(key: str) -> Optional[str]:
    """
    Get an environment variable by checking the active environment,
    followed by the local env file, and then the global env file.

    Args:
        key: The environment variable key

    Returns:
        The value of the environment variable if found, None otherwise
    """
    # First look at active os.environ
    if key in os.environ:
        return os.environ[key]

    # Then look at local env
    local_vars = load_env_file(get_local_env_path())
    if key in local_vars:
        return local_vars[key]

    # Then look at global env
    global_vars = load_env_file(get_global_env_path())
    if key in global_vars:
        return global_vars[key]

    return None


def delete_env_var(key: str, is_global: bool = False) -> bool:
    """
    Delete an environment variable from local or global config.

    Args:
        key: The environment variable key
        is_global: If True, delete from global; otherwise delete from local

    Returns:
        True if the variable was deleted, False if it didn't exist
    """
    path = get_global_env_path() if is_global else get_local_env_path()
    env_vars = load_env_file(path)
    if key in env_vars:
        del env_vars[key]
        save_env_file(path, env_vars)
        if key in os.environ:
            del os.environ[key]
        return True
    return False


def list_env_vars(is_global: Optional[bool] = None) -> Dict[str, str]:
    """
    List environment variables.

    Args:
        is_global: If True, list only global; if False, list only local;
                   if None, list combined (local overrides global)

    Returns:
        A dictionary of environment variables
    """
    if is_global is True:
        return load_env_file(get_global_env_path())
    elif is_global is False:
        return load_env_file(get_local_env_path())
    else:
        global_vars = load_env_file(get_global_env_path())
        local_vars = load_env_file(get_local_env_path())
        # Local overrides global
        return {**global_vars, **local_vars}


def load_all_env_to_os() -> None:
    """
    Load all local and global environment variables into os.environ.
    This is called automatically during SDK initialization and CLI startup.
    """
    for k, v in list_env_vars().items():
        if k not in os.environ:
            os.environ[k] = v
