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
from . import AutoBlindEval


# Class representing a value for a condition (either value or via item/eval)
class AbValue(AutoBlindTools.AbItemChild):
    # Constructor
    # abitem: parent AbItem instance
    # name: Name of value
    def __init__(self, abitem, name):
        super().__init__(abitem)
        self.__name = name
        self.__value = None
        self.__item = None
        self.__eval = None
        self.__cast_func = None

    # Indicate of object is empty (neither value nor item nor eval set)
    def is_empty(self):
        return self.__value is None and self.__item is None and self.__eval is None

    # Set value
    # value: string indicating value or source of value
    # name: name of object ("time" is being handeled different)
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
            self.__item = self._sh.return_item(field_value)
            self.__eval = None
        elif source == "eval":
            self.__value = None
            self.__item = None
            self.__eval = field_value

    # Set cast function
    # cast_func: cast function
    def set_cast(self, cast_func):
        self.__cast_func = cast_func
        self.__value = self.__do_cast(self.__value)

    # determine and return value
    def get(self):
        if self.__value is not None:
            return self.__value
        elif self.__eval is not None:
            return self.__get_eval()
        elif self.__item is not None:
            return self.__get_from_item()

    def get_type(self):
        if self.__value is not None:
            return "value"
        elif self.__item is not None:
            return "item"
        elif self.__eval is not None:
            return "eval"
        else:
            return None

    # Write condition to logger
    # logger: Instance of AbLogger to write log messages to
    def write_to_logger(self):
        if self.is_empty():
            return

        if self.__value is not None:
            self._log_debug("{0}: {1}", self.__name, self.__value)
        if self.__item is not None:
            self._log_debug("{0} from item: {1}", self.__name, self.__item.id())
        if self.__eval is not None:
            self._log_debug("{0} from eval: {1}", self.__name, self.__eval)

    # Cast given value, if cast-function is set
    # value: value to cast
    def __do_cast(self, value):
        if value is not None and self.__cast_func is not None:
            try:
                # noinspection PyCallingNonCallable
                value = self.__cast_func(value)
            except Exception as e:
                self._log_info("Problem casting value '{0}': {1}.", value, e)
                return None

        return value

    # Determine value by executing eval-function
    def __get_eval(self):
        if isinstance(self.__eval, str):
            # noinspection PyUnusedLocal
            sh = self._sh
            if self.__eval.startswith("autoblind_eval"):
                # noinspection PyUnusedLocal
                autoblind_eval = AutoBlindEval.AbEval(self._sh, self._abitem.logger)
            try:
                value = eval(self.__eval)
            except Exception as e:
                self._log_info("Problem evaluating '{0}': {1}.", AutoBlindTools.get_eval_name(self.__eval), e)
                return None
        else:
            try:
                # noinspection PyCallingNonCallable
                value = self.__eval()
            except Exception as e:
                self._log_info("Problem calling '{0}': {1}.", AutoBlindTools.get_eval_name(self.__eval), e)
                return None

        return self.__do_cast(value)

    # Determine value from item
    def __get_from_item(self):
        try:
            # noinspection PyCallingNonCallable
            value = self.__item()
        except Exception as e:
            self._log_info("Problem while reading item '{0}': {1}.", self.__item.id(), e)
            return None

        return self.__do_cast(value)
