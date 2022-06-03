# Data.py
# This file holds all the constant sets and dicts of data used in the game.
# This file is a dependency of Core.py

# It consists of four main parts;
# 1. Useful strings			(Useful strings of data primarily used in Parser.py)
# 2. Useful sets			(Sets of strings primarily used in Parser.py)
# 3. Game term dictionary	(Game terms used by Define() in Parse.py)
# 4. Intro Logo Data		(Strings and lists used for the intro animation)




####################
## USEFUL STRINGS ##
####################

menuinstructions = "\nType 'info' for information on how to play\nType 'new' to start a new game\nType 'load' to load a save file\nType 'delete' to delete a save file\nType 'quit' to quit the game\n"

gameinfo = "="*70 + "\n\nPotions & Pythons\nv.Alpha\nBy Carter Peene, 2022\n\n" + "-"*70 + "\n\nTo play, type a command of the form:\n[verb] [*noun] [*preposition] [*noun]\nOR\n[verb] [*preposition] [*noun]\n\n* denotes a term that can be omitted when unnecessary\nArticles, determiners, and most symbols are removed from your input\n\n" + "-"*70 + "\n\nDuring the game:\nGet a list of valid commands by typing 'help'\nGet a list of command examples by typing 'examples'\nSee your main player statistics by typing 'stats' and 'traits'\nSee a description of your current location by typing 'here'\nLearn about most game terms and commands by typing 'define [term]'\n\n" + "="*70

examples = "\nValid input examples include:\n- go\n- go north\n- go nw\n- go up the stairs\n- go back\n- go to tunnel\n- look at python\n- i will fight the python!\n- hit the python with my sword\n- attack python sword\n- equip a sword\n- unequip sword\n- take red potion\n- take the red potion from the chest\n- put red potion in the chest\n- put red potion chest\n- drop the red potion\n- close chest"

symbols = ".,!?~`\"()[]{}<>+=/*&^%$#@\t"

numsymbols = "-0123456789"

vowels = "aeiouAEIOU"

physicaldmg = "bps"
elementaldmg = "acfltx"
magicaldmg = "inrv"




#################
## USEFUL SETS ##
#################

articles = {"a","an","her","his","i","its","my","that","the","their","this","will"}

cancels = {"cancel","done","end","nevermind","no","undo"}

yesses = {"absolutely","affirmative","aye","certainly","definitely","indeed","ja","ok","okay","oui","si","sure","surely","y","ya","yaa","yaaa","yaaaa","ye","yea","yeah","yes","yess","yesss","yup"}

noes = {"absolutely not","certainly not","definitely not","n","na","nah","nahh","nahhh","nay","negative","negatory","nein","no","noo","nooo","noooo","nope"}

# note that "u" and "d" are included here as abbreviations of "up" and "down"
# this is because "up" and "down" are also in the "directions" dict
# they are not necessary entries here, but make interpreting more consistent...
# for use in the Go() action functions
prepositions = {"above","across","at","behind","below","beneath","by","d","down","for","from","in","inside","into","near","off","on","onto","out","over","through","to","toward","under","u","up","upon","using","with"}

pronouns = {"she","he","they","her","him","them","it"}

# TODO: words which will be split into two meaningful words
# make this a dict?
compounds = {"downstairs"}

# used in nounify() in Parser.py to combine multiple words that might have a single meaning as a whole term
miscexpressions = {"it all","spell list"}

directions = {"n":"north","ne":"northeast","e":"east","se":"southeast","s":"south","sw":"southwest","w":"west","nw":"northwest","u":"up","d":"down","into":"in","o":"out","b":"beyond"}

dmgtypes = {"a":"acid","b":"bludgeoning","c":"cold","e":"essential","f":"fire","i":"psychic","l":"lightning","n":"necrotic","p":"piercing","r":"radiant","s":"slashing","t":"thunder","v":"force","x":"poison"}

# gear dict used to initialize the player object
initgear = {"head":-1, "body":-1, "left":-1, "right":-1, "legs":-1}

# action verbs which should not take any in-game time to execute
instantactions = {"describe","define","gear","help","hp","info","information","inventory","inv","level","lv","money","mp","quit","room","rp","save","status","time","traits","xp"}


