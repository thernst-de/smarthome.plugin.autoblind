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
import logging

logger = logging.getLogger()


class AbFunctions:
    def __init__(self, smarthome):
        self.__sh = smarthome

    def manual_item_update_eval(self, item_id, caller=None, source=None):
        item = self.__sh.return_item(item_id)
        original_caller, original_source = AutoBlindTools.get_original_caller(self.__sh, caller, source)

        retval_NoTrigger = item()
        retval_Trigger = not item()

        if "as_manual_exclude" in item.conf:
            # get list of exclude entries
            exclude = item.conf["as_manual_exclude"]
            if isinstance(exclude, str):
                exclude = [exclude, ]
            elif not isinstance(exclude, list):
                logger.error("Item '{0}', Attribute 'as_manual_exclude': Value must be a string or a list!")
                return retval_NoTrigger

            # If current value is in list -> Return "NoTrigger"
            for entry in exclude:
                entry_caller, __, entry_source = entry.partition(":")
                if (entry_caller == original_caller or entry_caller == "*") and (
                        entry_source == original_source or entry_source == "*"):
                    return retval_NoTrigger

        if "as_manual_include" in item.conf:
            # get list of include entries
            include = item.conf["as_manual_include"]
            if isinstance(include, str):
                include = [include, ]
            elif not isinstance(include, list):
                logger.error("Item '{0}', Attribute 'as_manual_include': Value must be a string or a list!")
                return retval_NoTrigger

            # If current value is in list -> Return "Trigger"
            for entry in include:
                entry_caller, __, entry_source = entry.partition(":")
                if (entry_caller == original_caller or entry_caller == "*") and (
                        entry_source == original_source or entry_source == "*"):
                    return retval_Trigger

            # Current value not in list -> Return "No Trigger
            return retval_NoTrigger
        else:
            # No include-entries -> return "Trigger"
            return retval_Trigger
