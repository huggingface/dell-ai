import abc
import subprocess
from typing import Any, List, Literal

import rich
from pydantic import BaseModel
from pydantic_extra_types.semantic_version import SemanticVersion
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
        if not supported_values:
            return
        self_value = getattr(self, attr_name)
        if self_value is None:
            Printer.echo(Printer.not_found(tag=tag, attr_name=attr_name), level="error")
            return
        try:
            if float(self_value) < min([float(x) for x in supported_values]):
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

    @classmethod
    def _version_parse(cls, v):
        try:
            return SemanticVersion.parse(v)
        except ValueError as e:
            if "v" in v:
                return cls._version_parse(v.removeprefix("v"))
            if "0" in v:
                major, minor, patch = v.split(".")
                return SemanticVersion(
                    major=int(major), minor=int(minor), patch=int(patch)
                )
            else:
                raise e

    def software_version_compare(
        self,
        attr_name: str,
        others: List[Self],
        tag: str,
    ):
        supported_versions = []
        for other in others:
            value = getattr(other, attr_name)
            if value is not None:
                if isinstance(value, str):
                    try:
                        parsed_value = self._version_parse(value)
                        supported_versions.append(parsed_value)
                    except ValueError:
                        Printer.echo(
                            f"Comparison {tag} ({attr_name}) {value} cannot be parsed as semantic version",
                            level="error",
                        )
                else:
                    Printer.echo(
                        f"Comparison {tag} ({attr_name}) {value} is not a string",
                        level="error",
                    )
        if not supported_versions:
            return
        self_value = getattr(self, attr_name)
        if self_value is None:
            Printer.echo(Printer.not_found(tag=tag, attr_name=attr_name), level="error")
            return
        if isinstance(self_value, str):
            try:
                parsed_self_value = self._version_parse(self_value)
            except ValueError:
                Printer.echo(
                    f"This {tag} ({attr_name}) {self_value} cannot be parsed as semantic version",
                    level="error",
                )
            else:
                min_supported_version = min(supported_versions)
                max_supported_version = max(supported_versions)
                if min_supported_version <= parsed_self_value <= max_supported_version:
                    # found in list of supported versions, nothing to do
                    return
                elif parsed_self_value < min_supported_version:
                    Printer.echo(
                        Printer.version_compare_styled(
                            tag=tag,
                            attr_name=attr_name,
                            self_value=self_value,
                            min_supported_value=str(min_supported_version),
                            max_supported_value=str(max_supported_version),
                            greater=False,
                        ),
                        level="error",
                    )
                elif parsed_self_value > max_supported_version:
                    Printer.echo(
                        Printer.version_compare_styled(
                            tag=tag,
                            attr_name=attr_name,
                            self_value=self_value,
                            min_supported_value=str(min_supported_version),
                            max_supported_value=str(max_supported_version),
                            greater=True,
                        ),
                        level="warn",
                    )
        else:
            Printer.echo(
                f"This {tag} ({attr_name}) {self_value} is not a string", level="error"
            )
            return


class Printer:
    @classmethod
    def echo(cls, message: str, level: Literal["info", "warn", "error"] = "info"):
        rich.print(cls.styled(message, level=level))

    @classmethod
    def styled(
        cls, message: str, level: Literal["info", "warn", "error"] = "info"
    ) -> str:
        if level == "warn":
            return f":warning: [yellow]WARNING: {message} [/yellow]"
        elif level == "error":
            return f":red_circle: [red]ERROR: {message} [/red]"
        return f":grey_exclamation: [green]INFO: {message} [/green]"

    @classmethod
    def list_compare_styled(
        cls, self_value: Any, supported_values: List[Any], tag: str, attr_name: str
    ) -> str:
        return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] not found in supported values: {supported_values}"

    @classmethod
    def minimum_styled(
        cls,
        self_value: int | float | str,
        supported_values: List[int | float | str],
        tag: str,
        attr_name: str,
    ) -> str:
        return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] lesser than supported values: {supported_values}"

    @classmethod
    def not_found(cls, tag, attr_name):
        return f"[italics]{tag}[/italics] {attr_name} not found!"

    @classmethod
    def version_compare_styled(
        cls,
        self_value: str,
        tag: str,
        attr_name: str,
        min_supported_value: str,
        max_supported_value: str,
        greater: bool = True,
    ) -> str:
        if greater:
            return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] greater than max supported value: {max_supported_value}"
        else:
            return f"[italics]{tag}[/italics] {attr_name}=[bold]{self_value}[/bold] lesser than min supported value: {min_supported_value}"
