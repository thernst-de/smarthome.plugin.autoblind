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

    # Error in condition
    @property
    def error(self):
        return self.__error

        # Initialize the condition

    # smarthome: Instance of smarthome.py-class
    # name: Name of condition
    def __init__(self, smarthome, name: str):
        self.__sh = smarthome
        self.__name = name
        self.__item = None
        self.__eval = None
        self.__value = None
        self.__value_item = None
        self.__value_eval = None
        self.__min = None
        self.__min_item = None
        self.__min_eval = None
        self.__max = None
        self.__max_item = None
        self.__max_eval = None
        self.__negate = False
        self.__agemin = None
        self.__agemax = None
        self.__agenegate = None
        self.__error = None
        self.__cast_func = None

    # set a certain function to a given value
    # func: Function to set ('item', 'eval', 'value', 'min', 'max', 'negate', 'agemin', 'agemax' or 'agenegate'
    # value: Value for function
    def set(self, func, value):
        if func == "as_item":
            self.__set_item(value)
        elif func == "as_eval":
            self.__eval = value
        elif func == "as_value" or func == "as_min" or func == "as_max":
            self.set_split(func, value)
        elif func == "as_negate":
            self.__negate = value
        elif func == "as_agemin":
            self.__agemin = value
        elif func == "as_agemax":
            self.__agemax = value
        elif func == "as_agenegate":
            self.__agenegate = value

    # set a min/max/value function to a given value/item
    # func: FUnction to set ('value', 'min', 'max')
    # value: value/item for function
    def set_split(self, func, value):
        source, field_value = AutoBlindTools.partition_strip(value, ":")

        if self.name == "time" and source.isdigit() and field_value.isdigit():
            field_value = value
            source = "value"
        elif field_value == "":
            field_value = source
            source = "value"

        if source == "value":
            if func == "as_value":
                self.__value = field_value
                self.__value_item = None
                self.__value_eval = None
            elif func == "as_min":
                self.__min = field_value
                self.__min_item = None
                self.__min_eval = None
            elif func == "as_max":
                self.__max = field_value
                self.__max_item = None
                self.__max_eval = None
        elif source == "item":
            if func == "as_value":
                self.__value = None
                self.__value_item = self.__sh.return_item(field_value)
                self.__value_eval = None
            elif func == "as_min":
                self.__min = None
                self.__min_item = self.__sh.return_item(field_value)
                self.__min_eval = None
            elif func == "as_max":
                self.__max = None
                self.__max_item = self.__sh.return_item(field_value)
                self.__max_eval = None
        elif source == "eval":
            if func == "as_value":
                self.__value = None
                self.__value_item = None
                self.__value_eval = field_value
            elif func == "as_min":
                self.__min = None
                self.__min_item = None
                self.__min_eval = field_value
            elif func == "as_max":
                self.__max = None
                self.__max_item = None
                self.__max_eval = field_value

    # Complete condition (do some checks, cast value, min and max based on item or eval data types)
    # item_state: item to read from
    # abitem_object: Related AbItem instance for later determination of current age and current delay
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_state, abitem_object):
        # check if it is possible to complete this condition
        if self.__min is None and self.__max is None and self.__value is None \
                and self.__min_item is None and self.__max_item is None and self.__value_item is None \
                and self.__min_eval is None and self.__max_eval is None and self.__value_eval is None \
                and self.__agemin is None and self.__agemax is None:
            return False

        # set 'eval' for some known conditions if item and eval are not set, yet
        if self.__item is None and self.__eval is None:
            if self.__name == "weekday":
                self.__eval = AutoBlindCurrent.values.get_weekday
            elif self.__name == "sun_azimut":
                self.__eval = AutoBlindCurrent.values.get_sun_azimut
            elif self.__name == "sun_altitude":
                self.__eval = AutoBlindCurrent.values.get_sun_altitude
            elif self.__name == "age":
                self.__eval = abitem_object.get_age
            elif self.__name == "delay":
                self.__eval = abitem_object.get_delay
            elif self.__name == "time":
                self.__eval = AutoBlindCurrent.values.get_time
            elif self.__name == "random":
                self.__eval = AutoBlindCurrent.values.get_random
            elif self.__name == "month":
                self.__eval = AutoBlindCurrent.values.get_month
            elif self.__name == "laststate":
                self.__eval = abitem_object.get_laststate_id

        # missing item in condition: Try to find it
        if self.__item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "as_item_" + self.__name)
            if result is not None:
                self.__set_item(result)

        # missing eval in condition: Try to find it
        if self.__eval is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "as_eval_" + self.__name)
            if result is not None:
                self.__eval = result

        # no we should have either 'item' or 'eval' set. If not ... very bad ....
        if self.__item is None and self.__eval is None:
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

        # 'agemin' and 'agemax' can only be used for items, not for eval
        if self.__item is None and (self.__agemin is not None or self.__agemax is not None):
            self.__error = "Condition {}: 'agemin'/'agemax' can not be used for eval!".format(self.__name)
            raise ValueError(self.__error)

        return True

    # Check if condition is matching
    # logger: Instance of AbLogger to write log messages
    def check(self, logger: AutoBlindLogger.AbLogger):
        # Ignore if errors occured during preparing
        if self.__error is not None:
            logger.info("condition'{0}': Ignoring because of error: {1}", self.__name, self.__error)
            return True

        # Ignore if no current value can be determined (should not happen as we check this earlier, but to be sure ...)
        if self.__item is None and self.__eval is None:
            logger.info("condition '{0}': No item or eval found! Considering condition as matching!", self.__name)
            return True

        if not self.__check_value(logger):
            return False
        if not self.__check_age(logger):
            return False
        return True

    # Write condition to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__error is not None:
            logger.debug("error: {0}", self.__error)
        if self.__item is not None:
            logger.debug("item: {0}", self.__item.id())
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__get_eval_name())
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)
        if self.__value_item is not None:
            logger.debug("value from item: {0}", self.__value_item.id())
        if self.__value_eval is not None:
            logger.debug("value from eval: {0}", self.__value_eval)
        if self.__min is not None:
            logger.debug("min: {0}", self.__min)
        if self.__min_item is not None:
            logger.debug("min from item: {0}", self.__min_item.id())
        if self.__min_eval is not None:
            logger.debug("min from eval: {0}", self.__min_eval)
        if self.__max is not None:
            logger.debug("max: {0}", self.__max)
        if self.__max_item is not None:
            logger.debug("max from item: {0}", self.__max_item.id())
        if self.__max_eval is not None:
            logger.debug("max from eval: {0}", self.__max_eval)
        if self.__negate is not None:
            logger.debug("negate: {0}", self.__negate)
        if self.__agemin is not None:
            logger.debug("age min: {0}", self.__agemin)
        if self.__agemax is not None:
            logger.debug("age max: {0}", self.__agemax)
        if self.__agenegate is not None:
            logger.debug("age negate: {0}", self.__agenegate)

    # Cast 'value', 'min' and 'max' using given cast function
    # cast_func: cast function to use
    def __cast_all(self, cast_func):
        if self.__value is not None:
            self.__value = cast_func(self.__value)
        if self.__min is not None:
            self.__min = cast_func(self.__min)
        if self.__max is not None:
            self.__max = cast_func(self.__max)
        if self.__negate is not None:
            self.__negate = AutoBlindTools.cast_bool(self.__negate)
        if self.__agemin is not None:
            self.__agemin = AutoBlindTools.cast_num(self.__agemin)
        if self.__agemax is not None:
            self.__agemax = AutoBlindTools.cast_num(self.__agemax)
        if self.__agenegate is not None:
            self.__agenegate = AutoBlindTools.cast_bool(self.__agenegate)
        self.__cast_func = cast_func

    # Check if value conditions match
    # logger: Instance of AbLogger to write to
    def __check_value(self, logger: AutoBlindLogger.AbLogger):
        current = self.__get_current()
        try:
            if self.__value is not None or self.__value_item is not None or self.__value_eval is not None:
                # 'value' is given. We ignore 'min' and 'max' and check only for the given value
                value = self.__get_value()

                # If current and value have different types, convert both to string
                if type(value) != type(current):
                    value = str(value)
                    current = str(current)

                logger.debug("Condition '{0}': value={1} negate={2} current={3}", self.__name, value,
                             self.__negate, current)
                logger.increase_indent()

                if self.__negate:
                    if current != value:
                        logger.debug("not OK but negated -> matching")
                        return True
                else:
                    if current == value:
                        logger.debug("OK -> matching")
                        return True

                logger.debug("not OK -> not matching")
                return False

            else:

                min_value = self.__get_min()
                max_value = self.__get_max()

                # 'value' is not given. We check 'min' and 'max' (if given)
                logger.debug("Condition '{0}': min={1} max={2} negate={3} current={4}",
                             self.__name, min_value, max_value, self.__negate, current)
                logger.increase_indent()

                if min_value is None and max_value is None:
                    logger.debug("no limit given -> matching")
                    return True

                if not self.__negate:
                    if min_value is not None and current < min_value:
                        logger.debug("to low -> not matching")
                        return False

                    if max_value is not None and current > max_value:
                        logger.debug("to high -> not matching")
                        return False
                else:
                    if min_value is not None and current > min_value and (max_value is None or current < max_value):
                        logger.debug("not lower than min -> not matching")
                        return False

                    if max_value is not None and current < max_value and (min_value is None or current > min_value):
                        logger.debug("not higher than max -> not matching")
                        return False

                logger.debug("given limits ok -> matching")
                return True
        finally:
            logger.decrease_indent()

    # Check if age conditions match
    # logger: Instance of AbLogger to write to
    def __check_age(self, logger: AutoBlindLogger.AbLogger):
        # No limits given -> OK
        if self.__agemin is None and self.__agemax is None:
            logger.info("Age of '{0}': No limits given", self.__name)
            return True

        # Ignore if no current value can be determined (should not happen as we check this earlier, but to be sure ...)
        if self.__item is None:
            logger.info("Age of '{0}': No item found! Considering condition as matching!", self.__name)
            return True

        current = self.__item.age()
        try:
            # We check 'min' and 'max' (if given)
            logger.debug("Age of '{0}': min={1} max={2} negate={3} current={4}",
                         self.__name, self.__agemin, self.__agemax, self.__agenegate, current)
            logger.increase_indent()

            if not self.__agenegate:
                if self.__agemin is not None and current < self.__agemin:
                    logger.debug("to young -> not matching")
                    return False

                if self.__agemax is not None and current > self.__agemax:
                    logger.debug("to old -> not matching")
                    return False
            else:
                if self.__agemin is not None and current > self.__agemin and (
                        self.__agemax is None or current < self.__agemax):
                    logger.debug("not younger than min -> not matching")
                    return False

                if self.__agemax is not None and current < self.__agemax and (
                        self.__agemin is None or current > self.__agemin):
                    logger.debug("not older than max -> not matching")
                    return False

            logger.debug("given age limits ok -> matching")
            return True
        finally:
            logger.decrease_indent()

    # set item
    # item: value for item
    def __set_item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # Current value of condition (based on item or eval)
    def __get_current(self):
        if self.__item is not None:
            # noinspection PyCallingNonCallable
            return self.__item()
        if self.__eval is not None:
            return self.__do_eval(self.__eval)
        raise ValueError("Condition {}: Neither 'item' nor eval given!".format(self.__name))

    # Return value for condition
    def __get_value(self):
        if self.__value_item is not None:
            # noinspection PyCallingNonCallable
            return self.__cast_func(self.__value_item())
        elif self.__value_eval is not None:
            return self.__do_eval(self.__value_eval)
        else:
            return self.__value

    # Return min value for condition
    def __get_min(self):
        if self.__min_item is not None:
            # noinspection PyCallingNonCallable
            return self.__cast_func(self.__min_item())
        elif self.__min_eval is not None:
            return self.__do_eval(self.__min_eval)
        else:
            return self.__min

    # Return max value for condition
    def __get_max(self):
        if self.__max_item is not None:
            # noinspection PyCallingNonCallable
            return self.__cast_func(self.__max_item())
        elif self.__max_eval is not None:
            return self.__do_eval(self.__max_eval)
        else:
            return self.__max

    # Name of eval-Object to be displayed in log
    def __get_eval_name(self):
        if self.__item is not None or self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__

    def __do_eval(self, eval_object):
        if isinstance(eval_object, str):
            # noinspection PyUnusedLocal
            sh = self.__sh
            try:
                value = eval(eval_object)
            except Exception as e:
                raise ValueError("Condition {}: problem evaluating {}: {}".format(self.__name, str(object), e))
            else:
                return value
        else:
            # noinspection PyCallingNonCallable
            return eval_object()
