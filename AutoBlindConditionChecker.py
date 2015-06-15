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
#
# AutoBlindConditionChecker
#
# Preparation and checking of conditions
# Everything that has to do with conditions is placed in here, so if 
# additional conditions are required it should be sufficient to extend 
# this class
#########################################################################
import time
import math
from . import AutoBlindTools
import logging

logger = logging.getLogger()


# Create abConditionChecker-Instance
def create(smarthome):
    return AbConditionChecker(smarthome)


# add conditionset based on attributes of an item
# @param conditionsets: dictionary to update
# @param condition_name: name of condition set
# @param item: Item from which the attributes are used
# @param grandparent_item: Parent of parent-Item, containing item_* attributes
# @param smarthome: reference to smarthome-class
def fill_conditionset(conditionsets, condition_name, item, grandparent_item, smarthome):
    # Load existing condition set, create initial condition set if not existing
    if condition_name in conditionsets:
        conditions = conditionsets[condition_name]
    else:
        conditions = {
            "min_time": None,
            "max_time": None,
            "min_weekday": None,
            "max_weekday": None,
            "min_sun_azimut": None,
            "max_sun_azimut": None,
            "min_sun_altitude": None,
            "max_sun_altitude": None,
            "min_age": None,
            "max_age": None,
            "min_delay": None,
            "max_delay": None,
            "items": {}
        }

    # Update conditions in condition set
    if item is not None:
        for attribute in item.conf:
            try:
                # Write known condition attributes from item into conditions-dictionary
                if attribute == "min_sun_azimut" or attribute == "max_sun_azimut" \
                        or attribute == "min_sun_altitude" or attribute == "max_sun_altitude" \
                        or attribute == "min_age" or attribute == "max_age" \
                        or attribute == "min_delay" or attribute == "max_delay" \
                        or attribute == "min_weekday" or attribute == "max_weekday":
                    conditions[attribute] = AutoBlindTools.get_int_attribute(item, attribute)
                elif attribute == "min_time" or attribute == "max_time":
                    conditions[attribute] = AutoBlindTools.get_time_attribute(item, attribute)
                elif attribute.startswith("min_"):
                    name = attribute.split("_", 1)[1]
                    if name not in conditions["items"]:
                        conditions["items"][name] = {}
                    conditions["items"][name]["min"] = item.conf[attribute]
                elif attribute.startswith("max_"):
                    name = attribute.split("_", 1)[1]
                    if name not in conditions["items"]:
                        conditions["items"][name] = {}
                    conditions["items"][name]["max"] = item.conf[attribute]
                elif attribute.startswith("value_"):
                    name = attribute.split("_", 1)[1]
                    if name not in conditions["items"]:
                        conditions["items"][name] = {}
                    conditions["items"][name]["value"] = item.conf[attribute]
            except ValueError as ex:
                logger.exception(ex)

    # Update item from grandparent_item
    for attribute in grandparent_item.conf:
        if attribute.startswith("item_"):
            name = attribute.split("_", 1)[1]
            value = grandparent_item.conf[attribute]
            item = smarthome.return_item(value)
            if name not in conditions["items"]:
                conditions["items"][name] = {}
            conditions["items"][name]["item"] = item

    # Update conditionset
    conditionsets[condition_name] = conditions


# Check the condition sets, optimize and complete them
def complete_conditionsets(conditionsets, item, smarthome, logger):
    for name in conditionsets:
        conditions = conditionsets[name]
        remove = []
        for condname in conditions["items"]:
            condition = conditions["items"][condname]

            # neither value nor min nor max in condition: Something to ignore. We remove it
            if "value" not in condition and "min" not in condition and "max" not in condition:
                remove.append(condname)
                continue

            # missing item in condition: Try to find it
            if "item" not in condition:
                search_for = "item_" + condname
                result = find_item(item, search_for, smarthome)
                if result is not None:
                    condition["item"] = result
                else:
                    logger.warning("missing condition. item= {0}", item.id())
                    continue

            # cast value, min and max
            if "value" in condition:
                condition["value"] = condition["item"].cast(condition["value"])
            if "min" in condition:
                condition["min"] = condition["item"].cast(condition["min"])
            if "max" in condition:
                condition["max"] = condition["item"].cast(condition["max"])

        for condname in remove:
            del conditions["items"][condname]


