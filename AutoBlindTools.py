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
import datetime


#
# Some general tool functions
#


# Find a certain item below a given item.
# item: Item to search below
# child_id: Id of child item to search (without prefixed id of "item")
# returns: child item if found, otherwise None
def get_child_item(item, child_id):
    search_id = item.id() + "." + child_id
    for child in item.return_children():
        if child.id() == search_id:
            return child
    return None


# Find and return a certain string attribute of an item
# item: Item to search attribute
# attribute_name: Name of attribute to search and return
# default: Value to return if item does not contain attribute
# returns: Attribute value if found. Otherwise given default value or None of no default value is given
def get_str_attribute(item, attribute_name, default=None):
    if attribute_name in item.conf:
        return cast_str(item.conf[attribute_name])
    else:
        return default


# Find and return a certain item that is named as attribute of another item
# item: Item to search attribute
# attribute_name: Name of attribute to search
# smarthome: Instance of smarthome.py base class
# returns: item which is named in the given attribute of the given item or None if attribute or named item not found
def get_item_attribute(item, attribute_name, smarthome):
    item_name = get_str_attribute(item, attribute_name)
    if item_name is None:
        return None
    return smarthome.return_item(item_name)


# Find and return a certain num attribute of an item
# item: Item to search attribute
# attribute_name: Name of attribute to search and return
# default: Value to return if item does not contain attribute
# returns: Attribute value if found. Otherwise given default value or 0 of no default value is given
def get_num_attribute(item, attribute_name, default=None):
    if attribute_name in item.conf:
        return cast_num(item.conf[attribute_name])
    else:
        return default


# Returns the last part of the id of an item (everythig behind last .)
# item: Item for which the last part of the id should be returned
# returns: last part of item id
def get_last_part_of_item_id(item):
    return item.id().rsplit(".", 1)[1]


# cast a value as numeric. Throws ValueError if cast not possible
# Taken from smarthome.py/lib/item.py
# value: value to cast
# returns: value as num or float
def cast_num(value):
    if isinstance(value, float):
        return value
    try:
        return int(value)
    except:
        pass
    try:
        return float(value)
    except:
        pass
    raise ValueError


# cast a value as boolean. Throws ValueError or TypeError if cast is not possible
# Taken from smarthome.py/lib/item.py
# value: value to cast
# returs: value as boolean
def cast_bool(value):
    if type(value) in [bool, int, float]:
        if value in [False, 0]:
            return False
        elif value in [True, 1]:
            return True
        else:
            raise ValueError
    elif type(value) in [str, str]:
        if value.lower() in ['0', 'false', 'no', 'off']:
            return False
        elif value.lower() in ['1', 'true', 'yes', 'on']:
            return True
        else:
            raise ValueError
    else:
        raise TypeError


# cast a value as string. Throws ValueError if cast is not possible
# Taken from smarthome.py/lib/item.py
# value: value to cast
# returns: value as string
def cast_str(value):
    if isinstance(value, str):
        return value
    else:
        raise ValueError


# cast value as datetime.time. Throws ValueError if cast is not possible
# value: value to cast
# returns: value as datetime.time
def cast_time(value):
    if isinstance(value, datetime.time):
        return value

    orig_value = value
    value = value.replace(",", ":")
    value_parts = value.split(":")
    if len(value_parts) != 2:
        raise ValueError("Can not cast '{0}' to data type 'time' due to incorrect format!".format(orig_value))
    else:
        try:
            hour = int(value_parts[0])
            minute = int(value_parts[1])
        except ValueError:
            raise ValueError("Can not cast '{0}' to data type 'time' due to non-numeric parts!".format(orig_value))
        if hour == 24 and minute == 0:
            return datetime.time(23, 59, 59)
        else:
            return datetime.time(hour, minute)


# find a certain attribute for a generic condition. If an "use"-attribute is found, the "use"-item is searched
# recursively
# smarthome: instance of smarthome.py base class
# base_item: base item to search in
# attribute: name of attribute to find
def find_attribute(smarthome, base_item, attribute):
    # 1: parent of given item could have attribute
    parent_item = base_item.return_parent()
    if parent_item is not None:
        if attribute in parent_item.conf:
            return parent_item.conf[attribute]

    # 2: if item has attribute "use", get the item to use and search this item for required attribute
    if "use" in base_item.conf:
        use_item = smarthome.return_item(base_item.conf["use"])
        result = find_attribute(smarthome, use_item, attribute)
        if result is not None:
            return result

    # 3: nothing found
    return None


# split value at the first occurrence of splitchar
# value: what to split
# splitchar: where to split
# returns: Parts before and after split, whitespaces stripped
def split(value, splitchar):
    parts = value.partition(splitchar)
    return parts[0].strip(), parts[2].strip()