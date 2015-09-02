#Automatic Object Control plugin for smarthome.py#


##Description of functionality##

Via additional items objects can be defined that have an arbitrary number of user-defined states in items/*.conf files of smarthome.py. Each state can have a set of enter and leave conditions as well as several actions that are perfomed once the state becomes current. In regular intervals the states for each object are checked:
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

Previously this plugins main intention was to control blinds. But as requirements grew, it developed to a plugin that can control nearly everything. Actually its a [finite state machine](https://en.wikipedia.org/wiki/Finite-state_machine).

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
        #startup_delay_default = 10
        #suspend_time_default = 3600
        #laststate_name_manually_locked = Manuell gesperrt
        #laststate_name_suspended = Ausgesetzt bis %X
        #log_level = 0
        #log_directory = var/log/AutoBlind/
        #log_maxage = 0

Commented parameters are default values which may be canged on your needs.

Name                  | Description
--------------------- | -----------
startup_delay_default | Default startup interval for first check (seconds)
suspend_time_default  | Default time to suspend the automatic controll after manual actions (seconds)
laststate_name_manually_locked | Text to show as "laststate_name" if controlled object is manually locked
laststate_name_suspended | Text to show as "laststate_name" if controlled object is suspended. The given text is used as base for time.strftime, which adds the end time of the suspension. see [strftime() and strptime() Behavior](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior) for more information on the time format string.
log_level             | Extended logging: Loglevel (0: off, 1: info, 2: debug
log_directory         | Extended logging: Directory for Logfiles (directory has to exist!)
log_maxage            | Extended logging: Number of days after which the files in `log_directory` should be deleted

##Extended logging##
Search for issues with AutoBlind condition sets using normal smarthome.py logging is problematic as in info/debug mode there are to much other messages in the log. Therefore an extended logging has been included in the plugin.

The extended logging writes a separate logfile per day and object. This is especially useful when the "housemate" states friday night that "the blinds in the childrens room where where moving somehow strange on monday morning". One can now check the logfile for the blinds in the childrens room from monday morning and see how (loglevel = info) and why (loglevel = debug) they moved. 

To activate the extended logging set parameter `log_level` in plugin.conf to either 1 (info) or 2 (debug). Via parameter `log_directory` the directory can be set in which the logs will be written. By default the directory is `<smarthome_base_directory>/var/log/AutoBlind/`. If the given directory name starts with "/" the directory name is taken as absolute directory. Any other directory name is handeled as subdirectory of the smarthome base directory. If the given directory does not exist, it will be created. 
The filenames of the logfiles consist from date and id of the blind item. Dots in the blind item id are replaced by underscores, e.g. "2015-05-15-room1_raffstore.log"

Old log files can be deleted after a certain time. Via parameter `log_maxage` the number of days after which the log files should be deleted can be set. The deletion is suspended as long as `log_maxage` is 0. If `log_maxage` is set to another value, the age of the files in the log directory is checked at smarthome.py startup as well as once a day and outdated files will be deleted. Important: The deletion functionality deletes all files in the given log directory whether they are log files or not. So do not place other files inside this directory

##Configuration of objects##
For each object which should be automated by the AutoBlind plugin an item containing all AutoBlind configuration for this object is required ("object item").
To tell the AutoBlind plugin which items contain AutoBlind configuration information add the attribute `as_plugin = active` to the item. For debugging you may set this the value of this attribute to something different. This will cause the AutoBlind plugin to ignore the configuration.

Inside the object configuration item, two attributes are mandatory:

    [myFirstAutoBlindControlledObject]
        type = bool
        as_plugin = active

Name           | Description
-------------- | -----------
type           | Data type of the item. Use "bool" here.
as_plugin      | Mark this item as "containing AutoBlind configuration"

The following general attributes are optional:

    [myFirstAutoBlindControlledObject]
        (...)
        name = Some very nice example
        as_startup_delay = 10
        as_laststate_item_id = room1.raffstore.auto_laststate_id
        as_laststate_item_name = room1.raffstore.auto_laststate_name
        

Name                   | Description | What happens if attribute is missing?
---------------------- | ----------- | -------------------------------------
name                   | A name for this item | Item Id will be used as name
as_startup_delay       | Delay on smarthome.py startup after which the first calculation of the current state is triggered (seconds). | The value from `startup_delay_default` in the plugin configuration is used as startup delay
as_laststate_item_id   | Id of the item which is used to store the id of the current state. | The current state is recorded internally and not preserved when restarting smarthome.py.
as_laststate_item_name | Id of the item which is used to store the nane of the current state (use this item for display purposes) | The name of the current state is not available.

If used, the items used for `as_laststate_item_id` and `as_laststate_item_name` should be defined as following:

    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[auto_laststate_id]]]
                type = str
                visu_acl = r
                cache = on
            [[[auto_laststate_name]]]
                type = str
                visu_acl = r
                cache = on

###Triggering the calculation of the current state###
The calculation of the current state is performed every time the value for this item is set. You can therefore use smarthome.py standard functionality as cycle, crontab and eval_trigger to trigger the calculation of the current state. To keep the configuration simple, the plugin modifies some settings of the item so that it is not required to set them manually for each object config item.
    
    [myFirstAutoBlindControlledObject]
        (...)
        cycle = 300
        crontab = 0 5 * * | 0 6 * * 
        eval_trigger = room1.light.main | room1.light.wall
        
               
Name                  | Description
--------------------- | -----------
cycle                 | Trigger calculation on a regular base (in the example every 300 seconds) 
crontab               | Trigger calculation on certain times (in the example at 05:00 and 06:00 o'clock)
eval_trigger          | Trigger calculation if an item changes
        
See [smarthome.py documentation on these attributes](http://mknx.github.io/smarthome/config.html#crontab) for details.
Some additional hints regarding these settings: 
* It is not required so set values with cycle, crontab. The AutoBlind plugin adds them automatically if requred.
* It is not required to add an attribute "eval = (something)" when using eval_trigger. The AutoBlind plugin adds this automatically if required
* crontab = init is currently not working for the AutoBlind plugin. Use the `as_startup_delay` setting to run the first calculation of the current state after starting smarthome.py.
 
You may also use other ways to set the value for this item (such as for example assigning a KNX address to listen to) which also triggers the calculation of the current state.

__Important:__
__It is not recommended to use this any trigger method for security related states as for example moving blinds up at to much wind. Security related functions have to be as simple as possible. It is therefore highly recommended to use the lock functionality that all up-to-date blind actuators provide fur such functions.__
              
###Locking automatic control###
Automatic control can be locked via an item.

    [myFirstAutoBlindControlledObject]
        (...)
        as_lock_item = room1.raffstore.auto_lock

Name                  | Description | What happens if attribute is missing?
--------------------- | ----------- | -------------------------------------
as_lock_item          | Id of the item which is used to lock the automatic control. | The automatic control for this object is always unlocked

The item for `as_lock_item` should be defined as following (here with KNX group adresses):
                
    [room1]
        [[raffstore]]
            [[[auto_lock]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/7
                knx_status = 1/1/8
                knx_listen = 1/1/7 | 1/0/7
                visu_acl = rw
                cache = on
             
If the item is set to "True", no automatic control will take place. When the item is set to "False" an update of the current state is triggered immediately. Afterwards the update of the current state will be triggered as defined in the object item.                 

###Suspending automatic control on manual actions###
Automatic control can be suspended for a certain time after manual actions have been detected. There are a couple of attributes to control this feature

    [myFirstAutoBlindControlledObject]
        (...)
        as_suspend_item = room1.raffstore.auto_suspend
        as_suspend_time = 10
        as_suspend_watch = watch.item.one | watch.item.two
                
Name                  | Description | What happens if attribute is missing?
--------------------- | ----------- | -------------------------------------
as_suspend_item       | Id of the item indication a suspension of the automatic control. | You have no possibility to see if the automatic control is suspended.
as_suspend_time       | Time (seconds) for which the automatic control should be suspended after detecting a manual action | Suspension time is taken from plugin configuration value suspend_time_default. If this variable is also missing, suspension time is 3600 seconds (1 hour)
as_suspend_watch      | List of items that are watched. Any change on these items is considered as manual change and triggers the suspension | Suspension functionality is inactive

The item for `as_suspend_item` should be defined as following (here with KNX group adresses):
                
    [room1]
        [[raffstore]]
            [[[auto_suspend]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/9
                visu_acl = r          

To cancel the suspension, use the locking feature. Any change on the lock-item causes the suspension to be cancelled and the automatic control to behave like set by the lock-item.

##States##
All subitems of a object item are considered as object states ("state item"). Their ids are arbitrary and used as values for the item given as `as_laststate_item_id`. If you configure names for the items, they are used as values for the item given as `as_laststate_item_name`. (otherwise the item id is used here, too)

Every state can have an arbitrary number of "enter" and "leave" condition sets. An state can become current if one of the "enter" condition sets is fulfilled. Once the state is current and has "leave" condition sets, it can only be left if one of the "leave" condition sets is fulfilled. Inside every condition set an arbitrary number of conditions can be defined. If a state does not have any condition sets, the state can always be entered/left. This can be used to have a default state.

Every state can have an arbitray number of "actions" defined. Once the state becomes current, all actions are performed. If an state stays current in further checks, the actions are reperformed under several conditions. Actions are defined as attributes `as_set_(action_name)` or similar.

Conditions and actions usually relate to items. These items have to be defined in the object item as `as_item_(condition_name/action_name)`

####Example####

    [myFirstAutoBlindControlledObject]
        (...)
        as_item_height = room1.raffstore.height
        as_item_lamella = room1.raffstore.lamella
        [[day]]
            type = foo
            name = Day (static)
            as_use = some.default.item
            [[[enter]]]
                (...)
            [[[leave]]]
                (...)
            as_set_height = value:100
            as_set_lamella = value:0      

##Condition sets##
All subitems of the state item are considered as condition sets ("condition set item"). In general, there are two types of condition sets:
- **Enter condition sets**: Condition sets that are checked if the current state is calculated.
- **Leave condition sets**: Condition sets that are checked in order to determine if a state can be left.

Whether a subitem is an enter or a leave condition set is determined by the id of the subitem. If the id is "enter" or starts with "enter_", it is an enter condition set. The id of a leave condition set is always "leave" or starts with "leave_".

The following rules apply:
- A single condition set is fulfilled if each condition defined in the condition set is being matched ("AND"). Possible limits that are not defined in this condition are not checked.
- A state can be left if any of the defined leave condition sets is fulfilled ("OR"). Checking stops at the first fulfilled condition set.
- A state can be entered if any of the defined enter condition sets is fulfilled ("OR"). Checking stops at the first filfilled condition set.
- A state that does not have condition sets can always be entered and left. You can define such a state as last state in the list to have a default state

####Example####
    
    [myFirstAutoBlindControlledObject]
        (...)
        as_item_height = room1.raffstore.height
        as_item_lamella = room1.raffstore.lamella
        [[night]]
            type = foo
            name = Night                
            as_use = some.default.item
            [[[enter_todark]]]
                (... some conditions to enter this state if it is to dark ...)
            [[enter_tolate]]]
                (... some conditions to enter this state if it is to late ...)
            [[[leave]]]
                (...)
            as_set_height = value:100
            as_set_lamella = value:0


Object | Function
------ | --------
Attributes `as_item_height`, `as_item_lamella` | Items wich are changed by actions `as_set_height` and `as_set_lamella`
Attribute `name` | Name of state. Will be written in item `as_laststate_item_name` if state is current and can be displayed in visualization
Attribute `as_use` | Import settings from a different item. If the current item also contains enter/leave condition sets, these settings change/append the imported settings   
Child items  `enter` or `enter_(some name)` | Condition sets of which one has to be fulfilled before the state can become current
Child items `leave` or `leave_(some_name)` | Condition sets of which one has to be fulfilled before the state can be left
Attributes `as_set_height`and `as_set_leave` | New static values for `as_item_height` and `as_item_leave` 

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
minimum | as_min_(condition name) | The condition is fulfilled if the current value is greater than the given minimum
maximum | as_max_(condition name) | The condition is fulfilled if the current value is lower than the given maximum
distinct value | as_value_(condition name) | The condition is fulfilled if the current value is equal the given value
negate | as_negate_(condition name) | The value condition is negated
minimum age | as_agemin_(condition_name) | The condition is fulflled if the age of the item used to retrieve the value is greater than the given minimum
maximum age | as_agemax_(condition_name) | The condition is fulflled if the age of the item used to retrieve the value is lower than the given maximum
negate age | as_agenegate_(condition_name) | The age condition is negated

The current value can either be provided by an item or by an eval function. If both are given, the item is used and eval is ignored.
The name of the item or the eval function are set by specific attributes `as_item_(condition name)` or `as_eval_(condition name)` in the object item. Their name has also to correspond with the condition name. Obviously, age related conditions (`as_agemin_(condition name)`, `as_agemax_(condition name)`, `as_agenegate_(condition_name)`) can only be used when the value is provided by an item.

For `as_min_(condition name)`, `as_max_(condition name)` and `as_value_(condition name)` value to check against can either be a static value, or provided from an item, too.
To use a static value, just set the condition to `(some value)` or `value:(some value)` To use an item, set the condition to `item:(item id)`:

####Example####

    [myFirstAutoBlindControlledObject]
            (...)
            as_item_height = room1.raffstore.height
            as_item_lamella = room1.raffstore.lamella
            as_item_brightness = my.wetherstation.brightness
            [[twilight]]
                type = foo
                name = Twilight                
                as_use = some.default.item
                as_set_height = value:100
                as_set_lamella = value:25
                [[[enter]]]                    
                    as_min_brightness = 500
                    as_max_brightness = value:1000
                
            [[night]]
                type = foo
                name = Night                
                as_use = some.default.item
                as_set_height = value:100
                as_set_lamella = value:0
                [[[enter_todark]]]
                    as_max_brightness = 500
                
            [[special]]
                type = foo
                name = Some special condition set
                as_use = some.default.item
                as_set_height = value:66
                as_set_lamella = value:33
                [[[enter]]]
                    as_min_brightness = item:an.item.returning.the.value
                          
                          
###"Special" conditions###
For some conditions you do not need to set an item or eval-function to determine the current value. The plugin will do this for you if you use some predefined condition names. These condition names should therefore not be used for your other conditions.

The following "special" condition names can be used:

**time:** Current time.
Values for `as_value_time`, `as_min_time` and `as_max_time` need to be given in format "hh:mm". 24h time is being used. Examples: "08:00" or "13:37". To mark the end of the day, the value "24:00" can be used, which is automatically converted to "23:59:59" for the checks.

**weekday:**
Day of week as number. 0 represents Monday, 6 represents Sunday

**month:**
Month as number. 1 represents January, 12 represents December

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

The age is being calculated via the last change of the item given with attribute `as_laststate_item_id`.

**delay:**
Time since enter conditions of state are not matched (seconds)

**random:**
Radom number between 0 and 100

If you want to do something randomly with a propability of 60%, e.g. use condition `max_random = 60` 

##Actions##
Like conditions, every action requires a name, too. The action name is again arbitrary and just used in the attribute naming. The names of all attributes belonging to one action follow the same pattern `as_(function name)_(action name)`

Currently there are three types of actions that can be performed:
* An item can be set to a value
* A function can be run
* A logic can be triggered

###Setting an item to value###
The item to be changed has to be defined as attribute in the object item named `as_item_(action name)`.
The value for the item has to be defined as attribute in the state item named `as_set_(action name)`.

The value can either be a static value, the result of executing a function or the current value of another item. A prefix in the attribute value defines which one is being used.

attibute value | function
-------------- | ---------
value:(static value) | use the given static value
eval:(function name) | execute the given function and use the result returned by the function as value
item:(item id) | Use the current value of the given item as value

####Using a delta to prevent small changes####
It is possible to define a minimum delta for changes. If the difference between the current value of an item and the new value is less than the configured delta, no change will be made. This can be done with attribute `as_mindelta_(action name)` in the object item

###Running a function###
A function to run van be defined as attribute in the state item named `as_run_(actionname)`. This is similar to execute a function to get the value for an item, but it does not need an item and just ignores any return value of the function.

    as_run_(action name) = eval:(function)

###Predefined action functions###
The AutoBlind plugin provides a set of predefined functions that can easily be used for actions. These functions are contained in a class which is instanciated just before executing an action if required. The following functions can be used:

####Calculate lamella angle for sun tracking####
 
    as_set_(action name) = eval:autoblind_eval.sun_tracking()
    
####Random integer value####
    
    as_set_(action name) = eval:autoblind_eval.get_random_int(min,max)
    
Set `min` and `max` to the minimum/maximum value of the number you want to receive. You can omit min and max, the defaults are 0 for min and 255 for max.

####Run a shell command####

    as_set_(action name) = eval:autoblind_eval.execute(command)
    
Run shell command `command`

###Trigger logics###
Instead of setting an item to an value it is also possible to trigger a logic. To do so, the logic to trigger has to be named using the attribute `as_trigger_(some name)`.
You can add a value that should be sent to the logic by adding  `:(value)` after the logic name in the attribute value

###Example###

    [myFirstAutoBlindControlledObject]
            (...)
            as_item_height = room1.raffstore.height
            as_mindelta_height = 10
            as_item_lamella = room1.raffstore.lamella
            as_mindelta_lamella = 5
            [[twilight]]
                (...)
                as_set_height = value:100
                as_set_lamella = value:25
            [[night]]
                (...)
                as_set_height = value:100
                as_set_lamella = value:0
            [[suntracking]]
                (...)
                as_set_height = value:100
                as_set_lamella = eval:autoblind_eval.sun_tracking()
            [[logic]]
                (...)
                as_trigger_logic1 = myLogic:42

##Using default values##
It is possible to define some default states inside the configuration and use them later for distinct object states. It is also possible to overwrite settings from the used default state.
When defining the default states inside a parent item, do not mark this parent item with `as_plugin = active` as it does not contain a complete object configuration.

####Example####
                
    [autoblind]
        [[default]]
            (...)
            [[[night]]]
                (...)
                [[[[enter]]]]
                    (...)
                as_set_height = value:100
                as_set_lamella = 0
            [[[dawn]]]
                (...)
                [[[[enter]]]]
                    (...)
                as_set_height = value:100
                as_set_lamella = 25
                
            [[[dusk]]]
                (...)
                [[[[enter]]]]
                    (...)
                as_set_height = value:100
                as_set_lamella = 75
                    
            [[[day]]]
                (...)
                [[[[enter]]]]
                    (...)
                as_set_height = value:0
                as_set_lamella = 100
                                 
    [myFirstAutoBlindControlledObject]
            (...)
            as_item_height = room1.raffstore.height
            as_item_lamella = room1.raffstore.lamella
            [[night]]
                as_use = autoblind.default.night
                [[[enter_additional]]]
                    (... additional enter condition set ...)
            [[dawn]]
                as_use = autoblind.default.dawn
            [[dusk]]
                as_use = autoblind.default.dusk
                [[[enter]]]
                    (... changes on default enter condition ...)
            [[suntracking]]
                (...)
                as_set_height = value:100
                as_set_lamella = eval:autoblind_eval.SunTracking()
            [[day]]
                as_use = autoblind.default.day
            
As you can see here, the items and the values for actions can be defined at different places. Here the items are defined in the object item while the values are defined at the default items. The same can be done for conditions.
    
#Full example#

First, we are defining some default states:

    [autoblind]
        [[default]]            
            as_item_temperature = weatherstation.temperature
            [[[night]]]
                name = Night
                as_set_height = value:100
                as_set_lamella = 0
                [[[[enter]]]]
                    as_max_brightness = 500
                    as_min_time = 09:00
                    as_max_time = 19:00
                    as_negate_time = True
            [[[dawn]]]
                name = "Twilight in the morning"
                as_set_height = value:100
                as_set_lamella = 25          
                [[[[enter]]]]
                    as_min_brightness = 500
                    as_max_brightness = 1000      
            [[[dusk]]]
                name = "Twilight in the evening"
                as_set_height = value:100
                as_set_lamella = 75
                [[[[enter]]]]
                    as_min_brightness = 500
                    as_max_brightness = 1000
            [[[suntrack]]]
                name =  "Day (suntracking)"
                [[[[enter]]]]
                    as_min_brightness = 50000
                    as_min_sun_azimut = 140
                    as_max_sun_azimut = 220
                    as_min_sun_altitude = 20
                    as_min_temperature = 25
                 [[[[leave_todark]]]]
                    as_max_brightness = 30000
                    as_min_delay = 1200
                 [[[[leave_azimut]]]
                    as_min_sun_azimut = 140
                    as_max_sun_azimut = 220
                    as_negate_sun_azimut = True                 
            [[[day]]]
                name = "Day (static)"
                as_set_height = value:0
                as_set_lamella = 100
                             
__Remarks:__
- Notice that there is no attribute `as_plugin` for these items. 
- The item to determine the temperature is configured in the default states. You can use conditions for this item in the defaults and in the specific state items which import default states.
- The item to determine the brightness is not configured in the default states. You need to make sure that every specific object that imports the default states has a definition for the brightness item. However, different objects can import the same default states but use different items for the brightness.
- Condition item "autoblind.default.night.enter": Time is negated, in this case the state can be entered between 19:00 and 09:00 o'clock if brightness is less than 500.
- State item "autoblind.default.suntrack" has two leave conditions. "leave_todark" is fulfilled if brightness is to low for at least 1200 seconds. "leave_azimut" is fulfilled if the sun position is out of range.                                 
                                 
                                 
Then we need the items for the blind we want to automate:

    [room1]
        [[raffstore]]
            name = Raffstore Room 1
            [[[auto_lock]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/7
                knx_status = 1/1/8
                knx_listen = 1/1/7 | 1/0/7
                visu_acl = rw
                cache = on
            [[[auto_suspend]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/9
                visu_acl = r  
            [[[auto_laststate_id]]]
                type = str
                visu_acl = r
                cache = on
            [[[auto_laststate_name]]]
                type = str
                visu_acl = r
                cache = on
            [[[updown]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/1
                visu_acl = rw
                enforce_updates = on
            [[[stepstop]]]
                type = bool
                knx_dpt = 1
                knx_send = 1/1/2
                visu_acl = rw
                enforce_updates = on
            [[[height]]]
                type = num
                knx_dpt = 5.001
                knx_send = 1/1/3
                knx_init = 1/1/4
                visu_acl = rw
                cache = on
            [[[lamella]]]
                type = num
			    knx_dpt = 5.001
			    knx_send = 1/1/5
			    knx_init = 1/1/6
			    visu_acl = rw
			    cache = on
			
Now we can add our specific AutoBlind object item with all required subitems to controll this blind.            
            
    [myFirstAutoBlindControlledObject]
        type = bool
        name = Some very nice example
        as_plugin = active
        cycle = 300
        as_lock_item = room1.raffstore.auto_lock
        as_suspend_item = room1.raffstore.auto_suspend
        as_suspend_time = 7200
        as_suspend_watch = room1.raffstore.updown | room1.raffstore.stepstop
        as_laststate_item_id = room1.raffstore.auto_laststate_id
        as_laststate_item_name = room1.raffstore.auto_laststate_name        
        as_item_height = room1.raffstore.height
        as_item_lamella = room1.raffstore.lamella
        as_item_presence = room1.presence
        as_item_brightness = weatherstation.brightness
        [[night]]
            as_use = autoblind.default.night
            [[[enter_presence]]]
                as_max_brightness = 750
                as_min_time = 09:00
                as_max_time = 19:00
                as_negate_time = True
                as_value_presence = True
            [[[[enter]]]]
                as_value_presence = False
                                        
        [[dawn]]
            as_use = autoblind.default.dawn
        [[dusk]]
            as_use = autoblind.default.dusk            
        [[suntracking]]
            as_use = autoblind.default.suntracking
        [[day]]
            as_use = autoblind.default.day
            
__Remarks:__
- Notice that there is an attribute `as_plugin` for the object item 
- The state "night" is using the default configuration but changes are made:
    - The condition set "enter" is extended with an additional condition
    - An additional enter condition set "enter_presence" is added
- In this example, the plugin is triggered every 5 minutes (300 seconds). Instead of `cycle` you can also use `crontab` or `eval_trigger` to trigger the plugin.
    