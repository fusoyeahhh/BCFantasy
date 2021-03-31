# Beyond Chaos Fantasy / Crowd Control
[image]


Use !register to get started with 1000 points. You will also get 10 points for every one minute that you are registered. Some commands can only be acted on once in/out of battle. If the required state isn't available, but may be soon, the command will be queued until such time as it is ready to fire.Available commands and usage is below.
## Command List
### activate_golem

`!cc activate_golem`

Activates the "Earth Wall" effect for the duration of the battle. Default HP reservoir is 1000.

Precondition: in battle

Costs: 125
### add_gp

`!cc add_gp`

Add 1000 GP to total.

Precondition: None

Costs: 50
### cant_run

`!cc cant_run`

Prevent player from running from current battle.

Precondition: must be in battle

Costs: 100
### fallen_one

`!cc fallen_one`

Immediately drop all party members HP to one.

Precondition: must be in battle

Costs: 500
### give_rare_equip

`!cc give_rare_equip`

Add a random rare equip from the following list into the inventory:
`genjiarmor`, `behemothsuit`, `dragonhorn`, `assassin`, `punisher`, `risingsun`, `drainer`, `hardened`,
`soulsabre`, `rainbowbrsh`, `tabbysuit`, `chocobosuit`, `mooglesuit`, `aura`, `redjacket`, `ogrenix`,
`doomdarts`, `thiefknife`, `dragonclaw`, `striker`, `pearllance`, `wingedge`, `strato`, `healrod`, `graedus`,
`scimitar`, `tigerfangs`, `stunner`, `auralance`, `genjishld`, `atmaweapon`, `cathood`, `skyrender`, `excalibur`,
`flameshld`, `iceshld`, `snowmuffler`, `tortoiseshld`, `magusrod`, `thundershld`, `forcearmor`, `fixeddice`,
`aegisshld`, `minerva`, `cursedshld`, `ragnarok`, `forceshld`, `valiantknife`, `illumina`, `paladinshld`

Precondition: None

Costs: 150
### give_rare_relic

`!cc give_random_relic`

Add a random rare relic from the following list into the inventory:
`offering`, `meritaward`, `economizer`, `gembox`,
`marvelshoes`, `exp.egg`, `mooglecharm`, `podbracelet`, `genjiglove`


Precondition: None

Costs: 100
### give_restorative

`!cc give_restorative [name]`

Add one of specified restorative item.
Allowed items: `tonic`, `potion`, `tincture`, `ether`, `x-potion`,
`elixir`, `megalixir`, `x-ether` , `remedy`, `revivify`, `fenixdown`

Precondition: Item name must be valid and in the permitted list

Costs: {'elixir': 75, 'ether': 25, 'fenixdown': 50, 'megalixir': 100, 'potion': 25, 'tincture': 12, 'tonic': 12, 'x-ether': 50, 'x-potion': 50, 'revivify': 25, 'remedy': 25}
### life_1

`!cc life_1 [slot #: 1-4]`

Life-like effect, remove wounded status and restore some HP to selected slot.

Precondition: must be in battle, target must be valid and dead

Costs: 50
### life_2

`!cc life_2 [slot #: 1-4]`

Life2-like effect, remove wounded status and restore all HP to selected slot.

Precondition: must be in battle, target must be valid and dead

Costs: 125
### life_3

`!cc life_3 [slot #: 1-4]`

Life3-like effect, adds life3 status to selected slot.

Precondition: must be in battle, target must be valid

Costs: 250
### moogle_charm

`!cc moogle_charm`

Prevent encounters for a certain amount of time (default 30 seconds)

Precondition: None

Costs: 250
### nullify_element

`!cc null_elem [element]`

Toggle a ForceField like effect (nullification) of the specified element.

Valid elements: `fire`, `ice`, `lightning`, `poison`, `wind`, `pearl`, `earth`, `water`

Precondition: in battle

Costs: 50
### power_overwhelming

`!cc power_overwhelming [slot #: 1-4]`

Make the specified slot very strong for this battle.

Precondition: must be in battle and target valid slot

Costs: 250
### power_underwhelming

`!cc power_underwhelming [slot #: 1-4]`

Make the specified slot very weak for this battle.

Precondition: must be in battle and target valid slot

Costs: 250
### random_status

`!cc random_status [slot #: 1-4]`

Apply a random status from a preselected list to selected slot.
The game does enforce relic immunities which may invalidate this.

Precondition: must be in battle, target must be valid and not dead

Costs: 100
### remedy

`!cc remedy [slot #: 1-4]`

Remedy-like effect, remove all "negative" statuses (except wounded) from selected slot.

Precondition: must be in battle, target must be valid and not dead

Costs: 50
### remove_gp

`!cc remove_gp`

Take 1000 GP from total.

Precondition: None

Costs: 100
### bs1a

`!cc bs1a`

Sets battle speed to maximum and turns on active ATB.

Precondition: None

Costs: 100
### set_name

`!cc set_name [name] [actor: 1-14]`

Set the name of the given *actor* index, e.g. Terra = 1.
Note that the name will be truncated to 6 characters, and some special characters are not yet supported.

Actor indices are: 1 `Terra`, 2 `Locke`, 3 `Cyan`, 4 `Shadow`, 5 `Edgar`, 6 `Sabin`,
7 `Celes`, 8 `Strago`, 9 `Relm`, 10 `Setzer`, 11 `Mog`, 12 `Gau`,
13 `Gogo`, 14 `Umaro`

Precondition: None

Costs: 25
### pick_fight

`!cc pick_fight`

Max out threat counter to trigger battle. Note that this command is pre-empted by moogle_charm
but will fire after that effect has expired. Will not work in areas where threat counter is
disabled, (e.g. most towns, event maps)

Precondition: must not be in battle

Costs: 50
