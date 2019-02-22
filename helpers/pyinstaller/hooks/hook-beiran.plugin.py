# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
