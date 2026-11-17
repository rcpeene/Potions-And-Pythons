# Data.py
# This file holds all the constant sets and dicts of data used in the game.
# This file is a dependency of Core.py and Menu.py

# It consists of four main parts;
# 1. Useful strings			(Useful strings of data primarily used in Parser.py)
# 2. Useful sets			(Sets of strings primarily used in Parser.py)
# 3. Game term dictionary	(Game terms used by Define() in Parse.py)
# 4. Intro Logo Data		(Strings and lists used for the intro animation)

from dataclasses import dataclass, field



TERMINAL_HEIGHT = 32
TERMINAL_WIDTH = 118


####################
## USEFUL STRINGS ##
####################

menuinstructions = "\nType 'info' for information on how to play.\nType 'new' to start a new game.\nType 'load' to load a save file.\nType 'delete' to delete a save file.\nType 'quit' to quit the game.\n"

gameinfo = "="*TERMINAL_WIDTH + "\n\n\tPotions & Pythons\n\tv.Alpha\n\tBy Carter Peene, 2022\n\n" + "-"*TERMINAL_WIDTH + "\n\n\tTo play, type a command of the form:\n\t[verb] [*noun] [*preposition] [*noun]\n\tOR\n\t[verb] [*preposition] [*noun]\n\t* denotes a term that can be omitted when unnecessary.\n\tArticles, determiners, and most symbols are ignored.\n\n" + "-"*TERMINAL_WIDTH + "\n\n\tDuring the game, you may type...\n\tSee these instructions:\t\t'info' or 'help'\n\tGet a list of valid commands:\t'commands'\n\tGet a list of command examples:\t'examples'\n\tSee your player statistics:\t'stats' and 'abilities'\n\tSee your items:\t\t\t'inv' and 'gear'\n\tLearn about your location:\t'here' and 'where'\n\tLearn about most game terms:\t'define [term]'\n\tSave the game:\t\t\t'save [savename]'\n\tQuit:\t\t\t\t'quit'\n\n" + "="*TERMINAL_WIDTH

examples = "\nValid input examples include:\n - go\n - go northwest\n - go nw\n - go up the stairs\n - go back\n - go to tunnel\n - look around\n - look at python\n - i will fight the python!\n - hit the python with my sword\n - attack python sword\n - fight it\n - equip a sword\n - unequip sword\n - take red potion\n - take the potion from the chest\n - take all\n - take all from chest\n - put red potion in the chest\n - put potion chest\n - drop the red potion\n - pour it out\n - close chest\nGet a complete list of commands by typing 'commands'."

symbols = ".,!?~`\"[]{}<>+=/*&^%$#@\t"

numsymbols = "-0123456789"

vowels = "aeiouAEIOU"



#################
## USEFUL SETS ##
#################

superfluous = {"a","again","an","hers","his","i","ill","i'll","its","of","some","that","the","then","their","this","will"}

shortactions = {"cast","here","room","clear","cls","quit"}

cancels = {"cancel","done","end","nevermind","no","nvm","undo"}

yesses = {"absolutely","affirmative","aye","certainly","definitely","indeed","ja","ok","okay","oui","si","sure","surely","y","ya","yaa","yaaa","yaaaa","ye","yea","yeah","yes","yess","yesss","yup"}

noes = {"absolutely not","certainly not","definitely not","n","na","nah","nahh","nahhh","nay","negative","negatory","nein","no","noo","nooo","noooo","nope"}

hellos = {"ahoy","ahoy there","aloha","greetings","good tidings","hail","hail thee","hello","hello there","hi","hi there","howdy","peace to you","salutations","salute thee","omens aghast","well met","why, hello there"}

goodbyes = {"adieu","bye","bye bye","bye then","prosper and live long","may luck","omens beware","fare thee well","farewell","gods be with ye","goodbye","goodbye then","peace be with you","so long"}

laughs = {"haha","hahaha","hehe","hehehe","heehee","lol","rofl","lmao"}

# note that "u" and "d" are included here as abbreviations of "up" and "down"
# this is because "up" and "down" are also in the "directions" dict
# they are not necessary entries here, but make interpreting more consistent...
# for use in the Go() action functions
prepositions = {"above","across","around","at","away","away from","behind","below","beneath","by","d","down","for","from","in","inside","into","near","off","of","on","onto","out","out of","outside","over","through","to","toward","under","u","up","upon","using","with"}

pronouns = {"she","he","they","her","him","them","it"}

objectives = {"she":"her","he":"him","they":"them","her":"her","him":"him","them":"them","it":"it"}

subjectives = {"her":"she","him":"he","them":"they","it":"it"}

reflexives = {"her":"herself","him":"himself","them":"themself","it":"itself","me":"myself","you":"yourself"}

compounds = {"downstairs":["down","stairs"], "indoors":["in","door"], "upstairs":["up","stairs"]}

# used in nounify() in Parser.py to combine multiple words that might have a single meaning as a whole term
miscexpressions = {"it all"}

directions = {"n":"north","ne":"northeast","e":"east","se":"southeast","s":"south","sw":"southwest","w":"west","nw":"northwest","u":"up","d":"down","inside":"in","into":"in","o":"out","b":"back","upward":"up","upwards":"up","downward":"down","downards":"down","onto":"on","upon":"on","off":"down","off of":"down","outside":"out","out of":"out","over":None,"to":None}

cardinals = ("north","east","south","west","northeast","southeast","southwest","northwest")

