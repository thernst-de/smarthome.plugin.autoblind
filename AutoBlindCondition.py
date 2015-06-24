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
from . import AutoBlindCurrent


# Class representing a single condition
class AbCondition:
    # Name of condition
    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = AutoBlindTools.cast_str(name)

    # Item to get current value for condition
    @property
    def item(self):
        return self.__item

    @item.setter
    def item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # Function to get current value for condition
    @property
    def eval(self):
        return self.__eval

    @eval.setter
    def eval(self, eval_value):
        self.__eval = eval_value

    # Required value for the condition to be matched
    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    # Required minimum value for the condition to be matched
    @property
    def min(self):
        return self.__min

    @min.setter
    def min(self, min_value):
        self.__min = min_value

    # Required maximum for the condition to be matched
    @property
    def max(self):
        return self.__max

    @max.setter
    def max(self, max_value):
        self.__max = max_value

    # Flag: Negate condition (contition is matched if value/min/max are NOT matching)
    @property
    def negate(self):
        return self.__negate

    @negate.setter
    def negate(self, negate):
        self.__negate = AutoBlindTools.cast_bool(negate)

    # Error that occurred while preparing the condition (empty if condition is OK)
    @property
    def error(self):
        return self.__error

    # Current value of condition (based on item or eval)
    @property
    def current(self):
        if self.__item is not None:
            # noinspection PyCallingNonCallable
            return self.__item()
        if self.__eval is not None:
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
        raise ValueError("Condition {}: Neither 'item' nor eval given!".format(self.__name))

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
        self.__eval = None
        self.__value = None
        self.__min = None
        self.__max = None
        self.__negate = False
        self.__error = None

    # set a certain function to a given value
    # func: Function to set ('item', 'eval', 'value', 'min', 'max' or 'negate'
    # value: Value for function
    def set(self, func, value):
        if func == "item":
            self.item = value
        elif func == "eval":
            self.eval = value
        elif func == "value":
            self.value = value
        elif func == "min":
            self.min = value
        elif func == "max":
            self.max = value
        elif func == "negate":
            self.negate = value

    # Complete condition (do some checks, cast value, min and max based on item or eval data types)
    # item_position: item to read from
    # abitem_object: Related AbItem instance for later determination of current age and current delay
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_position, abitem_object):
        # set 'eval' for some known conditions if item and eval are not set, yet
        if self.item is None and self.eval is None:
            if self.name == "weekday":
                self.eval = AutoBlindCurrent.values.get_weekday
            elif self.name == "sun_azimut":
                self.eval = AutoBlindCurrent.values.get_sun_azimut
            elif self.name == "sun_altitude":
                self.eval = AutoBlindCurrent.values.get_sun_altitude
            elif self.name == "age":
                self.eval = abitem_object.get_age
            elif self.name == "delay":
                self.eval = abitem_object.get_delay
            elif self.name == "time":
                self.eval = AutoBlindCurrent.values.get_time
            elif self.name == "random":
                self.eval = AutoBlindCurrent.values.get_random

        # missing item in condition: Try to find it
        if self.item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_position, "item_" + self.name)
            if result is not None:
                self.item = result

        # missing eval in condition: Try to find it
        if self.eval is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_position, "eval_" + self.name)
            if result is not None:
                self.eval = result

        # no we should have either 'item' or 'eval' set. If not ... very bad ....
        if self.item is None and self.eval is None:
            self.__error = "Condition {}: Neither 'item' nor 'eval' given!".format(self.__name)
            raise ValueError(self.__error)

        # cast stuff
        try:
            if self.__item is not None:
                self.__cast_all(self.__item.cast)
            elif self.__name in ("weekday", "sun_azimut", "sun_altitude", "age", "delay"):
                self.__cast_all(AutoBlindTools.cast_num)
            elif self.__name == "time":
                self.__cast_all(AutoBlindTools.cast_time)
        except Exception as ex:
            self.__error = str(ex)
            raise ValueError(self.__error)

        # 'min' must not be greather than 'max'
        if self.__min is not None and self.__max is not None and self.__min > self.__max:
            self.__error = "Condition {}: 'min' must not be greater than 'max'!".format(self.__name)
            raise ValueError(self.__error)

    # Check if condition is matching
    # logger: Instance of AbLogger to write log messages
    def check(self, logger: AutoBlindLogger.AbLogger):
        # Ignore if errors occured during preparing
        if self.error is not None:
            logger.info("condition'{0}': Ignoring because of error: {1}", self.name, self.error)
            return True

        # Ignore if no current value can be determined (should not happen as we check this earlier, but to be sure ...)
        if self.item is None and self.eval is None:
            logger.info("condition '{0}': no item or eval found! Considering condition as matching!", self.name)
            return True

        current = self.current
        try:
            if self.value is not None:
                # 'value' is given. We ignore 'min' and 'max' and check only for the given value
                logger.debug("Condition '{0}': value={1} negate={2} current={3}", self.name, self.value, self.negate,
                             current)
                logger.increase_indent()

                if (not self.negate and current == self.value) or (self.negate and current != self.value):
                    logger.debug("OK -> matching")
                    return True

                logger.debug("not OK -> not matching")
                return False

            else:
                # 'value' is not given. We check 'min' and 'max' (if given)
                logger.debug("Condition '{0}': min={1} max={2} negate={3} current={4}",
                             self.name, self.min, self.max, self.negate, current)
                logger.increase_indent()

                if self.min is None and self.max is None:
                    logger.debug("no limit given -> matching")
                    return True

                if not self.negate:
                    if self.min is not None and current < self.min:
                        logger.debug("to low -> not matching")
                        return False

                    if self.max is not None and current > self.max:
                        logger.debug("to high -> not matching")
                        return False
                else:
                    if self.min is not None and current > self.min and (self.max is None or current < self.max):
                        logger.debug("not lower than min -> not matching")
                        return False

                    if self.max is not None and current < self.max and (self.min is None or current > self.min):
                        logger.debug("not higher than max -> not matching")
                        return False

                logger.debug("given limits ok -> matching")
                return True
        finally:
            logger.decrease_indent()

    # Write condition to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__error is not None:
            logger.debug("error: {0}", self.error)
        if self.__item is not None:
            logger.debug("item: {0}", self.item.id())
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__eval_name)
        if self.__value is not None:
            logger.debug("value: {0}", self.value)
        if self.__min is not None:
            logger.debug("min: {0}", self.min)
        if self.__max is not None:
            logger.debug("max: {0}", self.max)
        if self.__negate is not None:
            logger.debug("negate: {0}", self.negate)

    # Cast 'value', 'min' and 'max' using given cast function
    # cast_func: cast function to use
    def __cast_all(self, cast_func):
        if self.__value is not None:
            self.__value = cast_func(self.__value)
        if self.__min is not None:
            self.__min = cast_func(self.__min)
        if self.__max is not None:
            self.__max = cast_func(self.__max)
