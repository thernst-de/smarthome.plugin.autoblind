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
# AutoBlindTools
#
# Some general tool functions
#########################################################################


# Find a certain item below a given item.
# @param item: Item to search below
# @param child_id: Id of child item to search (without prefixed id of "item")
# @return child item if found, otherwise None
def get_child_item(item, child_id):
    search_id = item.id() + "." + child_id
    for child in item.return_children():
        if child.id() == search_id:
            return child
    return None


# Returns the last part of the id of an item (everythig behind last .)
# @param item: Item for which the last part of the id should be returned
# @return last part of item id
def get_last_part_of_item_id(item):
    return item.id().rsplit(".", 1)[1]


# Return the value of a given attribute as integer
# @param: item to read the attribute from
# @param: name of attribute to return
# @return: value of attribute as integer or None if value of attribute can not be converted into integer
def get_int_attribute(item, attribute):
    if attribute not in item.conf:
        return None
    value = item.conf[attribute]
    try:
        return int(value)
    except ValueError:
        raise ValueError(
            "Das Konfigurations-Attribut '{0}' im Item '{1}' muss numerisch angegeben werden.".format(attribute,
                                                                                                      item.id()))


# Return the values of a given attribute as array
# @param: item to read the attribute from
# @param: name of attribute to return
# @return: value of attribute as array or None if attribute is missing or empty
def get_array_attribute(item, attribute):
    if attribute not in item.conf:
        return None
    value = item.conf[attribute]
    if value == "":
        return None
    return [v.strip() for v in value.split(",")]


# Return the value of a given attribute as time [hour, minute]
# @param: item to read the attribute from
# @param: name of attribute to return
# @return: value of attribute as time or None if value of attribute can not be converted into time
def get_time_attribute(item, attribute):
    if attribute not in item.conf:
        return None

    value = item.conf[attribute]
    value_parts = value.split(",")
    if len(value_parts) != 2:
        raise ValueError(
            "Das Konfigurations-Attribut '{0}' im Item '{1}' muss im Format '###, ###' angegeben werden.".format(
                attribute, item.id()))
    else:
        try:
            hour = int(value_parts[0])
            minute = int(value_parts[1])
            return [hour, minute]
        except ValueError:
            raise ValueError(
                "Das Konfigurations-Attribut '{0}' im Item '{1}' muss im Format '###, ###' angegeben werden.".format(
                    attribute, item.id()))


# Return the value of a given attribute as position ([height, lamella] or 'auto')
# @param: item to read the attribute from
# @param: name of attribute to return
# @return: value of attribute as position or None if value of attribute can not be converted into position
def get_position_attribute(item, attribute):
    if attribute not in item.conf:
        return None

    value = item.conf[attribute]
    if value == "auto":
        return "auto"
    value_parts = value.split(",")
    if len(value_parts) != 2:
        raise ValueError(
            "Das Konfigurations-Attribut '{0}' im Item '{1}' muss im Format '###, ###' angegeben werden.".format(
                attribute, item.id()))
    else:
        try:
            height = int(value_parts[0])
            lamella = int(value_parts[1])
            return [height, lamella]
        except ValueError:
            raise ValueError(
                "Das Konfigurations-Attribut '{0}' im Item '{1}' muss im Format '###, ###' angegeben werden.".format(
                    attribute, item.id()))


# Compares two times (as List [hour, minute])
# -1: time1 < time2
# 0: time1 = time2
# 1: time1 > time2
def compare_time(time1, time2):
    if time1[0] < time2[0]:
        return -1
    elif time1[0] > time2[0]:
        return 1
    else:
        if time1[1] < time2[1]:
            return -1
        elif time1[1] > time2[1]:
            return 1
        else:
            return 0
