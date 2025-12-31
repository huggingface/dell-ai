import platform
from typing import List, Optional

import pytest
from pydantic_extra_types.semantic_version import SemanticVersion
from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer, cmd_stdout


def test_cmd_stdout():
    if platform.system() == "Linux":
        assert cmd_stdout(["ls"])
        assert cmd_stdout(["xyz"]) is None


def test_cmd_stdout_patched(fp):
    fp.register(["xyz"], stdout="some output")
    assert cmd_stdout(["xyz"]) == "some output"
    fp.register(["xyz"], stdout="xyz: command not found", returncode=1)
    assert cmd_stdout(["xyz"]) is None


def test_simple_list_compare(monkeypatch, printer_echo_mock):
    class Obj(ComparableBaseModel):
        val: int | None = None

        def compare(self, others: List[Self]):
            self.simple_list_compare("val", others, "Val")

    success = Obj(val=1)
    failure = Obj(val=5)
    others = [Obj(val=1), Obj(val=2)]

    success.compare(others)
    printer_echo_mock.assert_not_called()

    none_obj = Obj()
    none_obj.compare(others)
    printer_echo_mock.assert_called_with(Printer.not_found("Val", "val"), level="error")

    failure.compare(others)
    printer_echo_mock.assert_called_with(
        Printer.list_compare_styled(
            tag="Val", attr_name="val", supported_values=[1, 2], self_value=5
        ),
        level="info",
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


def test_more_than_at_least_one(monkeypatch, printer_echo_mock):
    class Obj(ComparableBaseModel):
        val: int | None = None

        def compare(self, others: List[Self]):
            self.more_than_at_least_one("val", others, "Val")

    success = Obj(val=5)
    failure = Obj(val=1)
    others = [Obj(val=2), Obj(val=3)]

    success.compare(others)
    printer_echo_mock.assert_not_called()

    none_obj = Obj()
    none_obj.compare(others)
    printer_echo_mock.assert_called_with(Printer.not_found("Val", "val"), level="error")

    failure.compare(others)
    printer_echo_mock.assert_called_with(
        Printer.minimum_styled(
            tag="Val", self_value=1, supported_values=[2, 3], attr_name="val"
        ),
        level="info",
    )


def test_version_compare_simple_cases(monkeypatch, printer_echo_mock):
    class Obj(ComparableBaseModel):
        v: str | int | None = None

        def compare(self, others: List[Self]):
            self.software_version_compare("v", others, "Val")

    success = Obj(v="1.2.3")
    error = Obj(v="0.0.1")
    warn = Obj(v="2.0.0")
    others = [Obj(v="0.1.1"), Obj(v="1.2.3"), Obj(v="1.5.1")]
    others_failing_first = [Obj(v="1.2")]
    others_failing_second = [Obj(v=1)]

    success.compare(others)
    printer_echo_mock.assert_not_called()

    none_obj = Obj()
    none_obj.compare(others)
    printer_echo_mock.assert_called_with(Printer.not_found("Val", "v"), level="error")

    error.compare(others)
    printer_echo_mock.assert_called_with(
        Printer.version_compare_styled(
            tag="Val",
            attr_name="v",
            self_value="0.0.1",
            min_supported_value="0.1.1",
            max_supported_value="1.5.1",
            greater=False,
        ),
        level="error",
    )

    warn.compare(others)
    printer_echo_mock.assert_called_with(
        Printer.version_compare_styled(
            tag="Val",
            attr_name="v",
            self_value="2.0.0",
            min_supported_value="0.1.1",
            max_supported_value="1.5.1",
            greater=True,
        ),
        level="warn",
    )

    success.compare(others_failing_first)
    printer_echo_mock.assert_called_with(
        "Comparison Val (v) 1.2 cannot be parsed as semantic version", level="error"
    )

    success.compare(others_failing_second)
    printer_echo_mock.assert_called_with(
        "Comparison Val (v) 1 is not a string", level="error"
    )

    Obj(v="1.2").compare(others)
    printer_echo_mock.assert_called_with(
        "This Val (v) 1.2 cannot be parsed as semantic version", level="error"
    )

    Obj(v=1).compare(others)
    printer_echo_mock.assert_called_with(
        "This Val (v) 1 is not a string", level="error"
    )


def test_version_semver():
    assert SemanticVersion.parse("1.2.3")
    with pytest.raises(ValueError):
        SemanticVersion.parse("v1.2.3")

    assert SemanticVersion.parse("1.2.3") == SemanticVersion.parse("1.2.3")
    assert SemanticVersion.parse("1.2.3") < SemanticVersion.parse("2.0.0")

    assert sorted([SemanticVersion.parse("2.0.0"), SemanticVersion.parse("1.2.3")]) == [
        SemanticVersion.parse("1.2.3"),
        SemanticVersion.parse("2.0.0"),
    ]


def test__version_parse():
    parser = ComparableBaseModel._version_parse
    assert parser("1.2.3") == SemanticVersion.parse("1.2.3")
    assert parser("1.2.03") == SemanticVersion.parse("1.2.3")
    assert parser("v1.2.3") == SemanticVersion.parse("1.2.3")
    assert parser("v1.2.03") == SemanticVersion.parse("1.2.3")
