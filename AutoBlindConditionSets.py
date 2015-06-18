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
from . import AutoBlindConditionSet
from . import AutoBlindLogger


# Class representing a list of condition sets
class AbConditionSets:
    # Initialize the list of condition sets
    # smarthome: Instance of smarthome.py-class
    def __init__(self, smarthome):
        self.__sh = smarthome
        self.__name = None
        self.__condition_sets = {}

    # Return number of condition sets in list
    def count(self):
        return len(self.__condition_sets)

    # Fill a condition set
    # conditionset_name: Name of condition set
    # item: item containing settings for condition set
    # grandparent_item: grandparent item of item (containing the definition if items and evals)
    # logger: Instance of AbLogger to write log messages to
    def fill(self, conditionset_name, item, grandparent_item, logger: AutoBlindLogger.AbLogger):
        # Add condition set if not yet existing
        if conditionset_name not in self.__condition_sets:
            self.__condition_sets[conditionset_name] = AutoBlindConditionSet.AbConditionSet(self.__sh,
                                                                                            conditionset_name)
        # Update this condition set
        self.__condition_sets[conditionset_name].update(item, grandparent_item, logger)

    # Check the condition sets, optimize and complete them
    # item_position: item to read from
    # abitem_object: Related AbItem instance for later determination of current age and current delay
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_position, abitem_object, logger):
        for conditionset_name in self.__condition_sets:
            self.__condition_sets[conditionset_name].complete(item_position, abitem_object, logger)

    # Write all condition sets to logger
    # logger: Instance of AbLogger to write log messages to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        for conditionset_name in self.__condition_sets:
            logger.info("Condition Set '{0}':", conditionset_name)
            logger.increase_indent()
            self.__condition_sets[conditionset_name].write_to_logger(logger)
            logger.decrease_indent()

    # check if one of the conditions sets in the list is matching.
    # logger: Instance of AbLogger to write log messages to
    # returns: True = one condition set is matching or no condition sets are defined, False: no condition set matching
    def one_conditionset_matching(self, logger: AutoBlindLogger.AbLogger):
        if self.count() == 0:
            logger.debug("No condition sets defined -> matching")
            return True
        for conditionset_name in self.__condition_sets:
            if self.__condition_sets[conditionset_name].all_conditions_matching(logger):
                return True
        return False