dmgtypes = {"a":"acid","b":"bludgeoning","c":"cold","d":"drowning","e":"essential","f":"fire","h":"hunger","i":"psychic","l":"lightning","n":"necrotic","p":"piercing","r":"radiant","s":"slashing","t":"thunder","v":"force","x":"poison"}
dmgclasses = {"a":"elem","b":"phys","c":"elem","d":"phys","e":"dev","f":"elem","h":"phys","i":"mag","l":"elem","n":"mag","p":"phys","r":"mag","s":"phys","t":"elem","v":"mag","x":"elem"}

# verbs for reporting damage greater than a quarter of max hp
dmgverbs = ("received","sustained","endured")

# emphasis phrases for reporting especially large figures
emphasis = ("a whopping","a staggering","a crushing","a devastating","a monstrous",
"a punishing","an eye-watering","a ruinous","a dire",
"a bone-chilling","a merciless","a titanic","a savage",
"a hellacious","a jaw-dropping","an unholy","a tremendous",
"a gut-wrenching","an obscene","a stupefying")

# emphasis phrases for reporting outright implausible figures
superEmphasis = ("a ridiculous","a colossal","an absurd","a cataclysmic","a ludicrous",
"a preposterous","an earth-shattering","a silly little")


# gear dict used to initialize creatures
initgear = {"over":None, "head":None, "torso":None, "left":None, "right":None,
"legs":None, "feet":None}


############################
## STATUS CONDITION CODES ##
############################


# a StatusCondition is the shared, immutable record of properties for one
# status condition name; entries on objects store only [name, source, duration]
@dataclass(frozen=True,kw_only=True)
class StatusCondition:
	name: str
	# (factor, dmgtype) damage rolled against the bearer each tick, or None
	damage: tuple = None
	# "blessing of" / "curse of" / None; classifies the condition for
	# class-targeted effects and derives the default gain/loss messages
	prefix: str = None
	# display color code for reports and the stats panel: "g"/"r"/None=white
	color: str = None
	# magical conditions are the targets of dispel-class effects
	magical: bool = False
	# bearer-facing report text: a verb-first predicate completed by the
	# subject (e.g. "are burning." -> "You are/The wolf is burning.");
	# leading adverbs are allowed; "" suppresses the report entirely;
	# derived from name/prefix when not authored
	gainMsg: str = None
	lossMsg: str = None
	# trait modifiers summed into stat getters while present, e.g. {"STR":10}
	# (multiplied by entry count for compounding conditions)
	modifies: dict = field(default_factory=dict)
	# other creatures' instances of this condition are reported/shown to you
	public: bool = False
	# shown in the bearer's stats panel and in the 'status' command output
	displayable: bool = True
	# prevents movement and most actions
	immobile: bool = False
	# may a new entry be added while the condition is already present?
	stackable: bool = True
	# do multiple entries compound the effect, or do reads cap at 1?
	compounds: bool = False
	# condition names whose addition this condition vetoes while present
	blocks: tuple = ()
	# cascading effects that conditions can trigger
	# onAdd/onRemove trigger on any status entry operations, while-
	# onGain/onLoss trigger on the first addition and last removal of the condition
	# onTick and onExpire refer to duration counts of the condition
	# onBlock triggers when an attempt to add a blocked condition occurs
	onAdd: tuple = ()
	onGain: tuple = ()
	onRemove: tuple = ()
	onLoss: tuple = ()
	onTick: tuple = ()
	onExpire: tuple = ()
	onBlock: tuple = ()

	def __post_init__(self):
		assert isinstance(self.blocks,tuple) and \
			all(isinstance(n,str) for n in self.blocks), \
			f"StatusCondition '{self.name}' blocks must be a tuple of names"
		assert isinstance(self.modifies,dict) and all(
			isinstance(k,str) and isinstance(v,int)
			for k,v in self.modifies.items()), \
			f"StatusCondition '{self.name}' modifies must map trait names to ints"
		# cascade hooks must be authored in canonical form: a tuple of
		# (name, *args) tuple descriptors
		for hook in ("onAdd","onGain","onRemove","onLoss","onTick","onExpire",
		"onBlock"):
			val = getattr(self,hook)
			assert isinstance(val,tuple) and all(
				isinstance(d,tuple) and d and isinstance(d[0],str) for d in val), \
				f"StatusCondition '{self.name}' {hook} must be a canonical " \
				f"tuple of descriptors"
		# derive default predicate report messages from the name and prefix
		if self.gainMsg is None:
			gain = f"have the {self.prefix} {self.name}." if self.prefix \
				else f"are {self.name}."
			object.__setattr__(self,"gainMsg",gain)
		if self.lossMsg is None:
			loss = f"no longer have the {self.prefix} {self.name}." \
				if self.prefix else f"are no longer {self.name}."
			object.__setattr__(self,"lossMsg",loss)

	# look up the shared record for a status condition name
	# unregistered names resolve to a plain default record (the ylem pattern)
	@classmethod
	def get(cls,name):
		return statusConditions.get(name,DEFAULT_STATUS_CONDITION)


