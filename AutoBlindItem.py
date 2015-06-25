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
class AbItem:
    # return item id
    @property
    def id(self):
        return self.__item.id()

    # Constructor
    # smarthome: instance of smarthome.py
    # item: item to use
    def __init__(self, smarthome, item):
        self.sh = smarthome
        self.__cycle = None
        self.__startup_delay = None
        self.__name = None
        self.__item_active = None
        self.__item_laststate_id = None
        self.__item_laststate_name = None
        self.__states = []
        self.__manual_break = 0
        self.__delay = 0
        self.__actions = {}
        self.__can_not_leave_current_state_since = 0
        self.__just_changing_active = False

        # get required items for this AutoBlindItem
        self.__item = item
        self.__myLogger = AbLogger.create(item)
        self.__myLogger.header("Initialize Item {0}".format(self.id))

        # initialize everything else
        self.__init_config()
        self.__init_states()
        self.__init_watch_manual()
        self.__init_watch_trigger()

    # Validate data in instance
    # A ValueError is being thown in case of errors
    def validate(self):
        if self.__item is None:
            raise ValueError("No item configured!")

        item_id = self.__item.id()

        if self.__item_active is None:
            raise ValueError("{0}: Item does not have an item for 'active' configured!".format(item_id))

        if self.__item_laststate_id is None:
            raise ValueError("{0}: Item does not have an item for 'state_id' configured!".format(item_id))

        if self.__item_laststate_name is None:
            raise ValueError("{0}: Item does not have an item for 'state_name' configured!".format(item_id))

        if len(self.__states) == 0:
            raise ValueError("{0}: No states defined!".format(item_id))

    # log item data
    def write_to_log(self):
        self.__myLogger.header("Configuration of item {0}".format(self.__name))
        self.__myLogger.info("startup_delay: {0} seconds", self.__startup_delay)
        self.__myLogger.info("cycle: {0} seconds", self.__cycle)
        self.__myLogger.info("Item 'Active': {0}", self.__item_active.id())
        self.__myLogger.info("Item 'State Id': {0}", self.__item_laststate_id.id())
        self.__myLogger.info("Item 'State Name': {0}", self.__item_laststate_name.id())
        for state in self.__states:
            state.write_to_log(self.__myLogger)

    # return age of item
    def get_age(self):
        return self.__item_laststate_id.age()

    # return delay of item
    def get_delay(self):
        return self.__delay

    # Find the state, matching the current conditions and perform the actions of this state
    # caller: Caller that triggered the update
    # noinspection PyCallingNonCallable
    def update_state(self, caller=None):
        self.__myLogger.update_logfile()
        self.__myLogger.header("Update state of item {0}".format(self.__name))
        if caller:
            self.__myLogger.debug("Update triggered by {0}", caller)

        # Check if this AutoBlindItem is active. Leave if not
        if not self.__check_active():
            return

        # Update current values
        AutoBlindCurrent.update()

        # get last state
        last_state = self.__get_last_state()
        if last_state is not None:
            self.__myLogger.info("Last state: {0} ('{1}')", last_state.id, last_state.name)
        if self.__can_not_leave_current_state_since == 0:
            self.__delay = 0
        else:
            self.__delay = time.time() - self.__can_not_leave_current_state_since

        # check if current state can be left
        if last_state is not None and not last_state.can_leave(self.__myLogger):
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
                if state.can_enter(self.__myLogger):
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
            if new_state.can_enter(self.__myLogger):
                self.__can_not_leave_current_state_since = 0

        # get data for new state
        if last_state is not None and new_state.id == last_state.id:
            # New state is last state
            if self.__item_laststate_name() != new_state.name:
                self.__item_laststate_name(new_state.name)
            self.__myLogger.info("Staying at {0} ('{1}')", new_state.id, new_state.name)
        else:
            # New state is different from last state
            self.__myLogger.info("Changing to {0} ('{1}')", new_state.id, new_state.name)
            self.__item_laststate_id(new_state.id)
            self.__item_laststate_name(new_state.name)

        new_state.activate(self.__myLogger)

    # startup scheduler after startup_delay
    def startup(self):
        name = "autoblind-" + self.id
        self.sh.scheduler.add(name, self.update_state, cycle=self.__cycle, offset=self.__startup_delay)

    # get last state based on laststate_id item
    # returns: AbState instance of last state or "None" if no last state could be found
    def __get_last_state(self):
        # noinspection PyCallingNonCallable
        last_state_id = self.__item_laststate_id()
        for state in self.__states:
            if state.id == last_state_id:
                return state
        return None

    # callback function that is called when one of the items given at "watch_manual" is being changed
    # noinspection PyUnusedLocal
    def __watch_manual_callback(self, item, caller=None, source=None, dest=None):
        # ignore changes by plugin or timer
        if caller == "plugin" or caller == "Timer":
            return

        self.__myLogger.update_logfile()
        self.__myLogger.header("Watch_Manual triggered")
        self.__myLogger.debug("Manual operation: Change of item '{0}' by '{1}'", item.id(), caller)
        self.__myLogger.increase_indent()
        if not self.__get_active() and not self.__get_active_timer_active():
            self.__myLogger.debug("Automatic mode already deactivated manually")
        else:
            self.__myLogger.debug("Deactivating automatic mode for {0} seconds.", self.__manual_break)
            self.__set_active(0, self.__manual_break)
            self.__check_active(True)
        self.__myLogger.decrease_indent()

    # callback function that is called when the item "active" is being changed
    # noinspection PyUnusedLocal
    def __reset_active_callback(self, item, caller=None, source=None, dest=None):
        # we're just changing "active" ourselve, .. ignore
        if self.__just_changing_active:
            return

        self.__myLogger.update_logfile()
        self.__myLogger.header("Item 'active' changed")
        if caller == "Timer" and self.__get_active():
            # triggered by timer and active is not TRUE: this was the reactivation by timer
            self.__myLogger.info("Reactivating automatic mode")
        elif self.__get_active_timer_active():
            # A timer is active: remove it as the value has been overwritten
            self.__myLogger.info("Remove timer on 'Active' as value been set to '{0}' by '{1}'", self.__get_active(),
                                 caller)
            self.__remove_active_trigger()
        else:
            # Something else: Just log
            self.__myLogger.debug("'Active' set to '{0}' by '{1}'", self.__get_active(), caller)
        self.__check_active(True)

    # callback function called when item triggering an update is being changed
    # noinspection PyUnusedLocal
    def __watch_trigger_callback(self, item, caller=None, source=None, dest=None):
        self.update_state("item '{0}' changed by '{1}".format(item.id(), caller))

    # set the value of the item "active"
    # value: new value for item
    # reset_interval: Interval after which the value should be reset to the previous value
    def __set_active(self, value, reset_interval=None):
        try:
            self.__just_changing_active = True
            # noinspection PyCallingNonCallable
            self.__item_active(value)
            if reset_interval is not None:
                self.__item_active.timer(reset_interval, not value)
        finally:
            self.__just_changing_active = False

    # get the value of the item "active"
    # returns: value of item "active"
    def __get_active(self):
        # noinspection PyCallingNonCallable
        return self.__item_active()

    # remove timer on item "active"
    def __remove_active_trigger(self):
        # noinspection PyCallingNonCallable
        self.__item_active.timer(0, self.__item_active())

    # return time when timer on item "active" will be called. None if no timer is set
    # returns: time that has been set for the timer on item "active"
    def __get_active_timer_time(self):
        # check if we can find a Timer-Entry for this item inside the scheduler-configuration
        timer_key = self.__item_active.id() + "-Timer"
        scheduler_next = self.sh.scheduler.return_next(timer_key)
        if not isinstance(scheduler_next, datetime.datetime):
            return None
        if scheduler_next <= datetime.datetime.now(scheduler_next.tzinfo):
            return None

        return scheduler_next

    # indicates if a timer on item "active" is active
    # returns: True = a timer is active, False = no timer is active
    def __get_active_timer_active(self):
        return self.__get_active_timer_time() is not None

    # check if item is active and update laststate_name if not
    # set_name_if_active: True = Update laststate_name if active, too, False = Leave laststate_name unchanged if active
    def __check_active(self, set_name_if_active=False):
        # item is active
        if self.__get_active():
            if set_name_if_active:
                # noinspection PyCallingNonCallable
                self.__item_laststate_name("Wird beim nächsten Durchgang aktualisiert")
            return True

        # check if we can find a Timer-Entry for this item inside the scheduler-configuration
        active_timer_time = self.__get_active_timer_time()
        if active_timer_time is not None:
            self.__myLogger.info(
                "AutoBlind has been deactivated automatically after manual changes. Reactivating at {0}",
                active_timer_time)
            # noinspection PyCallingNonCallable
            self.__item_laststate_name(active_timer_time.strftime("Automatisch deaktviert bis %X"))
            return False

        # must have been manually deactivated
        self.__myLogger.info("AutoBlind is inactive")
        # noinspection PyCallingNonCallable
        self.__item_laststate_name("Manuell deaktiviert")
        return False

    # initialize configuration
    def __init_config(self):
        self.__name = str(self.__item)
        self.__cycle = AutoBlindTools.get_num_attribute(self.__item, "cycle", AutoBlindDefaults.cycle)
        if self.__cycle == 0:
            self.__cycle = None
        self.__startup_delay = AutoBlindTools.get_num_attribute(self.__item, "startup_delay",
                                                                AutoBlindDefaults.startup_delay)
        self.__manual_break = AutoBlindTools.get_num_attribute(self.__item, "manual_break",
                                                               AutoBlindDefaults.manual_break)

        self.__item_active = AutoBlindTools.get_item_attribute(self.__item, "item_active", self.sh)
        self.__item_laststate_id = AutoBlindTools.get_item_attribute(self.__item, "item_state_id", self.sh)
        self.__item_laststate_name = AutoBlindTools.get_item_attribute(self.__item, "item_state_name", self.sh)

    # find states and init them
    def __init_states(self):
        items_states = self.__item.return_children()
        non_state_item_ids = []
        if self.__item_active is not None:
            non_state_item_ids.append(self.__item_active.id())
        if self.__item_laststate_id is not None:
            non_state_item_ids.append(self.__item_laststate_id.id())
        if self.__item_laststate_name is not None:
            non_state_item_ids.append(self.__item_laststate_name.id())
        for item_state in items_states:
            if item_state.id() in non_state_item_ids:
                continue

            state = AutoBlindState.AbState(self.sh, item_state, self.__item, self, self.__myLogger)
            if state.validate():
                self.__states.append(state)

    # initialize "watch_manual" if configured
    def __init_watch_manual(self):
        if "watch_manual" not in self.__item.conf:
            return

        self.__myLogger.info("watch_manual items:")
        self.__myLogger.increase_indent()
        if isinstance(self.__item.conf["watch_manual"], str):
            self.__item.conf["watch_manual"] = [self.__item.conf["watch_manual"]]
        for entry in self.__item.conf["watch_manual"]:
            for item in self.sh.match_items(entry):
                item.add_method_trigger(self.__watch_manual_callback)
                self.__myLogger.info(item.id())
        if self.__item_active is not None:
            self.__item_active.add_method_trigger(self.__reset_active_callback)
        self.__myLogger.decrease_indent()

    # initialize "watch_trigger" if configured
    def __init_watch_trigger(self):
        if 'watch_trigger' not in self.__item.conf:
            return

        self.__myLogger.info("watch_trigger items:")
        self.__myLogger.increase_indent()
        if isinstance(self.__item.conf["watch_trigger"], str):
            self.__item.conf["watch_trigger"] = [self.__item.conf["watch_trigger"]]
        for entry in self.__item.conf["watch_trigger"]:
            for item in self.sh.match_items(entry):
                item.add_method_trigger(self.__watch_trigger_callback)
                self.__myLogger.info(item.id())
        self.__myLogger.decrease_indent()
