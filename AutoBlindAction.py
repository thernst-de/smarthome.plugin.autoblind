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
        if self.__item is not None or self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__

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

    # set the action based on the set_(action_name) attribute
    # item_position: position item to read from
    # value: Value from set_(action_name) attribute
    def update(self, position_item, value):

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

    # Complete action
    # item_position: position item to read from
    def complete(self, item_position):
        # missing item in action: Try to find it
        if self.item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_position, "item_" + self.name)
            if result is not None:
                self.item = result

    # Execute action
    # logger: Instance of AbLogger to write to
    def execute(self, logger: AutoBlindLogger.AbLogger):
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
                try:
                    value = eval(self.__eval)
                except Exception as e:
                    logger.info("Action '{0}: problem evaluating {1}: {2}.", self.__name, self.__eval_name, e)
            else:
                # noinspection PyCallingNonCallable
                value = self.__eval()
        elif self.__from_item is not None:
            # noinspection PyCallingNonCallable
            value = self.__from_item()

        if value is not None:
            logger.debug("Action '{0}: Set '{1}' to '{2}'", self.__name, self.__item.id(), value)
            # noinspection PyCallingNonCallable
            self.__item(value)

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__item is not None:
            logger.debug("item: {0}", self.item.id())
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__eval_name)
        if self.__from_item is not None:
            logger.debug("value from item: {0}", self.from_item.id())
