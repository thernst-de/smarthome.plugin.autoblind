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
from . import AutoBlindCurrent
from . import AutoBlindLogger

class AbEval:
    def __init__(self, smarthome, logger: AutoBlindLogger.AbLogger):
        self.__sh = smarthome
        self.__logger = logger

    def SunTracking(self):
        self.__logger.debug("Executing method 'SunTracking'")
        self.__logger.increase_indent()

        altitude = AutoBlindCurrent.values.get_sun_altitude()
        self.__logger.debug("Current sun altitude is {0}°",altitude)

        value = 90 - altitude
        self.__logger.debug("Blinds at right angle to the sun at {0}°", value)

        self.__logger.decrease_indent()
        return value