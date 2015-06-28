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


# Class representing a list of actions
class AbActions:
    # Initialize the set of actions
    # smarthome: Instance of smarthome.py-class
    def __init__(self, smarthome):
        self.__sh = smarthome
        self.__actions = {}

    # Return number of actions in list
    def count(self):
        return len(self.__actions)

    # get action name from attribute and ensure action exists (base for all updates)
    # attribute: name of attribute that defines action
    def update(self, item_state, attribute):
        # Split attribute in function and action name
        func, __, action_name = attribute.partition("_")
        if func not in ("set", "trigger") or action_name == "":
            return

        # Ensure action exists
        if action_name not in self.__actions:
            action = AutoBlindAction.AbAction(self.__sh, action_name)
            self.__actions[action_name] = action

        # Set action depending on function
        if func == "set":
            self.__actions[action_name].update_set(item_state, item_state.conf[attribute])
        elif func == "trigger":
            self.__actions[action_name].update_trigger(item_state.conf[attribute])

    # Check the actions optimize and complete them
    # item_state: item to read from
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_state):
        for action_name in self.__actions:
            self.__actions[action_name].complete(item_state)

    # Execute all actions
    # logger: Instance of AbLogger to write log messages to
    def execute(self, logger: AutoBlindLogger.AbLogger):
        for action_name in self.__actions:
            self.__actions[action_name].execute(logger)

    # log all actions
    # logger: Instance of AbLogger to write log messages to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        for action_name in self.__actions:
            logger.info("Action '{0}':", action_name)
            logger.increase_indent()
            self.__actions[action_name].write_to_logger(logger)
            logger.decrease_indent()
