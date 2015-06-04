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

import logging
import re
import time
from .AutoBlindLogger import AbLogger
from . import AutoBlindItem
from . import AutoBlindConditionChecker

logger = logging.getLogger("")


class AutoBlind:
    _items = {}
    __item_regex = re.compile(".*\.AutoBlind\.active$")
    __item_id_height = "hoehe"
    __item_id_lamella = "lamelle"
    __cycle = 300
    __manual_break_default = 3600
    alive = False

    # Constructor
    # @param smarthome: instance of smarthome.py
    # @cycle: intervall to update the bind positions
    # @param item_id_height: name of item to controll the blind's height below the main item of the blind
    # @param item_id_lamella: name of item to controll the blind's lamella below the main item of the blind
    def __init__(self, smarthome, cycle=300, item_id_height="hoehe", item_id_lamella="lamelle", log_level=0,
                 log_directory="/usr/local/smarthome/var/log/AutoBlind/", manual_break_default=3600):
        logger.info("Init AutoBlind (cycle={0}, item_id_height={1}, item_id_lamella={2}".format(cycle, item_id_height,
                                                                                                item_id_lamella))

        self.sh = smarthome

        self.__item_id_height = item_id_height
        self.__item_id_lamella = item_id_lamella
        self.__cycle = cycle
        self.__manual_break_default = manual_break_default

        AbLogger.set_loglevel(log_level)
        AbLogger.set_logdirectory(log_directory)

    # Called during initialization of smarthome.py for each item
    def parse_item(self, item):
        # If item matches __item_regex, store it for later use
        if self.__item_regex.match(item.id()):
            use_item = item.return_parent().return_parent()
            self._items[use_item.id()] = use_item

        return None

    # Initialization of plugin
    def run(self):
        self.alive = True

        # init AutoBlindItems based on previously stored items
        logger.info("Init AutoBlind Items")
        items = self._items
        self._items = {}
        for item_id in items:
            item = AutoBlindItem.create(self.sh, items[item_id], self.__item_id_height, self.__item_id_lamella,
                                        self.__manual_break_default)
            if item.validate():
                self._items[item_id] = item
                item.log()

        # if we have items, wait some time, update the blind positions and afterwards schedule regular
        # recheck of updateing the blind positions
        if len(self._items) > 0:
            logger.info("Using AutoBlind for {} items".format(len(self._items)))
            time.sleep(10)
            self.update_positions()
            self.sh.scheduler.add("autoblind", self.update_positions, cycle=self.__cycle)
        else:
            logger.info("AutoBlind deactivated because no items have been found.")

    # Stopping of plugin
    def stop(self):
        self.alive = False

    # Update the positions of all configured blinds
    def update_positions(self):
        logger.info("Updating positions")

        condition_checker = AutoBlindConditionChecker.create(self.sh)

        # call position update for each AutoBlindItem
        for item in self._items:
            AbLogger.set_section(self._items[item].id())
            self._items[item].update_position(condition_checker)
            AbLogger.clear_section()
