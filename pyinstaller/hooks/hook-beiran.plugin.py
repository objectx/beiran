"""
Static replacement of some modules which loads plugin's modules
and submodules for pyinstaller.
"""

from beiran import plugin
from beiran.cli import BeiranCLI


def _get_installed_plugins():
    """
    Replaces `beiran.plugin.get_installed_plugins` method.

    Returns:
        list: list of package name of installed beiran plugins.

    """
    return [
        "beiran_package_docker",
    ]


plugin.get_installed_plugins = _get_installed_plugins


def _list_commands(self, ctx):  # type: ignore
    """
    Replaces `beiran.cli.BeiranCLI.list_commands` method.

    Args:
        ctx (BeiranContext): context object

    Returns:
        list: list of subcommand names

    """
    commands = list()
    commands.append("docker")
    commands.append("node")
    commands.sort()
    return commands


BeiranCLI.list_commands = _list_commands
