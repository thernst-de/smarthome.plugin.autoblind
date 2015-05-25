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
# AutoBlindPosition
#
# Class representing a blind position, consisting of name, conditions
# to be met and configured position of blind
#########################################################################
import logging
from . import AutoBlindTools
from . import AutoBlindConditionChecker
from .AutoBlindLogger import AbLogger

logger = logging.getLogger('')


# Create abPosition-Instance
def create(smarthome, item, item_autoblind):
    return AbPosition(smarthome, item, item_autoblind)


class AbPosition:
    # Name of position
    __name = ''

    # Item defining the position
    __item = None

    # Dictionary containing all conditions for entering this position
    # (class abConditionChecker ensures all relevant conditions are included)
    __enterConditionSets = {}

    # Dictionary containing all conditions for leaving this position
    # (class abConditionChecker ensures all relevant conditions are included)
    __leaveConditionSets = {}

    # Position (list [height, lamella] or "auto" for lamella following the sun)
    __position = [None, None]

    # Return id of position (= id of defining item)
    def id(self):
        return self.__item.id()

    # Return name of position ( = name of defining item)
    @property
    def name(self):
        return self.__name

    # Return conditions to enter this position
    def get_enter_conditionsets(self):
        return self.__enterConditionSets

    # Return conditions to leave this position
    def get_leave_conditionsetss(self):
        return self.__leaveConditionSets

    # Constructor
    # @param smarthome: instance of smarthome
    # @param item: item containing configuration of AutoBlind position
    def __init__(self, smarthome, item, item_autoblind):
        logger.info("Init AutoBlindPosition {}".format(item.id()))
        self.sh = smarthome
        self.__item = item
        self.__enterConditionSets = {}
        self.__leaveConditionSets = {}
        self.__fill(self.__item, 0, item_autoblind)

    # Read configuration from item and populate data in class
    # @param item: item to read from
    # @param recursion_depth: current recursion_depth (recursion is canceled after five levels)
    def __fill(self, item, recursion_depth, item_autoblind):
        if recursion_depth > 5:
            logger.error("{0}/{1}: to many levels of 'use'".format(self.__item.id(), item.id()))
            return

        # Import data from other item if attribute "use" is found
        if 'use' in item.conf:
            use_item = self.sh.return_item(item.conf['use'])
            if use_item is not None:
                self.__fill(use_item, recursion_depth + 1, item_autoblind)
            else:
                logger.error("{0}: Referenced item '{1}' not found!".format(item.id(), item.conf['use']))

        # Get condition sets
        parent_item = item.return_parent()
        items_conditionsets = item.return_children()
        for item_conditionset in items_conditionsets:
            condition_name = AutoBlindTools.get_last_part_of_item_id(item_conditionset)
            if condition_name == "enter" or condition_name.startswith("enter_"):
                AutoBlindConditionChecker.fill_conditionset(self.__enterConditionSets, condition_name,
                                                            item_conditionset, parent_item, self.sh)
            elif condition_name == "leave" or condition_name.startswith("leave_"):
                AutoBlindConditionChecker.fill_conditionset(self.__leaveConditionSets, condition_name,
                                                            item_conditionset, parent_item, self.sh)

        # This is the blind position for this item
        if "position" in item.conf:
            self.__position = AutoBlindTools.get_position_attribute(item, "position")

        # if an item name is given, or if we do not have a name after returning from all recursions,
        # use item name as position name
        if str(item) != item.id() or (self.__name == '' and recursion_depth == 0):
            self.__name = str(item)

    # validate position data
    # @return TRUE: data ok, FALSE: data not ok
    def validate(self):
        if self.__position is None:
            return False

        return True

    # log position data
    def log(self):
        AbLogger.info("Position {0}:".format(self.id()))
        AbLogger.info("\tName: {0}".format(self.__name))
        AbLogger.info("\tCondition sets to enter position:")
        AutoBlindConditionChecker.log_conditionsets(self.__enterConditionSets)
        AbLogger.info("\tCondition sets to leace position:")
        AutoBlindConditionChecker.log_conditionsets(self.__leaveConditionSets)

    # return position data for position
    # @param sun_azimut: current azimut of sun
    # @param sun_altitude: current altitude of sun
    # @return list [%-heigth,%-lamella]: blind position
    def get_position(self, sun_altitude):
        if self.__position != 'auto':
            return self.__position

        logger.debug("Calculating blind position based on sun position (altitude {0}°)".format(sun_altitude))

        # Blinds at right angle to sun
        angel = 90 - sun_altitude
        logger.debug("Lamella angle to {0}°".format(angel))

        return [100, angel]
