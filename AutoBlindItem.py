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
        return self.__item.id()

    # Constructor
    # smarthome: instance of smarthome.py
    # item: item to use
    def __init__(self, smarthome, item):
        self.__sh = smarthome
        self.__item = item
        self.__name = str(self.__item)

        self.__startup_delay = AutoBlindTools.get_num_attribute(self.__item, "as_startup_delay",
                                                                AutoBlindDefaults.startup_delay)
        self.__update_delay = 1

        self.__item_lock = None

        self.__suspend_item = None
        self.__suspend_until = None
        self.__suspend_time = None
        self.__suspend_watch_items = []

        self.__laststate_item_id = None
        self.__laststate_internal_id = ""
        self.__laststate_item_name = None
        self.__laststate_internal_name = ""

        self.__states = []
        self.__delay = 0
        self.__actions = {}
        self.__can_not_leave_current_state_since = 0
        self.__repeat_actions = True

        self.__myLogger = None

    # Complete everything
    def complete(self):
        if self.__item is None:
            raise ValueError("No item configured!")

        # initialize logging
        self.__myLogger = AbLogger.create(self.__item)
        self.__myLogger.header("Initialize Item {0}".format(self.id))

        # initialize everything else
        self.__init_check_item_config()
        self.__laststate_init()
        self.__lock_init()
        self.__suspend_init()
        self.__init_states()

        # do some checks
        item_id = self.__item.id()
        if len(self.__states) == 0:
            raise ValueError("{0}: No states defined!".format(item_id))

        # add item trigger
        self.__item.add_method_trigger(self.update_state)

        # timer with startup-delay
        if self.__startup_delay != 0:
            self.__item.timer(self.__startup_delay, 1)

    # log item data
    def write_to_log(self):
        # get crons and cycles
        crons, cycles = self.__get_crons_and_cycles()

        repeat = "Yes" if self.__repeat_actions else "No"

        # log general config
        self.__myLogger.header("Configuration of item {0}".format(self.__name))
        self.__myLogger.info("Cycle: {0}", cycles)
        self.__myLogger.info("Cron: {0}", crons)
        self.__myLogger.info("Startup Delay: {0}", self.__startup_delay)
        self.__myLogger.info("Repeat actions if state is not changed: {0}",repeat)

        self.__laststate_log()
        self.__lock_log()
        self.__suspend_log()

        for state in self.__states:
            state.write_to_log()

    # Find the state, matching the current conditions and perform the actions of this state
    # caller: Caller that triggered the update
    # noinspection PyCallingNonCallable,PyUnusedLocal
    def update_state(self, item, caller=None, source=None, dest=None):
        self.__myLogger.update_logfile()
        self.__myLogger.header("Update state of item {0}".format(self.__name))
        if caller:
            self.__myLogger.debug("Update triggered by {0} (source={1} dest={2})", caller, source, dest)

        # check if locked
        if self.__lock_is_active():
            self.__myLogger.info("AutoBlind is locked")
            self.__laststate_name = AutoBlindDefaults.laststate_name_manually_locked
            return

        # check if suspended
        if self.__suspend_is_active():
            active_timer_time = self.__suspend_get_time()
            self.__myLogger.info(
                "AutoBlind has been suspended after manual changes. Reactivating at {0}", active_timer_time)
            self.__laststate_name = active_timer_time.strftime(AutoBlindDefaults.laststate_name_suspended)
            return

        # Update current values
        AutoBlindCurrent.update()

        # get last state
        last_state = self.__laststate_get_state()
        if last_state is not None:
            self.__myLogger.info("Last state: {0} ('{1}')", last_state.id, last_state.name)
        if self.__can_not_leave_current_state_since == 0:
            self.__delay = 0
        else:
            self.__delay = time.time() - self.__can_not_leave_current_state_since

        # check if current state can be left
        if last_state is not None and not last_state.can_leave():
            self.__myLogger.info("Can not leave current state, staying at {0} ('{1}')", last_state.id, last_state.name)
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
                    self.__myLogger.info("No matching state found, no previous state available. Doing nothing.")
                else:
                    self.__myLogger.info("No matching state found, staying at {0} ('{1}')", last_state.id,
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
            if self.__laststate_name != new_state.name:
                self.__laststate_name = new_state.name
            else:
                do_actions = self.__repeat_actions
            self.__myLogger.info("Staying at {0} ('{1}')", new_state.id, new_state.name)
        else:
            # New state is different from last state
            self.__myLogger.info("Changing to {0} ('{1}')", new_state.id, new_state.name)
            self.__laststate_id = new_state.id
            self.__laststate_name = new_state.name

        if do_actions:
            new_state.activate()
        else:
            self.__myLogger.info("Repeating actions is deactivated.")

    # region Laststate *************************************************************************************************
    # Init laststate_id and laststate_name
    def __laststate_init(self):
        self.__laststate_item_id = AutoBlindTools.get_item_attribute(self.__item, "as_laststate_item_id", self.__sh)
        if self.__laststate_item_id is not None:
            self.__laststate_internal_id == self.__laststate_item_id()
        self.__laststate_item_name = AutoBlindTools.get_item_attribute(self.__item, "as_laststate_item_name", self.__sh)
        if self.__laststate_item_name is not None:
            self.__laststate_internal_name == self.__laststate_item_name()

    # Log laststate settings
    def __laststate_log(self):
        if self.__laststate_item_id is not None:
            self.__myLogger.info("Item 'Laststate Id': {0}", self.__laststate_item_id.id())
        if self.__laststate_item_name is not None:
            self.__myLogger.info("Item 'Laststate Name': {0}", self.__laststate_item_name.id())

    # Get laststate_id
    @property
    def __laststate_id(self):
        return self.__laststate_internal_id

    # Set laststate_id
    # text: Text for laststate_id
    @__laststate_id.setter
    def __laststate_id(self, text):
        self.__laststate_internal_id = text
        if self.__laststate_item_id is not None:
            # noinspection PyCallingNonCallable
            self.__laststate_item_id(self.__laststate_internal_id)

    # Get laststate_name if available
    # text: Text for laststate_name
    @property
    def __laststate_name(self):
        return self.__laststate_internal_name

    # Set laststate_name
    # text: Text for laststate_name
    @__laststate_name.setter
    def __laststate_name(self, text):
        self.__laststate_internal_name = text
        if self.__laststate_item_name is not None:
            # noinspection PyCallingNonCallable
            self.__laststate_item_name(self.__laststate_internal_name)

    # get last state object based on laststate_id
    # returns: AbState instance of last state or "None" if no last state could be found
    def __laststate_get_state(self):
        last_state_id = self.__laststate_id
        for state in self.__states:
            if state.id == last_state_id:
                return state
        return None

    # endregion

    # region Lock ******************************************************************************************************
    # Init lock item
    def __lock_init(self):
        self.__item_lock = AutoBlindTools.get_item_attribute(self.__item, "as_lock_item", self.__sh)
        if self.__item_lock is not None:
            self.__item_lock.add_method_trigger(self.__lock_callback)

    # Log lock settings
    def __lock_log(self):
        if self.__item_lock is not None:
            self.__myLogger.info("Item 'Lock': {0}", self.__item_lock.id())

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

        self.__myLogger.update_logfile()
        self.__myLogger.header("Item 'lock' changed")
        self.__myLogger.debug("'{0}' set to '{1}' by '{2}'", item.id(), item(), caller)

        # Any manual change of lock removes suspension
        if self.__suspend_is_active():
            self.__suspend_remove()

        # trigger delayed update
        self.__item.timer(self.__update_delay, 1)

    # endregion

    # region Suspend ***************************************************************************************************
    # init suspension item. Create dummy item if missing
    def __suspend_init(self):
        self.__suspend_item = AutoBlindTools.get_item_attribute(self.__item, "as_suspend_item", self.__sh)
        self.__suspend_until = None
        self.__suspend_watch_items = []
        self.__suspend_time = AutoBlindTools.get_num_attribute(self.__item, "as_suspend_time",
                                                               AutoBlindDefaults.suspend_time)

        if "as_suspend_watch" in self.__item.conf:
            suspend_on = self.__item.conf["as_suspend_watch"]
        else:
            return

        if isinstance(suspend_on, str):
            suspend_on = [suspend_on]
        for entry in suspend_on:
            for item in self.__sh.match_items(entry):
                item.add_method_trigger(self.__suspend_watch_callback)
                self.__suspend_watch_items.append(item)

    # Log suspension settings
    def __suspend_log(self):
        if self.__suspend_item is not None:
            self.__myLogger.info("Item 'Suspend': {0}", self.__suspend_item.id())
        if len(self.__suspend_watch_items) > 0:
            self.__myLogger.info("Suspension time on manual changes: {0}", self.__suspend_time)
            self.__myLogger.info("Items causing suspension when changed:")
            self.__myLogger.increase_indent()
            for watch_manual_item in self.__suspend_watch_items:
                self.__myLogger.info("{0} ('{1}')", watch_manual_item.id(), str(watch_manual_item))
            self.__myLogger.decrease_indent()

    # suspend automatic mode for a given time
    def __suspend_set(self):
        self.__myLogger.debug("Suspending automatic mode for {0} seconds.", self.__suspend_time)
        self.__suspend_until = self.__sh.now() + datetime.timedelta(seconds=self.__suspend_time)
        self.__sh.scheduler.add(self.id + "SuspensionRemove-Timer", self.__suspend_reactivate_callback,
                                next=self.__suspend_until)

        if self.__suspend_item is not None:
            self.__suspend_item(True, caller="AutoBlind")

        # trigger delayed update
        self.__item.timer(self.__update_delay, 1)

    # remove suspension
    def __suspend_remove(self):
        self.__myLogger.debug("Removing suspension of automatic mode.")
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
        self.__myLogger.update_logfile()
        self.__myLogger.header("Watch suspend triggered")
        self.__myLogger.debug("Manual operation: Change of item '{0}' by '{1}' (source='{2}', dest='{3}')",
                              item.id(), caller, source, dest)
        self.__myLogger.increase_indent()
        if caller == "AutoBlind Plugin":
            self.__myLogger.debug("Ignoring changes from AutoBlind Plugin")
        elif self.__lock_is_active():
            self.__myLogger.debug("Automatic mode alreadylocked")
        else:
            self.__suspend_set()
        self.__myLogger.decrease_indent()

    # callback function that is called when the suspend time is over
    def __suspend_reactivate_callback(self):
        self.__myLogger.update_logfile()
        self.__myLogger.header("Suspend time over")
        self.__suspend_remove()

    # endregion

    # region Additional initialization *********************************************************************************
    # Check item settings and update if required
    # noinspection PyProtectedMember
    def __init_check_item_config(self):
        self.__repeat_actions = AutoBlindTools.get_bool_attribute(self.__item, "as_repeat_actions", True)

        # set "enforce updates" for item
        self.__item._enforce_updates = True

        # set "eval" for item if initial
        if self.__item._eval_trigger and self.__item._eval is None:
            self.__item._eval = "1"

        # Check scheduler settings and update if requred
        job = self.__sh.scheduler._scheduler.get(self.__item.id())
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
            self.__sh.scheduler.change(self.__item.id(), cycle=new_cycle, cron=new_cron)

    # find states and init them
    def __init_states(self):
        # These items are referenced items, if they are below the object item, they are no states
        non_state_item_ids = []
        if self.__item_lock is not None:
            non_state_item_ids.append(self.__item_lock.id())
        if self.__suspend_item is not None:
            non_state_item_ids.append(self.__suspend_item.id())
        if self.__laststate_item_id is not None:
            non_state_item_ids.append(self.__laststate_item_id.id())
        if self.__laststate_item_name is not None:
            non_state_item_ids.append(self.__laststate_item_name.id())

        for item_state in self.__item.return_children():
            if item_state.id() in non_state_item_ids:
                continue
            state = AutoBlindState.AbState(self.__sh, item_state, self.__item, self, self.__myLogger)
            self.__states.append(state)
    # endregion

    # region Helper methods ********************************************************************************************
    # get crons and cycles in readable format
    def __get_crons_and_cycles(self):
        # get crons and cycles
        cycles = ""
        crons = ""

        # noinspection PyProtectedMember
        job = self.__sh.scheduler._scheduler.get(self.__item.id())
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

    # get triggers in readable format
    def __get_triggers(self):
        triggers = ""
        for trigger in self.__item._eval_trigger:
            if triggers != "":
                triggers += ", "
            triggers += trigger
        if triggers == "":
            triggers = "Inactive"
        return triggers

    # endregion

    # region Methods for CLI commands **********************************************************************************
    def cli_list(self, handler):
        handler.push("{0}: {1}\n".format(self.id, self.__laststate_name))

    def cli_detail(self, handler):
        # get data
        crons, cycles = self.__get_crons_and_cycles()
        triggers = self.__get_triggers()

        handler.push("AutoState Item {0}:\n".format(self.id))
        handler.push("\tCurrent state: {0}\n".format(self.__laststate_name))
        handler.push("\tStartup Delay: {0}\n".format(self.__startup_delay))
        handler.push("\tCycle: {0}\n".format(cycles))
        handler.push("\tCron: {0}\n".format(crons))
        handler.push("\tTrigger: {0}\n".format(triggers))

    # endregion

    # return age of item
    def get_age(self):
        if self.__laststate_item_id is not None:
            return self.__laststate_item_id.age()
        else:
            self.__myLogger.warning('No item for last state id given. Can not determine age!')
            return 0

    # return delay of item
    def get_delay(self):
        return self.__delay

    # return id of last state
    def get_laststate_id(self):
        return self.__laststate_id