# the following are tuples because their order should be preserved for printing


# base Creature stats
traits = ("STR","SKL","SPD","STM","CON","CHA","INT","WIS","FTH","LCK")

# derived creature stats. they can be found as Creature methods
abilities = ("ACCU","ATCK","ATHL","ATSP","BRDN","CAST","CRIT","CSSP","DCPT","DFNS","ENDR","EVSN","INVS","KNWL","LOOT","MVMT","MXHP","MXMP","PRSD","RESC","RITL","SLTH","SPLS","TNKR")

# verb commands which may only be entered as single, lonesome words
shortverbs = ("back","clear","cry","dance","examples","hi","hello","help","here","info","information","laugh","quit","return","save","scream","shout","sing","time","yawn","yell")

# commands which just serve to print stats to the player
statcommands = ("abilities","accu","atck","athl","atsp","brdn","cast","crit","cssp","dcpt","dfns","endr","evsn","gear","hp","inventory","inv","invs","knwl","level","loot","lv","money","mp","mvmt","mxhp","mxmp","prsd","resc","ritl","rp","slth","spls","stats","status","tnkr","traits","weapons","xp")

# all valid verbs which are not a shortverb or a statcommand
verbs = ("attack","bite","break","build","carry","cast","catch","climb","close","craft","crawl","create","cross","crouch","cut","dash","define","describe","do","dodge","doff","don","drink","drop","duck","dump","eat","enter","equip","escape","examine","exit","feed","feel","fight","fill","find","fish","follow","fuck","get","give","go","grab","grapple","head","hear","hide","hit","ignite","insert","jump","kick","kill","lay","leave","lick","light","listen","lock","look","make","mount","move","obtain","open","pet","pick","pick up","place","play","point","pour","pray","pull","punch","push","put","put down","put on","quaff","read","release","remove","rest","restrain","return","ride","ring","rub","run","search","set","set down","shove","shut","slap","sleep","slice","smell","sneak","sniff","speak","steal","stomp","stow","strike","struggle","swim","take","take off","talk","taste","throw","tie","tinker","toss","touch","travel","trip","unequip","unlock","untie","use","view","wait","walk","wave","wear")
# trade/buy/sell, speak,say/greet/converse, brew/cook, clean/sweep/mop, dig, leap, blow/breath, clap, scratch, spit, stand, dive, lift, observe, think, write, laydown/sitdown, fuck, shit on




##########################
## GAME TERM DICTIONARY ##
##########################

