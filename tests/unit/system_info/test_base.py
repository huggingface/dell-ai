import platform
from typing import List, Optional
from unittest.mock import Mock

import pytest
import typer
from typing_extensions import Self

from dell_ai.system_utils.base import cmd_stdout, ComparableBaseModel


def test_cmd_stdout():
    if platform.system() == "Linux":
        assert cmd_stdout(["ls"])
        assert cmd_stdout(["xyz"]) is None


def test_cmd_stdout_patched(fp):
    fp.register(["xyz"], stdout="some output")
    assert cmd_stdout(["xyz"]) == "some output"
    fp.register(["xyz"], stdout="xyz: command not found", returncode=1)
    assert cmd_stdout(["xyz"]) is None


def test_simple_list_compare(monkeypatch, typer_echo_mock):
    class Obj(ComparableBaseModel):
        val: int | None = None

        def compare(self, others: List[Self]):
            self.simple_list_compare("val", others, "Val")

    success = Obj(val=1)
    failure = Obj(val=5)
    others = [Obj(val=1), Obj(val=2)]

    success.compare(others)
    typer_echo_mock.assert_not_called()

    none_obj = Obj()
    none_obj.compare(others)
    typer_echo_mock.assert_not_called()

    failure.compare(others)
    typer_echo_mock.assert_called_with(
        f"Expected Val '5' not found in val: Supported [1, 2]"
    )


def test_simple_list_compare_attr_check(monkeypatch):
    class Obj(ComparableBaseModel):
        val: Optional[int] = None

        def compare(self, others: List[Self]):
            self.simple_list_compare(
                "val1", others, "Val"
            )  # wrong attribute provided, should raise AttributeError

    success = Obj(val=1)
    others = [Obj(val=1), Obj(val=2)]
    with pytest.raises(AttributeError):
        success.compare(others)


def test_more_than_at_least_one(monkeypatch, typer_echo_mock):
    class Obj(ComparableBaseModel):
        val: int | None = None

        def compare(self, others: List[Self]):
            self.more_than_at_least_one("val", others, "Val")

    success = Obj(val=5)
    failure = Obj(val=1)
    others = [Obj(val=2), Obj(val=3)]

    success.compare(others)
    typer_echo_mock.assert_not_called()

    none_obj = Obj()
    none_obj.compare(others)
    typer_echo_mock.assert_not_called()

    failure.compare(others)
    typer_echo_mock.assert_called_with(
        "Could not find a minimum match for Val in val='1' from [2, 3]"
    )
