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
# AutoBlindItem
#
# Class representing a blind item
#########################################################################
import logging
from . import AutoBlindTools
from .AutoBlindLogger import abLogger
from . import AutoBlindPosition

logger = logging.getLogger('')

def create(smarthome,item, item_id_height = 'hoehe', item_id_lamella = 'lamelle'):
	return abItem(smarthome,item, item_id_height, item_id_lamella)

# Class representing a blind item
class abItem:
	__item = None
	__item_item_autoblind = None
	__item_active = None
	__item_lastpos_id = None
	__item_lastpos_name = None
	__item_height = None
	__item_lamella = None
	__positions = []
	__watch_manual = []
	__manual_break = 0
	
	# Constructor
	# @param smarthome: instance of smarthome.py
	# @param item: item to use
	# @param item_id_height: name of item to controll the blind's height below the main item of the blind
	# @param item_id_lamella: name of item to controll the blind's lamella below the main item of the blind
	# @param manual_break_default: default value for "manual_break" if no value is set for specific item
	def __init__(self,smarthome,item, item_id_height = 'hoehe', item_id_lamella = 'lamelle', manual_break_default = 3600):
		logger.info("Init AutoBlindItem {}".format(item.id()))
		self.sh = smarthome		
		self.__item_id_height = item_id_height
		self.__item_id_lamella = item_id_lamella
		self.__positions = []
		
		# get required items for this AutoBlindItem
		self.__item = item
		self.__item_height = AutoBlindTools.get_child_item(self.__item,self.__item_id_height)
		self.__item_lamella = AutoBlindTools.get_child_item(self.__item,self.__item_id_lamella)		
		self.__item_autoblind = AutoBlindTools.get_child_item(self.__item,"AutoBlind")
		if self.__item_autoblind != None:
			# get items
			self.__item_active = AutoBlindTools.get_child_item(self.__item_autoblind,"active")
			self.__item_lastpos_id = AutoBlindTools.get_child_item(self.__item_autoblind,"lastpos_id")
			self.__item_lastpos_name = AutoBlindTools.get_child_item(self.__item_autoblind,"lastpos_name")
				
			#get positions
			items_position =  self.__item_autoblind.return_children()
			for item_position in items_position:
				if not 'position' in item_position.conf and not 'use' in item_position.conf: continue				
				position = AutoBlindPosition.create(self.sh, item_position, self.__item_autoblind)
				if position.validate():
					self.__positions.append(position)		
			
			# set triggers for watch_manual
			if 'watch_manual' in self.__item_autoblind.conf:
				for entry in self.__item_autoblind.conf["watch_manual"]:
					for item in self.sh.match_items(entry):
						item.add_method_trigger(self.__watch_manual_callback)
						self.__watch_manual.append(item.id())
				self.__item_active.add_method_trigger(self.__reset_active_callback)
				
			# get manual_break time
			if 'manual_break' in self.__item_autoblind.conf:
				self.__manual_break = int(self.__item_autoblind.conf["manual_break"])
			else:
				self.__manual_break = manual_break_default
			
	# Validate data in instance
	# @return: TRUE: Everything ok, FALSE: Errors occured
	def validate(self):
		if self.__item == None:
			logger.error("No item configured!")
			return False
		
		item_id = self.__item.id()
		
		if self.__item_autoblind == None: 
			logger.error("{0}: Item '{1}' does not have a sub-item 'AutoBlind'!".format(item_id,item_id))
			return False
		
		autoblind_id = self.__item_autoblind.id()
		
		if self.__item_active == None: 
			logger.error("{0}: Item '{1}' does not have a sub-item 'active'!".format(item_id,autoblind_id))
			return False
		
		if self.__item_lastpos_id == None:
			logger.error("{0}: Item '{1}' does not have a sub-item 'lastpos_id'!".format(item_id,autoblind_id))
			return False
		
		if self.__item_lastpos_name == None:
			logger.error("{0}: Item '{1}' does not have a sub-item 'lastpos_name'!".format(item_id,autoblind_id))
			return False

		if self.__item_height == None:
			logger.error("{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id, item_id, self.__item_id_height))
			return False
				
		if self.__item_lamella == None:
			logger.error("{0}: Item '{1}' does not have a sub-item '{2}'!".format(item_id,item_id, self.__item_id_lamella))
			return False
		
		if len(self.__positions) == 0:
			logger.error("{0}: No positions defined!".format(item_id,item_id, self.__item_id_lamella))
			return False
		
		return True
	
	# log item data
	def log(self):
		abLogger.setSection(self.id())
		abLogger.info("AutoBlind Configuration ========================================================================================================")
		abLogger.info("Item 'Height': {0}".format(self.__item_height.id()));
		abLogger.info("Item 'Lamella': {0}".format(self.__item_lamella.id()));
		abLogger.info("Item 'Active': {0}".format(self.__item_active.id()));
		abLogger.info("Item 'LastPos Id': {0}".format(self.__item_lastpos_id.id()));
		abLogger.info("Item 'LastPos Name': {0}".format(self.__item_lastpos_name.id()));
		for position in self.__positions:
			position.log()
		abLogger.clearSection()		
	
	# return item id
	def id(self):
		return self.__item.id()
		
	# Find the positition, matching the current conditions and move the blinds to this position		
	def update_position(self, condition_checker):		
		logger.info("Update position of {0}".format(self.__item._name))		
		abLogger.info("Update Position ================================================================================================================")
		
		# Check if this AutoBlindItem is active. Leave if not
		if self.__item_active() != 1:
			abLogger.info("AutoBlind inactive");
			self.__item_lastpos_name('(inactive)')
			return
		
		# update item dependent conditions
		condition_checker.set_current_age(self.__item_lastpos_id.age())
		
		# get last position 
		last_pos_id = self.__item_lastpos_id()
		last_pos_name = self.__item_lastpos_name()
		abLogger.info("Last position: {0} ('{1}')".format(last_pos_id, last_pos_name))
		
		# check if current possition can be left
		can_leave_position = True
		for position in self.__positions:
			if position.id() == last_pos_id:
				if not condition_checker.can_leave(position):
					abLogger.info("Can not leave current position.")
					can_leave_position = False
					new_position = position
					break
				
		if can_leave_position:		
			# find new position
			new_position = None
			for position in self.__positions:
				if condition_checker.can_enter(position):
					new_position = position
					break;
						
			# no new position -> leave
			if new_position == None:
				abLogger.info("No matching position found.")
				return

			
		# get data for new position
		new_pos_id = new_position.id()
		if new_pos_id == last_pos_id:
			# New position is last position			
			abLogger.info("Position unchanged")
		else:
			# New position is different from last position
			abLogger.info("New position: {0} ('{1}')".format(new_pos_id, new_position._name))
			self.__item_lastpos_id(new_pos_id)
			self.__item_lastpos_name(new_position._name)
		
		# move blinds to this position
		target_position = new_position.get_position(condition_checker.get_sun_altitude())
				
		# Change height only if we change for at least 10%
		height_delta = self.__item_height() - target_position[0] 
		if abs(height_delta) >= 10:
			self.__item_height(target_position[0])

		# Change lamella only if we change for at least 5%
		lamella_delta = self.__item_lamella() - target_position[1]
		if abs(lamella_delta) >= 5:
			self.__item_lamella(target_position[1])
			
	# called when one of the items given at "watch_manual" is being changed
	def __watch_manual_callback(self, item, caller=None, source=None, dest=None):
		if caller != 'plugin' and caller != 'Timer':
			# deactivate "active"
			if self.__item_active()==0:return
			self.__item_active(0)
			# schedule reactivation of "active"
			self.__item_active.timer(self.__manual_break,1)
		
	# called when the item "active" is being changed
	def __reset_active_callback(self, item, caller=None, source=None, dest=None):
		# reset timer for reactivation of "active"
		self.__item_active.timer(0,self.__item_active())			