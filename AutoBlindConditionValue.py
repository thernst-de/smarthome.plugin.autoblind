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


# Class representing a value for a condition (either value or via item/eval)
class AbConditionValue:
    # smarthome: Instance of smarthome.py-class
    def __init__(self, smarthome, name):
        self.__name = name
        self.__value = None
        self.__item = None
        self.__eval = None
        self.__cast_func = None
        self.__sh = smarthome

    def is_empty(self):
        return self.__value is None and self.__item is None and self.__eval is None

    def set(self, value, name):
        source, field_value = AutoBlindTools.partition_strip(value, ":")

        if name == "time" and source.isdigit() and field_value.isdigit():
            field_value = value
            source = "value"
        elif field_value == "":
            field_value = source
            source = "value"

        if source == "value":
            self.__value = field_value
            self.__item = None
            self.__eval = None
        elif source == "item":
            self.__value = None
            self.__item = self.__sh.return_item(field_value)
            self.__eval = None
        elif source == "eval":
            self.__value = None
            self.__item = None
            self.__eval = field_value

    def get(self):
        if self.__item is not None:
            # noinspection PyCallingNonCallable
            return self.__cast_func(self.__item())
        elif self.__eval is not None:
            if isinstance(self.__eval, str):
                # noinspection PyUnusedLocal
                sh = self.__sh
                try:
                    value = eval(self.__eval)
                except Exception as e:
                    raise ValueError("Condition {}: problem evaluating {}: {}".format(self.__name, str(self.__eval), e))
                else:
                    return value
            else:
                # noinspection PyCallingNonCallable
                return self.__eval()
        else:
            return self.__value

    def get_type(self):
        if self.__value is not None:
            return "value"
        elif self.__item is not None:
            return "item"
        elif self.__eval is not None:
            return "eval"
        else:
            return None

    def set_cast(self, cast_func):
        if self.is_empty():
            return

        self.__cast_func = cast_func
        if self.__value is not None:
            self.__value = self.__cast_func(self.__value)

    # Write condition to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.is_empty():
            return

        if self.__value is not None:
            logger.debug("{0}: {1}", self.__name, self.__value)
        if self.__item is not None:
            logger.debug("{0} from item: {1}", self.__name, self.__item.id())
        if self.__eval is not None:
            logger.debug("{0} from eval: {1}", self.__name, self.__eval)
