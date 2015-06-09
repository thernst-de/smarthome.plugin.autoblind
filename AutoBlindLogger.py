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
# AutoBlindLogger
#
# Extended logging functionality for debugging AutoBlind plugin
# Enables to log into different files (e.g. depending on item, room or 
# similar)
#
#########################################################################
import logging
import datetime

logger = logging.getLogger("")


class AbLogger:
    # Log-Level: (0= off 1=Info, 2 = Debug)
    __loglevel = 2

    # Target directory for log files
    __logdirectory = "/usr/local/smarthome/var/log/AutoBlind/"

    # Section specific file name
    __filename = None

    # Indentation level
    __indentlevel = 0

    # Set log level
    # @param loglevel loglevel
    @staticmethod
    def set_loglevel(loglevel):
        try:
            AbLogger.__loglevel = int(loglevel)
        except ValueError:
            AbLogger.__loglevel = 2
            logger.error("Das Log-Level muss numerisch angegeben werden.")

    # Set log directory
    # @param logDirectory Target directory for AutoBlind log files
    @staticmethod
    def set_logdirectory(logdirectory):
        AbLogger.__logdirectory = logdirectory

    # Set section
    # @param section Name of section
    @staticmethod
    def set_section(section):
        if section is None:
            AbLogger.__filename = None
        else:
            today = str(datetime.date.today())
            section = section.replace(".", "_").replace("/", "")
            AbLogger.__filename = AbLogger.__logdirectory + today + "-" + section + ".log"
        AbLogger.__indentlevel = 0

    # clear section
    @staticmethod
    def clear_section():
        AbLogger.set_section(None)

    # Increase indentation level
    # @param by number of levels to increase
    @staticmethod
    def increase_indent(by=1):
        AbLogger.__indentlevel += by

    # Decrease indentation level
    # @param by number of levels to decrease
    @staticmethod
    def decrease_indent(by=1):
        if AbLogger.__indentlevel > by:
            AbLogger.__indentlevel -= by
        else:
            AbLogger.__indentlevel = 0

    # log text something
    # @param level Loglevel
    # @param text  text to log
    @staticmethod
    def log(level, text):
        if AbLogger.__filename is None:
            # No section given, log to normal smarthome.py-log
            # we ignore AutoBlindLogLevel as the logger has its own loglevel check
            if level == 2:
                logger.debug(text)
            else:
                logger.info(text)
            return
        else:
            # Section givn: Check level
            if level <= AbLogger.__loglevel:
                # Log to section specific logfile
                filename = str(AbLogger.__filename)
                indent = "\t" * AbLogger.__indentlevel
                logtext = "{0}{1} {2}\r\n".format(datetime.datetime.now(), indent, text)
                with open(filename, mode="a", encoding="utf-8") as f:
                    f.write(logtext)

    # log with level=info
    # @param text text to log
    @staticmethod
    def info(text):
        AbLogger.log(1, text)

    # log with lebel=debug
    # @param text text to log
    @staticmethod
    def debug(text):
        AbLogger.log(2, text)

    # log warning (always to main smarthome.py log)
    # @param text text to log
    @staticmethod
    def warning(text):
        logger.warning(text)

    # log error (always to main smarthome.py log)
    # @param text text to log
    @staticmethod
    def error(text):
        logger.error(text)
