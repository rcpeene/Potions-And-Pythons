# Parser.py
# This file contains the code to parse user input and execute player actions
# This file is dependent on Menu.py and is a dependency of PoPy.py

# It consists of five major parts;
# 1. Game startup		(call main menu and instantiate global objects P, W, G)
# 2. Parsing functions	(functions to parse user input)
# 3. Action functions	(action, shortaction, cheat functions called by parse())
# 4. Action dicts		(dictionaries used to call action functions from)
# 5. Parser design		(docstring explaining the design of this file)

from Menu import *


##################
## GAME STARTUP ##
##################

# formatting the prompt window
os.system("mode con:cols=128 lines=32")
os.system("title Potions ^& Pythons")

# import pygetwindow
# win = pygetwindow.getWindowsWithTitle('Potions & Pythons')[0]
# win.size = (128*8, 32*16) #128 x 32 tiles of 8 x 16 pixels


# run intro logo animation
gameIntro()
# print("\n"*64 + logo)

# mainMenu instantiates global objects Player, World, Game
P, W, G = mainMenu()


#######################
## PARSING FUNCTIONS ##
#######################

# checks if a noun refers to an exit, an object in the world or on the player...
# or an in-game definition or a miscellaneous expression
def isMeaningful(noun):
	if noun in G.currentroom.exits.values() or \
	G.inWorld(noun,W) or \
	P.search(noun) or \
	noun in actions or \
	noun in definitions or \
	noun in miscexpressions:
		return True
	return False

# recursively inspects the command, which is a list of words
# combines multiple words into single terms that appear to be a meaningful term.
# returns the command after any relevant words are joined into one term
def nounify(command,i):
	if i >= len(command)-1:
		return command
	possibleNoun = command[i]
	j = i+1
	while j < len(command):
		# possibleNoun is all words between i and j joined
		possibleNoun += ' '+command[j]
		# if new term refers to an rendered object, a location, or a game term:
		# combine words into one element and recur
		if isMeaningful(possibleNoun):
			del command[i:j+1]
			command.insert(i,possibleNoun)
			return nounify(command,i)
		j += 1
	return nounify(command,i+1)

# term must be a pronoun
def replacePronoun(term):
	obj = None
	if term == "it":				obj = G.it
	elif term in {"she","her"}:		obj = G.she
	elif term in {"he","him"}:		obj = G.he
	elif term in {"they","them"}:	obj = G.they
	if obj == None:					return None
	return obj.name

# validates user input and processes into into a command form usable by parse(),
# namely, it returns a list of words without capitals, symbols, or articles
# the last step, nounify(), joins words that may only be meaningful as one term
def processCmd(prompt,saveRawCmd=False):
	rawcommand = input(prompt + "\n> ")
	# take input until input has any non-whitespace characters in it
	while not any(i not in "\t " for i in rawcommand):
		rawcommand = input("> ")
	# for convenience, save raw command in game class
	if saveRawCmd:	G.lastRawCommand = rawcommand.split()
	# lowercase the sentence command, copy it excluding symbols
	rawcommand = rawcommand.lower()
	purecommand = ""
	for i in rawcommand:
		if i in symbols:	purecommand = purecommand + " "
		else:				purecommand = purecommand + i
	# copy command, delimited by spaces, into a list excluding articles
	listcommand = [i for i in purecommand.split() if i not in articles]
	# finally, combine certain words if they appear to make one noun term
	finalcommand = nounify(listcommand,0)
	return finalcommand

def getNoun(prompt):
	return " ".join(processCmd(prompt))

def parseWithoutVerb(prompt,preps):
	dobj = None
	iobj = None
	prep = None
	cmdInput = processCmd(prompt)

	# iterates through the input and assigns...
	# terms based on their position relative to the other terms present
	for term in cmdInput:
		# preposition is defined if the term is a known preposition
		if term in prepositions and prep == None:	prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:			dobj = term
		# indirect object is defined if a prep or dobj has been found
		else:										iobj = term

	if dobj in pronouns:	dobj = replacePronoun(dobj)
	if iobj in pronouns:	iobj = replacePronoun(iobj)

	return dobj,iobj,prep

# called in parse() when a command fails, it simply recurs parse(), and...
# prints a helpful message if user has provided invalid input 3 or more times
# n is the number of times parse() has recurred
def promptHelp(msg,n):
	if msg != "":	print(msg)
	if n >= 2:	print("Enter 'help' for a list of commands")
	if n > 32:	return False	# prevent stack overflow from repeated bad input
	return parse(n+1)	# ask again

