import abc
import logging
import subprocess
from typing import List

import typer
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
    def compare(self, others: List[Self]):
        pass

    def simple_list_compare(self, attr_name, others: List[Self], tag):
        supported_values = []
        for other in others:
            value = getattr(other, attr_name)
            if value is not None:
                supported_values.append(value)
        self_value = getattr(self, attr_name)
        if self_value is None:
            return
        if self_value not in supported_values:
            typer.echo(
                f"Expected {tag} '{self_value}' not found in {attr_name}: Supported {supported_values}"
            )

    def more_than_at_least_one(self, attr_name, others: List[Self], tag):
        supported_values = []
        for other in others:
            value = getattr(other, attr_name)
            if value is not None:
                supported_values.append(value)
        self_value = getattr(self, attr_name)
        if self_value is None:
            return
        try:
            if not [value for value in supported_values if self_value >= value]:
                typer.echo(
                    f"Could not find a minimum match for {tag} in {attr_name}='{self_value}' from {supported_values}"
                )
        except Exception as e:
            logger.error(e)
