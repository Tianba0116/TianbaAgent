"""TianbaAgent CLI entry point."""

import click
from cli import __version__
from cli.commands.skill import skill
from cli.commands.process import start, stop, restart, update, status, logs
from cli.commands.context import context
from cli.commands.install import install_browser
from cli.commands.knowledge import knowledge


HELP_TEXT = """Usage: tianba [COMMAND] [ARGS]...

  TianbaAgent CLI - Manage your TianbaAgent instance.

  Run without arguments to start dual mode (Web + CLI).

Commands:
  help     Show this message.
  version  Show the version.
  start    Start TianbaAgent as a background service.
  stop     Stop TianbaAgent.
  restart  Restart TianbaAgent.
  update   Update TianbaAgent and restart.
  status   Show TianbaAgent running status.
  logs     View TianbaAgent logs.
  skill    Manage TianbaAgent skills.
  knowledge  Manage knowledge base.
  install-browser  Install browser tool (Playwright + Chromium).

Startup modes:
  tianba              Dual mode: Web console + CLI (foreground)
  tianba start        Background service (Web console only)
  tianba start --dual Background service (Web + CLI)
  tianba start -f     Foreground, Web only

Tip: You can also send /help, /skill list, etc. in agent chat."""


class TianbaCLI(click.Group):

    def format_help(self, ctx, formatter):
        formatter.write(HELP_TEXT.strip())
        formatter.write("\n")

    def parse_args(self, ctx, args):
        if args and args[0] == 'help':
            click.echo(HELP_TEXT.strip())
            ctx.exit(0)
        return super().parse_args(ctx, args)


@click.group(cls=TianbaCLI, invoke_without_command=True, context_settings=dict(help_option_names=[]))
@click.pass_context
def main(ctx):
    """TianbaAgent CLI - Manage your TianbaAgent instance."""
    if ctx.invoked_subcommand is None:
        # Default: launch dual mode (Web + CLI) in foreground
        from cli.utils import run_dual_foreground
        run_dual_foreground()


@main.command()
def version():
    """Show the version."""
    click.echo(f"tianba {__version__}")


@main.command(name='help')
@click.pass_context
def help_cmd(ctx):
    """Show this message."""
    click.echo(HELP_TEXT.strip())


main.add_command(skill)
main.add_command(start)
main.add_command(stop)
main.add_command(restart)
main.add_command(update)
main.add_command(status)
main.add_command(logs)
main.add_command(context)
main.add_command(knowledge)
main.add_command(install_browser)


if __name__ == '__main__':
    main()