# find a certain item definition for a generic condition
def find_item(item, name, smarthome):
    # 1: parent of given item could have attribute "item_[name]"
    parent_item = item.return_parent()
    if parent_item is not None:
        if name in parent_item.conf:
            return smarthome.return_item(parent_item.conf[name])

    # 2: if item has attribute "use", get the item to use and search this item for required attribute
    if "use" in item.conf:
        use_item = smarthome.return_item(item.conf["use"])
        result = find_item(use_item, name, smarthome)
        if result is not None:
            return result

    # 3: nothing found
    return None


# Log all conditionsets in a dictionary
def log_conditionsets(logger, conditionsets):
    for key in conditionsets:
        logger.info("Condition Set '{0}':".format(key))
        logger.increase_indent()
        __log_conditions(logger, conditionsets[key])
        logger.decrease_indent()


# Log conditions-dictionary using abLogger-Class
# @param conditions: conditions-dictionary to log
def __log_conditions(logger, conditions):
    __log_condition(logger, conditions, "time")
    __log_condition(logger, conditions, "weekday")
    __log_condition(logger, conditions, "sun_azimut")
    __log_condition(logger, conditions, "sun_altitude")
    __log_condition(logger, conditions, "age")
    __log_condition(logger, conditions, "delay")

    items = conditions["items"]
    for key in items:
        if items[key] is None:
            logger.info("{0}: ERROR", key)
        else:
            logger.info("{0}:", key)
            logger.increase_indent()
            if "item" in items[key]:
                logger.info("item = {0}", items[key]["item"].id())
            if "value" in items[key]:
                logger.info("value = {0}", items[key]["value"])
            if "min" in items[key]:
                logger.info("min = {0}", items[key]["min"])
            if "max" in items[key]:
                logger.info("max = {0}", items[key]["max"])
            logger.decrease_indent()


# Log single condition (min/max) if values are given
# @param conditions: conditions-dictionary to log
# @param name: name of condition (without "min_" or "max_"
def __log_condition(logger, conditions, name):
    min_value = conditions["min_" + name] if "min_" + name in conditions else None
    max_value = conditions["max_" + name] if "max_" + name in conditions else None

    if min_value is None and max_value is None:
        return
    logger.info("{0}:", name)
    logger.increase_indent()
    if min_value is not None:
        logger.info("min = {0}", min_value)
    if max_value is not None:
        logger.info("max = {0}", max_value)
    logger.decrease_indent()


