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
from . import AutoBlindValue
import datetime


# Base class from which all action classes are derived
class AbActionBase:
    # Cast function for delay
    # value: value to cast
    @staticmethod
    def __cast_delay(value):
        if isinstance(value, str):
            delay = value.strip()
            if delay.endswith('m'):
                return int(delay.strip('m')) * 60
            else:
                return int(delay)
        elif isinstance(value, int):
            return value

    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # logger: Instance of AbLogger to write to
    # name: Name of action
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger, name: str):
        self._sh = smarthome
        self._logger = logger
        self._name = name
        self.__delay = AutoBlindValue.AbValue(self._sh, self._logger, "delay")
        self._scheduler_name = None

    def update_delay(self, value):
        self.__delay.set(value, "")
        self.__delay.set_cast(AbActionBase.__cast_delay)

    # Write action to logger
    def write_to_logger(self):
        self.__delay.write_to_logger()

    # Execute action (considering delay, etc)
    def execute(self):
        if not self._can_execute():
            return

        actionname = "Action '{0}'".format(self._name) if self.__delay == 0 else "Delay Timer '{0}'".format(
            self._scheduler_name)

        plan_next = self._sh.scheduler.return_next(self._scheduler_name)
        if plan_next is not None and plan_next > self._sh.now():
            self._logger.info("Action '{0}: Removing previous delay timer '{1}'.", self._name, self._scheduler_name)
            self._sh.scheduler.remove(self._scheduler_name)

        delay = 0 if self.__delay.is_empty() else self.__delay.get()
        if delay == 0:
            self._execute(actionname)
        else:
            self._logger.info("Action '{0}: Add {1} second timer '{2}' for delayed execution.", self._name,
                              delay, self._scheduler_name)
            next_run = self._sh.now() + datetime.timedelta(seconds=delay)
            self._sh.scheduler.add(self._scheduler_name, self._execute, value={'actionname': actionname}, next=next_run)

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        raise NotImplementedError("Class %s doesn't implement update()" % self.__class__.__name__)

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        raise NotImplementedError("Class %s doesn't implement complete()" % self.__class__.__name__)

    # Check if execution is possible
    def _can_execute(self):
        raise NotImplementedError("Class %s doesn't implement _can_execute()" % self.__class__.__name__)

    # Really execute the action (needs to be implemented in derived classes)
    def _execute(self, actionname: str):
        raise NotImplementedError("Class %s doesn't implement _execute()" % self.__class__.__name__)


# Class representing a single "as_set" action
class AbActionSetItem(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # logger: Instance of AbLogger to write to
    # name: Name of action
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger, name: str):
        AbActionBase.__init__(self, smarthome, logger, name)
        self.__item = None
        self.__value = AutoBlindValue.AbValue(self._sh, self._logger, "value")
        self.__mindelta = AutoBlindValue.AbValue(self._sh, self._logger, "mindelta")

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        self.__value.set(value, "")

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        # missing item in action: Try to find it.
        if self.__item is None:
            result = AutoBlindTools.find_attribute(self._sh, item_state, "as_item_" + self._name)
            if result is not None:
                self.__set_item(result)

        if self.__mindelta.is_empty():
            result = AutoBlindTools.find_attribute(self._sh, item_state, "as_mindelta_" + self._name)
            if result is not None:
                self.__mindelta.set(result, "")

        if self.__item is not None:
            self.__value.set_cast(self.__item.cast)
            self.__mindelta.set_cast(self.__item.cast)
            self._scheduler_name = self.__item.id() + "-AbItemDelayTimer"

    # Write action to logger
    def write_to_logger(self):
        AbActionBase.write_to_logger(self)
        if self.__item is not None:
            self._logger.debug("item: {0}", self.__item.id())
        self.__mindelta.write_to_logger()
        self.__value.write_to_logger()

    # Check if execution is possible
    def _can_execute(self):
        if self.__item is None:
            self._logger.info("Action '{0}': No item defined. Ignoring.", self._name)
            return False

        if self.__value.is_empty():
            self._logger.info("Action '{0}': No value defined. Ignoring.", self._name)
            return False

        return True

    # Really execute the action (needs to be implemented in derived classes)
    def _execute(self, actionname: str):
        value = self.__value.get()
        if value is None:
            return

        if not self.__mindelta.is_empty():
            mindelta = self.__mindelta.get()
            # noinspection PyCallingNonCallable
            delta = float(abs(self.__item() - value))
            if delta < mindelta:
                self._logger.debug(
                    "{0}: Not setting '{1}' to '{2}' because delta '{3:.2}' is lower than mindelta '{4}'", actionname,
                    self.__item.id(), value, delta, mindelta)
                return

        self._logger.debug("{0}: Set '{1}' to '{2}'", actionname, self.__item.id(), value)
        # noinspection PyCallingNonCallable
        self.__item(value)

    # set item
    # item: value for item
    def __set_item(self, item):
        if isinstance(item, str):
            self.__item = self._sh.return_item(item)
        else:
            self.__item = item


