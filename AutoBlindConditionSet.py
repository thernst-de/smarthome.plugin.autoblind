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
from . import AutoBlindCondition
from . import AutoBlindLogger
from . import AutoBlindTools


# Class representing a set of conditions
class AbConditionSet:
    # Name of condition set
    @property
    def name(self):
        return self.__name

    # List of conditions that are part of this condition set
    @property
    def conditions(self):
        return self.__conditions

    # Initialize the condition set
    # smarthome: Instance of smarthome.py-class
    # name: Name of condition set
    def __init__(self, smarthome, name):
        self.__sh = smarthome
        self.__name = name
        self.__conditions = {}

    # Update condition set
    # item: item containing settings for condition set
    # grandparent_item: grandparent item of item (containing the definition if items and evals)
    # logger: Instance of AbLogger to write log messages to
    def update(self, item, grandparent_item, logger: AutoBlindLogger.AbLogger):
        # Update conditions in condition set
        if item is not None:
            for attribute in item.conf:
                try:
                    func, name = AutoBlindTools.partition_strip(attribute, "_")
                    if name == "":
                        continue

                    if not func.startswith("as_"):
                        AutoBlindTools.log_obsolete(item, attribute, "as_" + attribute)

                    # update this condition
                    if name not in self.__conditions:
                        self.__conditions[name] = AutoBlindCondition.AbCondition(self.__sh, name)
                    self.__conditions[name].set(func, item.conf[attribute])

                except ValueError as ex:
                    logger.exception(ex)

        # Update item from grandparent_item
        for attribute in grandparent_item.conf:
            func, name = AutoBlindTools.partition_strip(attribute, "_")
            if name == "":
                continue

            # update item/eval in this condition
            if func == "item" or func == "eval":
                AutoBlindTools.log_obsolete(grandparent_item, attribute, "as_" + attribute)
                if name not in self.__conditions:
                    self.__conditions[name] = AutoBlindCondition.AbCondition(self.__sh, name)
                self.__conditions[name].set(func, grandparent_item.conf[attribute])
            elif func == "as_item" or func == "as_eval":
                if name not in self.__conditions:
                    self.__conditions[name] = AutoBlindCondition.AbCondition(self.__sh, name)
                self.__conditions[name].set(func, grandparent_item.conf[attribute])

    # Check the condition set, optimize and complete it
    # item_state: item to read from
    # abitem_object: Related AbItem instance for later determination of current age and current delay
    # logger: Instance of AbLogger to write log messages to
    def complete(self, item_state, abitem_object, logger: AutoBlindLogger.AbLogger):
        conditions_to_remove = []
        # try to complete conditions
        for condition_name in self.conditions:
            try:
                if not self.__conditions[condition_name].complete(item_state, abitem_object):
                    conditions_to_remove.append(condition_name)
                    continue
                error = self.__conditions[condition_name].error
            except ValueError as ex:
                error = str(ex)
            if error is not None:
                logger.error(
                    "Item '{0}', Condition Set '{1}', condition '{2}': {3}".format(item_state.id(), self.name,
                                                                                   condition_name, error))

        # Remove incomplete conditions
        for condition_name in conditions_to_remove:
            del self.conditions[condition_name]

    # Write the whole condition set to the logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        for condition_name in self.__conditions:
            logger.info("Condition '{0}':", condition_name)
            logger.increase_indent()
            self.__conditions[condition_name].write_to_logger(logger)
            logger.decrease_indent()

    # Check all conditions in the condition set. Return
    # logger: Instance of AbLogger to write to
    # returns: True = all conditions in set are matching, False = at least one condition is not matching
    def all_conditions_matching(self, logger: AutoBlindLogger.AbLogger):
        try:
            logger.info("Check condition set '{0}':", self.__name)
            logger.increase_indent()
            for condition_name in self.__conditions:
                if not self.__conditions[condition_name].check(logger):
                    return False
            return True
        finally:
            logger.decrease_indent()
