#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-     Thomas Ernst                       offline@gmx.net
#########################################################################
#  Finite state machine plugin for SmartHomeNG
#
#  This plugin is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This plugin is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this plugin. If not, see <http://www.gnu.org/licenses/>.
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
        self.__unassigned_repeats = {}
        self.__unassigned_orders = {}

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
            elif func == "as_repeat":
                # set repeat
                if name not in self.__actions:
                    # If we do not have the action yet (repeat-attribute before action-attribute), ...
                    self.__unassigned_repeats[name] = value
                else:
                    self.__actions[name].update_repeat(value)
                return
            elif func == "as_order":
                # set order
                if name not in self.__actions:
                    # If we do not have the action yet (order-attribute before action-attribute), ...
                    self.__unassigned_orders[name] = value
                else:
                    self.__actions[name].update_order(value)
                return
            elif func == "as_action":  # and name not in self.__actions:
                self.__handle_combined_action_attribute(name, value)
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
        elif func == "as_force":
            action = AutoBlindAction.AbActionForceItem(self._abitem, name)
        elif func == "as_byattr":
            action = AutoBlindAction.AbActionSetByattr(self._abitem, name)
        elif func == "as_trigger":
            action = AutoBlindAction.AbActionTrigger(self._abitem, name)
        elif func == "as_run":
            action = AutoBlindAction.AbActionRun(self._abitem, name)
        elif func == "as_special":
            action = AutoBlindAction.AbActionSpecial(self._abitem, name)
        else:
            return False

        if name in self.__unassigned_delays:
            action.update_delay(self.__unassigned_delays[name])
            del self.__unassigned_delays[name]

        if name in self.__unassigned_repeats:
            action.update_repeat(self.__unassigned_repeats[name])
            del self.__unassigned_repeats[name]

        if name in self.__unassigned_orders:
            action.update_order(self.__unassigned_orders[name])
            del self.__unassigned_orders[name]

        self.__actions[name] = action
        return True

    def __handle_combined_action_attribute(self, name, value_list):
        # value_list needs to be string or list
        if isinstance(value_list, str):
            value_list = [value_list, ]
        elif not isinstance(value_list, list):
            raise ValueError("Attribute 'as_action_{0}': Value must be a string or a list!".format(name))

        # parse parameters
        function = None
        value = None
        repeat = None
        delay = None
        force = None
        order = None
        for entry in value_list:
            key, val = AutoBlindTools.partition_strip(entry, ":")
            if key == "function":
                function = AutoBlindTools.cast_str(val)
            elif key == "value":
                value = val
            elif key == "force":
                force = AutoBlindTools.cast_bool(val)
            elif key == "repeat":
                repeat = val
            elif key == "delay":
                delay = val
            elif key == "order":
                order = val
            else:
                self._log_warning("Unknown parameter '{0}: {1}'!".format(key, val))

        # handle force
        if force is not None:
            # Parameter force is supported only for type "set" and type "force"
            if function != "set" and function != "force":
                self._log_warning("Attribute 'as_action_{0}': Parameter 'force' not supported for function '{1}'".format(name, function))
            elif force and function == "set":
                # Convert type "set" with force=True to type "force"
                self._log_info("Attribute 'as_action_{0}': Parameter 'function' changed from 'set' to 'force', because parameter 'force' is 'True'!".format(name))
                function = "force"
            elif not force and function == "force":
                # Convert type "force" with force=False to type "set"
                self._log_info("Attribute 'as_action_{0}': Parameter 'function' changed from 'force' to 'set', because parameter 'force' is 'False'!".format(name))
                function = "set"

        # create action based on function
        if function is None:
            raise ValueError("Attribute 'as_action_{0}: Parameter 'function' must be set!".format(name))
        elif function in ("set", "force", "byattr", "trigger", "run", "special"):
            func = "as_" + function
            if self.__ensure_action_exists(func, name):
                self.__actions[name].update(value)
                if repeat is not None:
                    self.__actions[name].update_repeat(repeat)
                if delay != 0:
                    self.__actions[name].update_delay(delay)
                if order is not None:
                    self.__actions[name].update_order(order)
        else:
            raise ValueError("Attribute 'as_action_{0}: Invalid value '{1}' for parameter 'function'!".format(name, function))

    # Check the actions optimize and complete them
    # item_state: item to read from
    def complete(self, item_state):
        for name in self.__actions:
            try:
                self.__actions[name].complete(item_state)
            except ValueError as ex:
                raise ValueError("State '{0}', Action '{1}': {2}".format(item_state.id(), name, str(ex)))

    # Execute all actions
    # is_repeat: Inidicate if this is a repeated action without changing the state
    # item_allow_repeat: Is repeating actions generally allowed for the item?
    # additional_actions: AbActions-Instance containing actions which should be executed, too
    def execute(self, is_repeat: bool, allow_item_repeat: bool, additional_actions=None):
        actions = []
        for name in self.__actions:
            actions.append((self.__actions[name].get_order(), self.__actions[name]))
        if additional_actions is not None:
            for name in additional_actions.__actions:
                actions.append((additional_actions.__actions[name].get_order(), additional_actions.__actions[name]))
        for order, action in sorted(actions, key=lambda x: x[0]):
            action.execute(is_repeat, allow_item_repeat)

    # log all actions
    def write_to_logger(self):
        actions = []
        for name in self.__actions:
            actions.append((self.__actions[name].get_order(), self.__actions[name]))
        for order, action in sorted(actions, key=lambda x: x[0]):
            # noinspection PyProtectedMember
            self._log_info("Action '{0}':", action._name)
            self._log_increase_indent()
            action.write_to_logger()
            self._log_decrease_indent()
