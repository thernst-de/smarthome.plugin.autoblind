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
import logging

logger = logging.getLogger()

startup_delay = 10

suspend_time = 3600

laststate_name_manually_locked = "Manuell gesperrt"

laststate_name_suspended = "Ausgesetzt bis %X"

plugin_identification = "AutoBlind Plugin"


def write_to_log():
    logger.info("AutoBlind default startup delay = {0}".format(startup_delay))
    logger.info("AutoBlind default suspension time = {0}".format(suspend_time))
