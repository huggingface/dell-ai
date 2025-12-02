import logging
import subprocess

logger = logging.getLogger(__name__)

def cmd_stdout(process_args, *args, **kwargs):
    try:
        return subprocess.run(
            process_args, capture_output=True, text=True, check=True, *args, **kwargs
        ).stdout
    except FileNotFoundError:  # command not found
        return None
    except subprocess.CalledProcessError as e:
        logger.error(e)
        return None