# the single source of truth for status condition properties, keyed by name
statusConditions = {s.name: s for s in (
	StatusCondition(name="anointed",color="g"),
	StatusCondition(name="apathy",prefix="curse of",color="r",modifies={"FTH":-10}),
	StatusCondition(name="asleep",immobile=True,public=True,gainMsg="falls asleep.",lossMsg="",onExpire=(("awaken",True),),onLoss=(("awaken",),)),
	StatusCondition(name="bleeding",damage=(15,"e"),public=True),
	StatusCondition(name="brawniness",prefix="blessing of",color="g",modifies={"STR":10}),
	StatusCondition(name="burning",damage=(50,"f"),public=True),
	StatusCondition(name="calamity",prefix="curse of",color="r",modifies={"LCK":-10}),
	StatusCondition(name="clumsiness",prefix="curse of",color="r",modifies={"SKL":-10}),
	StatusCondition(name="dead",color="r",immobile=True,stackable=False,blocks=("hungry","starving","tired","fatigued"),onGain=(("removeStatus","hungry"),("removeStatus","starving"),("removeStatus","tired"),("removeStatus","fatigued"))),
	StatusCondition(name="drowning",color="r",damage=(25,"d"),public=True),
	StatusCondition(name="enchanted",magical=True,modifies={"LOVE":50}),
	StatusCondition(name="fatigued",color="r",public=True,stackable=False,modifies={"STM":-5,"WIS":-3,"FTH":3}),
	StatusCondition(name="felicity",prefix="blessing of",color="g",modifies={"CHA":10}),
	StatusCondition(name="fidelity",prefix="blessing of",color="g",modifies={"FTH":10}),
	StatusCondition(name="fleetfooted",color="g"),
	StatusCondition(name="flying",color="g",public=True,onGain=(("Float",),)),
	StatusCondition(name="levitating",onGain=(("Float",),)),
	StatusCondition(name="frozen",immobile=True,damage=(20,"c"),public=True,blocks=("burning",),onGain=(("removeStatus","burning"),),onBlock=(("removeStatus","frozen"),)),
	StatusCondition(name="haunted",magical=True,modifies={"FEAR":50}),
	StatusCondition(name="hidden"),
	StatusCondition(name="hindered",color="r"),
	StatusCondition(name="hungry",color="r"),
	StatusCondition(name="illness",prefix="curse of",color="r",modifies={"CON":-10}),
	StatusCondition(name="insanity",prefix="curse of",color="r",modifies={"WIS":-10}),
	StatusCondition(name="invigorated",color="g"),
	StatusCondition(name="invisible"),
	StatusCondition(name="liveliness",prefix="blessing of",color="g",modifies={"STM":10}),
	StatusCondition(name="lucidity",prefix="blessing of",color="g",modifies={"WIS":10}),
	StatusCondition(name="mending",color="g"),
	StatusCondition(name="paralyzed",immobile=True,public=True),
	StatusCondition(name="poisoned",damage=(5,"x"),compounds=True),
	StatusCondition(name="prosperity",prefix="blessing of",color="g",modifies={"LCK":10}),
	StatusCondition(name="prowess",prefix="blessing of",color="g",modifies={"SKL":10}),
	StatusCondition(name="restrained",immobile=True,public=True),
	StatusCondition(name="sagacity",prefix="blessing of",color="g",modifies={"INT":10}),
	StatusCondition(name="slowness",prefix="curse of",color="r",public=True,modifies={"SPD":-10}),
	StatusCondition(name="starving",color="r",damage=(1,"h")),
	StatusCondition(name="stunned",immobile=True,public=True),
	StatusCondition(name="submerged",public=True,onGain=(("transferStatus","wet","IMMERSED","SUBMERGED"),),onLoss=(("transferStatus","wet","SUBMERGED","IMMERSED"),)),
	StatusCondition(name="stupidity",prefix="curse of",color="r",modifies={"INT":-10}),
	StatusCondition(name="swiftness",prefix="blessing of",color="g",public=True,modifies={"SPD":10}),
	StatusCondition(name="timidity",prefix="curse of",color="r",modifies={"CHA":-10}),
	StatusCondition(name="tired",color="r",stackable=False,modifies={"STM":-3}),
	StatusCondition(name="toughness",prefix="blessing of",color="g",modifies={"CON":10}),
	StatusCondition(name="unconscious",immobile=True,public=True),
	StatusCondition(name="weakness",prefix="curse of",color="r",modifies={"STR":-10}),
	StatusCondition(name="weariness",prefix="curse of",color="r",modifies={"STM":-10}),
	StatusCondition(name="wet",public=True,blocks=("burning",),onGain=(("removeStatus","burning"),),onAdd=(("removeStatus","asleep"),),onBlock=(("removeStatus","wet",None),)),
	StatusCondition(name="wildspeaking",color="g",public=True),
)}

# unregistered status names resolve to a plain default record
DEFAULT_STATUS_CONDITION = StatusCondition(name=None)

spawnpools = {
	"Woodlands": (("green python",1), ("goblin",1)),
	"Plains": (("red python",1), ("horse",1))
}

colors = {
	"red": "r",
	"orange": "o",
	"yellow": "y",
	"green": "g",
	"blue": "b",
	"magenta": "m",
	"grey": "k",
	"white": "w"
}

# ANSI color codes for terminal output
colorCodes = {
	"r":"31", "o": "38;5;215", "y":"38;5;227", "g":"32",
	"b":"34", "m":"35", "k":"90", "w":"37"
}

rarityColors = {-1:"r",0:"k",1:"w",2:"o",3:"g",4:"b",5:"m",6:"y"}

emoticons = {":)",":d",":(",";)",":o",":p"}

# the following are tuples because their order should be preserved for printing

# base Creature stats
traits = ("str","skl","spd","stm","con","cha","int","wis","fth","lck")

inittraits = [1]*10

