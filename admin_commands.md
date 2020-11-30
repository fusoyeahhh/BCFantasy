## `nextarea`

implemented in `nextarea`


    !nextarea -> no arguments, cycle to the next area in the sequence defined by the area table.
    
## `nextboss`

implemented in `nextboss`


    !nextboss -> no arguments, cycle to the next boss in the sequence defined by the boss table.
    
## `set`

implemented in `_set`


    !set [boss|area]=value

    Manually set a context category to a value.
    
## `give`

implemented in `give`


    !give --> [list of people to give to] [amt]
    
## `event`


implemented in `event`


    !event eventtype [arguments] -- Manually trigger an event

    valid eventtypes: bchardeath, enemykill, cantrun, backattack, chardeath, miab, debuff, gameover, bosskill, buff   

## `stop`

implemented in `stop`


    !stop [|annihilated|kefkadown] Tell the bot to save its contents, possibly for a reason (game over, Kefka beaten).

    Will set the bot to 'paused' state.
    
## `pause`

implemented in `pause`


    !pause -> no argument, toggle pause for processing of log. Automatically invoked by !reset and !stop
    
## `reset`

implemented in `reset`


    !reset -> no arguments; reset all contextual and user stores