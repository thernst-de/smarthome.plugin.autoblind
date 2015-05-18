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
# AutoBlindConditionChecker
#
# Preparation and checking of conditions
# Everything that has to do with conditions is placed in here, so if 
# additional conditions are required it should be sufficient to extend 
# this class
#########################################################################
import logging
import time
import datetime
import math
from . import AutoBlindTools
from .AutoBlindLogger import abLogger

logger = logging.getLogger('')

# Create abConditionChecker-Instance
def create(smarthome):
	return abConditionChecker(smarthome)

# Return an initial conditions dictionary
# @param conditions: dictionary to initialize
def init_conditions(conditions):
	conditions['min_time'] = None
	conditions['max_time'] = None
	conditions['min_sun_azimut'] = None
	conditions['max_sun_azimut'] = None
	conditions['min_sun_altitude'] = None
	conditions['max_sun_altitude'] = None
	conditions['min_age'] = None
	conditions['max_age'] = None	
	conditions['items'] = {}
	
# Update conditions-dictionary based on attributes of an item
# @param conditions: dictionary to update
# @param item: Item from which the attributes are used
# @param grandparent_item: Parent of parent-Item, containing item_* attributes 
# @param smarthome: reference to smarthome-class
def update_conditions(conditions, item, grandparent_item, smarthome):	
	if item != None:
		for attribute in item.conf:						
			# Write known condition attributes from item into conditions-dictionary
			if attribute == "min_sun_azimut" or attribute == "max_sun_azimut" \
			or attribute == "min_sun_altitude" or attribute == "max_sun_altitude" \
			or attribute == "min_age" or attribute == "max_age":
				conditions[attribute] = AutoBlindTools.get_int_attribute(item, attribute)
			elif attribute == "min_time" or attribute == "max_time":
				conditions[attribute] = AutoBlindTools.get_time_attribute(item, attribute)
			elif attribute.startswith("min_"):
				name = attribute.split("_",1)[1]
				if name not in conditions['items']: conditions['items'][name] = {}
				conditions['items'][name]['min'] = float(item.conf[attribute])
			elif attribute.startswith("max_"):
				name = attribute.split("_",1)[1]
				if name not in conditions['items']: conditions['items'][name] = {}
				conditions['items'][name]['max'] = float(item.conf[attribute])
			elif attribute.startswith("value_"):
				name = attribute.split("_",1)[1]
				if name not in conditions['items']: conditions['items'][name] = {}
				conditions['items'][name]['value'] = float(item.conf[attribute])
		
	for attribute in grandparent_item.conf:
		if attribute.startswith("item_"):
			name = attribute.split("_",1)[1]
			value = grandparent_item.conf[attribute]
			item = smarthome.return_item(value)
			if name not in conditions['items']: conditions['items'][name] = {}
			conditions['items'][name]['item'] = item

# Log conditions-dictionary using abLogger-Class
# @param conditions: conditions-dictionary to log
def log_conditions(conditions):
	for key in conditions:
		if key == "items": continue
		abLogger.info("\t\t{0} = {1}".format(key,conditions[key]))	
		
	items = conditions["items"]
	for key in items:
		if items[key] == None:
			abLogger.info("\t\t{0}: ERROR".format(key))
		else:
			abLogger.info("\t\t{0}:".format(key))
			for element in items[key]:
				if element=="item":
					value = items[key][element].id()
				else:
					value = items[key][element]
				abLogger.info("\t\t\t{0} = {1}".format(element,value)	)


