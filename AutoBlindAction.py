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


# Base class from which all action classes are derived
class AbActionBase:
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        self._sh = smarthome
        self._name = name
        self.__delay = 0
        self._scheduler_name = None

    def update_delay(self, value):
        if isinstance(value, str):
            delay = value.strip()
            if delay.endswith('m'):
                self.__delay = int(delay.strip('m')) * 60
            else:
                self.__delay = int(delay)
        elif isinstance(value, int):
            self.__delay = value

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        if self.__delay != 0:
            logger.debug("Delay: {0} Seconds", self.__delay)

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        raise NotImplementedError("Class %s doesn't implement update()" % self.__class__.__name__)

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        raise NotImplementedError("Class %s doesn't implement complete()" % self.__class__.__name__)

    # Execute action (considering delay, etc)
    # logger: Instance of AbLogger to write to
    def execute(self, logger: AutoBlindLogger.AbLogger):
        if not self._can_execute(logger):
            return

        actionname = "Action '{0}'".format(self._name) if self.__delay == 0 else "Delay Timer '{0}'".format(
            self._scheduler_name)

        plan_next = self._sh.scheduler.return_next(self._scheduler_name)
        if plan_next is not None and plan_next > self._sh.now():
            logger.info("Action '{0}: Removing previous delay timer '{1}'.", self._name, self._scheduler_name)
            self._sh.scheduler.remove(self._scheduler_name)

        if self.__delay == 0:
            self._execute(actionname, logger)
        else:
            logger.info("Action '{0}: Add {1} second timer '{2}' for delayed execution.", self._name, self.__delay,
                        self._scheduler_name)
            next_run = self._sh.now() + datetime.timedelta(seconds=self.__delay)
            self._sh.scheduler.add(self._scheduler_name, self._execute,
                                   value={'actionname': actionname, 'logger': logger}, next=next_run)

    # Check if execution is possible
    def _can_execute(self, logger: AutoBlindLogger.AbLogger):
        raise NotImplementedError("Class %s doesn't implement _can_execute()" % self.__class__.__name__)

    # Really execute the action (needs to be implemented in derived classes)
    def _execute(self, actionname: str, logger: AutoBlindLogger.AbLogger):
        raise NotImplementedError("Class %s doesn't implement _execute()" % self.__class__.__name__)

    # Execute eval and return result. In case of errors, write message to log and return None
    # logger: Instance of AbLogger to write to
    def _do_eval(self, actionname: str, eval_func, item, logger: AutoBlindLogger.AbLogger):
        if isinstance(eval_func, str):
            # noinspection PyUnusedLocal
            sh = self._sh
            if eval_func.startswith("autoblind_eval"):
                # noinspection PyUnusedLocal
                autoblind_eval = AutoBlindEval.AbEval(self._sh, logger)
            try:
                value = eval(eval_func)
            except Exception as e:
                logger.info("{0}: problem evaluating {1}: {2}.", actionname, AutoBlindTools.get_eval_name(eval_func), e)
                return None
        else:
            try:
                # noinspection PyCallingNonCallable
                value = eval_func()
            except Exception as e:
                logger.info("{0}: problem calling {1}: {2}.", actionname, AutoBlindTools.get_eval_name(eval_func), e)
                return None
        try:
            if item is not None:
                value = item.cast(value)
            return value
        except Exception as e:
            logger.debug("eval returned '{0}', trying to cast this returned exception '{1}'", value, e)
            return None


