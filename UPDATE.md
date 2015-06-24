#Required changes#

Due to some breaking changes, you need to update your configuration for the AutoBlind Plugin
This document lists all configuration changes that are required

##Indentifying items which contain AutoBlind configuration##
###Previous configuration###
In the past, the AutoBlind-Plugin was searching for an item "AutoBlind" having a child item "active". If such a combination was found, the item was parsed for AutoBlind configuration.

###New condfiguration###
Any item can contain the AutoBlind configuration. To indicate that a certain item contains AutoBlind configuration data, add the attribute 

    autoblind_plugin = active

to your item. Such an item will be called "object item" from now on.
You max set the value to something else than "active" to ignore the item e.g. for debugging purposes.
Nevertheless an object item still requires to have the subitems "active", "lastpos_id" and "lastpos_name". Any other subitem of the object item is taken as position

###Further planning###
No further changes in this area are planed currently.

##Defining positions##
###Previous configuration###
In the past general subitem names for "height" and "lamella" had to be defined in the plugin configuration. The item containing the "AutoBlind"-item had to have subitems with the configured names. Each position-item had a attribute "position" whose values where used for heigth and position.

###New configuration###
The position-attribute and the general subitem names for "height" and "lamella" are obsolete. Instead it is possible to define "actions" that are executed once a position becomes active. An "action" means currently that an item is set to a value. There are different ways to determine the value for the item:
- value: The item is set to a static value
- eval: A function is called which returns the new value for the item
- item: The new value for the item is taken from the current value of another item

An action is defined in the position-item with the attribute

    set_[action_name] = value:[static value]
    
or

    set_[action_name] = eval:[function to evaluate]
    
or

    set_[action_name] = item:[id of item to take value from]
    
In every case the if of the item that should be changed with the action needs to be defined as attribute of the parent item of the position item:

    item_[action_name] = [id of item to change]
    
A simple exampe where a position is being replaced:
__Old configuration:__

    (...)
    [[AutoBlind]]
        [[[active]]]
            (...)
        [[[lastpos_id]]]
            (...)
        [[[lastpos_name]]]
            (...)
        [[[Position1]]]
            [[[[enter]]]]
                (...)            
            [[[[leave]]]]
                (...)
            position = 100,25
__New configuration:__

    (...)
    [[some_name]]
        item_height = the.height.item.for.this.object
        item_lamella = the.lamella.item.for.this.object
        [[[active]]]
            (...)
        [[[lastpos_id]]]
            (...)
        [[[lastpos_name]]]
            (...)
        [[[Position1]]]
            [[[[enter]]]]
                (...)            
            [[[[leave]]]]
                (...)
            set_height = value: 100
            set_lamella = value:25
 These changes also allow you to have your configuration completely separate from the items they relate to. You could e.g. have a separate configuration file for all your blind. Also, the plugin can easier be used if you have shutters only or for other things like ventilation systems
 
###Further planning###
- The plugin should deliver some standard functions that can be used with "eval:" (e.g. track the sun)
- It should be possible to trigger logics, too 
 