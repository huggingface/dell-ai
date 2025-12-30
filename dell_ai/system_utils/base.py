import abc
import subprocess
from typing import Any, List, Literal

import rich
from pydantic import BaseModel
from typing_extensions import Self


def cmd_stdout(process_args, *args, **kwargs):
    try:
        return subprocess.run(
            process_args, capture_output=True, text=True, check=True, *args, **kwargs
        ).stdout
    except FileNotFoundError:  # command not found
        return None
    except subprocess.CalledProcessError as e:
        rich.print(e)
        return None


class ComparableBaseModel(BaseModel, abc.ABC):
    @abc.abstractmethod
    def compare(self, others: List[Self]):
        pass

    def simple_list_compare(
        self,
        attr_name,
        others: List[Self],
        tag,
        level: Literal["info", "warn", "error"] = "info",
    ):
        supported_values = []
        for other in others:
            value = getattr(other, attr_name)
            if value is not None:
                supported_values.append(value)
        if not supported_values:
            return
        self_value = getattr(self, attr_name)
        if self_value is None:
            Printer.echo(Printer.not_found(tag=tag, attr_name=attr_name), level="error")
            return
        if self_value not in supported_values:
            Printer.echo(
                Printer.list_compare_styled(
                    tag=tag,
                    self_value=self_value,
                    supported_values=supported_values,
                    attr_name=attr_name,
                ),
                level=level,
            )

    def more_than_at_least_one(
        self,
        attr_name,
        others: List[Self],
        tag,
        level: Literal["info", "warn", "error"] = "info",
    ):
        supported_values = []
        for other in others:
            value = getattr(other, attr_name)
            if value is not None:
                supported_values.append(value)
        self_value = getattr(self, attr_name)
        if not supported_values:
            return
        if self_value is None:
            Printer.echo(Printer.not_found(tag=tag, attr_name=attr_name), level="error")
            return
        try:
            if not [value for value in supported_values if self_value >= value]:
                Printer.echo(
                    Printer.minimum_styled(
                        tag=tag,
                        self_value=self_value,
                        supported_values=supported_values,
                        attr_name=attr_name,
                    ),
                    level=level,
                )
        except Exception as e:
            Printer.echo(f"{tag} ({attr_name}) {e}", level="error")


class Printer:
    @classmethod
    def echo(cls, message: str, level: Literal["info", "warn", "error"] = "info"):
        rich.print(cls.styled(message, level=level))

    @classmethod
    def styled(
        cls, message: str, level: Literal["info", "warn", "error"] = "info"
    ) -> str:
        if level == "warn":
            return f":warning:[yello]WARNING: {message} [/yellow]"
        elif level == "error":
            return f":error:[red]ERROR: {message} [/red]"
        return f":grey_exclamation:[green]INFO: {message} [/green]"

    @classmethod
    def list_compare_styled(
        cls, self_value: Any, supported_values: List[Any], tag: str, attr_name: str
    ) -> str:
        return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] not found in supported values: {supported_values}"

    @classmethod
    def minimum_styled(
        cls,
        self_value: int | float,
        supported_values: List[int | float],
        tag: str,
        attr_name: str,
    ) -> str:
        return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] lesser than supported values: {supported_values}"

    @classmethod
    def not_found(cls, tag, attr_name):
        return f"[italics]{tag}[/italics] {attr_name} not found!"