# derived creature stats. they can be found as Creature methods
abilities = ("accu","atck","athl","atsp","brdn","cast","crit","cssp","dcpt","dfns","endr","evsn","invs","knwl","loot","mvmt","mxhp","mxmp","prsd","rstn","ritl","slth","spls","tnkr")

# the sequence of hours in the daily calendar
hours = ("stag","rooster","juniper","bell","sword","willow","lily","hearth","cat","mouse","owl","serpent","wolf")
dayhours = hours[:9]
nighthours = hours[9:]


# a Material is the shared, immutable record of properties for one composition
# convert smell vocabulary to taste vocabulary in a sense description
def smellToTaste(text):
	return text.replace("smelling","tasting").replace("smell","taste") \
		.replace("scent","taste")


# convert taste vocabulary to smell vocabulary in a sense description
def tasteToSmell(text):
	return text.replace("tasting","smelling").replace("taste","smell") \
		.replace("flavor","scent")


# game objects store only their composition string; the Material it names is
# looked up at call time (via material() or GameObject.material()), so
# composition changes from mixing or brewing are always reflected, and saves
# never store Material objects
@dataclass(frozen=True,kw_only=True)
class Material:
	name: str
	# relative mass per unit of size; an object's size is its weight//density
	density: int = 1
	# liquids form Plashes, immerse objects, and can be drunk
	liquid: bool = False
	# transparent compositions can be seen through (no hiding inside/behind)
	transparent: bool = False
	# shatterable compositions scatter into Shards when they break
	shatterable: bool = False
	# how reactive this material is to fire and force, from 0 to 10:
	# 0 = inert (cannot burn or react at all)
	# 1-5 = flammable (a single fire hit of 25 - 5*volatility damage
	#       triggers its ignite effects, so 5 ignites from any fire at all;
	#       impact never triggers)
	# 6-10 = explosive (any fire triggers ignite; a single blunt hit of
	#        100 - 20*(volatility-5) damage triggers its impact effects)
	volatility: int = 0
	# if either sense is omitted, it is derived from the other at init;
	# materials with neither get nondescript defaults, as does texture
	taste: str = None
	scent: str = None
	texture: str = None
	# tuples of effect descriptors (effectName, *args) naming Effects.py
	# functions, run when something of this material is consumed, drenched
	# onto a target, touched, ignited, struck hard, unsealed, or broken
	consume: tuple = ()
	drench: tuple = ()
	touch: tuple = ()
	ignite: tuple = ()
	impact: tuple = ()
	expose: tuple = ()
	onBreak: tuple = ()

	def __post_init__(self):
		for trigger in ("consume","drench","touch","ignite","impact","expose",
		"onBreak"):
			val = getattr(self,trigger)
			assert isinstance(val,tuple) and all(
				isinstance(d,tuple) and d and isinstance(d[0],str) for d in val), \
				f"Material '{self.name}' {trigger} must be a canonical " \
				f"tuple of descriptors"
		if self.taste is None and self.scent is not None:
			object.__setattr__(self,"taste",smellToTaste(self.scent))
		if self.scent is None and self.taste is not None:
			object.__setattr__(self,"scent",tasteToSmell(self.taste))
		if self.taste is None:
			object.__setattr__(self,"taste","It doesn't taste like much in particular.")
		if self.scent is None:
			object.__setattr__(self,"scent","It doesn't smell like anything specific.")
		if self.texture is None:
			if self.liquid:
				object.__setattr__(self,"texture","It feels wet.")
			else:
				object.__setattr__(self,"texture","It feels completely featureless.")

	# look up the shared Material record for a composition string
	# unregistered compositions resolve to ylem, the formless default material
	@classmethod
	def get(cls,name):
		return materials.get(name,DEFAULT_MATERIAL)

	# the single fire hit damage required to trigger this material's ignite
	# effects, or None if it cannot burn (volatility 0)
	def igniteThreshold(self):
		if self.volatility == 0:
			return None
		return max(1,25 - 5*self.volatility)

	# the single blunt hit damage required to trigger this material's impact
	# effects, or None if it does not react to force (volatility 5 and under)
	def impactThreshold(self):
		if self.volatility <= 5:
			return None
		return max(1,100 - 20*(self.volatility-5))


