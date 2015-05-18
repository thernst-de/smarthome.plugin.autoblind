#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-2015 Thomas Ernst
#########################################################################
#  This file is part of SmartHome.py.    http://mknx.github.io/smarthome/
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
logger = logging.getLogger('')

class abLogger:
	# Log-Level: (0= off 1=Info, 2 = Debug) 
	__logLevel = 2

	# Target directory for log files
	__logDirectory = "/usr/local/smarthome/var/log/AutoBlind/"

	# Section specific file name
	__fileName = None

	# Set log level
	# @param loglevel loglevel
	@staticmethod
	def setLogLevel(logLevel):
		try:
			abLogger.__logLevel = int(logLevel)
		except ValueError:
			abLogger.__logLevel = 2
			logger.error("Das Log-Level muss numerisch angegeben werden.")
		
	# Set log directory
	# @param logDirectory Target directory for AutoBlind log files
	@staticmethod
	def setLogDirectory(logDirectory):
		abLogger.__logDirectory = logDirectory

	# Set section
	# @param Section Name of section 
	@staticmethod
	def setSection(Section):
		if Section == None:
			abLogger.__fileName = None
		else:			
			abLogger.__fileName = abLogger.__logDirectory + str(datetime.date.today()) +'-' + Section.replace(".","_").replace("/","")  + ".log"				

	# clear section
	@staticmethod
	def clearSection():
		abLogger.setSection(None)	

	# log text something
	# @param level Loglevel
	# @param text  text to log
	@staticmethod
	def log(level, text):
		if abLogger.__fileName == None:
			# No section given, log to normal smarthome.py-log
			# we ignore AutoBlindLogLevel as the logger has its own loglevel check
			if level == 2:
				logger.debug(text);
			else:
				logger.info(text);
			return
		else:
			# Section givn: Check level
			if level <= abLogger.__logLevel:
				# Log to section specific logfile
				logtext = "{0}\t{1}\r\n".format(datetime.datetime.now(),text)
				with open(abLogger.__fileName, mode="a", encoding="utf-8") as f:
					f.write(logtext)

	# log with level=info
	# @param text text to log
	@staticmethod
	def info(text):
		abLogger.log(1,text)

	# log with lebel=debug
	# @param text text to log
	@staticmethod
	def debug(text):
		abLogger.log(2,text)
			
	
