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
from . import AutoBlindTools
from . import AutoBlindCliCommands
import logging
import os

logger = logging.getLogger()


class AutoBlind:
    # Constructor
    # smarthome: instance of smarthome.py
    # startup_delay_default: default startup delay
    # manual_break_default: default break after manual changes of items
    # log_level: loglevel for extended logging
    # log_directory: directory for extended logging files
    def __init__(self, smarthome, startup_delay_default=10, suspend_time_default=3600, manual_break_default=0,
                 log_level=0, log_directory="var/log/AutoBlind/", log_maxage="0",
                 laststate_name_manually_locked="Manuell gesperrt", laststate_name_suspended="Ausgesetzt bis %X"):
        self._sh = smarthome
        self.__items = {}
        self.alive = False
        self.__cli = None

        logger.info("Init AutoBlind (log_level={0}, log_directory={1}".format(log_level, log_directory))

        AutoBlindDefaults.startup_delay = int(startup_delay_default)
        AutoBlindDefaults.suspend_time = int(suspend_time_default)
        AutoBlindDefaults.laststate_name_manually_locked = laststate_name_manually_locked
        AutoBlindDefaults.laststate_name_suspended = laststate_name_suspended
        AutoBlindDefaults.write_to_log()

        if manual_break_default != 0:
            logger.warning("Using obsolete plugin configuration attribute 'manual_break_default'. "
                           + "Change to 'suspend_time_default'!")

        AutoBlindCurrent.init(smarthome)

        log_level = AutoBlindTools.cast_num(log_level)
        if log_level > 0:
            if log_directory[0] != "/":
                base = self._sh.base_dir
                if base[-1] != "/":
                    base += "/"
                log_directory = base + log_directory
            if not os.path.exists(log_directory):
                os.makedirs(log_directory)
            AbLogger.set_loglevel(log_level)
            AbLogger.set_logdirectory(log_directory)
            logger.info(
                "AutoBlind extended logging is active. Logging to '{0}' with loglevel {1}.".format(log_directory,
                                                                                                   log_level))
        log_maxage = AutoBlindTools.cast_num(log_maxage)
        if log_level > 0 and log_maxage > 0:
            logger.info("AutoBlind extended log files will be deleted after {0} days.".format(log_maxage))
            AbLogger.set_logmaxage(log_maxage)
            self._sh.scheduler.add('AutoBlind: Remove old logfiles', AbLogger.remove_old_logfiles,
                                   cron=['init', '30 0 * *'], offset=0)

    # Parse an item
    # item: item to parse
    def parse_item(self, item):
        # leave if this is not an autoblind object item
        if 'as_plugin' not in item.conf or item.conf["as_plugin"] != "active":
            return None

        try:
            # Create AbItem object and return update_state method to be triggered on item changes
            ab_item = AutoBlindItem.AbItem(self._sh, item)
            self.__items[ab_item.id] = ab_item
            return None

        except ValueError as ex:
            logger.error(ex)
            return None

    # Initialization of plugin
    def run(self):
        self.alive = True

        # Complete all items
        logger.info("Complete AutoBlind items")
        incomplete = []
        for name, item in self.__items.items():
            try:
                item.complete()
                item.write_to_log()
            except ValueError as ex:
                logger.error(ex)
                incomplete.append(name)

        # Remove items which caused errors during completion
        for name in incomplete:
            del self.__items[name]

        if len(self.__items) > 0:
            logger.info("Using AutoBlind for {} items".format(len(self.__items)))
        else:
            logger.info("AutoBlind deactivated because no items have been found.")

        self.__cli = AutoBlindCliCommands.AbCliCommands(self._sh, self.__items)

    # Stopping of plugin
    def stop(self):
        self.alive = False
