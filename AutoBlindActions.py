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
from . import AutoBlindLogger
from . import AutoBlindAction
import logging

lg = logging.getLogger()


# Class representing a set of conditions
class AbActions:
    # Initialize the condition set
    # smarthome: Instance of smarthome.py-class
    # name: Name of condition set
    def __init__(self, smarthome):
        self.__sh = smarthome
        self.__actions = {}

    # Return number of condition sets in list
    def count(self):
        return len(self.__actions)

    # log action data
    # logger: Instance of AbLogger to write log messages to
    def write_to_log(self, logger: AutoBlindLogger.AbLogger):
        pass

    # Get a single action by name
    # name: Name of action to return
    # add: True = Add action if not existing, False = Return None if not existing
    # returns: requested condition or "None" if not existing and add=False
    def __get_action(self, name, add=False):
        if name in self.__actions:
            return self.__actions[name]
        elif add:
            action = AutoBlindAction.AbAction(self.__sh, name)
            self.__set_action(action)
            return action
        else:
            return None

    # Set a single action
    # condition: action to set
    def __set_action(self, action):
        self.__actions[action.name] = action

    # set a certain function to a given value
    # position_item: Item of position to which the action belongs
    # name: Name of action to update
    # value: value from set_(name) attribute
    def update(self, position_item, attribute):
        parts = attribute.partition("_")
        if parts[0] != "set":
            return
        self.__get_action(parts[2], True)
        self.__actions[parts[2]].update(position_item, position_item.conf[attribute])

    # Check the actions optimize and complete them
    # item_position: item to read from
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_position):
        for action_name in self.__actions:
            self.__actions[action_name].complete(item_position)

    # Write condition to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        for action_name in self.__actions:
            logger.info("Action '{0}':", action_name)
            logger.increase_indent()
            self.__actions[action_name].write_to_logger(logger)
            logger.decrease_indent()