# Class representing a single "as_set" action
class AbActionSetItem(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        AbActionBase.__init__(self, smarthome, name)
        self.__item = None
        self.__value = None
        self.__eval = None
        self.__from_item = None
        self.__mindelta = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        if self.__item is None:
            self.__set_item(AutoBlindTools.find_attribute(self._sh, item_state, "as_item_" + self._name))

        func, set_value = AutoBlindTools.partition_strip(value, ":")
        if set_value == "":
            set_value = func
            func = "value"

        if func == "value":
            self.__value = set_value
            self.__eval = None
            self.__from_item = None
        elif func == "eval":
            self.__value = None
            self.__eval = set_value
            self.__from_item = None
        elif func == "item":
            self.__value = None
            self.__eval = None
            self.__set_from_item(set_value)
        elif func == "byattr":
            message = "Attribute 'as_set_{0}' in item '{1}' uses obsolete function 'byattr'. Use attribute 'as_byattr_{0} instead!".format(
                self._name, item_state.id())
            raise ValueError(message)

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        # missing item in action: Try to find it.
        if self.__item is None:
            result = AutoBlindTools.find_attribute(self._sh, item_state, "as_item_" + self._name)
            if result is not None:
                self.__set_item(result)

        if self.__mindelta is None:
            result = AutoBlindTools.find_attribute(self._sh, item_state, "as_mindelta_" + self._name)
            if result is not None:
                self.__mindelta = result

        if self.__item is not None:
            if self.__value is not None:
                self.__value = self.__item.cast(self.__value)
            if self.__mindelta is not None:
                self.__mindelta = self.__item.cast(self.__mindelta)
            self._scheduler_name = self.__item.id() + "-AbItemDelayTimer"

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        AbActionBase.write_to_logger(self, logger)
        if self.__item is not None:
            logger.debug("item: {0}", self.__item.id())
        if self.__mindelta is not None:
            logger.debug("mindelta: {0}", self.__mindelta)
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)
        if self.__eval is not None:
            logger.debug("eval: {0}", AutoBlindTools.get_eval_name(self.__eval))
        if self.__from_item is not None:
            logger.debug("value from item: {0}", self.__from_item.id())

    # Check if execution is possible
    def _can_execute(self, logger: AutoBlindLogger.AbLogger):
        if self.__item is None:
            logger.info("Action '{0}': No item defined. Ignoring.", self._name)
            return False

        return True

    # Really execute the action (needs to be implemented in derived classes)
    def _execute(self, actionname: str, logger: AutoBlindLogger.AbLogger):
        value = None
        if self.__value is not None:
            value = self.__value
        elif self.__eval is not None:
            value = self._do_eval(actionname, self.__eval, self.__item, logger)
        elif self.__from_item is not None:
            # noinspection PyCallingNonCallable
            value = self.__from_item()

        if value is not None and self.__mindelta is not None:
            # noinspection PyCallingNonCallable
            delta = float(abs(self.__item() - value))
            if delta < self.__mindelta:
                logger.debug(
                    "{0}: Not setting '{1}' to '{2}' because delta '{3:.2}' is lower than mindelta '{4}'",
                    actionname, self.__item.id(), value, delta, self.__mindelta)
                return

        logger.debug("{0}: Set '{1}' to '{2}'", actionname, self.__item.id(), value)
        # noinspection PyCallingNonCallable
        self.__item(value)

    # set item
    # item: value for item
    def __set_item(self, item):
        if isinstance(item, str):
            self.__item = self._sh.return_item(item)
        else:
            self.__item = item

    # set from-item
    # from_item: value for from-item
    def __set_from_item(self, from_item):
        if isinstance(from_item, str):
            self.__from_item = self._sh.return_item(from_item)
        else:
            self.__from_item = from_item


# Class representing a single "as_setbyattr" action
class AbActionSetByattr(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        AbActionBase.__init__(self, smarthome, name)
        self.__byattr = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        self.__byattr = value

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        self._scheduler_name = self.__byattr + "-AbByAttrDelayTimer"

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        AbActionBase.write_to_logger(self, logger)
        if self.__byattr is not None:
            logger.debug("set by attriute: {0}", self.__byattr)

    # Check if execution is possible
    def _can_execute(self, logger: AutoBlindLogger.AbLogger):
        return True

    # Really execute the action
    def _execute(self, actionname: str, logger: AutoBlindLogger.AbLogger):
        logger.info("{0}: Setting values by attribute '{1}'.", actionname, self.__byattr)
        for item in self._sh.find_items(self.__byattr):
            logger.info("\t{0} = {1}", item.id(), item.conf[self.__byattr])
            item(item.conf[self.__byattr])


# Class representing a single "as_trigger" action
class AbActionTrigger(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        AbActionBase.__init__(self, smarthome, name)
        self.__logic = None
        self.__value = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        logic, value = AutoBlindTools.partition_strip(value, ":")
        self.__logic = logic
        if value != "":
            self.__value = value
        else:
            self.__value = None

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        self._scheduler_name = self.__logic + "-AbLogicDelayTimer"

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        AbActionBase.write_to_logger(self, logger)
        if self.__logic is not None:
            logger.debug("trigger logic: {0}", self.__logic)
        if self.__value is not None:
            logger.debug("value: {0}", self.__value)

    # Check if execution is possible
    def _can_execute(self, logger: AutoBlindLogger.AbLogger):
        return True

    # Really execute the action
    def _execute(self, actionname: str, logger: AutoBlindLogger.AbLogger):
        # Trigger logic
        logger.info("{0}: Triggering logic '{1}' using value '{2}'.", actionname, self.__logic,
                    self.__value)
        self._sh.trigger(self.__logic, by="AutoBlind Plugin", source=self._name, value=self.__value)


# Class representing a single "as_run" action
class AbActionRun(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # name: Name of action
    def __init__(self, smarthome, name: str):
        AbActionBase.__init__(self, smarthome, name)
        self.__eval = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        func, value = AutoBlindTools.partition_strip(value, ":")
        if value == "":
            value = func
            func = "eval"

        if func == "eval":
            self.__eval = value

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        self._scheduler_name = AutoBlindTools.get_eval_name(self.__eval) + "-AbRunDelayTimer"

    # Write action to logger
    # logger: Instance of AbLogger to write to
    def write_to_logger(self, logger: AutoBlindLogger.AbLogger):
        AbActionBase.write_to_logger(self, logger)
        if self.__eval is not None:
            logger.debug("eval: {0}", AutoBlindTools.get_eval_name(self.__eval))

    # Check if execution is possible
    def _can_execute(self, logger: AutoBlindLogger.AbLogger):
        return True

    # Really execute the action
    def _execute(self, actionname: str, logger: AutoBlindLogger.AbLogger):
        self._do_eval(actionname, self.__eval, None, logger)