class AbConditionChecker:
    # Current conditions when checking
    __current_age = None
    __current_delay = None
    __current_time = None
    __current_weekday = None
    __current_sun_azimut = None
    __current_sun_altitude = None
    __logger = None

    # Constructor
    def __init__(self, smarthome):
        self.sh = smarthome
        now = time.localtime()
        self.__current_time = [now.tm_hour, now.tm_min]
        self.__current_weekday = now.tm_wday
        azimut, altitude = self.sh.sun.pos()
        self.__current_sun_azimut = math.degrees(float(azimut))
        self.__current_sun_altitude = math.degrees(float(altitude))

    # Update current age for condition checks
    # @param age: current age
    def set_current_age(self, age):
        self.__current_age = age

    # Update current delay for condition checks
    # @param delay: current delay
    def set_current_delay(self, delay):
        self.__current_delay = delay

    # Set current logger instance
    # @param logger logger instance to use
    def set_logger(self, logger):
        self.__logger = logger

    # check if position matches currrent conditions
    # @param position: position to check
    # @return True: position matches current conditions, False: position does not match current conditions
    def can_enter(self, position):
        self.__logger.info("Check Position {0} ('{1}')", position.id(), position.name)
        self.__logger.increase_indent()
        conditionsets = position.get_enter_conditionsets()
        if len(conditionsets) == 0:
            self.__logger.info(
                "No condition sets to check when entering position {0} ('{1}')", position.id(), position.name)
            self.__logger.decrease_indent()
            return True

        for key in conditionsets:
            self.__logger.info("Check Condition Set '{0}'", key)
            self.__logger.increase_indent()
            if self.__match_all(conditionsets[key]):
                self.__logger.decrease_indent()
                self.__logger.info("Position {0} ('{1}') matching", position.id(), position.name)
                self.__logger.decrease_indent()
                return True
            self.__logger.decrease_indent()

        self.__logger.decrease_indent()
        self.__logger.info("Position {0} ('{1}') not matching", position.id(), position.name)
        return False

    # check if position matches currrent conditions
    # @param position: position to check
    # @return True: position matches current conditions, False: position does not match current conditions
    def can_leave(self, position):
        self.__logger.info("Check if position {0} ('{1}') can be left", position.id(), position.name)
        self.__logger.increase_indent()
        conditionsets = position.get_leave_conditionsets()
        if len(conditionsets) == 0:
            self.__logger.info(
                "No condition sets to check when leaving position {0} ('{1}')", position.id(), position.name)
            self.__logger.decrease_indent()
            return True

        for key in conditionsets:
            self.__logger.info("Check Condition Set '{0}'", key)
            self.__logger.increase_indent()
            if self.__match_all(conditionsets[key]):
                self.__logger.decrease_indent()
                self.__logger.info("Position {0} ('{1}') can be left", position.id(), position.name)
                self.__logger.decrease_indent()
                return True
            self.__logger.decrease_indent()

        self.__logger.decrease_indent()
        self.__logger.info("Position {0} ('{1}') must not be left", position.id(), position.name)
        return False

    # check if given conditions match current conditions
    # @param conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_all(self, conditions):
        if not self.__match_items(conditions):
            return False
        if not self.__match_age(conditions):
            return False
        if not self.__match_delay(conditions):
            return False
        if not self.__match_time(conditions):
            return False
        if not self.__match_weekday(conditions):
            return False
        if not self.__match_sun_azimut(conditions):
            return False
        if not self.__match_sun_altitude(conditions):
            return False
        return True

    # Check if given age matches age conditions
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_age(self, conditions):
        min_age = conditions["min_age"] if "min_age" in conditions else None
        max_age = conditions["max_age"] if "max_age" in conditions else None

        self.__logger.debug("condition 'age': min={0} max={1} current={2}", min_age, max_age, self.__current_age)
        self.__logger.increase_indent()
        if min_age is None and max_age is None:
            self.__logger.debug(" -> check age: no limit given")
            self.__logger.decrease_indent()
            return True

        if min_age is not None and self.__current_age < min_age:
            self.__logger.debug(" -> check age: to young")
            self.__logger.decrease_indent()
            return False
        if max_age is not None and self.__current_age > max_age:
            self.__logger.debug(" -> check age: to old")
            self.__logger.decrease_indent()
            return False
        self.__logger.debug(" -> check age: OK")
        self.__logger.decrease_indent()
        return True

    # Check if given dalay matches delay conditions
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_delay(self, conditions):
        min_delay = conditions['min_delay'] if 'min_delay' in conditions else None
        max_delay = conditions['max_delay'] if 'max_delay' in conditions else None

        self.__logger.debug(
            "condition 'delay': min={0} max={1} current={2}", min_delay, max_delay, self.__current_delay)
        self.__logger.increase_indent()

        if self.__current_delay is None:
            self.__logger.debug(" -> check delay: no value given")
            self.__logger.decrease_indent()
            return True

        if min_delay is None and max_delay is None:
            self.__logger.debug(" -> check delay: no limit given")
            self.__logger.decrease_indent()
            return True

        if min_delay is not None and self.__current_delay < min_delay:
            self.__logger.debug(" -> check delay: to early")
            self.__logger.decrease_indent()
            return False
        if max_delay is not None and self.__current_delay > max_delay:
            self.__logger.debug(" -> check age: to late")
            self.__logger.decrease_indent()
            return False
        self.__logger.debug(" -> check delay: OK")
        self.__logger.decrease_indent()
        return True

    # Check if given item conditions match conditions of position
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_items(self, conditions):
        for name in conditions["items"]:
            if not self.__match_item(name, conditions["items"][name]):
                return False
        return True

    # Check if single item condition matches condition of position
    # @param: name: name of element
    # @param: element: condition-information (item, min, max, value)
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_item(self, name, element):
        if "item" not in element:
            self.__logger.info("condition '{0}': no item found! Considering condition as matching!", name)
            return True

        current = element["item"]()

        if "value" in element:
            self.__logger.debug("condition '{0}': value={1} current={2}", name, element["value"], current)
            self.__logger.increase_indent()
            if current == element["value"]:
                self.__logger.debug(" -> matching")
                self.__logger.decrease_indent()
                return True
            else:
                self.__logger.debug(" -> not matching")
                self.__logger.decrease_indent()
                return False
        else:
            min_value = element["min"] if "min" in element else None
            max_value = element["max"] if "max" in element else None
            self.__logger.debug("condition '{0}': min={1} max={2} current={3}", name, min_value, max_value, current)
            self.__logger.increase_indent()
            if min_value is None and max_value is None:
                self.__logger.debug(" -> check {0}: no limit given".format(name))
                self.__logger.decrease_indent()
                return True

            if min_value is not None and current < min_value:
                self.__logger.debug(" -> check {0}: to low".format(name))
                self.__logger.decrease_indent()
                return False
            if max_value is not None and current > max_value:
                self.__logger.debug(" -> check {0}: to high".format(name))
                self.__logger.decrease_indent()
                return False
            self.__logger.debug(" -> check {0}: OK".format(name))
            self.__logger.decrease_indent()
            return True

    # Check if given time matches time conditions of position
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_time(self, conditions):
        min_time = conditions["min_time"] if "min_time" in conditions else None
        max_time = conditions["max_time"] if "max_time" in conditions else None

        self.__logger.debug("condition 'time': min={0} max={1} current={2}", min_time, max_time, self.__current_time)
        self.__logger.increase_indent()
        if min_time is None and max_time is None:
            self.__logger.debug(" -> check time: no limit given")
            self.__logger.decrease_indent()
            return True

        min_time = [0, 0] if min_time is None else min_time
        max_time = [24, 0] if max_time is None else max_time

        if AutoBlindTools.compare_time(min_time, max_time) != 1:
            # min </= max: Normaler Vergleich
            if AutoBlindTools.compare_time(self.__current_time, min_time) == -1 or AutoBlindTools.compare_time(
                    self.__current_time, max_time) == 1:
                self.__logger.debug(" -> check time: not in range (min <= max)")
                self.__logger.decrease_indent()
                return False
        else:
            # min > max: Invertieren
            if AutoBlindTools.compare_time(self.__current_time, min_time) == -1 and AutoBlindTools.compare_time(
                    self.__current_time, max_time) == 1:
                self.__logger.debug(" -> check time: not in range (min > max)")
                self.__logger.decrease_indent()
                return False
        self.__logger.debug(" -> check time: OK")
        self.__logger.decrease_indent()
        return True

    # Check if weekday matches weekday conditions of position
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_weekday(self, conditions):
        min_weekday = conditions["min_weekday"] if "min_weekday" in conditions else None
        max_weekday = conditions["max_weekday"] if "max_weekday" in conditions else None

        self.__logger.debug(
            "condition 'weekday': min={0} max={1} current={2}", min_weekday, max_weekday, self.__current_weekday)
        self.__logger.increase_indent()

        if min_weekday is None and max_weekday is None:
            self.__logger.debug(" -> check weekday: no limit given")
            self.__logger.decrease_indent()
            return True

        min_wday = 0 if min_weekday is None else min_weekday
        max_wday = 6 if max_weekday is None else max_weekday

        if min_wday <= max_wday:
            if self.__current_weekday < min_wday or self.__current_weekday > max_wday:
                self.__logger.debug(" -> check weekday: out of range (min <= max)")
                self.__logger.decrease_indent()
                return False
        else:
            if max_wday < self.__current_weekday < min_wday:
                self.__logger.debug(" -> check weekday: out of range (min > max)")
                self.__logger.decrease_indent()
                return False
        self.__logger.debug(" -> check weekday: OK")
        self.__logger.decrease_indent()
        return True

    # Check if given sun azimut matches sun azimut conditions of position
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_sun_azimut(self, conditions):
        min_sun_azimut = conditions["min_sun_azimut"] if "min_sun_azimut" in conditions else None
        max_sun_azimut = conditions["max_sun_azimut"] if "max_sun_azimut" in conditions else None

        self.__logger.debug("condition 'sun_azimut': min={0} max={1} current={2}", min_sun_azimut, max_sun_azimut,
                            self.__current_sun_azimut)
        self.__logger.increase_indent()

        if min_sun_azimut is None and max_sun_azimut is None:
            self.__logger.debug(" -> check sun azimut: no limit given")
            self.__logger.decrease_indent()
            return True

        min_azimut = 0 if min_sun_azimut is None else min_sun_azimut
        max_azimut = 360 if max_sun_azimut is None else max_sun_azimut

        if min_azimut <= max_azimut:
            if self.__current_sun_azimut < min_azimut or self.__current_sun_azimut > max_azimut:
                self.__logger.debug(" -> check sun azimut: out of range (min <= max)")
                self.__logger.decrease_indent()
                return False
        else:
            if max_azimut < self.__current_sun_azimut < min_azimut:
                self.__logger.debug(" -> check sun azimut: out of range (min > max)")
                self.__logger.decrease_indent()
                return False
        self.__logger.debug(" -> check sun azimut: OK")
        self.__logger.decrease_indent()
        return True

    # Check if given sun altitude matches sun altitude conditions of position
    # @param: conditions: conditions to check
    # @return: True= No Conditions or Conditions matched, False = Conditions not matched
    def __match_sun_altitude(self, conditions):
        min_sun_altitude = conditions["min_sun_altitude"] if "min_sun_altitude" in conditions else None
        max_sun_altitude = conditions["max_sun_altitude"] if "max_sun_altitude" in conditions else None

        self.__logger.debug(
            "condition 'sun_altitude': min={0} max={1} current={2}", min_sun_altitude, max_sun_altitude,
            self.__current_sun_altitude)
        self.__logger.increase_indent()

        if min_sun_altitude is None and max_sun_altitude is None:
            self.__logger.debug(" -> check sun altitude: no limit given")
            self.__logger.decrease_indent()
            return True

        if min_sun_altitude is not None and self.__current_sun_altitude < min_sun_altitude:
            self.__logger.debug(" -> check sun altitude: to low")
            self.__logger.decrease_indent()
            return False
        if max_sun_altitude is not None and self.__current_sun_altitude > max_sun_altitude:
            self.__logger.debug(" -> check sun altitude: to high")
            self.__logger.decrease_indent()
            return False
        self.__logger.debug(" -> check sun altitude: OK")
        self.__logger.decrease_indent()
        return True

    # Return current sun altitude
    # @return current sun altitude
    def get_sun_altitude(self):
        return self.__current_sun_altitude
