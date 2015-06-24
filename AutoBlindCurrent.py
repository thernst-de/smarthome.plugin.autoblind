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
import math
import datetime
from random import randint

# Static current conditions object
values = None
""":type : AbCurrent"""


# Init current conditions
def init(smarthome):
    global values
    values = AbCurrent(smarthome)


# Update current conditions
def update():
    values.update()


# Class representing the current conditions to check against
class AbCurrent:
    # Initialize
    # smarthome: Instance of smarthome.py-class
    def __init__(self, smarthome):
        self.__sh = smarthome
        self.__weekday = None
        self.__time = None
        self.__sun_azimut = None
        self.__sun_altitude = None
        self.update()

    # Return current weekday
    def get_weekday(self):
        return self.__weekday

    # Return current time
    def get_time(self):
        return self.__time

    # Return current sun_azimut
    def get_sun_azimut(self):
        return self.__sun_azimut

    # Return current sun_altitude
    def get_sun_altitude(self):
        return self.__sun_altitude

    # Return random number between 0 and 100
    def get_random(self):
        return randint(0,100)

    # Update current values
    def update(self):
        now = time.localtime()
        self.__weekday = now.tm_wday
        self.__time = datetime.datetime.time(datetime.datetime.now())
        azimut, altitude = self.__sh.sun.pos()
        self.__sun_azimut = math.degrees(float(azimut))
        self.__sun_altitude = math.degrees(float(altitude))


