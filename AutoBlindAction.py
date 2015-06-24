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
# noinspection PyUnresolvedReferences
from . import AutoBlindEval


# Class representing a single action
class AbAction:
    # name of action
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = AutoBlindTools.cast_str(name)

    # item to update if action is executed
    @property
    def item(self):
        return self.__item

    @item.setter
    def item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # function to get the value if action is executed
    @property
    def eval(self):
        return self.__eval

    @eval.setter
    def eval(self, eval_value):
        self.__eval = eval_value

    # static value to be set if action is executed
    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        if self.__item is not None and value is not None:
            value = self.__item.cast(value)
        self.__value = value

    # minimum delta, action is not executed if delta is below this value
    @property
    def mindelta(self):
        return self.__mindelta

    @mindelta.setter
    def mindelta(self, mindelta):
        if self.__mindelta is not None and mindelta is not None:
            mindelta = self.__item.cast(mindelta)
        self.__mindelta = mindelta

    # item to take the value from if action is executed
    @property
    def from_item(self):
        return self.__from_item

    @from_item.setter
    def from_item(self, from_item):
        if isinstance(from_item, str):
            self.__item = self.__sh.return_item(from_item)
        else:
            self.__item = from_item

    # Name of eval-object to be displayed in log
    @property
    def __eval_name(self):
        if self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__

    # logic to trigger
    @property
    def logic(self):
        return self.__logic

    @logic.setter
    def logic(self, logic):
        self.__logic = logic

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

    # set the action based on the set_(action_name) attribute
    # item_position: position item to read from
    # value: Value from set_(action_name) attribute
    def update_set(self, position_item, value):

        if self.item is None:
            self.item = AutoBlindTools.find_attribute(self.__sh, position_item, "item_" + self.__name)

        parts = value.partition(":")
        if parts[2] == "":
            func = "value"
            set_value = parts[2]
        else:
            func = parts[0]
            set_value = parts[2]

        if func == "value":
            self.value = set_value
            self.eval = None
            self.from_item = None
        elif func == "eval":
            self.value = None
            self.eval = set_value
            self.from_item = None
        elif func == "item":
            self.value = None
            self.eval = None
            self.from_item = set_value
        self.logic = None

    # set the action based on the trigger_(name) attribute
    # item_position: position item to read from
    # value: Value from set_(action_name) attribute
    def update_trigger(self, position_item, value):
        parts = value.partition(":")
        self.__logic = parts[0]
        if parts[2] != "":
            self.__value = parts[2]
        self.eval = None
        self.from_item = None


    # Complete action
    # item_position: position item to read from
    def complete(self, item_position):
        if self.logic is None:
            # missing item in action: Try to find it. Nothing to do in case of logic
            if self.item is None:
                result = AutoBlindTools.find_attribute(self.__sh, item_position, "item_" + self.name)
                if result is not None:
                    self.item = result

            if self.mindelta is None:
                result = AutoBlindTools.find_attribute(self.__sh, item_position, "mindelta_" + self.name)
                if result is not None:
                    self.mindelta = result

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
            logger.info("Action '{0}: Triggering logic '{1}' using value '{2}'.", self.__name, self.__logic, self.__value)
            self.__sh.trigger(self.__logic, by="AutoBlind Plugin", source = self.__name, value = self.__value  )
            return

        if self.__item is None:
            logger.info("Action '{0}: No item defined. Ignoring.", self.__name)
            return

        value = None
        if self.__value is not None:
            value = self.__value
        elif self.__eval is not None:
            if isinstance(self.__eval, str):
                # noinspection PyUnusedLocal
                sh = self.__sh
                if self.__eval.startswith("autoblind_eval"):
                    # noinspection PyUnusedLocal
                    autoblind_eval = AutoBlindEval.AbEval(self.__sh,logger)
                try:
                    value = eval(self.__eval)
                except Exception as e:
                    logger.info("Action '{0}: problem evaluating {1}: {2}.", self.__name, self.__eval_name, e)
            else:
                # noinspection PyCallingNonCallable
                value = self.__eval()
            try:
                value = self.__item.cast(value)
            except Exception as e:
                logger.debug("eval returned '{0}', trying to cast this returned exception '{1}'",value, e)
                value = None
        elif self.__from_item is not None:
            # noinspection PyCallingNonCallable
            value = self.__from_item()

        if value is not None:
            if self.mindelta is not None:
                # noinspection PyCallingNonCallable
                delta = abs(self.__item() - value)
                if delta < self.mindelta:
                    logger.debug(
                        "Action '{0}: Not setting '{1}' to '{2}' because delta '{3}' is lower than mindelta '{4}'",
                        self.__name, self.__item.id(), value, delta, self.mindelta)
                    return

            logger.debug("Action '{0}: Set '{1}' to '{2}'", self.__name, self.__item.id(), value)
            # noinspection PyCallingNonCallable
            self.__item(value)

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__logic is not None:
            logger.debug("logic: {0}", self.__logic)
        if self.__item is not None:
            logger.debug("item: {0}", self.__item.id())
        if self.__mindelta is not None:
            logger.debug("mindelta: {0}", self.__mindelta)
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__eval_name)
        if self.__from_item is not None:
            logger.debug("value from item: {0}", self.__from_item.id())