# the primary input parsing function for the game
# its purpose is to parse command grammar and call the related action function
# it is called by main() with processCmd() as its first argument
# it is called on infinite loop until it returns True
# it returns True only when the player successfully takes an action in the game
# n denotes how many times parse has recurred
def parse(n):
	command = processCmd("What will you do?",saveRawCmd=True)
	if len(command) == 0:
		return promptHelp("Command not understood",n)
	verb = command[0]	# verb is always first word
	dobj = None			# values are None by default, they may remain None
	iobj = None
	prep = None

	if verb in cheatcodes.keys():
		return cheatcodes[verb](G.lastRawCommand)
	elif verb in shortverbs or verb in statcommands:
		if len(command) != 1:
			return promptHelp(f"The '{verb}' command can only be one word",n)
		if verb.upper() in abilities:
			return P.printAbility(verb.upper())
		return shortactions[verb]()
	elif verb not in verbs:
		return promptHelp(f"'{verb}' is not a valid verb",n)

	# iterates through the command (skips the verb) and assigns...
	# terms based on their position relative to the other terms present
	for term in command[1:]:
		# preposition is defined if the term is a known preposition
		if term in prepositions and prep == None:	prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:			dobj = term
		# indirect object is defined if a prep or dobj has been found
		else:										iobj = term

	if dobj in pronouns:	dobj = replacePronoun(dobj)
	if iobj in pronouns:	iobj = replacePronoun(iobj)

	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	# if action was instant, loop for another command
	if verb in instantactions:	return False
	# if action was not completed for some reason, recur
	if not actionCompleted:		return promptHelp('',n)
	return True


##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################

def Get(command):
	objname = command[1].lower()
	if objname in {"p","player","my"}:
		obj = P
	elif objname in {"g","game"}:
		obj = G
	elif objname in {"here","room"}:
		obj = G.currentroom
	else:
		obj = objSearch(objname,G.currentroom,d=3)
	if obj == None:
		try: obj = W[objname]
		except:	pass
	if obj == None:
		print("Object not found")
		return
	attrString = command[2]
	try:	print(getattr(obj,attrString))
	except:	print("Attribute does not exist")

def Learn(command):
	try:	P.gainxp(int(command[1]))
	except:	print("Value not number")

def Mode(command):
	try:
		G.mode = int(command[1])
		print("mode set to " + str(G.mode))
	except:	print("Value not number")

def Pypot(command):
	try:	P.money = P.money + int(command[1])
	except:	print("Value not number")

def Set(command):
	if command[1] in {"p","player"}:
		obj = P
	else:
		obj = objSearch(command[1],G.currentroom,d=3)
	attrString = command[2]
	val = command[3]
	setStat(obj,attrString,val)

def Teleport(command):
	location = command[1]
	if location in W:	G.changeRoom(W[location],P,W)
	else:				print("Location not in world")

def Test(command):
	pass

def Warp(command):
	try:	G.time += int(command[1])
	except:	print("Value not number")

def Zap(command):
	objname = " ".join(command[1:])
	allObjects = G.getAllObjects(W,getSources=True)
	zappedObjects = 0
	for (obj,source) in allObjects:
		if objname.lower() == obj.name.lower():
			if isinstance(obj,Item):
				obj.Break(G,W,source)
			elif isinstance(obj,Creature):
				obj.death(P,G,W)
			zappedObjects += 1
	print("Zapped objects: " + str(zappedObjects))


#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################

def Cry(): print("A single tear sheds from your eye")
def Dance(): print("You bust down a boogie")
def Examples(): print("\n"*64 + examples)

def Help():
	clearScreen()
	print("\nPlayer Statistics Commands")
	columnPrint(statcommands,10,10)
	print("\nOther Single-Word Commands")
	columnPrint(shortverbs,10,10)
	print("\nVerb Commands (Does not include cheat codes and secret commands)")
	columnPrint(verbs,10,10)
	print("\nType 'info' for information on the game and how to play")

def Info(): print("\n"*64 + gameinfo)

def Laugh(): print("HAHAHAHAHA!")
def Quit():
	if yesno("Are you sure you want to quit? (Anything unsaved will be lost)"):
		sys.exit()
