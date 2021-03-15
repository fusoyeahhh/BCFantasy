# Beyond Chaos Fantasy / Crowd Control
[image]


Use `!cc help` to get the current list of available commands. Some commands can only be acted on once in/out of battle. If the required state isn't available, but may be soon, the command will be queued until such time as it is ready to fire.Available commands and usage is below.
## Command List
### activate_golem

`!cc activate_golem`

Activates the "Earth Wall" effect for the duration of the battle. Default HP reservoir is 1000.

Precondition: in battle

### add_gp

`!cc add_gp`

Add 1000 GP to total.

Precondition: None

### cant_run

`!cc moogle_charm`

Prevent encounters for a certain amount of time (default 30 seconds)

Precondition: None

### fallen_one

`!cc fallen_one`

Immediately drop all party members HP to one.

Precondition: must be in battle

### give_item

`!cc give_item [id] [qty]`

__Admin Only__ Give qty of an inventory item specified by id.

Precondition: Item id and qty must be valid

### give_rare_equip

`!cc give_restorative [name]`

__Admin Only__ Add one of specified restorative item.

Precondition: None

### give_rare_relic

`!cc give_restorative [name]`

__Admin Only__ Add one of specified restorative item.

Precondition: None

### give_restorative

`!cc give_restorative [name]`

__Admin Only__ Add one of specified restorative item.

Precondition: Item name must be valid and in the permitted list

### life_1

`!cc life_1 [slot #]`

Life-like effect, remove wounded status and restore some HP.

Precondition: must be in battle, target must be valid and dead

### life_2

`!cc life_2 [slot #]`

Life2-like effect, remove wounded status and restore all HP.

Precondition: must be in battle, target must be valid and dead

### life3

`!cc life_3 [slot #]`

Life3-like effect, adds life3 status to target.

Precondition: must be in battle, target must be valid

### mirror_buttons

`!cc mirror_buttons`

"Inverts" all button pairs for an amount of time, default 10 seconds.

Precondition: None

### moogle_charm

`!cc moogle_charm`

Prevent encounters for a certain amount of time (default 30 seconds)

Precondition: None

### nullify_element

`!cc nullify_element [element]`

Toggle a ForceField like effect (nullification) of the specified element.

Precondition: in battle

### power_overwhelming

`!cc power_overwhelming [slot #]`

Make the specified slot very strong for this battle

Precondition: must be in battle and target valid slot

### random_relic_effect

`!cc random_relic_effect`

Apply a random relic effect from a preselected list for a given duration, default is 30 seconds.

Precondition: must not be in battle

### random_status

`!cc random_status [slot #]`

Apply a random status from a preselected list

Precondition: must be in battle, target must be valid and not dead

### remedy

`!cc remedy [slot #]`

Remedy-like effect, remove all "negative" statuses (except wounded).

Precondition: must be in battle, target must be valid and not dead

### bs1a

`!cc bs1a`

Sets battle speed to maximum and turns on active ATB.

Precondition: None

### set_name

`!cc set_name [name] [actor]`


Precondition: None

### set_relic_effect

`!cc set_relic_effect`

Toggle the selected relic effect.

Precondition: must not be in battle

### set_stat

`!cc set_stat [stat] [value] [slot #]`

__Admin Only__ Change the specified stat for the specified slot

Precondition: None

### set_status

`!cc set_status [slot #]`

__Admin Only__ Apply any status to the specified slot

Precondition: None

### pick_fight

`!cc pick_fight`

Max out threat counter to trigger battle.

Precondition: must not be in battle

### write_arbitrary