# the single source of truth for material properties, keyed by material name
materials = {m.name: m for m in (
	Material(name="acid",liquid=True,taste="It tastes painful... Ouch!"),
	Material(name="air",transparent=True),
	Material(name="black potion",liquid=True,volatility=9,taste="It tastes acrid, like smoke and saltpeter.",scent="It smells faintly of sulfur and char.",consume=(("damage",10,"x"),),ignite=(("explode","t"),),impact=(("explode","t"),)),
	Material(name="blue potion",liquid=True,taste="It tastes cool and tingly, like a winter breeze.",consume=(("resurge",20),)),
	Material(name="bread",taste="It tastes like fluffy dreams and joy.",texture="It is soft and fluffy."),
	Material(name="brick",density=2,shatterable=True,taste="It tastes like dry gritty clay.",texture="It feels flat and gritty."),
	Material(name="bronze",density=3,taste="It has a light metallic taste."),
	Material(name="canvas",texture="It feels like coarse woven fabric."),
	Material(name="ceramic",density=2,shatterable=True,texture="It feels smooth and almost squeaky."),
	Material(name="cheese",taste="It tastes sharp, creamy, and divine.",scent="It has a pungent funk."),
	Material(name="clay",density=2,texture="It feels dense and earthen."),
	Material(name="cloth",texture="It feels soft and woven."),
	Material(name="coffee",liquid=True,taste="It tastes bold, bitter, and invigorating.",scent="It has a rich, roasty aroma.",consume=(("impartStatus","invigorated",50),)),
	Material(name="crystal",density=2,transparent=True,shatterable=True,texture="It feels smooth and solid."),
	Material(name="earth",taste="It has a sharp taste of ancient musty dirt.",texture="It feels dry and crumbly."),
	Material(name="energy"),
	Material(name="fire",scent="It smells of smoke and char.",texture="It feels searingly hot!"),
	Material(name="flesh",taste="Yuck!",scent="It smells a little like body odor.",texture="It feels soft and fleshy."),
	Material(name="freshwater",liquid=True,taste="It tastes crisp and pure.",texture="It feels cold and wet."),
	Material(name="glass",density=2,transparent=True,shatterable=True,taste="It has little taste.",texture="It is very smooth."),
	Material(name="gold",density=4),
	Material(name="grass",taste="It tastes like grass.",texture="It feels soft and grassy."),
	Material(name="green potion",liquid=True,taste="It tastes sharp and herbaceous.",consume=(("impartStatus","swiftness",100),)),
	Material(name="ice",transparent=True),
	Material(name="iron",density=3,taste="It tastes like iron.",texture="It feels smooth and sturdy."),
	Material(name="lava",density=2,liquid=True),
	Material(name="lead",density=4,taste="It tastes sweet and metallic. Probably fine."),
	Material(name="leather",texture="It feels tough and supple."),
	Material(name="magic"),
	Material(name="mud",taste="It is wet and pungent, tasting mildly of dirt.",texture="It feels wet and sticky."),
	Material(name="mudwater",liquid=True,taste="It tastes dank and dirty.",texture="It feels wet and slightly slimy."),
	Material(name="oil",liquid=True,volatility=4,taste="It tastes oily.",texture="It feels wet and oily.",ignite=(("areaStatus","burning",15),)),
	Material(name="paper",texture="It feels thin and dry."),
	Material(name="python",texture="It feels smooth and scaly. Ew."),
	Material(name="red potion",liquid=True,taste="It tastes sweet and warm, like cherries and cinnamon.",consume=(("heal",20),)),
	Material(name="rust",taste="It tastes like dirty iron.",texture="It feels rough."),
	Material(name="saltwater",liquid=True,taste="It tastes salty and foamy.",texture="It feels wet and foamy."),
	Material(name="sand",texture="It feels coarse and rough."),
	Material(name="silver",density=4),
	Material(name="slime",liquid=True),
	Material(name="smoke",scent="It smells of noxious smoke."),
	Material(name="soil",taste="It has a deep and full fresh earthy taste.",texture="It feels loamy and moist."),
	Material(name="steel",density=3,taste="It has a slightly metallic taste.",texture="It feels smooth and sturdy."),
	Material(name="stone",density=2,shatterable=True,taste="It has a dull taste of chalk and lime.",texture="It feels slighty rough and very solid."),
	Material(name="urine",liquid=True,taste="It tastes acrid and bitter."),
	Material(name="vegetable",taste="It tastes... nutritious",texture="It feels firm and fibrous."),
	Material(name="void"),
	Material(name="water",liquid=True,transparent=True,taste="It doesn't taste like much.",texture="It feels wet."),
	Material(name="wicker",texture="It feels like woven dry reeds."),
	Material(name="wine",liquid=True,taste="It tastes rich, fruity, and dry.",texture="It feels wet and slightly sticky."),
	Material(name="wood",taste="It has a heady and slightly bitter taste.",texture="It feels like a hard sturdy wood."),
	# ylem is the primordial undifferentiated substance; it is the material of
	# anything whose composition is None or not registered here
	Material(name="ylem"),
)}
# unregistered compositions resolve to ylem, the formless default material
DEFAULT_MATERIAL = materials["ylem"]
# objects with no composition are made of ylem as well
materials[None] = DEFAULT_MATERIAL


### Celestial Descriptions:
eclipseDesc = "The bold bronze sun is blackened by the ominous moon. The world is dark above and below but for the ring of violet light tracing the moon. Those golden lines of fire that scar the moon's surface seem like cracks through which the sun's rays seep faintly through. All is still in the heavens as they bear witness to this solemn union."
morningSunDesc = "A burning ball of red fire marches upward in the sky. In the morning air it paints the heavens a tinge of pale green."
highSunDesc = "A burning ball of bronze fire hangs high in the verdant sky. It warms your face with its bold glow."
eveningSunDesc = "A burning ball of red fire rests in the sky. As it descends toward the horizon it draws a curtain of violet across the world above."
fullMoonDesc = "A shimmering silver orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. The stars seem to dance around it joyously. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate."
newMoonDesc = "On a night without the moon the world is full of silence and cold. The stars seem to shiver lonesomely. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate."
moonDesc = "A shimmering silver orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. It hangs amongst a scattering of sparkling drops on all sides. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate."
eveningStarsDesc = "The stars are just starting to appear as tiny pinpricks of silver light. They shimmer faintly against the deepening teal of the evening sky."
auroraDesc = "Tides of the red, blue, and green aurora gently sweep over the sky. The colors seem to bathe the heavens as it caresses the shimmering silver stars."
meteorDesc = "Bolts of yellow light streak deftly across the sky, leaving their imprint for no more than a moment. They almost seem to take turns whizzing past like a flock of sparrows, eager to follow one another toward the edge of the heavens."


