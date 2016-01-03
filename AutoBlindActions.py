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
from . import AutoBlindAction
from . import AutoBlindTools


# Class representing a list of actions
class AbActions(AutoBlindTools.AbItemChild):
    # Initialize the set of actions
    # abitem: parent AbItem instance
    def __init__(self, abitem):
        super().__init__(abitem)
        self.__actions = {}
        self.__unassigned_delays = {}

    # Return number of actions in list
    def count(self):
        return len(self.__actions)

    # update action
    # attribute: name of attribute that defines action
    # value: value of the attribute
    def update(self, attribute, value):
        # Split attribute in function and action name
        func, name = AutoBlindTools.partition_strip(attribute, "_")
        try:
            if func == "as_delay":
                # set delay
                if name not in self.__actions:
                    # If we do not have the action yet (delay-attribute before action-attribute), ...
                    self.__unassigned_delays[name] = value
                else:
                    self.__actions[name].update_delay(value)
                return
            elif self.__ensure_action_exists(func, name):
                # update action
                self.__actions[name].update(value)
        except ValueError as ex:
            raise ValueError("Action {0}: {1}".format(attribute, str(ex)))

    # ensure that action exists and create if missing
    # func: action function
    # name: action name
    def __ensure_action_exists(self, func, name):
        # Check if action exists
        if name in self.__actions:
            return True

        # Create action depending on function
        if func == "as_set":
            action = AutoBlindAction.AbActionSetItem(self._abitem, name)
        elif func == "as_byattr":
            action = AutoBlindAction.AbActionSetByattr(self._abitem, name)
        elif func == "as_trigger":
            action = AutoBlindAction.AbActionTrigger(self._abitem, name)
        elif func == "as_run":
            action = AutoBlindAction.AbActionRun(self._abitem, name)
        else:
            return False

        if name in self.__unassigned_delays:
            action.update_delay(self.__unassigned_delays[name])
            del self.__unassigned_delays[name]

        self.__actions[name] = action
        return True

    # Check the actions optimize and complete them
    # item_state: item to read from
    def complete(self, item_state):
        for name in self.__actions:
            try:
                self.__actions[name].complete(item_state)
            except ValueError as ex:
                raise ValueError("State '{0}', Action '{1}': {2}".format(item_state.id(), name, str(ex)))

    # Execute all actions
    def execute(self):
        for name in self.__actions:
            self.__actions[name].execute()

    # log all actions
    def write_to_logger(self):
        for name in self.__actions:
            self._log_info("Action '{0}':", name)
            self._log_increase_indent()
            self.__actions[name].write_to_logger()
            self._log_decrease_indent()