def Return(): return Go(None, G.prevroom.name, None) #go to previous room
def Save(): saveGame(P,W,G)
def Shout(): print("AHHHHHHHHHH")
def Sing(): print("Falalalaaaa")
def Time(): print("Time:", G.time)
def Yawn():	print("This is no time for slumber!")


##################################
## ACTION AND RELATED FUNCTIONS ##
##################################

def Attack(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False

	if iobj == None:
		if len(P.weapons()) == 0:
			iobj = "fist"
		elif P.gear["right"] == Empty() and P.gear["left"] == Empty():
			iobj = getNoun("What will you attack with?")
			if iobj in cancels:
				return False
	weapon = P.weapon
	if iobj != None:
		weapon = P.inGear(iobj)
		if weapon == None:	weapon = P.inInv(iobj)
		if iobj in {"fist","hand"}:		weapon = Hand("your hand","",4,-1)
		if iobj in {"foot","leg"}:		weapon = Foot("your foot","",8,-1)
		if iobj in {"mouth","teeth"}:	weapon = Mouth("your mouth","",4,-1)
		if weapon == None:
			print(f"There is no '{iobj}' in your inventory")
			return False

	if dobj == None:	dobj = getNoun("What will you attack?")
	target = G.currentroom.inOccupants(dobj)
	if target == None:	target = G.currentroom.inContents(dobj)
	if dobj in {"myself","me"}: target = P
	if target == None:
		print(f"There is no '{dobj}' here")
		return False

	if iobj in {"fist","hand","foot","leg","mouth","teeth"}:
		stowedweapons = P.weapon,P.weapon2
		P.weapon,P.weapon2 = weapon.improviseWeapon(),Empty()
	elif weapon not in P.gear.values():
		P.equipInHand(weapon)

	G.setPronouns(target)
	print(f"\nYou attack the {target.name} with {P.weapon.name}")
	if isinstance(target,Creature):		P.attackCreature(target,G,W)
	elif isinstance(target,Item):		P.attackItem(target,G,W)
	if iobj in {"fist","hand","foot","leg"}:
		P.weapon,P.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
	if dobj == None:
		dobj = getNoun("What do you want to bite?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:	I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	if hasMethod(I,"Eat"):
		return Eat(dobj,iobj,prep)
	else:
		return Attack(dobj,"mouth",prep)

	# TODO: if u add the ability to "bite" items, maybe actually damage them...
	# if their durability is low enough or smth. Maybe append the item's...
	# description to include "it has a bite taken out of it"
	# perhaps if player swallows something inedible, take damage?

def Break(dobj,iobj,prep):
	# TODO: potentially just redirect this func to attack, idk
	if prep not in {"with",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to break?")
		if dobj in cancels:
			return False

	I,source = P.search(dobj,getSource=True)
	if I == None:	I,source = G.currentroom.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Break"):
		print("You can't break the " + I.name)
		return False
	I.Break(P,G,source)
	return True

def Carry(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to carry?")
		if dobj in cancels:
			return False

	G.setPronouns(I)
	print("NOT IMPLEMENTED YET!!")

def Cast(dobj,iobj,prep):
	print("casting")

def Catch(dobj,iobj,prep):
	print("catching")

# def Climb(dobj,iobj,prep):
# 	print("climbing")

def Close(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you close?")
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None:	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasattr(I,"open"):
		print("You can't close the " + I.name)
		return False
	if not I.open:
		print(f"The {I.name} is already closed")
		return False
	if hasMethod(I,"Close"):
		I.Close()
	else:
		I.open = False
		print("You close the " + I.name)
	return True

def Craft(dobj,iobj,prep):
	print("crafting")

def Crawl(dobj,iobj,prep):
	print("crawling")

def Cross(dobj,iobj,prep):
	print("crossing")

def Crouch(dobj,iobj,prep):
	print("crouching")

def Cut(dobj,iobj,prep):
	print("cuting")

def Define(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only define one word at once")
		return False
	if dobj == None:
		dobj = getNoun("What term would you like defined?")
		if dobj in cancels:
			return False

	if dobj in definitions:
		print("\n"+definitions[dobj])
		return True
	elif dobj == P.name.lower():
		print(f"\n{P.name}\nThat is you!")
		return True
	print(f"'{dobj}' is unknown")
	return False

def Describe(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only describe one thing at once")
		return False
	if dobj == None:	#if no dobj, ask
		dobj = getNoun("What do you want to be described?")
		if dobj in cancels:
			return False

	D = P.search(dobj)
	if dobj == G.currentroom.name or dobj in {"room","here"}:
		D = G.currentroom
	if D == None:	D = G.currentroom.search(dobj)
	if D == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(D)
	D.describe()
	return True

def Do(dobj,iobj,prep):
	print("doing")

def Dodge(dobj,iobj,prep):
	print("dodgeing")

def Doff(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to doff?")
		if dobj in cancels:
			return False

	I = P.inGear(dobj)
	if I == None or not isinstance(I,Armor):
		print(f"You aren't wearing a '{dobj}'")
		return False

	G.setPronouns(I)
	P.unequip(I)
	print(f"You doff your {I.name}")
	return True

def Don(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to don?")
		if dobj in cancels:
			return False

	I = P.inInv(dobj)
	if I == None:
		print(f"There is no available '{dobj}' in your inventory")
		return False

	if not isinstance(I,Armor):
		print(f"You cannot wear your {I.name}")
		return False
	if I in P.gear.values():
		print(f"You are already wearing your {I.name}")
		return False

	G.setPronouns(I)
	if not P.equipArmor(I):
		return False
	print(f"You don your {I.name}")
	return True

def Drink(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to drink?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Drink"):
		print("You can't drink the " + I.name)
		return False
	I.Drink(P,G,S)
	return True

def Drop(dobj,iobj,prep):
	if prep != None:
		return Put(dobj,iobj,prep)
	if dobj == None:
		dobj = getNoun("What will you drop?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if isinstance(I,Compass) and P.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not yesno(q):
			return False
	print("You drop your " + I.name)
	S.removeItem(I)
	G.currentroom.addItem(I)
	return True

def Dump(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you dump?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	G.setPronouns(I)
	if hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep)
	else:
		return Drop(dobj,iobj,prep)

def Eat(dobj,iobj,prep):
	if prep not in {"with",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to eat?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Eat"):
		print("You can't eat the " + I.name)
		return False
	I.Eat(P,G,S)
	return True

def Enter(dobj,iobj,prep):
	print("entering")

def Equip(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to equip?")
		if dobj in cancels:
			return False

	I = P.inInv(dobj)
	if I == None:
		print(f"There is no available '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if P.inGear(dobj) and P.invNames(lower=True).count(dobj) == 1:
		print(f"Your {dobj} is already equipped")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Armor):		P.equipArmor(I)
	else:						P.equipInHand(I)
	print(f"You equip your {I.name}")
	return True

def Escape(dobj,iobj,prep):
	print("escapeing")

def Exit(dobj,iobj,prep):
	print("exiting")

def Feed(dobj,iobj,prep):
	print("feeding")

def Fill(dobj,iobj,prep):
	print("filling")

def Find(dobj,iobj,prep):
	print("finding")

def Fish(dobj,iobj,prep):
	print("fishing")

def Follow(dobj,iobj,prep):
	print("following")

def Give(dobj,iobj,prep):
	print("giveing")

def GoVertical(dir):
	if P.hasCondition("fly"):
		newroom = G.currentroom.exits[dir]
		print(f"You fly {dir}!")
		return G.changeRoom(W[newroom],P,W)

	objname = getNoun(f"What will you go {dir}?")
	obj = G.currentroom.search(objname)
	if obj == None:
		print(f"There is no '{objname}' to go {dir} here")
		return False
	if hasMethod(obj,"Traverse"):
		return obj.Traverse(P,W,G,dir)

def Go(dobj,iobj,prep):
	preps = {"down","through","to","toward","up","in","into","on","onto"}
	dir = None
	if dobj == None and iobj == None and prep == None:
		dobj,iobj,prep = parseWithoutVerb("Where will you go?",preps)
	if dobj == None:	dobj = iobj
	if dobj == None:	dobj = prep
	if prep in directions.values():
		dir = prep
		prep = None
	if prep != None and prep not in preps:
		print("Command not understood")
		return False

	if dobj == "back":	dobj = G.prevroom.name
	if dobj == G.currentroom.name:
		print("You are already there")
		return False
	if not any(isinstance(item,Compass) for item in P.inv):
		if dobj != "back" and prep not in {"up","down"}:
			print("\nWithout your compass, you go in a random direction")
			dobj = choice(list(G.currentroom.exits.values()))

	if dobj in directions.keys():
		dobj = directions[dobj]
	exits = G.currentroom.exits
	if dobj in exits.keys():
		dobj = exits[dobj]

	if "up" in exits.keys() and exits["up"] == dobj:
		return GoVertical("up")
	if "down" in exits.keys() and exits["down"] == dobj:
		return GoVertical("down")
	if dobj in exits.values():
		return G.changeRoom(W[dobj],P,W)
	passage = G.currentroom.inContents(dobj)
	if passage:
		if hasMethod(passage,"Traverse"):
			return passage.Traverse(P,W,G,dir)

	if dobj in directions.values():
		print(f"There is no exit leading {dobj} here")
	else:
		print(f"There is no exit leading to a '{dobj}' here")
	return False

# add in the ability to try to 'grab' creatures?
def Grab(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you grab?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' to grab here")
		return False

	G.setPronouns(I)
	if isinstance(I,Item):
		return Take(dobj,iobj,prep)
	elif isinstance(I,Creature):
		return Restrain(dobj,iobj,prep)
	else:
		print(f"You cannot grab the {I.name}")
		return False

def Hide(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		print("Command not understood")
		return False

	if dobj == None:	dobj = iobj
	if dobj == None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not isinstance(I,Fixture):
		print("You can't hide behind " + I.name)
		return False

	P.addCondition("hiding",-3)
	return

def Ignite(dobj,iobj,prep):
	print("igniteing")

def Insert(dobj,iobj,prep):
	print("inserting")

def Jump(dobj,iobj,prep):
	print("jumping")

def Kick(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you kick?")
		if dobj in cancels:
			return False
	return Attack(dobj,"foot","with")

def Kill(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False
	if dobj in {"myself","me"}:
		if yesno("Are you sure you want to kill yourself?"):
			P.death()
			return True
		print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)

def Lick(dobj,iobj,prep):
	print("licking")

def Light(dobj,iobj,prep):
	print("lighting")

def Listen(dobj,iobj,prep):
	print("listening")

def Lock(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False

	if dobj == None:
		dobj = getNoun("What will you lock?")
		if dobj in cancels:
			return False
	I = G.currentroom.search(dobj)
	if I == None: I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Lock"):
		print(f"The {I.name} doesn't lock")
		return False

	if iobj == None:
		iobj = getNoun("What will you lock with?")
		if iobj in cancels:
			return False
	K = P.search(iobj)
	if K == None:
		print(f"There is no '{iobj}' in your inventory")
		return False
	if not isinstance(K,Key):
		print(f"You can't lock with the {K.name}")
		return False

	return I.Lock(K)

def Look(dobj,iobj,prep):
	if prep not in {"at","in","inside","into","on","through",None}:
		print("Command not understood")
		return False
	if dobj == None:	dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you look at?")
		if dobj in cancels:
			return False

	if dobj in {"room", "here"}:
		G.currentroom.describe()
		return True
	if dobj in {"me","myself",P.name}:
		print("You are " + P.desc)
		return True
	L = G.currentroom.search(dobj)
	if L == None: L = P.search(dobj)
	if L == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(L)
	L.describe()
	if hasMethod(L,"Look"):
		L.Look()
	return True

def Mount(dobj,iobj,prep):
	print("mounting")

def Move(dobj,iobj,prep):
	print("moveing")

def Open(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you open?")
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None: I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Open"):
		print("You can't open the " + I.name)
		return False
	if hasattr(I,"locked") and I.locked:
		print(f"The {I.name} is locked")
		return False
	I.Open()
	return True

def Pet(dobj,iobj,prep):
	print("peting")

def Play(dobj,iobj,prep):
	print("playing")

def Point(dobj,iobj,prep):
	print("pointing")

def Pour(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you pour?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Pour"):
		print(f"You can't pour the {I.name}")
		return False

	R = None
	if iobj != None:
		if iobj == "here":	R = G.currentroom
		R = P.search(iobj)
		if R == None:
			R = G.currentroom.search(iobj)
		if R == None:
			print(f"There is no '{iobj}' here")
			return False

	if prep == None:	prep = "on"
	if R != None:		print(f"You pour your {I.name} {prep} the {R.name}")
	else:				print(f"You pour out your {I.name}")
	I.Pour(P,G,S)
	return True

def Pray(dobj,iobj,prep):
	print("praying")

def Press(dobj,iobj,prep):
	print("pressing")

def Pull(dobj,iobj,prep):
	print("pulling")

def Punch(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you punch?")
		if dobj in cancels:
			return False
	return Attack(dobj,"fist","with")

def Push(dobj,iobj,prep):
	print("pushing")

def Put(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you put?")
		if dobj in cancels:
			return False
	if iobj == None:
		iobj = getNoun(f"What will you put your {dobj} in?")

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	if isinstance(I,Compass) and P.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not yesno(q):
			return False
	G.setPronouns(I)

	R = P.search(iobj)
	if iobj == "here":	R = G.currentroom
	if R == None:
		R = G.currentroom.search(iobj)
	if R == None:
		print(f"There is no '{iobj}' here")
		return False
	if not isinstance(R,Table) and not isinstance(R,Box):
		print(f"You can't put the {I.name} {prep} the {R.name}")
		return False

	outprep = "on" if isinstance(R,Table) else "in"
	if iobj == "here":	print(f"You put your {I.name} here")
	else:				print(f"You put your {I.name} {outprep} the {R.name}")
	S.removeItem(I)
	R.addItem(I)
	return True

def Release(dobj,iobj,prep):
	print("releaseing")

# def Remove(dobj,iobj,prep):
# 	print("removeing")

def Rest(dobj,iobj,prep):
	print("resting")

def Restrain(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False

	if dobj == None:
		dobj = getNoun("What will you restrain?")
		if dobj in cancels:
			return False
	C = G.currentroom.search(dobj)
	if C == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(C)
	if not isinstance(C,Creature):
		print(f"You can't restrain the {C.name}")
		return False

	I = None
	if iobj != None:
		I = P.search(iobj)
		if I == None:
			print(f"There is no '{iobj}' in your inventory")
			return False
		if not hasMethod(I,"RestrainWith"):
			print(f"You can't restrain with the {I.name}")
			return False

	if not C.Restrain(P,I):
		print(f"You fail to restrain the {C.name}")
		return False
	print(f"You restrain the {C.name}")
	return True

def Ring(dobj,iobj,prep):
	print("ringing")

def Rub(dobj,iobj,prep):
	print("rubbing")

def Search(dobj,iobj,prep):
	print("searching")

def Shoot(dobj,iobj,prep):
	print("shooting")

def Shove(dobj,iobj,prep):
	print("shoveing")

def Smell(dobj,iobj,prep):
	print("smelling")

def Steal(dobj,iobj,prep):
	print(f"stealing {dobj} {prep} {iobj}")

def Struggle(dobj,iobj,prep):
	print("struggleing")

def Swim(dobj,iobj,prep):
	print("swiming")

def Talk(dobj,iobj,prep):
	print("talking")

def Throw(dobj,iobj,prep):
	print("throwing")

def Tie(dobj,iobj,prep):
	print("tieing")

def Take(dobj,iobj,prep):
	if prep not in {"from","in","inside","up",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you take?")
		if dobj in cancels:
			return False
	if dobj in {"all","everything","it all"}:
		C = [item.name.lower() for item in G.currentroom.contents if not isinstance(item,Fixture)]
		taken = False
		for name in C:
			taken = Take(name,iobj,prep) or taken
		return taken

	I,path = objSearch(dobj,G.currentroom,d=2,getPath=True,reqSource=iobj)
	if I == None:	I,path = objSearch(dobj,P,d=2,getPath=True,reqSource=iobj)
	if I == None:
		if prep in {None,"up"}:	print(f"There is no '{dobj}' here")
		else:				print(f"There is no '{dobj}' in a '{iobj}' here")
		return False
	if not isinstance(I,Item):
		print("You can't take the " + dobj)
		return False
	G.setPronouns(I)

	S = path[0]		#S is the 'source' object, the object containing I
	if isinstance(S,Creature) and prep == "from":	return Steal(dobj,iobj,prep)
	count = S.contentNames().count(I.name)
	if S is P:
		print("You can't take from your own Inventory")
		return False

	if S is G.currentroom:		appendstring = ""
	elif P in path:				appendstring = " from your " + S.name
	else:						appendstring = " from the " + S.name
	det = "the" if count == 1 else "a"
	msg = f"You take {det} {I.name}{appendstring}"
	return P.obtainItem(I,S,W,G,msg)

def Touch(dobj,iobj,prep):
	print("touching")

def Trip(dobj,iobj,prep):
	print("triping")

def Unequip(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in cancels:
			return False

	I = P.inGear(dobj)
	if I == None:
		print(f"You do not have a '{dobj}' equipped")
		return False

	G.setPronouns(I)
	print(f"You unequip your {I.name}")
	P.unequip(I)
	return True

def Unlock(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you unlock?")
		if dobj in cancels:
			return False
	I = G.currentroom.search(dobj)
	if I == None: I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Lock"):
		print(f"The {I.name} doesn't lock")
		return False

	if iobj == None:
		iobj = getNoun("What will you unlock with?")
		if iobj in cancels:
			return False
	K = P.search(iobj)
	if K == None:
		print(f"There is no '{iobj}' in your inventory")
		return False
	if not isinstance(K,Key):
		print(f"You can't unlock with the {K.name}")
		return False

	return I.Unlock(K)

def Untie(dobj,iobj,prep):
	print("untieing")

def Use(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you use?")
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None:	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' to use here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Use"):
		print(f"You can't use the {I.name}")
		return False
	I.Use(P,W,G)
	return True

def Wait(dobj,iobj,prep):
	print("waiting")

def Wave(dobj,iobj,prep):
	print("waveing")


##################################
## ACTION FUNCTION DICTIONARIES ##
##################################

cheatcodes = {
	"\\get":Get,
	"\\zap":Zap,
	"\\lrn":Learn,
	"\\mod":Mode,
	"\\pot":Pypot,
	"\\set":Set,
	"\\tst":Test,
	"\\tpt":Teleport,
	"\\wrp":Warp
}

shortactions = {
"abilities":P.printAbilities,
"back":Return,
"clear":clearScreen,
"cry":Cry,
"dance":Dance,
"examples":Examples,
"gear":P.printGear,
"help":Help,
"hp":P.printHP,
"info": Info,
"information": Info,
"inventory":P.printInv,
"inv":P.printInv,
"laugh":Laugh,
"level":P.printLV,
"lv":P.printLV,
"money":P.printMoney,
"mp":P.printMP,
"quit":Quit,
"return":Return,
"here":G.describeRoom,
"rp":P.printRP,
"save":Save,
"scream":Shout,
"shout":Shout,
"sing":Sing,
"stats":P.printStats,
"status":P.printStatus,
"time":Time,
"traits":P.printTraits,
"weapons":P.printWeapons,
"xp":P.printXP,
"yell":Shout,
"yawn":Yawn
}

actions = {
"attack":Attack,
"bite":Bite,
"break":Break,
"build":Craft,
"carry":Carry,
"cast":Cast,
"catch":Catch,
"climb":Go,
"close":Close,
"craft":Craft,
"crawl":Crawl,
"create":Craft,
"cross":Cross,
"crouch":Crouch,
"cut":Cut,
"define":Define,
"describe":Describe,
"do":Do,
"dodge":Dodge,
"doff":Doff,
"don":Don,
"drink":Drink,
"drop":Drop,
"duck":Crouch,
"dump":Dump,
"eat":Eat,
"empty":Dump,
"enter":Go,
"equip":Equip,
"escape":Escape,
"examine":Look,
"exit":Exit,
"feed":Feed,
"feel":Touch,
"fight":Attack,
"fill":Fill,
"find":Find,
"fish":Fish,
"follow":Follow,
"get":Take,
"give":Give,
"go":Go,
"grab":Grab,
"grapple":Grab,
"head":Go,
"hear":Listen,
"hide":Hide,
"hit":Attack,
"ignite":Ignite,
"insert":Insert,
"jump":Jump,
"kick":Kick,
"kill":Kill,
"lay":Crouch,
"leave":Exit,
"lick":Lick,
"light":Ignite,
"listen":Listen,
"lock":Lock,
"look":Look,
"make":Craft,
"mount":Mount,
"move":Move,
"obtain":Take,
"open":Open,
"pet":Pet,
"pick":Take,
"pick up":Take,
"place":Put,
"play":Play,
"point":Point,
"pour":Pour,
"pray":Pray,
"press":Press,
"pull":Pull,
"punch":Punch,
"push":Push,
"put":Put,
"put down":Put,
"put on":Don,
"quaff":Drink,
"read":Look,
"release":Release,
"remove":Unequip,
"rest":Rest,
"restrain":Restrain,
"ride":Mount,
"ring":Ring,
"rub":Rub,
"run":Go,
"search":Search,
"set":Put,
"shoot":Shoot,
"shove":Shove,
"shut":Close,
"slap":Punch,
"sleep":Rest,
"slice":Cut,
"smell":Smell,
"sniff":Smell,
"speak":Talk,
"steal":Steal,
"stomp":Kick,
"stow":Unequip,
"strike":Attack,
"struggle":Struggle,
"swim":Swim,
"take":Take,
"take off":Doff,
"talk":Talk,
"taste":Lick,
"throw":Throw,
"tie":Tie,
"tinker":Craft,
"toss":Throw,
"touch":Touch,
"travel":Go,
"trip":Trip,
"unequip":Unequip,
"unlock":Unlock,
"untie":Untie,
"use":Use,
"view":Look,
"wait":Wait,
"walk":Go,
"wave":Wave,
"wear":Don
}


###########################
## PARSER GENERAL DESIGN ##
###########################

design = '''
INTRO

the game basically runs an infinite loop, repeatedly taking player input. After a lot of processing and attempting to parse input, either the input is invalid and the loop repeats, or the input was valid, and some action is completed (and then the loop repeats). In principle, the parser delegates actions to action functions, and the action functions alter something about the player object, about the world object, or both (with a bit more flavor text and panache of course)

Valid input must always begin with a valid verb. After input is processed, the "action function dictionary" maps the verb to the corresponding action function, and the action function is called, passing in the rest of the player's valid input as parameters.

Using the passed-in command information, the action function may ask for additional information. It will then either complete the action or fail to complete it depending on the specific circumstances involved.



NOTES ON PARSING AND INTERFACING BETWEEN OBJECTS AND VERBS

there is a global dictionary of verb: action() pairs, where each verb string maps to an action() function, multiple verbs can map to the same action

every action function must corroborate its parameters (prepositions and objects) to check if that action can be done, given the state of the player object and the environment (the current room)

action functions will return false if the command input is not understood
action function will return true as long as action was understood, even if the action was not achieved

every item should have a method for each action that is possible to be done to itself, called a reaction() function. For example, if it is possible to break a bottle object, it must contain a Break() reaction method.

if the item can be used as an indirect object, it should be passed into the direct object's reaction() function

some action functions only serve to redirect to other functions depending on the preposition and object parameters passed in



INPUT AND PREPROCESSING:

processCmd() takes input in the form of a string
(loop until input is not an empty string)

convert to total lowercase

remove punctuation, and invalid symbols
(maybe except some symbols for special situations)

nounify

split string into list delimited by spaces

remove articles, and determiners



OUTLINE FOR MAIN PARSER FUNCTION:

verb = word1
validate verb
if verb is a cheat code:
	call cheat function
	return
if there's one word:
	if verb is a shortverb (doesnt require an object):
		pass
if there's two words:
	dobj = word2
if there's three words:
	if word2 is a preposition:
		prep = word2
		iobj = word3
	elif word3 is a preposition:
		dobj = word2
		prep = word3
	else:
		dobj = word2
		iobj = word3
if there's four words:
	dobj = word2
	prep = word3
	iobj = word4
if there's more than four words:
	"invalid input, command too long"
call action function:
	validate preposition
	validate dobj
	validate/check for iobj
	//shortverbs don't need to validate these
	if verb returns false:
		print("Im sorry, i didnt understand that")



GENERAL FORM OF AN ACTION FUNCTION (THERE ARE MANY EXCEPTIONS):

def action(dobj,iobj,prep)
	if proposition not in verb's list of valid prepositions
		return false
		//many actions would include an "" empty preposition, they dont need one

	if the verb requires a direct object, and there is none
		dobj = askforobject();

	if the verb requires an indirect object, and there is none
		iobj = askforobject():

	validate/triage the choice of the direct object
	depending on the action, iterate through room, then iterate through inv
	if dobj == "all"
		if no possible objects in room
			"there's nothing in here to [verb]"
		else
			call action on all possible items in room
	if any item/creature name == dobj
		select item or creature
	if not
		"there is no [obj]"
		return false

	if there's an indirect object
		validate/triage the choice of the indirect object
		check if this verb is in the iobj's set of use verbs
		depending on the action, iterate through inv, then iterate through room
			if any item/creature name == iobj
			select item or creature

	if prep == prep1
		do certain action, or call other action
		...
	elif prep == prep2
		do a different action
		...
	else
		do action as though there is no prep (if possible)

		ping the direct object like so;
		if(dobj.hasattr(action) and callable(dobj.action))
			dobj.action(iobj)


'''