##########################
## GAME TERM DICTIONARY ##
##########################

# Glossary of game terms to help players, used by the Define() verb in Parser.py
glossary = {
"ability":"Ability\nOne of 24 stats which dictate the chance to accomplish a goal, such as attacking, investigating, or persuading. The 24 abilities are ACCU, ATCK, ATHL, ATSP, BRDN, CAST, CRIT, CSSP, DCPT, DFNS, ENDR, EVSN, INVS, KNWL, LOOT, MVMT, MXHP, MXMP, PRSD, RSTN, RITL, SLTH, SPLS, and TNKR. Type 'abilities' to view your abilities.",

"accuracy":"Accuracy\nChance to hit against target EVSN. ACCU is determined primarily by SKL, and is also improved by LCK and Sleight. Type 'accu' to view your ACCU.",

"animal":"Animal\nA Creature which can act passively or aggressively.",

"armor":"Armor\nItems which can be equipped in a Creature's Gear. The Protection value of Armor increases the Creature's DFNS. Equipping Armor which is heavier than four times your CON will lower your CAST, CSSP, and MVMT.",

"athletics":"Athletics\nAbility to achieve physical actions such as running, jumping, and climbing. ATHL is improved by STR, SKL, and STM. Type 'athl' to view your ATHL.",

"attack":"Attack\nRange of possible damage that can be dealt to a target. ATCK is determined by STR and might. Type 'atck' to view your ATCK.",

"attack speed":"Attack Speed\nATSP determines the number of attacks against a target in one turn and if attacker or target hits first. Additionally, ATSP is the main factor in EVSN. ATSP is determined by SPD and can be reduced if the Items Equipped in player hands are too heavy. Type 'atsp' to view your ATSP.",

"burden":"Burden\nMaximum inventory weight without hindrance. Being Hindered reduces CSSP, MVMT and SLTH. BRDN is determined by CON and STR. Type 'brdn' to view your BRDN.",

"casting bonus":"Casting Bonus\nBonus added to various Spells and magical effects in different ways. CAST is determined by WIS, FTH, and INT, and can be reduced if the Equipped Armor is too heavy. Type 'cast' to view your CAST.",

"casting speed":"Casting Speed\nSpeed that spells can be casted. CSSP is determined by WIS, and can be reduced if Equipped Armor is too heavy or if player is Hindered. Type 'cssp' to view your CSSP.",

"charisma":"Charisma\nTrait representing charm and panache. CHA contributes to DCPT and PRSD. Type 'cha' to view your CHA.",

"constitution":"Constitution\nTrait representing physical fortitude. CON contributes to BRDN, DFNS, ENDR, and MXHP. Type 'con' to view your CON.",

"creature":"Creature\nAnything in the game that can be interacted with, that can also act on its own, unlike an Item. The main types of Creatures are People, Monsters, and Animals.",

"critical":"Critical\nPercent chance that a hitting attack will deal twice the Damage. CRIT is deterimined primarily by SKL, and is also improved by LCK and Sharpness. Type 'crit' to view your CRIT.",

"damage":"Damage\nAmount that target HP will be reduced from an attack. DFNS reduces incoming damage. Certain damage types deal double damage, half damage, or no damage if the target has Vulnerability, Invulnerability, or Immunity. The main categories of Damage are Physical Damage, Elemental Damage, and Magical Damage.",

"deception":"Deception\nAbility to deceive creatures. DCPT is determined primarily by CHA, and is also improved by INT. Type 'dcpt' to view your DCPT.",

"defense":"Defense\nAmount that incoming Physical Damage is reduced. DFNS is determined by CON, and the Protection values of Armor and Shields. Type 'dfns' to view your DFNS.",

"elemental damage":"Elemental Damage\nDamage types which are characterized by the power of the elements. The Elemental Damage types are Acid, Cold, Fire, Lightning, Thunder, and Poison.",

"endurance":"Endurance\nAbility to endure afflictions such as poison, pressure, breath-holding. ENDR is determined primarily by STM and is also improved by CON. Type 'endr' to view your ENDR.",

"evasion":"Evasion\nChance to not be hit by an attack. EVSN negates attacker ACCU. EVSN is determined primarily by ATSP, and is also improved by LCK. Type 'evsn' to view your EVSN.",

"faith":"Faith\nTrait representing divine conviction in the eyes of the gods. FTH contributes to CAST, LOOT, RITL, and RSNC. Type 'FTH' to view your FTH.",

"gear":"Gear\nPlayer's Gear. Has slots for all the Equipped Items from the player Inventory. Type 'gear' to view your Gear.",

"hindered":"Hindered\nA Status Condition which can arise from having too heavy an Inventory. Specifically, when your total Inventory weight exceeds your BRDN. Being Hindered lowers your CSSP, MVMT, and SLTH.",

"health points":"Health Points\nPlayer health. HP can be replenished up to Max HP (MXHP). Player dies if HP is reduced to 0. Type 'hp' to view your HP.",

"immunity":"Immunity\nStatus Conditions which confer Immunity to some Damage type. Creatures which are Immune to a Damage type take no Damage from attacks of the type.",

"intelligence":"Intelligence\nTrait representing memory and capability to solve problems. INT contributes to determining CAST, DCPT, INVS, KNWL, RITL, SLTH, SPLS, and TNKR. Type 'int' to view your INT.",

"inventory":"Inventory\nThe player Inventory. It can contain Items. If the weight of all Items in the player Inventory is greater than the player's BRDN, the player CSSP, MVMT, and SLTH will start to be penalized. Type 'inv' to view your inventory.",

"investigation":"Investigation\nLikelihood to identify and perceive secrets and hidden things. INVS is determined primarily by INT, and is also improved by WIS. Type 'invs' to view your INVS.",

"invulnerability":"Invulnerability\nStatus Conditions which confer Invulnerability to some Damage type. Creatures which are Invulnerable to a Damage type take half Damage from attacks of that type.",

"item":"Item\nAnything in the game that can be interacted with, but does not act on its own, unlike a Creature.",

"knowledge":"Knowledge\nAbility and likelihood to know things. KNWL is determined primarily by INT, and is also determined by LCK. Type 'knwl' to view your KNWL. |20+| <m>THIS IS A HIDDEN MESSAGE... IF YOU CAN READ THIS, YOU ARE VERY SMART :)</>",

"luck":"Luck\nTrait representing good fortune and happy accidents. LCK contributes to ACCU, CRIT, EVSN, KNWL, and LOOT. Type 'lck' to view your LCK.",

"level":"Level\nLevel is determined by XP. Player Level starts at 1. Player gains 1 QP upon Level-up. Type 'lv' to view your Level.",

"loot rate":"Loot Rate\nRate and tier at which items and Serpens are dropped by creatures. LOOT is determined primarily by LCK, is also improved by FTH. Type 'loot' to view your LOOT.",

"magical damage":"Magical Damage\nDamage types which are characterized by their magical nature. The Magical Damage types are Psychic, Necrotic, Radiant, and Force.",

"max hp":"Max HP\nMaximum value HP can be. MXHP is primarily determined by Level and CON, and is also improved by STM. Type 'mxhp' to view your MXHP.",

"max mp":"Max MP\nMaximum value MP can be. MXMP is primarily determined by Level and WIS, and is also improved by STM. Type 'mxmp' to view your MXMP.",

"might":"Might\nWeapons have a Might value. When making an attack, ATCK is determined by Might and STR.",

"money":"Money\nPlayer currency in the local denomination, Serpens (§). Money can be used to buy and sell goods. Type 'money' to view your Money.",

"monster":"Monster\nAny Creature which can use Items, but cannot Talk or Trade.",

"movement":"Movement\nSpeed of movement in action. MVMT is determined is determined by SPD and STM and can be reduced if Armor is too heavy or if player is Hindered. Type 'mvmt' to view your MVMT.",

"magic points":"Magic Points\nPlayer magic potential. MP can be replenished up to MXMP. MP are used to cast spells and magical effects. Type 'mp' to view your MP.",

"people":"People\nPlural of 'Person'.Creatures which can Talk and Trade.",

"person":"Person\nAny creature which can Talk and Trade.",

"persuasion":"Persuasion\nAbility to persuade People. PRSN is determined primarily by CHA, and is also improved by WIS. Type 'prsd' to view your PRSD.",

"physical damage":"Physical Damage\nDamage types which are from purely physical sources. The Physical Damage types are Blugeoning, Piercing, and Slashing.",

"protection":"Protection\nArmor and Shields have protection values. DFNS is increased by the Protection values of Equipped Armor and Shields.",

"qp":"Quality Points\nQP are used to improve player Traits. 1 QP is gained upon Level-up..",

"range":"Range\nWeapons have a range value. When making an attack at a distance, ACCU is determined by Range, Sleight, SKL, and LCK. If the distance of the target is greater than weapon range, ACCU will be reduced. Weapons intended for melee attacks which are thrown usually have a poor Range..",

"resistance":"Resistance\nAmount that incoming Magical Damage is reduced. RSTN is determined primarily by FTH, and is also improved by STM. Type 'rstn' to view your RSTN.",

"ritual":"Ritual\nBonus added to rituals and healing Spells. RITL is determined primarily by FTH and is also improved by LCK. Type 'ritl' to view your RITL.",

"reputation points":"Reputation Points\nRP indicates how People may perceive the player. Player starts with 0 RP. RP can increase to 100 or decrease to -100. RP is changed by social interaction. Type 'rp' to view your RP.",

"sharpness":"Sharpness\nWeapons have a sharpness value. When making an attack, CRIT is determined by sharpness, SKL, and LCK.",

"shield":"Shield\nItems which can be Equipped in a Creature's hands. The Protection value of Shields increases the Creature's DFNS. Equipping a Shield which is heavier than four times your CON will lower your ATSP.",

"skill":"Skill\nTrait representing physical dexterity. SKL contributes to ACCU, ATHL, CRIT, SLTH and TNKR. Type 'skl' to view your SKL.",

"sleight":"Sleight\nWeapons have a Sleight value. When making an attack, ACCU is determined by Sleight, SKL, and LCK.",

"speed":"Speed\nTrait representing physical quickness. SPD contributes to determining ATSP and MVMT. Type 'spd' to view your SPD.",

"spell":"Spell\nA magical effect which can be cast using a Creature's CAST and CSSP. Spells can do damage, bestow a Status Condition, or have some other effect. The number of spells a Creature can know is determined by SPLS. Type 'spell list' to view your Spell List.",

"spells":"Spells\nNumber of spells that can be learned. SPLS is determined by INT. Type 'spls' to view your SPLS. Type 'spells' to view your Spell List.",

"spell list":"Spell List\nList of spells which a Creature has learned. The maximum number of spells a Creature can know is determined by SPLS. Type 'spell list' to view your Spell List.",

"stamina":"Stamina\nTrait representing physical energy capacity. STM contributes to determining ATHL, ENDR, MVMT, MXHP, MXMP, and RSTN. Type 'stm' to view your STM.",

"status conditions":"Status Conditions\nAll the player Status Conditions including Blessings and Curses. Status Conditions are temporary and affect player Stats in a variety of ways. Type 'status' to view your Status.",

"stealth":"Stealth\nAbility to hide and be sneaky. SLTH is determined primarily by SKL and is also improved by INT. SLTH can be reduced if player is Hindered. Type 'slth' to view your SLTH.",

"strength":"Strength\nTrait representing physical capability. STR contributes to determining, ATCK, ATHL, and BRDN. Type 'str' to view your STR.",

"tinker":"Tinker\nLikelihood and Quality of crafting magical and nonmagical items. TNKR is determined primarily by INT, and is also improved by SKL. Type 'tnkr' to view your TNKR.",

"trait":"Trait\nOne of 10 Core player Stats that start at 1 and can be increased to a maximum of 20 using QP. Traits determine Abilities\nThe Traits are STR, SPD, SKL, STM, CON, CHA, INT, WIS, FTH, and LCK.\nType 'traits' to view your traits.",

"vulnerability":"Vulnerability\nStatus Conditions which confer Vulnerability to some Damage type. Creatures which are Vulnerable to a Damage type take double Damage from attacks of that type..",

"weight":"Weight\nEvery Item has a weight value. Inventory weight is the combined weight of every Item in your Inventory. Weapons used that are too heavy can reduce ATSP. Armor Equipped that is too heavy can reduce CSSP, CAST, and MVMT.",

"wisdom":"Wisdom\nTrait representing perceptiveness and unworldly insight. WIS contributes to determining CAST, CSSP, INVS, MXMP, and PRSD. Type 'wis' to view your WIS.",

"experience points":"Experience Points\nXP determines Level. Player can gain XP from fighting, socializing, exploring, tinkering, and more. Type 'xp' to view your XP."
}


