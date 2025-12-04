import abc
import logging
import subprocess

from pydantic import BaseModel
from typing_extensions import Self

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


class ComparableBaseModel(BaseModel, abc.ABC):
    @abc.abstractmethod
    def compare(self, other: Self):
        pass
