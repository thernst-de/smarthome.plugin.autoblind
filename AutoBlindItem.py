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
# AutoBlindItem
#
# Class representing a blind item
#########################################################################
import time
from . import AutoBlindTools
from .AutoBlindLogger import AbLogger
from . import AutoBlindPosition
from . import AutoBlindConditionChecker


def create(smarthome, item, item_id_height="hoehe", item_id_lamella="lamelle", manual_break_default=3600):
    return AbItem(smarthome, item, item_id_height, item_id_lamella, manual_break_default)


# Class representing a blind item
class AbItem:
    __item = None
    __item_item_autoblind = None
    __item_active = None
    __item_lastpos_id = None
    __item_lastpos_name = None
    __item_height = None
    __item_lamella = None
    __positions = []
    __manual_break = 0
    __can_not_leave_current_pos_since = 0

    # Constructor
    # @param smarthome: instance of smarthome.py
    # @param item: item to use
    # @param item_id_height: name of item to controll the blind's height below the main item of the blind
    # @param item_id_lamella: name of item to controll the blind's lamella below the main item of the blind
    # @param manual_break_default: default value for "manual_break" if no value is set for specific item
    def __init__(self, smarthome, item, item_id_height="hoehe", item_id_lamella="lamelle", manual_break_default=3600):
        AbLogger.info("Init AutoBlindItem {}".format(item.id()))
        self.sh = smarthome
        self.__item_id_height = item_id_height
        self.__item_id_lamella = item_id_lamella
        self.__positions = []

        # get required items for this AutoBlindItem
        self.__item = item
        self.__item_height = AutoBlindTools.get_child_item(self.__item, self.__item_id_height)
        self.__item_lamella = AutoBlindTools.get_child_item(self.__item, self.__item_id_lamella)
        self.__item_autoblind = AutoBlindTools.get_child_item(self.__item, "AutoBlind")
        if self.__item_autoblind is not None:
            # get items
            self.__item_active = AutoBlindTools.get_child_item(self.__item_autoblind, "active")
            self.__item_lastpos_id = AutoBlindTools.get_child_item(self.__item_autoblind, "lastpos_id")
            self.__item_lastpos_name = AutoBlindTools.get_child_item(self.__item_autoblind, "lastpos_name")

            # get positions
            items_position = self.__item_autoblind.return_children()
            for item_position in items_position:
                if "position" not in item_position.conf and "use" not in item_position.conf:
                    continue
                position = AutoBlindPosition.create(self.sh, item_position, self.__item_autoblind)
                if position.validate():
                    self.__positions.append(position)

            # set triggers for watch_manual
            if "watch_manual" in self.__item_autoblind.conf:
                if isinstance(self.__item_autoblind.conf["watch_manual"], str):
                    self.__item_autoblind.conf["watch_manual"] = [self.__item_autoblind.conf["watch_manual"]]
                for entry in self.__item_autoblind.conf["watch_manual"]:
                    for item in self.sh.match_items(entry):
                        item.add_method_trigger(self.__watch_manual_callback)
                self.__item_active.add_method_trigger(self.__reset_active_callback)

            if 'watch_trigger' in self.__item_autoblind.conf:
                if isinstance(self.__item_autoblind.conf["watch_trigger"], str):
                    self.__item_autoblind.conf["watch_trigger"] = [self.__item_autoblind.conf["watch_trigger"]]
                for entry in self.__item_autoblind.conf["watch_trigger"]:
                    for item in self.sh.match_items(entry):
                        item.add_method_trigger(self.__watch_trigger_callback)

            # get manual_break time
            if "manual_break" in self.__item_autoblind.conf:
                self.__manual_break = int(self.__item_autoblind.conf["manual_break"])
            else:
                self.__manual_break = manual_break_default

    # Validate data in instance
    # @return: TRUE: Everything ok, FALSE: Errors occured
    def validate(self):
        if self.__item is None:
            AbLogger.error("No item configured!")
            return False

        item_id = self.__item.id()

        if self.__item_autoblind is None:
            AbLogger.error("{0}: Item '{1}' does not have a sub-item 'AutoBlind'!".format(item_id, item_id))
            return False

        autoblind_id = self.__item_autoblind.id()

        if self.__item_active is None:
            AbLogger.error("{0}: Item '{1}' does not have a sub-item 'active'!".format(item_id, autoblind_id))
            return False

        if self.__item_lastpos_id is None:
            AbLogger.error("{0}: Item '{1}' does not have a sub-item 'lastpos_id'!".format(item_id, autoblind_id))
            return False

        if self.__item_lastpos_name is None:
            AbLogger.error("{0}: Item '{1}' does not have a sub-item 'lastpos_name'!".format(item_id, autoblind_id))
            return False

        if self.__item_height is None:
            AbLogger.error(
                "{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id, item_id, self.__item_id_height))
            return False

        if self.__item_lamella is None:
            AbLogger.error(
                "{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id, item_id, self.__item_id_lamella))
            return False

        if len(self.__positions) == 0:
            AbLogger.error("{0}: No positions defined!".format(item_id, item_id, self.__item_id_lamella))
            return False

        return True

    # log item data
    def log(self):
        AbLogger.set_section(self.id())
        AbLogger.info(
            "AutoBlind Configuration =================================================================================")
        AbLogger.info("Item 'Height': {0}".format(self.__item_height.id()))
        AbLogger.info("Item 'Lamella': {0}".format(self.__item_lamella.id()))
        AbLogger.info("Item 'Active': {0}".format(self.__item_active.id()))
        AbLogger.info("Item 'LastPos Id': {0}".format(self.__item_lastpos_id.id()))
        AbLogger.info("Item 'LastPos Name': {0}".format(self.__item_lastpos_name.id()))
        for position in self.__positions:
            position.log()
        AbLogger.clear_section()

    # return item id
    def id(self):
        return self.__item.id()

    # Find the position, matching the current conditions and move the blinds to this position
    def update_position(self, condition_checker):
        AbLogger.info(
            "Update Position =========================================================================================")

        # Check if this AutoBlindItem is active. Leave if not
        if self.__item_active() != 1:
            AbLogger.info("AutoBlind is inactive")
            self.__item_lastpos_name("(inactive)")
            return

        # update item dependent conditions
        condition_checker.set_current_age(self.__item_lastpos_id.age())
        if self.__can_not_leave_current_pos_since == 0:
            condition_checker.set_current_delay(0)
        else:
            condition_checker.set_current_delay(time.time() - self.__can_not_leave_current_pos_since)

        # get last position
        last_pos_id = self.__item_lastpos_id()
        last_pos_name = self.__item_lastpos_name()
        AbLogger.info("Last position: {0} ('{1}')".format(last_pos_id, last_pos_name))

        # check if current position can be left
        can_leave_position = True
        new_position = None
        for position in self.__positions:
            if position.id() == last_pos_id:
                if not condition_checker.can_leave(position):
                    AbLogger.info("Can not leave current position.")
                    can_leave_position = False
                    new_position = position
                    if self.__can_not_leave_current_pos_since == 0:
                        self.__can_not_leave_current_pos_since = time.time()
                break

        if can_leave_position:
            # find new position
            for position in self.__positions:
                if condition_checker.can_enter(position):
                    new_position = position
                    self.__can_not_leave_current_pos_since = 0
                    break

            # no new position -> leave
            if new_position is None:
                AbLogger.info("No matching position found.")
                return
        else:
            # if current position can not be left, check if enter conditions are still valid.
            # If yes, update "can_not_leave_current_pos_since"
            if condition_checker.can_enter(new_position):
                self.__can_not_leave_current_pos_since = 0

        # get data for new position
        new_pos_id = new_position.id()
        if new_pos_id == last_pos_id:
            # New position is last position
            AbLogger.info("Position unchanged")
        else:
            # New position is different from last position
            AbLogger.info("New position: {0} ('{1}')".format(new_pos_id, new_position.name))
            self.__item_lastpos_id(new_pos_id)
            self.__item_lastpos_name(new_position.name)

        # move blinds to this position
        target_position = new_position.get_position(condition_checker.get_sun_altitude())

        # Change height only if we change for at least 10%
        height_delta = self.__item_height() - target_position[0]
        if abs(height_delta) >= 10:
            self.__item_height(target_position[0])

        # Change lamella only if we change for at least 5%
        lamella_delta = self.__item_lamella() - target_position[1]
        if abs(lamella_delta) >= 5:
            self.__item_lamella(target_position[1])

    # called when one of the items given at "watch_manual" is being changed
    # noinspection PyUnusedLocal
    def __watch_manual_callback(self, item, caller=None, source=None, dest=None):
        if caller != "plugin" and caller != "Timer":
            AbLogger.set_section(self.__item.id())
            AbLogger.info("Handling manual operation after change if item '{0}'".format(item.id()))
            AbLogger.increase_indent()
            # deactivate "active"
            if self.__item_active() == 0:
                AbLogger.debug("Automatic mode already inactive")
                AbLogger.clear_section()
                return

            AbLogger.debug("Deactivated automatic mode for {0} seconds.".format(self.__manual_break))
            self.__item_active(0)

            # schedule reactivation of "active"
            self.__item_active.timer(self.__manual_break, 1)
            AbLogger.clear_section()

    # called when the item "active" is being changed
    # noinspection PyUnusedLocal
    def __reset_active_callback(self, item, caller=None, source=None, dest=None):
        # reset timer for reactivation of "active"
        AbLogger.set_section(self.__item.id())
        AbLogger.info("Reactivate automatic mode.")
        self.__item_active.timer(0, self.__item_active())
        AbLogger.clear_section()

    # called when item triggering an update is being changed
    # noinspection PyUnusedLocal
    def __watch_trigger_callback(self, item, caller=None, source=None, dest=None):
        AbLogger.set_section(self.__item.id())
        AbLogger.info('Updating {0} triggered by item {1}'.format(str(self.__item), item.id()))

        condition_checker = AutoBlindConditionChecker.create(self.sh)

        # call position update for this AutoBlindItem
        self.update_position(condition_checker)
        AbLogger.clear_section()