# Class representing a single "as_setbyattr" action
class AbActionSetByattr(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # logger: Instance of AbLogger to write to
    # name: Name of action
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger, name: str):
        AbActionBase.__init__(self, smarthome, logger, name)
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
    def write_to_logger(self):
        AbActionBase.write_to_logger(self)
        if self.__byattr is not None:
            self._logger.debug("set by attriute: {0}", self.__byattr)

    # Check if execution is possible
    def _can_execute(self):
        return True

    # Really execute the action
    def _execute(self, actionname: str):
        self._logger.info("{0}: Setting values by attribute '{1}'.", actionname, self.__byattr)
        for item in self._sh.find_items(self.__byattr):
            self._logger.info("\t{0} = {1}", item.id(), item.conf[self.__byattr])
            item(item.conf[self.__byattr])


# Class representing a single "as_trigger" action
class AbActionTrigger(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # logger: Instance of AbLogger to write to
    # name: Name of action
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger, name: str):
        AbActionBase.__init__(self, smarthome, logger, name)
        self.__logic = None
        self.__value = None

    # set the action based on a set_(action_name) attribute
    # item_state: state item to read from
    # value: Value of the set_(action_name) attribute
    def update(self, item_state, value):
        logic, value = AutoBlindTools.partition_strip(value, ":")
        self.__logic = logic
        self.__value = None if value == "" else value

    # Complete action
    # item_state: state item to read from
    def complete(self, item_state):
        self._scheduler_name = self.__logic + "-AbLogicDelayTimer"

    # Write action to logger
    def write_to_logger(self):
        AbActionBase.write_to_logger(self)
        if self.__logic is not None:
            self._logger.debug("trigger logic: {0}", self.__logic)
        if self.__value is not None:
            self._logger.debug("value: {0}", self.__value)

    # Check if execution is possible
    def _can_execute(self):
        return True

    # Really execute the action
    def _execute(self, actionname: str):
        # Trigger logic
        self._logger.info("{0}: Triggering logic '{1}' using value '{2}'.", actionname, self.__logic, self.__value)
        self._sh.trigger(self.__logic, by="AutoBlind Plugin", source=self._name, value=self.__value)


# Class representing a single "as_run" action
class AbActionRun(AbActionBase):
    # Initialize the action
    # smarthome: Instance of smarthome.py-class
    # logger: Instance of AbLogger to write to
    # name: Name of action
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger, name: str):
        AbActionBase.__init__(self, smarthome, logger, name)
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
    def write_to_logger(self):
        AbActionBase.write_to_logger(self)
        if self.__eval is not None:
            self._logger.debug("eval: {0}", AutoBlindTools.get_eval_name(self.__eval))

    # Check if execution is possible
    def _can_execute(self):
        return True

    # Really execute the action
    def _execute(self, actionname: str):
        if isinstance(self.__eval, str):
            # noinspection PyUnusedLocal
            sh = self._sh
            if self.__eval.startswith("autoblind_eval"):
                # noinspection PyUnusedLocal
                autoblind_eval = AutoBlindEval.AbEval(self._sh, self._logger)
            try:
                eval(self.__eval)
            except Exception as e:
                self._logger.error(
                    "{0}: Problem evaluating '{1}': {2}.".format(actionname, AutoBlindTools.get_eval_name(self.__eval),
                                                                 e))
        else:
            try:
                # noinspection PyCallingNonCallable
                self.__eval()
            except Exception as e:
                self._logger.error(
                    "{0}: Problem calling '{0}': {1}.".format(actionname, AutoBlindTools.get_eval_name(self.__eval), e))
