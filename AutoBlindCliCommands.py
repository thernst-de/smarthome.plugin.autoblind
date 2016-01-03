#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-2016 Thomas Ernst                       offline@gmx.net
#########################################################################
#  This file is part of SmartHome.py.
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py. If not, see <http://www.gnu.org/licenses/>.
#########################################################################
import logging

logger = logging.getLogger()


class AbCliCommands:
    def __init__(self, smarthome, items):
        self.__items = items
        self._sh = smarthome

        # Add additional cli commands if cli is active (and functionality to add own cli commands is available)
        try:
            cli = self._sh.return_plugin("CLI")
            if cli is None:
                logger.debug("Additional CLI commands not registered because CLI plugin is not active")
            else:
                cli.add_command("as_list", self.cli_list, "as_list: list AutoState items")
                cli.add_command("as_detail", self.cli_detail, "as_detail asItem: show details on AutoState item asItem")
                logger.debug("Two additional CLI commands registered")
        except AttributeError:
            logger.debug("Additional CLI commands can not be registered. " +
                         "Required functinality is not yet included in your smarthome.py version")

    # CLI command as_list
    # noinspection PyUnusedLocal
    def cli_list(self, handler, parameter):
        handler.push("Items for AutoState Plugin\n")
        handler.push("==========================\n")
        for name in sorted(self.__items):
            self.__items[name].cli_list(handler)

    # CLI command as_detail
    def cli_detail(self, handler, parameter):
        item = self.__cli_getitem(handler, parameter)
        if item is not None:
            item.cli_detail(handler)

    # get item from parameter
    def __cli_getitem(self, handler, parameter):
        if parameter not in self.__items:
            handler.push("no AutoState item \"{0}\" found.\n".format(parameter))
            return None
        return self.__items[parameter]