glossaryXrefs = {
	"abilities":"ability",
	"accu":"accuracy",
	"animals":"animal",
	"atck":"attack",
	"athl":"athletics",
	"atsp":"attack speed",
	"brdn":"burden",
	"cast":"casting bonus",
	"cha":"charisma",
	"con":"constitution",
	"crit":"critical",
	"cssp":"casting speed",
	"dcpt":"deception",
	"dfns":"defense",
	"dmg":"damage",
	"endr":"endurance",
	"evsn":"evasion",
	"fth":"faith",
	"hp":"health points",
	"immune":"immunity",
	"int":"intelligence",
	"invs":"investigation",
	"invulnerable":"invulnerability",
	"knwl":"knowledge",
	"lck":"luck",
	"loot":"loot rate",
	"lv":"level",
	"monsters":"monster",
	"mp":"magic points",
	"mvmt":"movement",
	"mxhp":"max hp",
	"mxmp":"max mp",
	"prot":"protection",
	"prsd":"persuasion",
	"qp":"quality points",
	"ritl":"ritual",
	"rp":"reputation points",
	"rstn":"resistance",
	"serpen":"money",
	"serpens":"money",
	"shields":"shield",
	"skl":"skill",
	"slth":"stealth",
	"spd":"speed",
	"spls":"spells",
	"status":"status conditions",
	"status condition":"status conditions",
	"stm":"stamina",
	"str":"strength",
	"tnkr":"tinker",
	"traits":"trait",
	"vulnerable":"vulnerability",
	"wis":"wisdom",
	"xp":"experience points"
}




