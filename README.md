#Automatic Blind Control plugin for smarthome.py#

##IMPORTANT:##
##This documentation is not up to date. There have been several changes regarding the configuration of the plugin that are not yet reflected in this file. Please see the file UPDATE.md for a brief description of required configuration changes. This file will be updated after all planned changes have been made and properly tested.##


##Description of functionality##

Via additional items, user-defined states can be defined for each objects like blind in items/*.conf files. Each state can have a set of enter and leave conditions as well as several actions that are perfomed once the state becomes current. In regular intervals the states for each object are checked:
- If the conditions to leave the current state are not fulfilled, the object remains in the current state
- If the current condition can be left, all states are checked in the order they are defined in the configuration file.
- The first state that has all conditions to enter the state fulfilled gets current. Actions configured for this state are executed
- If no state matches, nothing happens, the objects remain in their current state.

He following conditions can be part of the condition sets:
- time of day (min, max)
- weekday (min, max)
- sun azimut (min, max)
- sun altitude (min, max)
- age of current position (min, max)
- delay of current position (min, max)
- random number (min, max)
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
        #cycle_default = 300
        #startup_delay_default = 10
        #manual_break_default = 3600
        #log_level = 0
        #log_directory = /usr/local/smarthome/var/log/AutoBlind/

Commented parameters are default values which may be canged on your needs.

Name                  | Description
--------------------- | -----------
cycle_default         | Default interval between two checks (seconds)
startup_delay_default | Default startup interval for first check (seconds)
manual_break_default  | Default time to deactivate the automatic controll after manual changes (seconds)
log_level             | Extended logging: Loglevel (0: off, 1: info, 2: debug
log_directory         | Extended logging: Directory for Logfiles (directory has to exist!)

##Extended logging##
Search for issues with AutoBlind condition sets using normal smarthome.py logging is problematic as in info/debug mode there are to much other messages in the log. Therefore an extended logging has been included in the plugin.

The extended logging writes a separate logfile per day and object. This is especially useful when the "housemate" states friday night that "the blinds in the childrens room where where moving somehow strange on monday morning". Some (man) can now check the logfile for the blinds in the childrens room from monday and see how (loglevel = info) and why (loglevel = debug) they moved. 

To activate the extended logging set parameter `log_level` in plugin.conf to either 1 (info) or 2 (debug). Via parameter `log_directory` the directory can be set in which the logs will be written. By default the directory is `/usr/local/smarthome/var/log/AutoBlind/`. The filenames of the logfiles consist from date and id of the blind item. Dots in the blind item id are replaced by underscores, e.g. "2015-05-15-room1_raffstore.log"

##Configuration of objects##
For each object which should be automated by the AutoBlind plugin an item containing all AutoBlind configuration for this object is required.
To tell the AutoBlind plugin which items contain AutoBlind configuration information add the attribute

    autoblind_plugin = active
To the item. For debugging you may set this the value of this attribute to something different. This will cause the AutoBlind plugin to ignore the configuration.

Inside the object configuration item, several attributes are mandatory:

    [myFirstAutoBlindControlledObject]        
        name = Some very nice example
        autoblind_plugin = active
        cycle = 300
        startup_delay = 10
        item_active = room1.raffstore.auto_active
        item_state_id = room1.raffstore.auto_state_id
        item_state_name = room1.raffstore.auto_state_name


Name                  | Description
--------------------- | -----------
name                  | A name for this item
autoblind_plugin      | Mark this item as "containing AutoBlind configuration"
cycle                 | Interval between two determinations of required state (seconds)
startup_delay         | Startup delay for first determination of required state (seconds)
item_active           | Id of the item which is used to activate and deactivate the automatic control
item_state_id         | Id of the item which is used to store the id of the current state
item_state_name       | Id of the item which is used to store the nane of the current state (use this item for display purposes)


`cycle`and `startup_delay` may be left out. In this case the values for these settings are taken from the plugin configuration values`cycle_default` and `startup_delay_default`

####Example (with knx group addresses)####
    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[auto_active]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/7
                knx_status = 1/1/8
                knx_listen = 1/1/7 | 1/0/7
                visu_acl = rw
                cache = on
            [[[auto_state_id]]]
                type = str
                visu_acl = r
                cache = on
            [[[auto_state_name]]]
                type = str
                visu_acl = r
                cache = on
                
###States###             
All subitems of the object config item are considered as object states. Their ids are arbitrary and used as values for the item given as `item_state_id`. If you configure names for the items, they are used as values for the item given as `item_state_name`. (otherwise the item id is used here, too)

Every state can have an arbitrary number of "enter" and "leave" condition sets. An state can become current if one of the "enter" condition sets is fulfilled. Once the state is current, it can only be left if one of the "leave" condition sets is fulfilled. An "enter" condition set is a subitem with id "enter" or "enter_(somename)". A leave condition set is a subitem with id "leave" or "leave_(somename)".
Inside every condition set an arbitrary number of conditions can be defined.

Every state can have an arbitray number of "actions" defined. Once the state becomes current, all actions are performed. If an state stays current in further checks, the actios are reperformed under several conditions. Actions are defined as attribute "set_(action_name)".

Conditions and actions usually relate to items. These items have to be defined in the object configuration item as "item_(condition_name/action_name)"


####Example####

    [myFirstAutoBlindControlledObject]
        (...)
        item_height = room1.raffstore.height
        item_lamella = room1.raffstore.lamella
        [[day]]
            type = foo
            name = Day (static)
            use = some.default.item
            [[[enter]]]
                (...)
            [[[leave]]]
                (...)
            set_height = value:100
            set_lamella = value:0

Object | Function
------ | --------
Attributes `item_height`, `item_lamella` | Items wich are changed by actions `set_height` and `set_lamella`
Attribute `name` | Name of state. Will be written in item `item_state_name` if state is current and can be displayed in visualization
Attribute `use` | Import settings from a different item. If `enter` and/or `leave` are included in the current item too, the conditions in this child items overwrite the matching imported conditions   
Child item  `enter` | Condition set that has to be fulfilled before the state can become current
Child item `leave` | Condition set that has to be fulfilled before the state can be left
Attributes `set_height`and `set_leave` | New static values for `item_height` and `item_leave` 


###Deactivate automatic control at manual action###
It is possible to deactivate the automatic control for a certain time if a manual action is being detected. To use this functionality, enter the items for manual action need to be configured "watch items". You can also set an individual time  after which the automatic controll will be automatically reactivated again. If you do not set an individual time, the time configured as manual_break_default in plugin.conf is being used. 

The items to watch need to be listed in attribute `watch_manual` in the main configuration item. Multiple items need to be separated by | (pipe). Via attribute „manual_break“ the deactivation period (in seconds) can be set 

    [myFirstAutoBlindControlledObject]
        (...)
        watch_manual = room1.raffstore.aufab | room1.raffstore.step
        manual_break = 7200
        (...)
            
This example would deactivate the automatic control for two hours (7200 seconds) once items room1.raffstore.aufab or room1.raffstore.step are set by someone. The deactivation time starts anew on every event that is received one of this item.        


###Trigger update of current state outside of cycle###
By default, the state that is current is updated in a regular interval (defined by configuration value `cycle`). If you require to act on some changes immediately, you can additionally use watch items and trigger an update of the state on every change of these items.  

The items to watch need to be listed in attribute `watch_trigger` in the main configuration item. Multiple items need to be separated by | (pipe).
 
    [myFirstAutoBlindControlledObject]
        (...)
        watch_trigger = room1.light.main | room1.light.wall
        (...)

In this example, the update of the current state will be executed at every change of item `room.light.main` or `room.light.wall`. The normal cycle will not be changed, every change of such an item triggers an additional update.

__Important:__
__It is not recommended to use this function for security related states as for example moving blinds up at to much wind. Security related functions have to be as simple as possible. It is therefore highly recommended to use the lock functionality that all up-to-date blind actuators provide fur such functions.__

##Condition sets##
All subitems of the state config item are considered as condition sets. In general, there are two types of condition sets:
- **Enter condition sets**: Condition sets that are checked if a new state is searched.
- **Leave condition sets**: Condition sets that are checked in order to determine if a state can be left.

Whether a subitem is an enter or a leave condition set is determined by the id of the subitem. If the id is "enter" or starts with "enter_", it is an enter condition set. The id of a leave condition set is always "leave" or starts with "leave_".

The following rules apply:
* A single condition set is fulfilled if each condition defined in the condition set is being matched ("AND"). Possible limits that are not defined in this condition are not checked.
* A state can be left if any of the defined leave condition sets is fulfilled ("OR"). Checking stops at the first fulfilled condition set.
* A state can be entered if any of the defined enter condition sets is fulfilled ("OR"). Checking stops at the first filfilled condition set.


####Example####
    
    [myFirstAutoBlindControlledObject]
        (...)
        item_height = room1.raffstore.height
        item_lamella = room1.raffstore.lamella
        [[night]]
            type = foo
            name = Night                
            use = some.default.item
            [[[enter_todark]]]
                (... some conditions to enter this state if it is to dark ...)
            [[enter_tolate]]]
                (... some conditions to enter this state if it is to late ...)
            [[[leave]]]
                (...)
            set_height = value:100
            set_lamella = value:0


##Conditions##
Every condition requires three main things:
* A name identifying the condition and the elements belonging to the condition
* Some limits to check if the condition is fulfilled
* Something to get a current value to check against the conditions

The name is arbitrary and just used in the attribute naming. The names of all attributes belonging to one condition follow the same pattern `(function name)_(condition name)`
There are some "special" condition names explained later

The limits are defined inside the condition set items. The following limits are possible:
limit | attribute | function
------|-----------|----------
minimum | min_(condition name) | The condition is fulfilled if the current value is lower than the given minimum
maximum | max_(condition name) | The condition is fulfilled if the current value is greater than the given maximum
distinct value | value_(condition name) | The condition is fulfilled if the current value is equal the given value
negate | negate_(condition name) | The whole condition is negated

The current value to check agains can either be provided by an item or by an eval function. If both are given, the item is used and eval is ignored.
The name of the item or the eval function are set by specific attributes `item_(condition name)` or `eval_(condition name)` in the main configuration item. Their name has also to correspond with the condidion name.

####Example####

    [myFirstAutoBlindControlledObject]
            (...)
            item_height = room1.raffstore.height
            item_lamella = room1.raffstore.lamella
            item_brightness = my.wetherstation.brightness
            [[twilight]]
                type = foo
                name = Twilight                
                use = some.default.item
                [[[enter]]]                    
                    min_brightness = 500
                    max_brightness = 1000
                set_height = value:100
                set_lamella = value:25
            [[night]]
                type = foo
                name = Night                
                use = some.default.item
                [[[enter_todark]]]
                    max_brightness = 500
                set_height = value:100
                set_lamella = value:0
            
###"Special" conditions###
For some conditions you do not need to set an item or eval-function to determine the current value. The plugin will do this for you if you use some predefined condition names. These condition names should therefore not be used for your other conditions.

The following "special" condition names can be used:

**time:** Current time.
Values for `value_time`, `min_time` and 'max_time' need to be given in format "hh:mm". 24h time is being used. Examples: "08:00" or "13:37". To mark the end of the day, the value "24:00" can be used, which is automatically converted to "23:59:59" for the checks.

**weekday:**
Day of week as number. 0 represents Monday, 6 represents Sunday

**sun_azimut:**
Sun position (horizontal angle)

Azimut is the compass direction in which the sun is, seen from one's current position. The azumut is calculated by smarthome.py based on current time and position. See [Smarthome.py documentation](http://mknx.github.io/smarthome/logic.html#sh-sun) for requirements.

0 → Sun exactly in the North 
90 → Sun exactly in the East
180 → Sun exactly in the South
270 → Sun exactly in the West

**sun_altitude:**
Sun position (vertical angle)

Altitude is the angle in which the sun is above the horizon. The altitude is calculated by smarthome.py based on current time and position. See [Smarthome.py documentation](http://mknx.github.io/smarthome/logic.html#sh-sun) for requirements.


negative → Sun below horizon
0 → Sunrise 
90 → Sun exactly in zenith (occurs only in equatorial areas)

**age:**
Time since last change of state (seconds)

The age is being calculated via the last change of the item given with attribute `item_state_id`.

**delay:**
Time since enter conditions of state are not matched (seconds)

**random:**
Radom number between 0 and 100

If you want to do something randomly with a propability of 60%, e.g. use condition `max_random = 60` 

##Actions##
Like conditions, every action requires a name, too. The action name is again arbitrary and just used in the attribute naming. The names of all attributes belonging to one action follow the same pattern `(function name)_(action name)`

Currently there are two types of actions that can be performed:
* An item can be set to a value
* A logic can be triggered

###Setting an item to value###
The item to be changed has to be defined as attribute in the main configuration item as `item_(action name)`.
The value for the item has to be defined as attribute in the state item as `set_(action name)`.

The value can either be a static value, the result of executing a function or the current value of another item. A prefix in the attribute value defines which one is being used.

attibute value | function
-------------- | ---------
value:(static value) | use the given static value
eval:(function name) | execute the given function and use the result returned by the function as value
item:(item id) | Use the current value of the given item as value


####Example####

    [myFirstAutoBlindControlledObject]
            (...)
            item_height = room1.raffstore.height
            item_lamella = room1.raffstore.lamella
            [[twilight]]
                (...)
                set_height = value:100
                set_lamella = value:25
            [[night]]
                (...)
                set_height = value:100
                set_lamella = value:0
            [[suntracking]]
                (...)
                set_height = value:100
                set_lamella = eval:autoblind_eval.SunTracking()


##Using default values##
It is possible to define some default states inside the configuration and use them later for distinct object states. It is also possible to overwrite settings from the used default state.
When defining the default states inside a parent item, do not mark this parent item with `autoblind_plugin = active` as it does not contain a complete object configuration.

####Example####

    [autoblind]
        [[default]]
            (...)
            [[[night]]]
                (...)
                [[[[enter]]]]
                    (...)
                set_height = value:100
                set_lamella = 0
            [[[dawn]]]
                (...)
                [[[[enter]]]]
                    (...)
                set_height = value:100
                set_lamella = 25
                
            [[[dusk]]]
                (...)
                [[[[enter]]]]
                    (...)
                set_height = value:100
                set_lamella = 75
                    
            [[[day]]]
                (...)
                [[[[enter]]]]
                    (...)
                set_height = value:0
                set_lamella = 100
                                 
    [myFirstAutoBlindControlledObject]
            (...)
            item_height = room1.raffstore.height
            item_lamella = room1.raffstore.lamella
            [[night]]
                use = autoblind.default.night
                [[[enter_additional]]]
                    (... additional enter condition set ...)
            [[dawn]]
                use = autoblind.default.dawn
            [[dusk]]
                use = autoblind.default.dusk
                [[[enter]]]
                    (... changes on default enter conditio ...)
            [[suntracking]]
                (...)
                set_height = value:100
                set_lamella = eval:autoblind_eval.SunTracking()
            [[day]]
                use = autoblind.default.day
            
As you can see here, the items and the values for actions can be defined at different places. Here the items are defined in the object item while the values are defined at the default items. The same can be done for conditions.

##Predefined action functions##
The AutoBlind plugin provides a set of predefined functions that can easily be used for actions. These functions are contained in a class which is instanciated just before executing an action if required. The following functions can be used:

###Calculate lamella angle for sun tracking###
 
    set_(action name) = eval:autoblind_eval.SunTracking()
    
###Random integer value###
    
    set_(action name) = eval:autoblind_eval.get_random_int(min,max)
    
Set `min` and `max` to the minimum/maximum value of the number you want to receive. You can omit min and max, the defaults are 0 for min and 255 for max.
    
    
    
    