# Library of game terms to help players, used by the Define() verb in Parser.py
definitions = {
"abilities":"Abilities\n24 stats which dictate the chance to accomplish a goal, such as attacking, investigating, or persuading. The 24 abilities are ACCU, ATCK, ATHL, ATSP, BRDN, CAST, CRIT, CSSP, DCPT, DFNS, ENDR, EVSN, INVS, KNWL, LOOT, MVMT, MXHP, MXMP, PRSD, RESC, RITL, SLTH, SPLS, and TNKR. Type 'abilities' to view your abilities",

"ability":"Ability\nOne of 24 stats which dictate the chance to accomplish a goal, such as attacking, investigating, or persuading. The 24 abilities are ACCU, ATCK, ATHL, ATSP, BRDN, CAST, CRIT, CSSP, DCPT, DFNS, ENDR, EVSN, INVS, KNWL, LOOT, MVMT, MXHP, MXMP, PRSD, RESC, RITL, SLTH, SPLS, and TNKR. Type 'abilities' to view your abilities",

"accu":"Accuracy\nChance to hit against enemy EVSN. ACCU is determined primarily by SKL, and is also improved by LCK and Sleight. Type 'accu' to view your ACCU",

"accuracy":"Accuracy\nChance to hit against target EVSN. ACCU is determined primarily by SKL, and is also improved by LCK and Sleight. Type 'accu' to view your ACCU",

"animal":"Animal\nA Creature which can act passively or aggressively",

"animals":"Animals\nCreatures which can act passively or aggresively",

"armor":"Armor\nItems which can be equipped in a Creature's Gear. The Protection value of Armor increases the Creature's DFNS. Equipping Armor which is heavier than four times your CON will lower your CAST, CSSP, and MVMT",

"atck":"Attack\nRange of possible Damage that can be dealt to a target. ATCK is determined by STR and Might. Type 'atck' to view your ATCK",

"athl":"Athletics\nAbility to achieve physical actions such as running, jumping, and climbing. ATHL is improved by STR, SKL, and STM. Type 'athl' to view your ATHL",

"athletics":"Athletics\nAbility to achieve physical actions such as running, jumping, and climbing. ATHL is improved by STR, SKL, and STM. Type 'athl' to view your ATHL",

"atsp":"Attack Speed\nATSP determines the number of attacks against a target in one turn and if attacker or target hits first. Additionally, ATSP is the main factor in EVSN. ATSP is determined by SPD and can be reduced if the Items Equipped in player hands are too heavy. Type 'atsp' to view your ATSP",

"attack":"Attack\nRange of possible damage that can be dealt to a target. ATCK is determined by STR and might. Type 'atck' to view your ATCK",

"attack speed":"Attack Speed\nATSP determines the number of attacks against a target in one turn and if attacker or target hits first. Additionally, ATSP is the main factor in EVSN. ATSP is determined by SPD and can be reduced if the Items Equipped in player hands are too heavy. Type 'atsp' to view your ATSP",

"brdn":"Burden\nMaximum inventory weight without hindrance. Being Hindered reduces CSSP, MVMT and SLTH. BRDN is determined by CON and STR. Type 'brdn' to view your BRDN",

"burden":"Burden\nMaximum inventory weight without hindrance. Being Hindered reduces CSSP, MVMT and SLTH. BRDN is determined by CON and STR. Type 'brdn' to view your BRDN",

"cast":"Casting Bonus\nBonus added to various spells and magical effects in different ways. CAST is determined by WIS, FTH, and INT, and can be reduced if  Equipped Armor is too heavy. Type 'cast' to view your CAST",

"casting bonus":"Casting Bonus\nBonus added to various Spells and magical effects in different ways. CAST is determined by WIS, FTH, and INT, and can be reduced if the Equipped Armor is too heavy. Type 'cast' to view your CAST",

"casting speed":"Casting Speed\nSpeed that spells can be casted. CSSP is determined by WIS, and can be reduced if Equipped Armor is too heavy or if player is Hindered. Type 'cssp' to view your CSSP",

"cha":"Charisma\nTrait representing charm and panache. CHA contributes to DCPT and PRSD. Type 'cha' to view your CHA",

"charisma":"Charisma\nTrait representing charm and panache. CHA contributes to DCPT and PRSD. Type 'cha' to view your CHA",

"con":"Constitution\nTrait representing physical fortitude. CON contributes to BRDN, DFNS, ENDR, and MXHP. Type 'con' to view your CON",

"constitution":"Constitution\nTrait representing physical fortitude. CON contributes to BRDN, DFNS, ENDR, and MXHP. Type 'con' to view your CON",

"creature":"Creature\nAnything in the game that can be interacted with, that can also act on its own, unlike an Item. The main types of Creatures are People, Monsters, and Animals",

"crit":"Critical\nPercent chance that a hitting attack will deal twice the Damage. CRIT is deterimined primarily by SKL, and is also improved by LCK and Sharpness. Type 'crit' to view your CRIT",

"critical":"Critical\nPercent chance that a hitting attack will deal twice the Damage. CRIT is deterimined primarily by SKL, and is also improved by LCK and Sharpness. Type 'crit' to view your CRIT",

"cssp":"Casting Speed\nSpeed that spells can be casted. CSSP is determined by WIS, and can be reduced if Equipped Armor is too heavy or if player is Hindered. Type 'cssp' to view your CSSP",

"damage":"Damage\nAmount that target HP will be reduced from an attack. DFNS reduces incoming damage. Certain damage types deal double damage, half damage, or no damage if the target has Vulnerability, Invulnerability, or Immunity. The main categories of Damage are Physical Damage, Elemental Damage, and Magical Damage",

"dcpt":"Deception\nAbility to deceive creatures. DCPT is determined primarily by CHA, and is also improved by INT. Type 'dcpt' to view your DCPT",

"deception":"Deception\nAbility to deceive creatures. DCPT is determined primarily by CHA, and is also improved by INT. Type 'dcpt' to view your DCPT",

"defense":"Defense\nAmount that incoming Physical Damage is reduced. DFNS is determined by CON, and the Protection values of Armor and Shields. Type 'dfns' to view your DFNS",

"dfns":"Defense\nAmount that incoming Physical Damage is reduced. DFNS is determined by CON, and the Protection values of Armor and Shields. Type 'dfns' to view your DFNS",

"dmg":"Damage\nAmount that target HP will be reduced from an attack. DFNS reduces incoming damage. Certain damage types deal double damage, half damage, or no damage if the target has Vulnerability, Invulnerability, or Immunity. The main categories of Damage are Physical Damage, Elemental Damage, and Magical Damage",

"elemental damage":"Elemental Damage\nDamage types which are characterized by the power of the elements. The Elemental Damage types are Acid, Cold, Fire, Lightning, Thunder, and Poison",

"endr":"Endurance\nAbility to endure afflictions such as poison, pressure, breath-holding. ENDR is determined primarily by STM and is also improved by CON. Type 'endr' to view your ENDR",

"endurance":"Endurance\nAbility to endure afflictions such as poison, pressure, breath-holding. ENDR is determined primarily by STM and is also improved by CON. Type 'endr' to view your ENDR",

"evsn":"Evasion\nChance to not be hit by an attack. EVSN negates attacker ACCU. EVSN is determined primarily by ATSP, and is also improved by LCK. Type 'evsn' to view your EVSN",

"evasion":"Evasion\nChance to not be hit by an attack. EVSN negates attacker ACCU. EVSN is determined primarily by ATSP, and is also improved by LCK. Type 'evsn' to view your EVSN",

"faith":"Faith\nTrait representing divine conviction in the eyes of the gods. FTH contributes to CAST, LOOT, RITL, and RSNC. Type 'FTH' to view your FTH",

"fth":"Faith\nTrait representing divine conviction in the eyes of the gods. FTH contributes to CAST, LOOT, RITL, and RSNC. Type 'FTH' to view your FTH",

"gear":"Gear\nPlayer's Gear. Has slots for all the Equipped Items from the player Inventory. Type 'gear' to view your Gear",

"hindered":"Hindered\nA Status Condition which can arise from having too heavy an Inventory. Specifically, when your total Inventory weight exceeds your BRDN. Being Hindered lowers your CSSP, MVMT, and SLTH",

"hp":"Health Points\nPlayer health. HP can be replenished up to MaxHP (MXHP). Player dies if HP is reduced to 0. Type 'hp' to view your HP",

"immune":"Immunity\nStatus Conditions which confer Immunity to some Damage type. Creatures which are Immune to a Damage type take no Damage from attacks of the type",

"immunity":"Immunity\nStatus Conditions which confer Immunity to some Damage type. Creatures which are Immune to a Damage type take no Damage from attacks of the type",

"int":"Intelligence\nTrait representing memory and capability to solve problems. INT contributes to determining CAST, DCPT, INVS, KNWL, RITL, SLTH, SPLS, and TNKR. Type 'int' to view your INT",

"intelligence":"Intelligence\nTrait representing memory and capability to solve problems. INT contributes to determining CAST, DCPT, INVS, KNWL, RITL, SLTH, SPLS, and TNKR. Type 'int' to view your INT",

"inventory":"Inventory\nThe player Inventory. It can contain Items. If the weight of all Items in the player Inventory is greater than the player's BRDN, the player CSSP, MVMT, and SLTH will start to be penalized. Type 'inv' to view your inventory",

"investigation":"Investigation\nLikelihood to identify and perceive secrets and hidden things. INVS is determined primarily by INT, and is also improved by WIS. Type 'invs' to view your INVS",

"invs":"Investigation\nLikelihood to identify and perceive secrets and hidden things. INVS is determined primarily by INT, and is also improved by WIS. Type 'invs' to view your INVS",

"invulnerability":"Invulnerability\nStatus Conditions which confer Invulnerability to some Damage type. Creatures which are Invulnerable to a Damage type take half Damage from attacks of that type",

"invulnerable":"Invulnerability\nStatus Conditions which confer Invulnerability to some Damage type. Creatures which are Invulnerable to a Damage type take half Damage from attacks of that type",

"item":"Item\nAnything in the game that can be interacted with, but does not act on its own, unlike a Creature",

"knowledge":"Knowledge\nAbility and likelihood to know things. KNWL is determined primarily by INT, and is also determined by LCK. Type 'knwl' to view your KNWL",

"knwl":"Knowledge\nAbility and likelihood to know things. KNWL is determined primarily by INT, and is also determined by LCK. Type 'knwl' to view your KNWL",

"lck":"Luck\nTrait representing good fortune and coincidence. LCK contributes to ACCU, CRIT, EVSN, KNWL, and LOOT. Type 'lck' to view your LCK",

"luck":"Luck\nTrait representing good fortune and happy accidents. LCK contributes to ACCU, CRIT, EVSN, KNWL, and LOOT. Type 'lck' to view your LCK",

"level":"Level\nLevel is determined by XP. Player Level starts at 1. Player gains 3 QP upon Level-up. Type 'lv' to view your Level",

"loot":"Loot Rate\nRate and tier at which items and Pylars are dropped by creatures. LOOT is determined primarily by LCK, is also improved by FTH. Type 'loot' to view your LOOT",

"loot rate":"Loot Rate\nRate and tier at which items and Pylars are dropped by creatures. LOOT is determined primarily by LCK, is also improved by FTH. Type 'loot' to view your LOOT",

"lv":"Level\nLevel is determined by XP. Player Level starts at 1. Player gains 3 QP upon Level-up. Type 'lv' to view your Level",

"magical damage":"Magical Damage\nDamage types which are characterized by their magical nature. The Magical Damage types are Psychic, Necrotic, Radiant, and Force",

"maxhp":"MaxHP\nMaximum value HP can be. MXHP is primarily determined by Level and CON, and is also improved by STM. Type 'mxhp' to view your MXHP",

"maxmp":"MaxMP\nMaximum value MP can be. MXMP is primarily determined by Level and WIS, and is also improved by STM. Type 'mxmp' to view your MXMP",

"might":"Might\nWeapons have a Might value. When making an attack, ATCK is determined by Might and STR",

"money":"Money\nPlayer currency in the local denomination, Pylars (ᵽ). Money can be used to buy and sell goods. Type 'money' to view your Money",

"monster":"Monster\nAny Creature which can use Items, but cannot Talk or Trade",

"monsters":"Monsters\nCreatures which can use Items, but cannot Talk or Trade",

"movement":"Movement\nSpeed of movement in on action. MVMT is determined is determined by SPD and STM and can be reduced if Armor is too heavy or if player is Hindered. Type 'mvmt' to view your MVMT",

"mp":"Magic Points\nPlayer magic potential. MP can be replenished up to MXMP. MP are used to cast spells and magical effects. Type 'mp' to view your MP",

"mvmt":"Movement\nSpeed of movement in on action. MVMT is determined is determined by SPD and STM and can be reduced if Armor is too heavy or if player is Hindered. Type 'mvmt' to view your MVMT",

"mxhp":"MaxHP\nMaximum value HP can be. MXHP is primarily determined by Level and CON, and is also improved by STM. Type 'mxhp' to view your MXHP",

"mxmp":"MaxMP\nMaximum value MP can be. MXMP is primarily determined by Level and WIS, and is also improved by STM. Type 'mxmp' to view your MXMP",

"people":"People\nCreatures which can Talk and Trade",

"person":"Person\nAny creature which can Talk and Trade",

"persuasion":"Persuasion\nAbility to persuade People. PRSN is determined primarily by CHA, and is also improved by WIS. Type 'prsd' to view your PRSD",

"physical damage":"Physical Damage\nDamage types which are from purely physical sources. The Physical Damage types are Blugeoning, Piercing, and Slashing",

"protection":"Protection\nArmor and Shields have protection values. DFNS is increased by the Protection values of Equipped Armor and Shields",

"prsd":"Persuasion\nAbility to persuade People. PRSN is determined primarily by CHA, and is also improved by WIS. Type 'prsd' to view your PRSD",

"pylar":"Pylar\nThe local denomination of currency. Money can be used to buy and sell goods. Type 'money' to view your money",

"pylars":"Pylars\nThe local denomination of currency. Money can be used to buy and sell goods. Type 'money' to view your money",

"qp":"Quality Points\nQP are used to improve player Traits. 3 QP are gained upon Level-up.",

"range":"Range\nWeapons have a range value. When making an attack at a distance, ACCU is determined by Range, Sleight, SKL, and LCK. If the distance of the target is greater than weapon range, ACCU will be reduced. Weapons intended for melee attacks which are thrown usually have a poor Range.",

"resc":"Resistance\nAmount that incoming Magical Damage is reduced. RESC is determined primarily by FTH, and is also improved by STM. Type 'resc' to view your RESC",

"resistance":"Resistance\nAmount that incoming Magical Damage is reduced. RESC is determined primarily by FTH, and is also improved by STM. Type 'resc' to view your RESC",

"ritl":"Ritual\nBonus added to rituals and healing Spells. RITL is determined primarily by FTH and is also improved by LCK. Type 'ritl' to view your RITL",

"ritual":"Ritual\nBonus added to rituals and healing Spells. RITL is determined primarily by FTH and is also improved by LCK. Type 'ritl' to view your RITL",

"rp":"Reputation Points\nRP indicates how People may perceive the player. Player starts with 0 RP. RP can increase to 100 or decrease to -100. RP is changed by social interaction. Type 'rp' to view your RP",

"sharpness":"Sharpness\nWeapons have a sharpness value. When making an attack, CRIT is determined by sharpness, SKL, and LCK",

"shield":"Shield\nItems which can be Equipped in a Creature's hands. The Protection value of Shields increases the Creature's DFNS. Equipping a Shield which is heavier than four times your CON will lower your ATSP",

"shields":"Shield\nItems which can be Equipped in a Creature's hands. The Protection value of Shields increases the Creature's DFNS. Equipping a Shield which is heavier than four times your CON will lower your ATSP",

"skill":"Skill\nTrait representing physical dexterity. SKL contributes to ACCU, ATHL, CRIT, SLTH and TNKR. Type 'skl' to view your SKL",

"skl":"Skill\nTrait representing physical dexterity. SKL contributes to ACCU, ATHL, CRIT, SLTH and TNKR. Type 'skl' to view your SKL",

"sleight":"Sleight\nWeapons have a Sleight value. When making an attack, ACCU is determined by Sleight, SKL, and LCK",

"slth":"Stealth\nAbility to hide and be sneaky. SLTH is determined primarily by SKL and is also improved by INT. SLTH can be reduced if player is Hindered. Type 'slth' to view your SLTH",

"speed":"Speed\nTrait representing physical quickness. SPD contributes to determining ATSP and MVMT. Type 'spd' to view your SPD",

"spd":"Speed\nTrait representing physical quickness. SPD contributes to determining ATSP and MVMT. Type 'spd' to view your SPD",

"spls":"Spells\nNumber of spells that can be learned. SPLS is determined by INT. Type 'spls' to view your SPLS. Type 'spell list' to view your Spell List",

"spell":"Spell\nA magical effect which can be cast using a Creature's CAST and CSSP. Spells can do damage, bestow a Status Condition, or have some other effect. The number of spells a Creature can know is determined by SPLS. Type 'spell list' to view your Spell List",

"spells":"Spells\nNumber of spells that can be learned. SPLS is determined by INT. Type 'spls'to view your SPLS. Type 'spell list' to view your Spell List",

"spell list":"Spell List\nList of spells which a Creature has learned. The maximum number of spells a Creature can know is determined by SPLS. Type 'spell list' to view your Spell List",

"stamina":"Stamina\nTrait representing physical energy capacity. STM contributes to determining ATHL, ENDR, MVMT, MXHP, MXMP, and RESC. Type 'stm' to view your STM",

"status":"Status Conditions\nAll the player Status Conditions including Blessings and Curses. Status Conditions are temporary and affect player Stats in a variety of ways. Type 'status' to view your Status",

"status condition":"Status Conditions\nAll the player Status Conditions including Blessings and Curses. Status Conditions are temporary and affect player Stats in a variety of ways. Type 'status' to view your Status",

"status conditions":"Status Conditions\nAll the player Status Conditions including Blessings and Curses. Status Conditions are temporary and affect player Stats in a variety of ways. Type 'status' to view your Status",

"stealth":"Stealth\nAbility to hide and be sneaky. SLTH is determined primarily by SKL and is also improved by INT. SLTH can be reduced if player is Hindered. Type 'slth' to view your SLTH",

"stm":"Stamina\nTrait representing physical energy capacity. STM contributes to determining ATHL, ENDR, MVMT, MXHP, MXMP, and RESC. Type 'stm' to view your STM",

"str":"Strength\nTrait representing physical force. STR contributes to determining, ATCK, ATHL, and BRDN. Type 'str' to view your STR",

"strength":"Strength\nTrait representing physical capability. STR contributes to determining, ATCK, ATHL, and BRDN. Type 'str' to view your STR",

"tinker":"Tinker\nLikelihood and Quality of crafting magical and nonmagical items. TNKR is determined primarily by INT, and is also improved by SKL. Type 'tnkr' to view your TNKR",

"tnkr":"Tinker\nLikelihood and Quality of crafting magical and nonmagical items. TNKR is determined primarily by INT, and is also improved by SKL. Type 'tnkr' to view your TNKR",

"trait":"Trait\nOne of 10 Core player Stats that start at 1 and can be increased to a maximum of 20 using QP. Traits determine Abilities\nThe Traits are STR, SPD, SKL, STM, CON, CHA, INT, WIS, FTH, and LCK.\nType 'traits' to view your traits",

"traits":"Trait\n10 core player stats that start at 1 and can be increased to a maximum of 20 using QP. Traits determine Abilities\nThe Traits are STR, SPD, SKL, STM, CON, CHA, INT, WIS, FTH, and LCK.\nType 'traits' to view your traits",

"vulnerability":"Vulnerability\nStatus Conditions which confer Vulnerability to some Damage type. Creatures which are Vulnerable to a Damage type take double Damage from attacks of that type.",

"vulnerable":"Vulnerability\nStatus Conditions which confer Vulnerability to some Damage type. Creatures which are Vulnerable to a Damage type take double Damage from attacks of that type.",

"weight":"Weight\nEvery Item has a weight value. Inventory weight is the combined weight of every Item in your Inventory. Weapons used that are too heavy can reduce ATSP. Armor Equipped that is too heavy can reduce CSSP, CAST, and MVMT",

"wis":"Wisdom\nTrait representing perceptiveness and unworldly understanding. WIS contributes to determining CAST, CSSP, INVS, MXMP, and PRSD. Type 'wis' to view your WIS",

"wisdom":"Wisdom\nTrait representing perceptiveness and unworldly understanding. WIS contributes to determining CAST, CSSP, INVS, MXMP, and PRSD. Type 'wis' to view your WIS",

"xp":"Experience Points\nXP determines Level. Player can gain XP from fighting, socializing, exploring, tinkering, and more. Type 'xp' to view your XP"
}




