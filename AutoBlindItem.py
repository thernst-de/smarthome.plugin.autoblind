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
from . import AutoBlindPosition
from . import AutoBlindDefaults


# Class representing a blind item
class AbItem:
    # return item id
    def id(self):
        return self.__item.id()

    # Constructor
    # smarthome: instance of smarthome.py
    # item: item to use
    # item_id_height: name of item to controll the blind's height below the main item of the blind
    # item_id_lamella: name of item to controll the blind's lamella below the main item of the blind
    # manual_break_default: default value for "manual_break" if no value is set for specific item
    def __init__(self, smarthome, item):
        self.sh = smarthome
        self.__positions = []

        self.__cycle = None
        self.__startup_delay = None
        self.__name = None
        self.__item_active = None
        self.__item_lastpos_id = None
        self.__item_lastpos_name = None
        self.__positions = []
        self.__manual_break = 0
        self.__delay = 0
        self.__actions = {}
        self.__can_not_leave_current_pos_since = 0
        self.__just_changing_active = False

        # get required items for this AutoBlindItem
        self.__item = item
        self.__myLogger = AbLogger.create(item)

        self.__myLogger.header("Initialize Item {0}".format(self.__name))
        self.__item_height = AutoBlindTools.get_child_item(self.__item, AutoBlindDefaults.item_id_height)
        self.__item_lamella = AutoBlindTools.get_child_item(self.__item, AutoBlindDefaults.item_id_lamella)
        self.__item_autoblind = AutoBlindTools.get_child_item(self.__item, "AutoBlind")
        if self.__item_autoblind is None:
            return

        # initialize everything else
        self.__init_config()
        self.__init_positions()
        self.__init_watch_manual()
        self.__init_watch_trigger()

    # Validate data in instance
    # A ValueError is being thown in case of errors
    def validate(self):
        if self.__item is None:
            raise ValueError("No item configured!")

        item_id = self.__item.id()

        if self.__item_autoblind is None:
            raise ValueError("{0}: Item '{1}' does not have a sub-item 'AutoBlind'!".format(item_id, item_id))

        autoblind_id = self.__item_autoblind.id()

        if self.__item_active is None:
            raise ValueError("{0}: Item '{1}' does not have a sub-item 'active'!".format(item_id, autoblind_id))

        if self.__item_lastpos_id is None:
            raise ValueError("{0}: Item '{1}' does not have a sub-item 'lastpos_id'!".format(item_id, autoblind_id))

        if self.__item_lastpos_name is None:
            raise ValueError(
                "{0}: Item '{1}' does not have a sub-item 'lastpos_name'!".format(item_id, autoblind_id))

        if self.__item_height is None:
            raise ValueError(
                "{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id, item_id,
                                                                         AutoBlindDefaults.item_id_height))

        if self.__item_lamella is None:
            raise ValueError(
                "{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id, item_id,
                                                                         AutoBlindDefaults.item_id_lamella))

        if len(self.__positions) == 0:
            raise ValueError("{0}: No positions defined!".format(item_id))

    # log item data
    def write_to_log(self):
        self.__myLogger.header("Configuration of item {0}".format(self.__name))
        self.__myLogger.info("startup_delay: {0} seconds", self.__startup_delay)
        self.__myLogger.info("cycle: {0} seconds", self.__cycle)
        self.__myLogger.info("Item 'Height': {0}", self.__item_height.id())
        self.__myLogger.info("Item 'Lamella': {0}", self.__item_lamella.id())
        self.__myLogger.info("Item 'Active': {0}", self.__item_active.id())
        self.__myLogger.info("Item 'LastPos Id': {0}", self.__item_lastpos_id.id())
        self.__myLogger.info("Item 'LastPos Name': {0}", self.__item_lastpos_name.id())
        for position in self.__positions:
            position.write_to_log(self.__myLogger)

    # return age of item
    def get_age(self):
        return self.__item_lastpos_id.age()

    # return delay of item
    def get_delay(self):
        return self.__delay

    # Find the position, matching the current conditions and move the blinds to this position
    # caller: Caller that triggered the update
    # noinspection PyCallingNonCallable
    def update_position(self, caller=None):
        self.__myLogger.update_logfile()
        self.__myLogger.header("Update Position of item {0}".format(self.__name))
        if caller:
            self.__myLogger.debug("Update triggered by {0}", caller)

        # Check if this AutoBlindItem is active. Leave if not
        if not self.__check_active():
            return

        # get last position
        last_position = self.__get_last_position()
        if last_position is not None:
            self.__myLogger.info("Last position: {0} ('{1}')", last_position.id(), last_position.name)
        if self.__can_not_leave_current_pos_since == 0:
            self.__delay = 0
        else:
            self.__delay = time.time() - self.__can_not_leave_current_pos_since

        # check if current position can be left
        if last_position is not None and not last_position.can_leave(self.__myLogger):
            self.__myLogger.info("Can not leave current position, staying at {0} ('{1}')", last_position.id(),
                                 last_position.name)
            can_leave_position = False
            new_position = last_position
            if self.__can_not_leave_current_pos_since == 0:
                self.__can_not_leave_current_pos_since = time.time()
        else:
            can_leave_position = True
            new_position = None

        if can_leave_position:
            # find new position
            for position in self.__positions:
                if position.can_enter(self.__myLogger):
                    new_position = position
                    self.__can_not_leave_current_pos_since = 0
                    break

            # no new position -> leave
            if new_position is None:
                self.__myLogger.info("No matching position found, staying at {0} ('{1}')", last_position.id(),
                                     last_position.name)
                return
        else:
            # if current position can not be left, check if enter conditions are still valid.
            # If yes, set "can_not_leave_current_pos_since" to 0
            if new_position.can_enter(self.__myLogger):
                self.__can_not_leave_current_pos_since = 0

        # get data for new position
        if new_position.id() == last_position.id():
            # New position is last position
            if self.__item_lastpos_name() != new_position.name:
                self.__item_lastpos_name(new_position.name)
            self.__myLogger.info("Staying at {0} ('{1}')", new_position.id(), new_position.name)
        else:
            # New position is different from last position
            self.__myLogger.info("Changing to {0} ('{1}')", new_position.id(), new_position.name)
            self.__item_lastpos_id(new_position.id())
            self.__item_lastpos_name(new_position.name)

        self.move_to(new_position)

    # Move to given position
    # position: Position to move to
    def move_to(self, position: AutoBlindPosition.AbPosition):
        # move blinds to this position
        target_position = position.get_position(self.__myLogger)

        # Change height only if we change for at least 10%
        height_delta = self.__item_height() - target_position[0]
        if abs(height_delta) >= 10:
            self.__item_height(target_position[0])

        # Change lamella only if we change for at least 5%
        lamella_delta = self.__item_lamella() - target_position[1]
        if abs(lamella_delta) >= 5:
            self.__item_lamella(target_position[1])

    # startup scheduler after startup_delay
    def startup(self):
        name = "autoblind-" + self.id()
        self.sh.scheduler.add(name, self.update_position, cycle=self.__cycle, offset=self.__startup_delay)

    # get last position based on lastpos_id item
    # returns: AbPosition instance of last position or "None" if no last position could be found
    def __get_last_position(self):
        # noinspection PyCallingNonCallable
        last_pos_id = self.__item_lastpos_id()
        for position in self.__positions:
            if position.id() == last_pos_id:
                return position
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
        self.update_position("item '{0}' changed by '{1}".format(item.id(), caller))

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

    # check if item is active and update lastpos_name if not
    # set_name_if_active: True = Update lastpos_name if active, too, False = Leave lastpos_name unchanged if active
    def __check_active(self, set_name_if_active=False):
        # item is active
        if self.__get_active():
            if set_name_if_active:
                # noinspection PyCallingNonCallable
                self.__item_lastpos_name("Wird beim nächsten Durchgang aktualisiert")
            return True

        # check if we can find a Timer-Entry for this item inside the scheduler-configuration
        active_timer_time = self.__get_active_timer_time()
        if active_timer_time is not None:
            self.__myLogger.info(
                "AutoBlind has been deactivated automatically after manual changes. Reactivating at {0}",
                active_timer_time)
            # noinspection PyCallingNonCallable
            self.__item_lastpos_name(active_timer_time.strftime("Automatisch deakviert bis %X"))
            return False

        # must have been manually deactivated
        self.__myLogger.info("AutoBlind is inactive")
        # noinspection PyCallingNonCallable
        self.__item_lastpos_name("Manuell deaktiviert")
        return False

    # initialize configuration
    def __init_config(self):
        self.__name = str(self.__item_autoblind)
        self.__cycle = AutoBlindTools.get_num_attribute(self.__item_autoblind, "cycle", AutoBlindDefaults.cycle)
        if self.__cycle == 0:
            self.__cycle = None
        self.__startup_delay = AutoBlindTools.get_num_attribute(self.__item_autoblind, "startup_delay",
                                                                AutoBlindDefaults.startup_delay)
        self.__manual_break = AutoBlindTools.get_num_attribute(self.__item_autoblind, "manual_break",
                                                               AutoBlindDefaults.manual_break)

        self.__item_active = AutoBlindTools.get_child_item(self.__item_autoblind, "active")
        self.__item_lastpos_id = AutoBlindTools.get_child_item(self.__item_autoblind, "lastpos_id")
        self.__item_lastpos_name = AutoBlindTools.get_child_item(self.__item_autoblind, "lastpos_name")

    # find positions and init them
    def __init_positions(self):
        items_position = self.__item_autoblind.return_children()
        for item_position in items_position:
            if "position" not in item_position.conf and "use" not in item_position.conf:
                continue
            position = AutoBlindPosition.AbPosition(self.sh, item_position, self.__item_autoblind, self,
                                                    self.__myLogger)
            if position.validate():
                self.__positions.append(position)

    # initialize "watch_manual" if configured
    def __init_watch_manual(self):
        if "watch_manual" not in self.__item_autoblind.conf:
            return

        self.__myLogger.info("watch_manual items:")
        self.__myLogger.increase_indent()
        if isinstance(self.__item_autoblind.conf["watch_manual"], str):
            self.__item_autoblind.conf["watch_manual"] = [self.__item_autoblind.conf["watch_manual"]]
        for entry in self.__item_autoblind.conf["watch_manual"]:
            for item in self.sh.match_items(entry):
                item.add_method_trigger(self.__watch_manual_callback)
                self.__myLogger.info(item.id())
        self.__item_active.add_method_trigger(self.__reset_active_callback)
        self.__myLogger.decrease_indent()

    # initialize "watch_trigger" if configured
    def __init_watch_trigger(self):
        if 'watch_trigger' not in self.__item_autoblind.conf:
            return

        self.__myLogger.info("watch_trigger items:")
        self.__myLogger.increase_indent()
        if isinstance(self.__item_autoblind.conf["watch_trigger"], str):
            self.__item_autoblind.conf["watch_trigger"] = [self.__item_autoblind.conf["watch_trigger"]]
        for entry in self.__item_autoblind.conf["watch_trigger"]:
            for item in self.sh.match_items(entry):
                item.add_method_trigger(self.__watch_trigger_callback)
                self.__myLogger.info(item.id())
        self.__myLogger.decrease_indent()
