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
import time
import datetime
from . import AutoBlindTools
from .AutoBlindLogger import AbLogger
from . import AutoBlindState
from . import AutoBlindDefaults
from . import AutoBlindCurrent


# Class representing a blind item
# noinspection PyCallingNonCallable
class AbItem:
    # return item id
    @property
    def id(self):
        return self.__id

    # return instance of smarthome.py class
    @property
    def sh(self):
        return self.__sh

    # return instance of logger class
    @property
    def logger(self):
        return self.__logger

    # return main autoblind item
    def item(self):
        return self.__item

    # Constructor
    # smarthome: instance of smarthome.py
    # item: item to use
    def __init__(self, smarthome, item):
        self.__sh = smarthome
        self.__item = item
        self.__id = self.__item.id()
        self.__name = str(self.__item)

        self.__startup_delay = AutoBlindTools.get_num_attribute(self.__item, "as_startup_delay",
                                                                AutoBlindDefaults.startup_delay)
        self.__update_delay = 1

        # Init lock settings
        self.__item_lock = AutoBlindTools.get_item_attribute(self.__item, "as_lock_item", self.__sh)

        # Init suspend settings
        self.__suspend_item = AutoBlindTools.get_item_attribute(self.__item, "as_suspend_item", self.__sh)
        self.__suspend_until = None
        self.__suspend_watch_items = []
        if "as_suspend_watch" in self.__item.conf:
            suspend_on = self.__item.conf["as_suspend_watch"]
            if isinstance(suspend_on, str):
                suspend_on = [suspend_on]
            for entry in suspend_on:
                for item in self.__sh.match_items(entry):
                    self.__suspend_watch_items.append(item)
        self.__suspend_time = AutoBlindTools.get_num_attribute(self.__item, "as_suspend_time",
                                                               AutoBlindDefaults.suspend_time)

        # Init laststate items/values
        self.__laststate_item_id = AutoBlindTools.get_item_attribute(self.__item, "as_laststate_item_id", self.__sh)
        self.__laststate_internal_id = "" if self.__laststate_item_id is None else self.__laststate_item_id()
        self.__laststate_item_name = AutoBlindTools.get_item_attribute(self.__item, "as_laststate_item_name", self.__sh)
        self.__laststate_internal_name = "" if self.__laststate_item_name is None else self.__laststate_item_name()

        self.__states = []
        self.__delay = 0
        self.__can_not_leave_current_state_since = 0
        self.__repeat_actions = AutoBlindTools.get_bool_attribute(self.__item, "as_repeat_actions", True)

        self.__update_trigger_item = None
        self.__update_trigger_caller = None
        self.__update_trigger_source = None
        self.__update_trigger_dest = None

        # initialize logging
        self.__logger = AbLogger.create(self.__item)
        self.__logger.header("Initialize Item {0}".format(self.id))

        # Check item configuration
        self.__check_item_config()

        # initialize states
        for item_state in self.__item.return_children():
            self.__states.append(AutoBlindState.AbState(self, item_state))
        if len(self.__states) == 0:
            raise ValueError("{0}: No states defined!".format(self.id))

        # Write settings to log
        self.__write_to_log()

        # now add all triggers
        self.__add_triggers()

        # start timer with startup-delay
        if self.__startup_delay != 0:
            self.__item.timer(self.__startup_delay, 1)

    # Find the state, matching the current conditions and perform the actions of this state
    # caller: Caller that triggered the update
    # noinspection PyCallingNonCallable,PyUnusedLocal
    def update_state(self, item, caller=None, source=None, dest=None):
        self.__logger.update_logfile()
        self.__logger.header("Update state of item {0}".format(self.__name))
        if caller:
            item_id = item.id() if item is not None else "(no item)"
            self.__logger.debug("Update triggered by {0} (item={1} source={2} dest={3})", caller, item_id, source, dest)

        self.__update_trigger_item = item.id()
        self.__update_trigger_caller = caller
        self.__update_trigger_source = source
        self.__update_trigger_dest = dest

        # check if locked
        if self.__lock_is_active():
            self.__logger.info("AutoBlind is locked")
            self.__laststate_internal_name = AutoBlindDefaults.laststate_name_manually_locked
            return

        # check if suspended
        if self.__suspend_is_active():
            # noinspection PyNoneFunctionAssignment
            active_timer_time = self.__suspend_get_time()
            self.__logger.info(
                "AutoBlind has been suspended after manual changes. Reactivating at {0}", active_timer_time)
            self.__laststate_internal_name = active_timer_time.strftime(AutoBlindDefaults.laststate_name_suspended)
            return

        # Update current values
        AutoBlindCurrent.update()

        # get last state
        last_state = self.__laststate_get()
        if last_state is not None:
            self.__logger.info("Last state: {0} ('{1}')", last_state.id, last_state.name)
        if self.__can_not_leave_current_state_since == 0:
            self.__delay = 0
        else:
            self.__delay = time.time() - self.__can_not_leave_current_state_since

        # check if current state can be left
        if last_state is not None and not last_state.can_leave():
            self.__logger.info("Can not leave current state, staying at {0} ('{1}')", last_state.id, last_state.name)
            can_leave_state = False
            new_state = last_state
            if self.__can_not_leave_current_state_since == 0:
                self.__can_not_leave_current_state_since = time.time()
        else:
            can_leave_state = True
            new_state = None

        if can_leave_state:
            # find new state
            for state in self.__states:
                if state.can_enter():
                    new_state = state
                    self.__can_not_leave_current_state_since = 0
                    break

            # no new state -> leave
            if new_state is None:
                if last_state is None:
                    self.__logger.info("No matching state found, no previous state available. Doing nothing.")
                else:
                    self.__logger.info("No matching state found, staying at {0} ('{1}')", last_state.id,
                                       last_state.name)
                return
        else:
            # if current state can not be left, check if enter conditions are still valid.
            # If yes, set "can_not_leave_current_state_since" to 0
            if new_state.can_enter():
                self.__can_not_leave_current_state_since = 0

        # get data for new state
        do_actions = True
        if last_state is not None and new_state.id == last_state.id:
            # New state is last state
            if self.__laststate_internal_name != new_state.name:
                self.__laststate_set(new_state)
            else:
                do_actions = self.__repeat_actions
            self.__logger.info("Staying at {0} ('{1}')", new_state.id, new_state.name)
        else:
            # New state is different from last state
            self.__logger.info("Changing to {0} ('{1}')", new_state.id, new_state.name)
            self.__laststate_set(new_state)

        if do_actions:
            new_state.activate()
        else:
            self.__logger.info("Repeating actions is deactivated.")

    # region Laststate *************************************************************************************************
    # Set laststate
    # new_state: new state to be used as laststate
    def __laststate_set(self, new_state):
        self.__laststate_internal_id = new_state.id
        if self.__laststate_item_id is not None:
            # noinspection PyCallingNonCallable
            self.__laststate_item_id(self.__laststate_internal_id)

        self.__laststate_internal_name = new_state.name
        if self.__laststate_item_name is not None:
            # noinspection PyCallingNonCallable
            self.__laststate_item_name(self.__laststate_internal_name)

    # get last state object based on laststate_id
    # returns: AbState instance of last state or "None" if no last state could be found
    def __laststate_get(self):
        for state in self.__states:
            if state.id == self.__laststate_internal_id:
                return state
        return None

    # endregion

    # region Lock ******************************************************************************************************
    # get the value of lock item
    # returns: value of lock item
    def __lock_is_active(self):
        if self.__item_lock is not None:
            # noinspection PyCallingNonCallable
            return self.__item_lock()
        else:
            return False

    # callback function that is called when the lock item is being changed
    # noinspection PyUnusedLocal
    def __lock_callback(self, item, caller=None, source=None, dest=None):
        # we're just changing "lock" ourselves ... ignore
        if caller == "AutoBlind":
            return

        self.__logger.update_logfile()
        self.__logger.header("Item 'lock' changed")
        self.__logger.debug("'{0}' set to '{1}' by '{2}'", item.id(), item(), caller)

        # Any manual change of lock removes suspension
        if self.__suspend_is_active():
            self.__suspend_remove()

        # trigger delayed update
        self.__item.timer(self.__update_delay, 1)

    # endregion

    # region Suspend ***************************************************************************************************
    # suspend automatic mode for a given time
    def __suspend_set(self):
        self.__logger.debug("Suspending automatic mode for {0} seconds.", self.__suspend_time)
        self.__suspend_until = self.__sh.now() + datetime.timedelta(seconds=self.__suspend_time)
        self.__sh.scheduler.add(self.id + "SuspensionRemove-Timer", self.__suspend_reactivate_callback,
                                next=self.__suspend_until)

        if self.__suspend_item is not None:
            self.__suspend_item(True, caller="AutoBlind")

        # trigger delayed update
        self.__item.timer(self.__update_delay, 1)

    # remove suspension
    def __suspend_remove(self):
        self.__logger.debug("Removing suspension of automatic mode.")
        self.__suspend_until = None
        self.__sh.scheduler.remove(self.id + "SuspensionRemove-Timer")

        if self.__suspend_item is not None:
            self.__suspend_item(False, caller="AutoBlind")

        # trigger delayed update
        self.__item.timer(self.__update_delay, 1)

    # check if suspension is active
    # returns: True = automatic mode is suspended, False = automatic mode is not suspended
    def __suspend_is_active(self):
        return self.__suspend_until is not None

    # return time when timer on item "suspended" will be called. None if no timer is set
    # returns: time that has been set for the timer on item "suspended"
    def __suspend_get_time(self):
        return self.__suspend_until

    # callback function that is called when one of the items given at "watch_manual" is being changed
    # noinspection PyUnusedLocal
    def __suspend_watch_callback(self, item, caller=None, source=None, dest=None):
        self.__logger.update_logfile()
        self.__logger.header("Watch suspend triggered")
        self.__logger.debug("Manual operation: Change of item '{0}' by '{1}' (source='{2}', dest='{3}')",
                            item.id(), caller, source, dest)
        self.__logger.increase_indent()
        if caller == "AutoBlind Plugin":
            self.__logger.debug("Ignoring changes from AutoBlind Plugin")
        elif self.__lock_is_active():
            self.__logger.debug("Automatic mode alreadylocked")
        else:
            self.__suspend_set()
        self.__logger.decrease_indent()

    # callback function that is called when the suspend time is over
    def __suspend_reactivate_callback(self):
        self.__logger.update_logfile()
        self.__logger.header("Suspend time over")
        self.__suspend_remove()

    # endregion

    # region Helper methods ********************************************************************************************
    # add all required triggers
    def __add_triggers(self):
        # add lock trigger
        if self.__item_lock is not None:
            self.__item_lock.add_method_trigger(self.__lock_callback)

        # add triggers for suspend watch items
        for item in self.__suspend_watch_items:
            item.add_method_trigger(self.__suspend_watch_callback)

        # add item trigger
        self.__item.add_method_trigger(self.update_state)

    # Check item settings and update if required
    # noinspection PyProtectedMember
    def __check_item_config(self):
        # set "enforce updates" for item
        self.__item._enforce_updates = True

        # set "eval" for item if initial
        if self.__item._eval_trigger and self.__item._eval is None:
            self.__item._eval = "1"

        # Check scheduler settings and update if requred
        job = self.__sh.scheduler._scheduler.get(self.id)
        if job is None:
            # We do not have an scheduler job so there is nothing to check and update
            return

        changed = False

        # inject value into cycle if required
        if "cycle" in job and job["cycle"] is not None:
            cycle = list(job["cycle"].keys())[0]
            value = job["cycle"][cycle]
            if value is None:
                value = "1"
                changed = True
            new_cycle = {cycle: value}
        else:
            new_cycle = None

        # inject value into cron if required
        if "cron" in job and job["cron"] is not None:
            new_cron = {}
            for entry, value in job['cron'].items():
                if value is None:
                    value = 1
                    changed = True
                new_cron[entry] = value
        else:
            new_cron = None

        # change scheduler settings if cycle or cron have been changed
        if changed:
            self.__sh.scheduler.change(self.id, cycle=new_cycle, cron=new_cron)

    # get triggers in readable format
    def __verbose_eval_triggers(self):
        # noinspection PyProtectedMember
        if not self.__item._eval_trigger:
            return "Inactive"

        triggers = ""
        # noinspection PyProtectedMember
        for trigger in self.__item._eval_trigger:
            if triggers != "":
                triggers += ", "
            triggers += trigger
        return triggers

    # get crons and cycles in readable format
    def __verbose_crons_and_cycles(self):
        # get crons and cycles
        cycles = ""
        crons = ""

        # noinspection PyProtectedMember
        job = self.__sh.scheduler._scheduler.get(self.__item.id)
        if job is not None:
            if "cycle" in job and job["cycle"] is not None:
                cycle = list(job["cycle"].keys())[0]
                cycles = "every {0} seconds".format(cycle)

            # inject value into cron if required
            if "cron" in job and job["cron"] is not None:
                for entry in job['cron']:
                    if crons != "":
                        crons += ", "
                    crons += entry

        if cycles == "":
            cycles = "Inactive"
        if crons == "":
            crons = "Inactive"
        return crons, cycles

    # log item data
    def __write_to_log(self):
        # get crons and cycles
        crons, cycles = self.__verbose_crons_and_cycles()
        triggers = self.__verbose_eval_triggers()
        repeat = "Yes" if self.__repeat_actions else "No"

        # log general config
        self.__logger.header("Configuration of item {0}".format(self.__name))
        self.__logger.info("Startup Delay: {0}", self.__startup_delay)
        self.__logger.info("Cycle: {0}", cycles)
        self.__logger.info("Cron: {0}", crons)
        self.__logger.info("Trigger: {0}".format(triggers))
        self.__logger.info("Repeat actions if state is not changed: {0}", repeat)

        # log laststate settings
        if self.__laststate_item_id is not None:
            self.__logger.info("Item 'Laststate Id': {0}", self.__laststate_item_id.id())
        if self.__laststate_item_name is not None:
            self.__logger.info("Item 'Laststate Name': {0}", self.__laststate_item_name.id())

        # log lock settings
        if self.__item_lock is not None:
            self.__logger.info("Item 'Lock': {0}", self.__item_lock.id())

        # log suspend settings
        if self.__suspend_item is not None:
            self.__logger.info("Item 'Suspend': {0}", self.__suspend_item.id())
        if len(self.__suspend_watch_items) > 0:
            self.__logger.info("Suspension time on manual changes: {0}", self.__suspend_time)
            self.__logger.info("Items causing suspension when changed:")
            self.__logger.increase_indent()
            for watch_manual_item in self.__suspend_watch_items:
                self.__logger.info("{0} ('{1}')", watch_manual_item.id(), str(watch_manual_item))
            self.__logger.decrease_indent()

        # log states
        for state in self.__states:
            state.write_to_log()

    # endregion

    # region Methods for CLI commands **********************************************************************************
    def cli_list(self, handler):
        handler.push("{0}: {1}\n".format(self.id, self.__laststate_internal_name))

    def cli_detail(self, handler):
        # get data
        crons, cycles = self.__verbose_crons_and_cycles()
        triggers = self.__verbose_eval_triggers()
        repeat = "Yes" if self.__repeat_actions else "No"
        handler.push("AutoState Item {0}:\n".format(self.id))
        handler.push("\tCurrent state: {0}\n".format(self.__laststate_internal_name))
        handler.push("\tStartup Delay: {0}\n".format(self.__startup_delay))
        handler.push("\tCycle: {0}\n".format(cycles))
        handler.push("\tCron: {0}\n".format(crons))
        handler.push("\tTrigger: {0}\n".format(triggers))
        handler.push("\tRepeat actions if state is not changed: {0}\n".format(repeat))

    # endregion

    # return age of item
    def get_age(self):
        if self.__laststate_item_id is not None:
            return self.__laststate_item_id.age()
        else:
            self.__logger.warning('No item for last state id given. Can not determine age!')
            return 0

    # return delay of item
    def get_delay(self):
        return self.__delay

    # return id of last state
    def get_laststate_id(self):
        return self.__laststate_internal_id

    # return update trigger item
    def get_update_trigger_item(self):
        return self.__update_trigger_item

    # return update trigger caller
    def get_update_trigger_caller(self):
        return self.__update_trigger_caller

    # return update trigger source
    def get_update_trigger_source(self):
        return self.__update_trigger_source

    # return update trigger dest
    def get_update_trigger_dest(self):
        return self.__update_trigger_dest