#####################
## INTRO LOGO DATA ##
#####################

# static final logo after animation
logo = "\
 ______________________		\n\
|   __  \   __\   ___  \	\n\
|  |  \  \  \  \  \  \  \	\n\
|  POTIONS  &  PYTHONS  |	\n\
|   ____/ /\  \  \   ___/	\n\
|  |    \ \_\  \__\  \		\n\
|__|     \_______/ \__\		"

# animation logo which serves as the 'background'
logoLines = ["",
" ______________________	",
"|   __  \   __\   ___  \	",
"|  |  \  \  \  \  \  \  \	",
"|  |__/  /   \  \  \__| |	",
"|   ____/ /\  \  \   ___/	",
"|  |    \ \_\  \__\  \		",
"|__|     \_______/ \__\	",
"","","","","","",""]

# animation logo which serves as the moving 'foreground'
popyLines = ["",
" _ POTIONS  &  PYTHONS 	",
"|  POTIONS  &  PYTHONS \	",
"|  POTIONS  &  PYTHONS  \	",
"|  POTIONS  &  PYTHONS  |	",
"|  POTIONS  &  PYTHONS _/	",
"|  POTIONS  &  PYTHONS		",
"|__POTIONS  &  PYTHONS 	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	",
"   POTIONS  &  PYTHONS   	"]









































# you're still here? it's over! go home.






















# go!
