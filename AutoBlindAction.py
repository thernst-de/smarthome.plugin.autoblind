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
import logging

lg = logging.getLogger()


# Class representing a single action
class AbAction:
    # Name of action
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = AutoBlindTools.cast_str(name)

    # Item to set value for action
    @property
    def item(self):
        return self.__item

    @item.setter
    def item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # Function to get value for action
    @property
    def eval(self):
        return self.__eval

    @eval.setter
    def eval(self, eval_value):
        self.__eval = eval_value

    # Value for the action
    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        if self.__item is not None and value is not None:
            value = self.__item.cast(value)
        self.__value = value

    # from-item for the action
    @property
    def from_item(self):
        return self.__from_item

    @from_item.setter
    def from_item(self, from_item):
        if isinstance(from_item, str):
            self.__item = self.__sh.return_item(from_item)
        else:
            self.__item = from_item

    # Name of eval-Object to be displayed in log
    @property
    def __eval_name(self):
        if self.__item is not None or self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__

    # Initialize the condition
    # smarthome: Instance of smarthome.py-class
    # name: Name of condition
    def __init__(self, smarthome, name: str):
        self.__sh = smarthome
        self.__name = name
        self.__item = None
        self.__value = None
        self.__eval = None
        self.__from_item = None

    # set a certain function to a given value
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

    # Complete condition (do some checks, cast value, min and max based on item or eval data types)
    # item_position: item to read from
    # abitem_object: Related AbItem instance for later determination of current age and current delay
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_position):
        # missing item in condition: Try to find it
        if self.item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_position, "item_" + self.name)
            if result is not None:
                self.item = result

    # Write condition to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__item is not None:
            logger.debug("item: {0}", self.item.id())
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__eval_name)
        if self.__value is not None:
            logger.debug("value: {0}", self.value)
