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
from . import AutoBlindEval
import datetime


# Class representing a single action
class AbAction:
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
        self.__byattr = None
        self.__mindelta = None
        self.__logic = None
        self.__isRun = False
        self.__delay = 0
        self.__scheduler_name = None

    def update_delay(self, value):
        if isinstance(value, str):
            delay = value.strip()
            if delay.endswith('m'):
                self.__delay = int(delay.strip('m')) * 60
            else:
                self.__delay = int(delay)
        elif isinstance(value,int):
            self.__delay = value

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update_set(self, item_state, value):
        if self.__item is None:
            self.__set_item(AutoBlindTools.find_attribute(self.__sh, item_state, "as_item_" + self.__name))

        func, set_value = AutoBlindTools.partition_strip(value, ":")
        if set_value == "":
            set_value = func
            func = "value"

        if func == "value":
            self.__value = set_value
            self.__eval = None
            self.__from_item = None
            self.__byattr = None
        elif func == "eval":
            self.__value = None
            self.__eval = set_value
            self.__from_item = None
            self.__byattr = None
        elif func == "item":
            self.__value = None
            self.__eval = None
            self.__set_from_item(set_value)
            self.__byattr = None
        elif func == "byattr":
            self.__value = None
            self.__eval = None
            self.__from_item = None
            self.__byattr = set_value

        self.__logic = None
        self.__isRun = False

    # set the action based on a trigger_(name) attribute
    # value: Value of the trigger_(action_name) attribute
    def update_trigger(self, value):

        logic, value = AutoBlindTools.partition_strip(value, ":")
        self.__logic = logic
        if value != "":
            self.__value = value
        else:
            self.__value = None
        self.__eval = None
        self.__from_item = None
        self.__byattr = None
        self.__isRun = False

    # set the action based on a run_(action_name) attribute
    # value: Value of the set_(action_name) attribute
    def update_run(self, value):
        func, set_value = AutoBlindTools.partition_strip(value, ":")
        if set_value == "":
            set_value = func
            func = "eval"

        if func == "eval":
            self.__value = None
            self.__eval = set_value
            self.__from_item = None
            self.__byattr = None
            self.__isRun = True

        self.__logic = None

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        # Nothing to complete if this action triggers a logic or is a "run"-Action or if it's a set-byattr Action
        if self.__logic is not None or self.__isRun or self.__byattr is not None:
            return

        # missing item in action: Try to find it.
        if self.__item is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "as_item_" + self.__name)
            if result is not None:
                self.__set_item(result)

        if self.__mindelta is None:
            result = AutoBlindTools.find_attribute(self.__sh, item_state, "as_mindelta_" + self.__name)
            if result is not None:
                self.__mindelta = result

        if self.__item is not None:
            if self.__value is not None:
                self.__value = self.__item.cast(self.__value)
            if self.__mindelta is not None:
                self.__mindelta = self.__item.cast(self.__mindelta)

        if self.__item is not None:
            self.__scheduler_name = self.__item.id() + "-AbItemDelayTimer"
        elif self.__logic is not None:
            self.__scheduler_name = self.__logic + "-AbLogicDelayTimer"
        elif self.__byattr is not None:
            self.__scheduler_name = self.__byattr + "-AbByAttrDelayTimer"
        else:
            self.__scheduler_name = self.__name + "-AbNameDelayTimer"

    # Execute action
    # logger: Instance of AbLogger to write to
    def execute(self, logger: AutoBlindLogger.AbLogger):
        plan_next = self.__sh.scheduler.return_next(self.__scheduler_name)
        if plan_next is not None and plan_next > self.__sh.now():
            logger.info("Action '{0}: Removing previous delay timer '{1}'.", self.__name, self.__scheduler_name)
            self.__sh.scheduler.remove(self.__scheduler_name)

        if self.__delay == 0:
            self.__execute(logger)
        else:
            logger.info("Action '{0}: Add {1} second timer '{2}' for delayed execution.", self.__name, self.__delay,
                        self.__scheduler_name)
            next_run = self.__sh.now() + datetime.timedelta(seconds=self.__delay)
            self.__sh.scheduler.add(self.__scheduler_name, self.__execute, value={'logger': logger}, next=next_run)

    # Execute action
    # logger: Instance of AbLogger to write to
    def __execute(self, logger: AutoBlindLogger.AbLogger):
        type_name = "Action '{0}'".format(self.__name) if self.__delay == 0 else "Delay Timer '{0}'".format(
            self.__scheduler_name)

        if self.__logic is not None:
            # Trigger logic
            logger.info("{0}: Triggering logic '{1}' using value '{2}'.", type_name, self.__logic,
                        self.__value)
            self.__sh.trigger(self.__logic, by="AutoBlind Plugin", source=self.__name, value=self.__value)
            return

        if self.__byattr is not None:
            logger.info("{0}: Setting values by attribute '{1}'.", type_name, self.__byattr)
            for item in self.__sh.find_items(self.__byattr):
                logger.info("\t{0} = {1}", item.id(), item.conf[self.__byattr])
                item(item.conf[self.__byattr])
            return

        if self.__item is None and not self.__isRun:
            logger.info("{0}: No item defined. Ignoring.", type_name)
            return

        value = None
        if self.__value is not None:
            value = self.__value
        elif self.__eval is not None:
            value = self.__do_eval(logger)
        elif self.__from_item is not None:
            # noinspection PyCallingNonCallable
            value = self.__from_item()

        if value is not None and not self.__isRun:
            if self.__mindelta is not None:
                # noinspection PyCallingNonCallable
                delta = float(abs(self.__item() - value))
                if delta < self.__mindelta:
                    logger.debug(
                        "{0}: Not setting '{1}' to '{2}' because delta '{3:.2}' is lower than mindelta '{4}'",
                        type_name, self.__item.id(), value, delta, self.__mindelta)
                    return

            logger.debug("{0}: Set '{1}' to '{2}'", type_name, self.__item.id(), value)
            # noinspection PyCallingNonCallable
            self.__item(value)

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__logic is not None:
            logger.debug("trigger logic: {0}", self.__logic)
        if self.__item is not None:
            logger.debug("item: {0}", self.__item.id())
        if self.__mindelta is not None:
            logger.debug("mindelta: {0}", self.__mindelta)
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)
        if self.__eval is not None:
            logger.debug("eval: {0}", self.__get_eval_name())
        if self.__from_item is not None:
            logger.debug("value from item: {0}", self.__from_item.id())
        if self.__byattr is not None:
            logger.debug("set by attriute: {0}", self.__byattr)
        if self.__delay != 0:
            logger.debug("Delay: {0} Seconds", self.__delay)

    # Execute eval and return result. In case of errors, write message to log and return None
    # logger: Instance of AbLogger to write to
    def __do_eval(self, logger: AutoBlindLogger.AbLogger):
        if isinstance(self.__eval, str):
            # noinspection PyUnusedLocal
            sh = self.__sh
            if self.__eval.startswith("autoblind_eval"):
                # noinspection PyUnusedLocal
                autoblind_eval = AutoBlindEval.AbEval(self.__sh, logger)
            try:
                value = eval(self.__eval)
            except Exception as e:
                logger.info("Action '{0}: problem evaluating {1}: {2}.", self.__name, self.__get_eval_name(), e)
                return None
        else:
            try:
                # noinspection PyCallingNonCallable
                value = self.__eval()
            except Exception as e:
                logger.info("Action '{0}: problem calling {1}: {2}.", self.__name, self.__get_eval_name(), e)
                return None
        try:
            if self.__item is not None:
                value = self.__item.cast(value)
            return value
        except Exception as e:
            logger.debug("eval returned '{0}', trying to cast this returned exception '{1}'", value, e)
            return None

    # set item
    # item: value for item
    def __set_item(self, item):
        if isinstance(item, str):
            self.__item = self.__sh.return_item(item)
        else:
            self.__item = item

    # set from-item
    # from_item: value for from-item
    def __set_from_item(self, from_item):
        if isinstance(from_item, str):
            self.__from_item = self.__sh.return_item(from_item)
        else:
            self.__from_item = from_item

    # Name of eval-object to be displayed in log
    def __get_eval_name(self):
        if self.__eval is None:
            return None
        if self.__eval is not None:
            if isinstance(self.__eval, str):
                return self.__eval
            else:
                return self.__eval.__module__ + "." + self.__eval.__name__
