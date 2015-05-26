#Automatic Blind Control plugin for smarthome.py#

##Description of functionality##

Via additional items, user-defined positions can be defined for each blind in items/*.conf files. Each position can have a set of enter and leave conditions. In regular intervals the positions for each blind are checked:
- If the conditions to leave the current position are not fulfilled, the blind remains in the current position
- If the current condition can be left, all positions are checked in the order they are defined in the configuration file.
- The first positions that has all conditions to enter the position fulfilled gets activated. Blinds are moved as defined in this position
- If no position matches, nothing happens, the blinds stay in their current position.

He following conditions can be part of the condition sets:
- time of day (min, max)
- sun azimut (min, max)
- sun altitude (min, max)
- age of current position (min, max)
Additionaly any number of items can be checked for value or min/max as condition.

##Installation##
To use the AutoBlind plugin, you can import it as a submodule in your own smarthome.py repository:

    cd [your smarthome.py base directory]/plugins
    git submodule add https://github.com/i-am-offline/smarthome.plugin.autoblind.git autoblind
    cd autoblind
    git checkout master

You can now do all required git actions (like fetch, pull, checkout, ...) on the submodule when inside the plugins/autoblind directory.

see [Git-Tools-Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) for more information on git submodules.

When having added the AutoBlind plugin as submodule, you need to update the submodule after cloning your own repository:
`git submodule init` initializes all submodules, 
`git submodule update` updates all submodules to the recorded version

##Configuration##
 
###plugin.conf###
To use the AutoBlind plugin, add the following to your plugin.conf file:

    [autoblind]
        class_name = AutoBlind
        class_path = plugins.autoblind
        #cycle = 300
        #item_id_height = hoehe
        #item_id_lamella = lamelle
        #log_level = 0
        #log_directory = /usr/local/smarthome/var/log/AutoBlind/
        #manual_break_default = 3600

Commented parameters are default values which may be canged on your needs.

Name                 | Description
-------------------- | -----------
cycle                | Interval between two checks
item_id_height       | Id of the sub-item which is used to set the height value for the blinds
item_id_lamella      | Id of the sub-item which is used to set the lamella angle value for the blinds
log_level            | Extended logging: Loglevel (0: off, 1: info, 2: debug
log_directory        | Extended logging: Directory for Logfiles (directory has to exist!)
manual_break_default | Default time to deactivate the automatic controll after manual changes (Seconds)

##Extended logging##
Search for issues with AutoBlind condition sets using normal smarthome.py logging is problematic as in info/debug mode there are to much other messages in the log. Therefore an extended logging has been included in the plugin.

The extended logging writes a separate logfile per day and blind object. This is especially useful when the "housemate" states friday night that "the blinds in the childrens room where where moving somehow strange on monday morning". Some (man) can now check the logfile for the blinds in the childrens room from monday and see how (loglevel = info) and why (loglevel = debug) they moved. 

To activate the extended logging set parameter `log_level` in plugin.conf to either 1 (info) or 2 (debug). Via parameter `log_directory` the directory can be set in which the logs will be written. By default the directory is `/usr/local/smarthome/var/log/AutoBlind/`. The filenames of the logfiles consist from date and id of the blind item. Dots in the blind item id are replaced by underscores, e.g. "2015-05-15-room1_raffstore.log"

##Configuration of items##
An item used for AutoBlind control needs to have at least the followng three child items:
- **AutoBlind** Konfiguration der automatischen Verschattungssteuerung für dieses Objekt
- **hoehe** Item zur Ansteuerung der Behanghöhe
- **lamelle** Item zur Ansteuerung des Lamellenwinkels

The items "hoehe" and "lamelle" may be named different, but need to be the same for all AutoBlind controlled blind items. In this case the name of the ims has to be set via parameters "item_id_height" and "item_id_lamella" in the plugin configuration.

###Item "AutoBlind"###
The item `AutoBlind` needs to have at least the following three child items:
- **active** Type „bool“, for activating and deactivating of automatic control
- **lastpos_id** Type „str“, to store the id of the current position
- **lastpos_name** Type „str“, to store the name of the current position

####Example (with knx group addresses)####
    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[AutoBlind]]]
                [[[[active]]]]
                    type = bool
                    knx_dpt = 1
                    knx_send = 1/1/7
                    knx_status = 1/1/8
                    knx_listen = 1/1/7 | 1/0/7
                    visu_acl = rw
                    cache = on
                [[[[lastpos_id]]]]
                    type = str
                    visu_acl = r
                    cache = on
                [[[[lastpos_name]]]]
                    type = str
                    visu_acl = r
                    cache = on
            [[[hoehe]]]
                type = num
                knx_dpt = 5.001
                knx_send = 1/1/2
                knx_init = 1/1/3
                visu_acl = rw
                cache = on
            [[[lamelle]]]
                type = num
                knx_dpt = 5.001
                knx_send = 1/1/4
                knx_init = 1/1/5
                visu_acl = rw
                cache = on
                
###Positions###             
Underneath `AutoBlind` further items will be created. Each item represents a possible position for the blinds. The id if the item is arbitrary but must not be "active", "lastpos_id" or "lastpos_name":

####Example####

            [[[[night]]]]
                type = foo
                name = Night
                position = 100,0
                use = some.default.item
                [[[[[enter]]]]]
                    (…)
                [[[[[leave]]]]]
                    (…)

Object | Function
------ | --------
Attribute `name` | Name of position. Will be written in `lastpos_name` if position is active and can be displayed in visualization
Attribute `position` | Blind position to set if position is active. See below for possible values
Attribute `use` | Import settings from a different item. If `enter` and/or `leave` are included in the current item too, the conditions in this child items overwrite the matching imported conditions   
Child item  `enter` | Condition set that has to be fulfilled before the position can become active
Child item `leave` | Condition set that has to be fulfilled before the position can be left

For the attribute `position` there are two possible types of values that can be used:
- **static position:** To values separated by comma. First value his the value for heigth, second value is the value for lamella angle. Example: `100,0`
- **dynamic position:** value "auto". Height will be set to 100%, lamella angle will be calculated based on sun position.

###Deactivate automatic control at manual action###
It is possible to deactivate the automatic control for a certain time if a manual action is being detected. To use this functionality, enter the items for manual action need to be configured watch items. You can also set an individual time  after which the automatic controll will be automatically activated again. If you do not set an individual time, the time configured as manual_break_default in plugin.conf is being used. 

The items to watch need to be listed in attribute `watch_manual` below `AutoBlind`. Multiple items need to be separated by | (pipe). Via attribute „manual_break“ the deactivation period (in seconds) can be set 

    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[AutoBlind]]]
                watch_manual = room1.raffstore.aufab | room1.raffstore.step
                manual_break = 7200


##Condition sets##
Each position can have several condition sets. In general, there are two types of condition sets:
- **Enter condition sets**: Condition sets that are checked if a new position is searched.
- **Leave condition sets**: Condition sets that are checked in order to determine if a position can be left.

The example above shows a simpe definition: One condition set of each type, named "enter" and "leave". 
For more complex conditions it is possible to have more than one condition set of each type. To separate different condition sets, they need to have different names. However, their name has to start with either "enter_" or "leave_" to indicate whether they are enter- or leave conditions.

The following rules apply:
* A single condition set is fulfilled if each condition defined in the condition set is being matched ("AND"). Possible limits that are not defined in this condition are not checked.
* A position can be left if any of the defined leave condition sets is fulfilled ("OR"). Checking stops at the first fulfilled condition set.
* A position can be entered if any if the defined enter condition sets is fulfilled ("OR"). Checking stops at the first filfilled condition set.


####Example####

            [[[[night]]]]
                type = foo
                name = Night
                position = 100,0
                use = some.default.item
                [[[[[enter_todark]]]]]
                    (... some conditions to enter this position if it is to dark ...)
                [[[[enter_tolate]]]]]
                    (... some conditions to enter this position if it is to late ...)
                [[[[[leave]]]]]
                    (...)


##Conditions inside a condition set##
###Specific Conditions###
Some values are calculated within the plugin. For this values specific conditions can be set in the condition sets 

####time####
Condition | Explanation
--------- | ----------
min_time  | Lower limit for time of day
max_time  | Upper limit for time of day

The time of day has to be entered as two comma separated values. The first value is the hour (24-hour clock), the second the minute. The value "8,30" means 8:30 (8:30am), "20,30" means 20:30 (8:30pm) 
min_time may me larger than max_time to define overnight periods:

    min_time = 17,0
    max_time = 8,0

Between 17:00 (5:00pm) und 08:00 (8:00am)

####sun azimut####
Condition | Explanation
--------- | ----------
min_sun_azimut  | Lower limit for sun position (horizontal angle)
max_sun_azimut  | Upper limit for sun position (horizontal angle)

Azimut is the compass direction in which the sun is, seen from one's current position. The azumut is calculated by smarthome.py based on current time and position. See [Smarthome.py documentation](http://mknx.github.io/smarthome/logic.html#sh-sun) for requirements.

0 → Sun exactly in the North 
90 → Sun exactly in the East
180 → Sun exactly in the South
270 → Sun exactly in the West

Here, too, min_sun_azimut may be larger than max_sun_azimut:

	min_sun_azimut = 270
	max_sun_azimut = 90

Fulfilled from the time where the sun is exactly in the West (in the evening) until the sun is exactly in the East (in the morning of the next day)

####sun altitude####
Condition | Explanation
--------- | ----------
min_sun_altitude  | Lower limit for sun position (vertical angle)
max_sun_altitude  | Upper limit for sun position (vertical angle)

Altitude is the angle in which the sun is above the horizon. The altitude is calculated by smarthome.py based on current time and position. See [Smarthome.py documentation](http://mknx.github.io/smarthome/logic.html#sh-sun) for requirements.


negative → Sun below horizon
0 → Sunrise 
90 → Sun exactly in zenith (occurs only in equatorial areas)

####age of position####
Condition | Explanation
--------- | ----------
min_age  | Lower limit for period sincle last change of position
max_age  | Upper limit forperiod sincle last change of position

The age is being calculated via the last change of item `lastpos_id`. Value is seconds.

###Generic conditions###
In addition to the described specific conditions, the value of any item can be used for a condition. This functionality is called "generic conditions".

If you want to use an item for a generic condition, you first need to add an attribute on the `autoblind` item where you specify the item for the generic condition. Then you can add conditions for this item in the condition sets. Item and conditions are linked via the attribute names:

Attribute | Function
--------- | -------
item_[name] | Id of the item which provides the current value
value_[name] | Fixed value condition
min_[name] | Lower limit for value
max_[name] | Upper limit for value

„[name]“ name is an arbitrary identification, that has to be the same for attributes belonging together.
If the condition "value_[name]" is set, the condition is fulfilled if the item has exactly the value defined in "value_[name]". Conditions "min_[name]" and "max_[name]" are not checked if "value_[name]" is set.
If "value_[name]" is not set, the value if the item has to be between "min_[name]" and "max_[name]" to fulfill the condition. "min_[name]" and "max_[name]" may be missing, in this case the missing limit will not be checked

##Examples##

###Default values###
Independen from blinds, some default items are defined. In the default items some items are derived from other items (using the `use` attribute). 

    [autoblind]
        [[default]]
            item_brightness = aussen.wetterstation.helligkeit
            item_temperature = aussen.wetterstation.temperatur
            [[[night]]]
                type = foo
                name = Night
                position = 100,0
                [[[[enter]]]]
                    max_brightness = 100
                    min_time = 17,0
                    max_time = 8,0
                
            [[[morning]]]
                type = foo
                name = Twilight in the morning
                position = 100,25
                [[[[enter]]]]
                    min_brightness = 100
                    max_brightness = 300
                    min_time = 0,0
                    max_time = 12,0
                
            [[[evening]]]
                type = foo
                name = Twilight in the evening
                position = 100,75
                [[[[enter]]]]
                    min_brightness = 100
                    max_brightness = 300
                    min_time = 12,0
                    max_time = 24,0
                
            [[[suntrack_front1]]]
                type = foo
                name = Day (tracking the sun)
                position = auto
                [[[[enter]]]]
                    min_brightness = 60000
                    min_sun_altitude = 20
                    min_sun_azimut = 170
                    max_sun_azimut = 270
                [[[[leave]]]]
                    max_brightness = 35000
                    min_age = 1800
                    
            [[[suntrack_front2]]]
                type = foo
                use = autoblind.default.suntrack_front1
                [[[[enter]]]]
                    min_sun_azimut = 260
                    max_sun_azimut = 360
                    
            [[[suntrack_front3]]]			
                type = foo
                use = autoblind.default.suntrack_front1
                [[[[enter]]]]
                    min_sun_azimut = 70
                    max_sun_azimut = 170
                    
            [[[day]]]
                type = foo
                name = Day (static)
                position = 0,100
                [[[[enter]]]]
                    min_time = 6,0
                    max_time = 22,0
                
            [[[child_nap]]]
                name = Childrens nap after lunch
                position = 100,0
                [[[[enter]]]]
                    min_time = 12,15
                    max_time = 16,0
                
            [[[child_sleep]]]
                name = Childrens sleep at night
                position = 100,0
                [[[[enter]]]]
                    min_time = 19,30
                    max_time = 08,30

###Some remarks explaining this example configuration:###

####Generic Conditions####
`item_*` as well as `min_*`, `max_*` and `value_*` settings can be made in default settings. The important thing is that the `item_*` attribute is two levels above the`min_*`, `max_*` and/or ' value_*' attriutes
####"morning"/"evening"####
During twilight the blinds should be down, but tilted so that some light can fall in. In the morning the blinds are tilted downwards, in the evening upwards. The differentiation between "morning" and "evening" is made via the time (morning = 00:00 till 12:00, evening = 12:00 till 24:00)
„Morgens“/“Abends“

####suntrack####
The example contains tree items for suntracking, one for each front of the building. `suntrack_front1` is defined completely. `suntrack_front2` and `suntrack_fron3` take the settings from `suntrack_front1`and just change the required azimut ranges because the different direction of the fronts.

Within `suntrack_front1`there is a leace condition set which should take care that sun sunny days with crossing clouds the position will not swap between suntrack and static day position to often. Suntracking will be activated if the sun position (azimut and altitude) is in certain areas and the brightness is greater than 60000 Lux. Position `suntrack_front*` can only be left if brightness is not higher than 35000 Lux and position has been active for at least 30 minutes (1800 seconds)

####"child_nap"/"child_sleep"####
Independend from other conditions, a room (childrens room) shold be darkend completely between 12:15 and 16:00 and 19:430 and 08:30.
 
###Specific blind objects###
For specific blind objects, the predefined default settings can simply be used:

    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[AutoBlind]]]
                [[[[active]]]]
                    type = bool
                    visu_acl = rw
                    cache = on
                [[[[lastpos_id]]]]
                    type = str
                    visu_acl = r
                    cache = on
                [[[[lastpos_name]]]]
                    type = str
                    visu_acl = r
                    cache = on
                [[[[night]]]]
                    use = autoblind.default.night
                [[[[morning]]]]
                    use = autoblind.default.morning
                [[[[evening]]]]
                    use = autoblind.default.evening
                [[[[suntrack]]]]
                    use = autoblind.default.suntrack_front2
                [[[[day]]]]
                    use = autoblind.default.day

So the basic conditions do not have to be defined for each blind object again. If required, parts of conditions can be changed for single blind objects anyway:                    

    [room2]
        [[raffstore]]
            name = Raffstore Room 2
            [[[AutoBlind]]]
                [[[[active]]]]
                    type = bool
                    knx_dpt = 1
                    knx_send = 1/2/7
                    knx_status = 1/2/8
                    knx_listen = 1/2/7 | 1/0/7
                    visu_acl = rw
                    cache = on
                [[[[lastpos_id]]]]
                    type = str
                    visu_acl = r
                    cache = on
                [[[[lastpos_name]]]]
                    type = str
                    visu_acl = r
                    cache = on
                [[[[night]]]]
                    use = autoblind.default.night
                [[[[morning]]]]
                    use = autoblind.default.morning
                [[[[evening]]]]
                    use = autoblind.default.evening
                [[[[suntrack]]]]
                    use = autoblind.default.Nachfuehren.suntrack_front2
                    [[[[[enter]]]]]
                        min_sun_azimut = 150
                        min_brightness = 40000
                    [[[[[leave]]]]]
                        max_brightness = 25000
                [[[[day]]]]
                    use = autoblind.default.day

In this example `suntrack` also uses the defaults for front 2. However, conditions `min_sun_azimut` und `min_brightness` to enter the position and `max_brightness` to leave the position are moidified. Conditions defined in `autoblind.default.Nachfuehren.suntrack_front2` and not overwritten here (`min_sun_altitude`, `max_sun_azimut` to enter position and `min_age` to leave position) keep their values set in the default condition sets.
 