class abConditionChecker:
	
	# Current conditions when checking
	__current_age = None
	__current_time = None
	__current_sun_azimut = None
	__current_sun_altitude = None
	
	# Constructor
	def __init__(self,smarthome):
		self.sh = smarthome
		now = time.localtime()        
		self.__current_time = [now.tm_hour,now.tm_min]
		azimut, altitude = self.sh.sun.pos()
		self.__current_sun_azimut = math.degrees(float(azimut))
		self.__current_sun_altitude = math.degrees(float(altitude))
	
	# Update current age for condition checks
	# @param age: current age
	def set_current_age(self, age):
		self.__current_age = age
			
	# check if position matches currrent conditions
	# @param position: position to check
	# @return True: position matches current conditions, False: position does not match current conditions
	def can_enter(self, position):
		abLogger.info("Check Position {0} ('{1}')".format(position.id(),position._name))		
		conditions = position.getEnterConditions()
		
		if not self.__match_items(conditions): return False
		if not self.__match_age(conditions): return False
		if not self.__match_time(conditions): return False
		if not self.__match_sun_azimut(conditions): return False
		if not self.__match_sun_altitude(conditions): return False
		
		
		abLogger.info("Position {0} ('{1}') matching".format(position.id(),position._name))
		return True
		
	# check if position matches currrent conditions
	# @param position: position to check
	# @return True: position matches current conditions, False: position does not match current conditions
	def can_leave(self, position):
		abLogger.info("Check if position {0} ('{1}') can be left".format(position.id(),position._name))
		conditions = position.getLeaveConditions()
		
		if not self.__match_items(conditions): return False
		if not self.__match_age(conditions): return False
		if not self.__match_time(conditions): return False
		if not self.__match_sun_azimut(conditions): return False
		if not self.__match_sun_altitude(conditions): return False
		
		abLogger.info("Position {0} ('{1}') can be left".format(position.id(),position._name))
		return True
			

			
	# Check if given age matches age conditions
	# @param: conditions: conditions to check
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched
	def __match_age(self, conditions):
		min_age = conditions['min_age'] if 'min_age' in conditions else None
		max_age = conditions['max_age'] if 'max_age' in conditions else None
		
		abLogger.debug("condition 'age': min={0} max={1} current={2}".format(min_age, max_age, self.__current_age))
		
		if min_age == None and max_age == None:
			abLogger.debug(" -> check age: no limit given")
			return True
		
		if min_age != None and self.__current_age < min_age:
			abLogger.debug(" -> check age: to young")
			return False
		if max_age != None and self.__current_age > max_age:
			abLogger.debug(" -> check age: to old")
			return False
		abLogger.debug(" -> check age: OK")
		return True
		

	# Check if given item conditions match conditions of position
	# @param: conditions: conditions to check
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched	
	def __match_items(self, conditions):
		for name in conditions['items']:
			if not self.__match_item(name, conditions['items'][name]): return False
		return True
		
	# Check if single item condition matches condition of position
	# @param: name: name of element
	# @param: element: condition-information (item, min, max, value)
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched	
	def __match_item(self,name, element):
		current = element['item']()
					
		if 'value' in element:
			abLogger.debug("condition '{0}': value={1} current={2}".format(name, element['value'], current))
			return current == element['value']		
		else:		
			min = element['min'] if 'min' in element else None;
			max = element['max'] if 'max' in element else None;
			abLogger.debug("condition '{0}': min={1} max={2} current={3}".format(name, min, max, current))
			if min == None and max == None:
				abLogger.debug(" -> check {0}: no limit given".format(name))
				return True
			
			if min != None and current < min:
				abLogger.debug(" -> check {0}: to low".format(name))
				return False
			if max != None and current > max:
				abLogger.debug(" -> check {0}: to high".format(name))
				return False
			abLogger.debug(" -> check {0}: OK".format(name))
			return True
		
	# Check if given time matches time conditions of position
	# @param: conditions: conditions to check
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched
	def __match_time(self, conditions):
		min_time = conditions['min_time'] if 'min_time' in conditions else None;
		max_time = conditions['max_time'] if 'max_time' in conditions else None;
		
		abLogger.debug("condition 'time': min={0} max={1} current={2}".format(min_time, max_time, self.__current_time))
		
		if min_time == None and max_time == None:
			abLogger.debug(" -> check time: no limit given")
			return True
			
		min_time = [0,0] if min_time == None else min_time;
		max_time = [24,0] if max_time == None else max_time;
		
		if AutoBlindTools.compare_time(min_time, max_time) != 1:
			# min </= max: Normaler Vergleich
			if AutoBlindTools.compare_time(self.__current_time, min_time) == -1 or AutoBlindTools.compare_time(self.__current_time, max_time) == 1:
				abLogger.debug(" -> check time: not in range (min <= max)")
				return False
		else:
			# min > max: Invertieren
			if AutoBlindTools.compare_time(self.__current_time, min_time) == -1 and AutoBlindTools.compare_time(self.__current_time, max_time) == 1:
				abLogger.debug(" -> check time: not in range (min > max)")
				return False
		abLogger.debug(" -> check time: OK")
		return True
		
	# Check if given sun azimut matches sun azimut conditions of position
	# @param: conditions: conditions to check
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched
	def __match_sun_azimut(self, conditions):
		min_sun_azimut = conditions['min_sun_azimut'] if 'min_sun_azimut' in conditions else None;
		max_sun_azimut = conditions['max_sun_azimut'] if 'max_sun_azimut' in conditions else None;
		
		abLogger.debug("condition 'sun_azimut': min={0} max={1} current={2}".format(min_sun_azimut, max_sun_azimut, self.__current_sun_azimut))
		
		if min_sun_azimut == None and max_sun_azimut == None:
			abLogger.debug(" -> check sun azimut: no limit given")
			return True
			
		min_azimut = 0 if min_sun_azimut == None else min_sun_azimut
		max_azimut = 360 if max_sun_azimut == None else max_sun_azimut
				
		if min_azimut <= max_azimut:
			if self.__current_sun_azimut < min_azimut or self.__current_sun_azimut > max_azimut:
				abLogger.debug(" -> check sun azimut: out of range (min <= max)")
				return False	
		else:
			if self.__current_sun_azimut > min_azimut and self.__current_sun_azimut < max_azimut:
				abLogger.debug(" -> check sun azimut: out of range (min > max)")
				return False				
		abLogger.debug(" -> check sun azimut: OK")
		return True
		
	# Check if given sun altitude matches sun altitude conditions of position
	# @param: conditions: conditions to check
	# @return: True= No Conditions or Conditions matched, False = Conditions not matched
	def __match_sun_altitude(self, conditions):
		min_sun_altitude = conditions['min_sun_altitude'] if 'min_sun_altitude' in conditions else None;
		max_sun_altitude = conditions['max_sun_altitude'] if 'max_sun_altitude' in conditions else None;
		
		abLogger.debug("condition 'sun_altitude': min={0} max={1} current={2}".format(min_sun_altitude, max_sun_altitude, self.__current_sun_altitude))
		
		if min_sun_altitude == None and max_sun_altitude == None:
			abLogger.debug(" -> check sun altitude: no limit given")
			return True
			
		if min_sun_altitude != None and self.__current_sun_altitude < min_sun_altitude:
			abLogger.debug(" -> check sun altitude: to low")
			return False
		if max_sun_altitude != None and self.__current_sun_altitude > smax_sun_altitude:
			abLogger.debug(" -> check sun altitude: to high")
			return False
		abLogger.debug(" -> check sun altitude: OK")
		return True

	# Return current sun altitude
	# @return current sun altitude
	def get_sun_altitude(self):
		return self.__current_sun_altitude