#####################
## INTRO LOGO DATA ##
#####################

# static final logo after animation
logo = "                    \n\t\
 ______________________		\n\t\
|   __  \   __\   ___  \	\n\t\
|  |  \  \  \  \  \  \  \	\n\t\
|  POTIONS  &  PYTHONS  |	\n\t\
|   ____/ /\  \  \   ___/	\n\t\
|  |    \ \_\  \__\  \		\n\t\
|__|     \_______/ \__\		"

# animation logo which serves as the 'background'
logoFrame = [""*40,
"	 ______________________     ",
"	|   __  \   __\   ___  \    ",
"	|  |  \  \  \  \  \  \  \   ",
"	|  |__/  /   \  \  \__| |   ",
"	|   ____/ /\  \  \   ___/   ",
"	|  |    \ \_\  \__\  \      ",
"	|__|     \_______/ \__\     ",
"","","","","","",""]

# animation logo which serves as the moving 'foreground'
titleMask = [""*40,
"	 _ POTIONS  &  PYTHONS      ",
"	|  POTIONS  &  PYTHONS \    ",
"	|  POTIONS  &  PYTHONS  \   ",
"	|  POTIONS  &  PYTHONS  |   ",
"	|  POTIONS  &  PYTHONS _/   ",
"	|  POTIONS  &  PYTHONS      ",
"	|__POTIONS  &  PYTHONS      ",
"	   POTIONS  &  PYTHONS      ",
"	   POTIONS  &  PYTHONS      ",
"	   POTIONS  &  PYTHONS   	",
"	   POTIONS  &  PYTHONS   	",
"	   POTIONS  &  PYTHONS   	",
"	   POTIONS  &  PYTHONS   	",
"	   POTIONS  &  PYTHONS      "]

























































# you're still here? it's over! go home.













































# go!
