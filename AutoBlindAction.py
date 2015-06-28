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
from . import AutoBlindTools
from . import AutoBlindLogger
from . import AutoBlindEval


# Class representing a single action
class AbAction:
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        self.__sh = smarthome
        self.__name = name
        self.__item = None
        self.__value = None
        self.__eval = None
        self.__from_item = None
        self.__mindelta = None
        self.__logic = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update_set(self, item_state, value):
        if self.__item is None:
            self.__set_item(AutoBlindTools.find_attribute(self.__sh, item_state, "item_" + self.__name))

        func, set_value = AutoBlindTools.partition_strip(value, ":")
        if set_value == "":
            set_value = func
            func = "value"

        if func == "value":
            self.__value = set_value
            self.__eval = None
            self.__from_item = None
        elif func == "eval":
            self.__value = None
            self.__eval = set_value
            self.__from_item = None
        elif func == "item":
            self.__value = None
            self.__eval = None
            self.__set_from_item(set_value)

        self.__logic = None

    # set the action based on a trigger_(name) attribute
    # value: Value of the trigger_(action_name) attribute
    def update_trigger(self, value):
        logic, value = AutoBlindTools.partition_strip(value, ":")
        self.__logic = logic
        if value != "":
            self.__value = value
        else:
            self.__value = None
        self.__eval = None
        self.__from_item = None

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        # Nothing to complete if this action triggers a logic
        if self.__logic is not None:
            return

        # missing item in action: Try to find it.
        if self.__item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "item_" + self.__name)
            if result is not None:
                self.__set_item(result)

        if self.__mindelta is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "mindelta_" + self.__name)
            if result is not None:
                self.__mindelta = result

        if self.__item is not None:
            if self.__value is not None:
                self.__value = self.__item.cast(self.__value)
            if self.__mindelta is not None:
                self.__mindelta = self.__item.cast(self.__mindelta)

    # Execute action
    # logger: Instance of AbLogger to write to
    def execute(self, logger: AutoBlindLogger.AbLogger):
        if self.__logic is not None:
            # Trigger logic
            logger.info("Action '{0}: Triggering logic '{1}' using value '{2}'.", self.__name, self.__logic,
                        self.__value)
            self.__sh.trigger(self.__logic, by="AutoBlind Plugin", source=self.__name, value=self.__value)
            return

        if self.__item is None:
            logger.info("Action '{0}: No item defined. Ignoring.", self.__name)
            return

        value = None
        if self.__value is not None:
            value = self.__value
        elif self.__eval is not None:
            value = self.__do_eval(logger)
        elif self.__from_item is not None:
            # noinspection PyCallingNonCallable
            value = self.__from_item()

        if value is not None:
            if self.__mindelta is not None:
                # noinspection PyCallingNonCallable
                delta = float(abs(self.__item() - value))
                if delta < self.__mindelta:
                    logger.debug(
                        "Action '{0}: Not setting '{1}' to '{2}' because delta '{3:.2}' is lower than mindelta '{4}'",
                        self.__name, self.__item.id(), value, delta, self.__mindelta)
                    return

            logger.debug("Action '{0}: Set '{1}' to '{2}'", self.__name, self.__item.id(), value)
            # noinspection PyCallingNonCallable
            self.__item(value)

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__logic is not None:
            logger.debug("trigger logic: {0}", self.__logic)
        if self.__item is not None:
            logger.debug("item: {0}", self.__item.id())
        if self.__mindelta is not None:
            logger.debug("mindelta: {0}", self.__mindelta)
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__get_eval_name())
        if self.__from_item is not None:
            logger.debug("value from item: {0}", self.__from_item.id())

    # Execute eval and return result. In case of errors, write message to log and return None
    # logger: Instance of AbLogger to write to
    def __do_eval(self, logger: AutoBlindLogger.AbLogger):
        if isinstance(self.__eval, str):
            # noinspection PyUnusedLocal
            sh = self.__sh
            if self.__eval.startswith("autoblind_eval"):
                # noinspection PyUnusedLocal
                autoblind_eval = AutoBlindEval.AbEval(self.__sh, logger)
            try:
                value = eval(self.__eval)
            except Exception as e:
                logger.info("Action '{0}: problem evaluating {1}: {2}.", self.__name, self.__get_eval_name(), e)
                return None
        else:
            try:
                # noinspection PyCallingNonCallable
                value = self.__eval()
            except Exception as e:
                logger.info("Action '{0}: problem calling {1}: {2}.", self.__name, self.__get_eval_name(), e)
                return None
        try:
            return self.__item.cast(value)
        except Exception as e:
            logger.debug("eval returned '{0}', trying to cast this returned exception '{1}'", value, e)
            return None

    # set item
    # item: value for item
    def __set_item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # set from-item
    # from_item: value for from-item
    def __set_from_item(self, from_item):
        if isinstance(from_item, str):
            self.__item = self.__sh.return_item(from_item)
        else:
            self.__item = from_item

    # Name of eval-object to be displayed in log
    def __get_eval_name(self):
        if self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__
