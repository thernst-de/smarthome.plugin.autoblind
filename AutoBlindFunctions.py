#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-2016 Thomas Ernst                       offline@gmx.net
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

    # return new item value for "manual" item
    # item_id: Id of "manual" item
    # caller: Caller that triggered the update
    # source: Source that triggered the update
    # The Method will determine the original caller/source and then check if this original caller/source is not
    # contained in as_manual_exclude list (if given) and is contained in as_manual_include list (if given).
    # If the original caller/source should be consiedered, the method returns the inverted value of the item.
    # Otherwise, the method returns the current value of the item, so that no change will be made
    def manual_item_update_eval(self, item_id, caller=None, source=None):
        text = "running manual_item_update_eval for item '{0}' source '{1}' caller '{2}'"
        logger.debug(text.format(item_id, caller, source))

        item = self.__sh.return_item(item_id)
        # original_caller, original_source = AutoBlindTools.get_original_caller(self.__sh, caller, source)
        original_caller, original_source = self.get_original_caller(self.__sh, caller, source)

        text = "original trigger by caller '{0}' source '{1}'"
        logger.debug(text.format(original_caller, original_source))

        logger.debug("Current value of item {0} is {1}".format(item.id(), item()))

        retval_no_trigger = item()
        retval_trigger = not item()

        if "as_manual_exclude" in item.conf:
            # get list of exclude entries
            exclude = item.conf["as_manual_exclude"]

            if isinstance(exclude, str):
                exclude = [exclude, ]
            elif not isinstance(exclude, list):
                logger.error("Item '{0}', Attribute 'as_manual_exclude': Value must be a string or a list!")
                return retval_no_trigger
            logger.debug("checking exclude values: {0}".format(exclude))

            # If current value is in list -> Return "NoTrigger"
            for entry in exclude:
                entry_caller, __, entry_source = entry.partition(":")
                if (entry_caller == original_caller or entry_caller == "*") and (
                        entry_source == original_source or entry_source == "*"):
                    logger.debug("{0}: matching. Writing value {1}".format(entry, retval_no_trigger))
                    return retval_no_trigger
                logger.debug("{0}: not matching".format(entry))

        if "as_manual_include" in item.conf:
            # get list of include entries
            include = item.conf["as_manual_include"]
            if isinstance(include, str):
                include = [include, ]
            elif not isinstance(include, list):
                logger.error("Item '{0}', Attribute 'as_manual_include': Value must be a string or a list!")
                return retval_no_trigger
            logger.debug("checking include values: {0}".format(include))

            # If current value is in list -> Return "Trigger"
            for entry in include:
                entry_caller, __, entry_source = entry.partition(":")
                if (entry_caller == original_caller or entry_caller == "*") and (
                        entry_source == original_source or entry_source == "*"):
                    logger.debug("{0}: matching. Writing value {1}".format(entry, retval_trigger))
                    return retval_trigger
                logger.debug("{0}: not matching".format(entry))

            # Current value not in list -> Return "No Trigger
            logger.debug("No include values matching. Writing value {0}".format(retval_no_trigger))
            return retval_no_trigger
        else:
            # No include-entries -> return "Trigger"
            logger.debug("No include limitation. Writing value {0}".format(retval_trigger))
            return retval_trigger


    # determine original caller/source
    # smarthome: instance of smarthome.py
    # caller: caller
    # source: source
    def get_original_caller(self, smarthome, caller, source, item=None):
        original_caller = caller
        original_source = source
        original_item = item
        while original_caller == "Eval":
            original_item = smarthome.return_item(original_source)
            if original_item is None:
                text = "get_original_caller({0}, {1}): original item not found"
                logger.debug(text.format(original_caller, original_source))
                break
            original_changed_by = original_item.changed_by()
            if ":" not in original_changed_by:
                text = "get_original_caller({0}, {1}): changed by {2} -> separator missing"
                logger.debug(text.format(original_caller, original_source, original_changed_by))
                break
            oc = original_caller
            os = original_source
            original_caller, __, original_source = original_changed_by.partition(":")
            text = "get_original_caller({0}, {1}): changed by {2}, {3}"
            logger.debug(text.format(oc, os, original_caller, original_source))
        if item is None:
            text = "get_original_caller: returning {0}, {1}"
            logger.debug(text.format(original_caller, original_source))
            return original_caller, original_source
        else:
            return original_caller, original_source, original_item