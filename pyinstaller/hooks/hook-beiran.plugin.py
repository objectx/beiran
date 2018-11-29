"""
Static replacement of some modules which loads plugin's modules
and submodules for pyinstaller.

All are commented, no need anymore, since stopped using pkgutil
for dynamic loading, keep example codes how to override objects
on the run time.
"""

# from beiran.cli import BeiranCLI
#
# def _list_commands(self, ctx):  # type: ignore
#     """
#     Replaces `beiran.cli.BeiranCLI.list_commands` method.
#
#     Args:
#         ctx (BeiranContext): context object
#
#     Returns:
#         list: list of subcommand names
#
#     """
#     commands = list()
#     commands.append("docker")
#     commands.append("node")
#     commands.sort()
#     return commands
#
#
# BeiranCLI.list_commands = _list_commands
