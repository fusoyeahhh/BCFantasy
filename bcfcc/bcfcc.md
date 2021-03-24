# Beyond Chaos Fantasy / Crowd Control
[image]


Some commands can only be acted on once in/out of battle. If the required state isn't available, but may be soon, the command will be queued until such time as it is ready to fire.Available commands and usage is below.
## Command List
### activate_golem

`!cc activate_golem`

Activates the "Earth Wall" effect for the duration of the battle. Default HP reservoir is 1000.

Precondition: in battle

Costs: 250
### add_gp

`!cc add_gp`

Add 1000 GP to total.

Precondition: None

Costs: 100
### fallen_one

`!cc fallen_one`

Immediately drop all party members HP to one.

Precondition: must be in battle

Costs: 1000
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

Costs: 300
### give_rare_relic

`!cc give_random_relic`

Add a random rare relic from the following list into the inventory:
`offering`, `meritaward`, `economizer`, `gembox`,
`marvelshoes`, `exp.egg`, `mooglecharm`, `podbracelet`, `genjiglove`


Precondition: None

Costs: 200
### give_restorative

`!cc give_restorative [name]`

Add one of specified restorative item.
Allowed items: `tonic`, `potion`, `tincture`, `ether`, `x-potion`, `elixir`, `megalixir`

Precondition: Item name must be valid and in the permitted list

Costs: {'elixir': 150, 'ether': 50, 'fenix_down': 100, 'megalixir': 200, 'potion': 50, 'tincture': 25, 'tonic': 25, 'x-ether': 100, 'x-potion': 100}
### life_1

`!cc life_1 [slot #: 1-4]`

Life-like effect, remove wounded status and restore some HP to selected slot.

Precondition: must be in battle, target must be valid and dead

Costs: 100
### life_2

`!cc life_2 [slot #: 1-4]`

Life2-like effect, remove wounded status and restore all HP to selected slot.

Precondition: must be in battle, target must be valid and dead

Costs: 250
### life_3

`!cc life_3 [slot #: 1-4]`

Life3-like effect, adds life3 status to selected slot.

Precondition: must be in battle, target must be valid

Costs: 500
### moogle_charm

`!cc moogle_charm`

Prevent encounters for a certain amount of time (default 30 seconds)

Precondition: None

Costs: 500
### nullify_element

`!cc nullify_element [element]`

Toggle a ForceField like effect (nullification) of the specified element.

Valid elements: `fire`, `ice`, `lightning`, `poison`, `wind`, `pearl`, `earth`, `water`

Precondition: in battle

Costs: 100
### power_overwhelming

`!cc power_overwhelming [slot #: 1-4]`

Make the specified slot very strong for this battle.

Precondition: must be in battle and target valid slot

Costs: 500
### random_relic_effect

`!cc random_relic_effect`

Apply a random relic effect from a preselected list for a given duration, default is 30 seconds.

Precondition: must not be in battle

Costs: 100
### random_status

`!cc random_status [slot #: 1-4]`

Apply a random status from a preselected list to selected slot.

Precondition: must be in battle, target must be valid and not dead

Costs: 200
### remedy

`!cc remedy [slot #: 1-4]`

Remedy-like effect, remove all "negative" statuses (except wounded) from selected slot.

Precondition: must be in battle, target must be valid and not dead

Costs: 100
### remove_gp

`!cc remove_gp`

Take 1000 GP from total.

Precondition: None

Costs: 200
### bs1a

`!cc bs1a`

Sets battle speed to maximum and turns on active ATB.

Precondition: None

Costs: 200
### set_name

`!cc set_name [name] [actor: 1-14]`

Set the name of the given *actor* index, e.g. Terra = 1.
Note that the name will be truncated to 6 characters, and some special characters are not yet supported.

Actor indices are: `Terra`, `Locke`, `Cyan`, `Shadow`, `Edgar`, `Sabin`, `Celes`,
`Strago`, `Relm`, `Setzer`, `Mog`, `Gau`, `Gogo`, `Umaro`

Precondition: None

Costs: 50
### pick_fight

`!cc pick_fight`

Max out threat counter to trigger battle. Note that this command is pre-empted by moogle_charm
but will fire after that effect has expired. Will not work in areas where threat counter is
disabled, (e.g. most towns, event maps)

Precondition: must not be in battle

Costs: 100
