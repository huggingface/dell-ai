"""Custom Typer group that prints full help on usage errors."""

import sys
from typing import Any, Optional, Sequence

import click
import typer.core


class DellAIGroup(typer.core.TyperGroup):
    """Typer group that shows command help when required args/options are missing."""

    def main(
        self,
        args: Optional[Sequence[str]] = None,
        prog_name: Optional[str] = None,
        complete_var: Optional[str] = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        if not standalone_mode:
            return super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )

        try:
            rv = super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )
        except click.UsageError as e:
            if e.ctx is not None:
                click.echo(e.format_message(), err=True)
                click.echo(e.ctx.get_help())
            else:
                e.show()
            sys.exit(e.exit_code)
        except click.ClickException as e:
            e.show()
            sys.exit(e.exit_code)
        except click.Abort:
            click.echo("Aborted!", err=True)
            sys.exit(1)
        except SystemExit as e:
            sys.exit(e.code)
        else:
            if isinstance(rv, int):
                sys.exit(rv)
            return rv
