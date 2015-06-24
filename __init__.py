#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-2015 Thomas Ernst                       offline@gmx.net
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
from .AutoBlindLogger import AbLogger
from . import AutoBlindItem
from . import AutoBlindCurrent
from . import AutoBlindDefaults
import logging

logger = logging.getLogger()


class AutoBlind:
    # Constructor
    # smarthome: instance of smarthome.py
    # cycle_default: default interval to update positions
    # startup_delay_default: default startup delay
    # manual_break_default: default break after manual changes of items
    # log_level: loglevel for extended logging
    # log_directory: directory for extended logging files
    def __init__(self, smarthome, cycle_default=300, startup_delay_default=10, manual_break_default=3600,
                 log_level=0, log_directory="/usr/local/smarthome/var/log/AutoBlind/"):
        self._sh = smarthome
        self.__items = {}
        self.alive = False

        logger.info("Init AutoBlind (log_level={0}, log_directory={1}".format(log_level, log_directory))

        AutoBlindDefaults.cycle = int(cycle_default)
        AutoBlindDefaults.startup_delay = int(startup_delay_default)
        AutoBlindDefaults.manual_break = int(manual_break_default)
        AutoBlindDefaults.write_to_log()

        AutoBlindCurrent.init(smarthome)

        AbLogger.set_loglevel(log_level)
        AbLogger.set_logdirectory(log_directory)

#    # Called during initialization of smarthome.py for each item
#    def parse_item(self, item):
#        # If item matches __item_regex, store it for later use
#        if "autoblind_plugin" in item.conf and item.conf["autoblind_plugin"] == "active":
#            self.__items[item.id()] = item
#
#        return None

    # Initialization of plugin
    def run(self):
        self.alive = True

        # init AutoBlindItems based on previously stored items
        logger.info("Init AutoBlind Items")
        possible_items = self._sh.find_items("autoblind_plugin")
        for possible_item in possible_items:
            if possible_item.conf["autoblind_plugin"] != "active":
                continue

            item = AutoBlindItem.AbItem(self._sh, possible_item)
            try:
                item.validate()
                self.__items[item.id] = item
                item.write_to_log()
            except ValueError as ex:
                logger.exception(ex)

        # if we have items, wait some time, update the blind positions and afterwards schedule regular
        # recheck of updating the blind positions
        if len(self.__items) > 0:
            logger.info("Using AutoBlind for {} items".format(len(self.__items)))

            for item_id in self.__items:
                self.__items[item_id].startup()

        else:
            logger.info("AutoBlind deactivated because no items have been found.")

    # Stopping of plugin
    def stop(self):
        self.alive = False
