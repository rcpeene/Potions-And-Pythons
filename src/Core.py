# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Creatures.py, Items.py, Menu.py, and Interpreter.py
# and is dependent on Data.py

# It consists of three main parts;
# 1. Core functions			(used throughout gameplay)
# 2. Dialogue Classes		(DialogueNode and DialogueTree)
# 3. Core class definitions	(GameObject, Game, Room, Item, Creature, Player, etc.)


import sys, os, re, subprocess
import tempfile
import subprocess
import atexit
from contextlib import contextmanager, nullcontext
try:
	import msvcrt
	sys.stdout.reconfigure(encoding='utf-8')
except:
	import termios, select, tty, shlex

from time import sleep
from random import choice,choices,randint,sample,shuffle
from math import ceil, floor, sqrt
from bisect import insort

import Data



####################
## CORE FUNCTIONS ##
####################


# Used to determine if a term has a match with any of an object's names
def nameMatch(term,obj):
	if term is None or obj is None:
		return False
	term = term.lower()
	# print(term, obj.name, obj.nounPhrase(), obj.nounPhrase('the'))
	if isinstance(obj, Room):
		return term == obj.name.lower() or term == "room"
	if obj is player.parent and term in ("here","this place"):
		return True
	return term == obj.name.lower() or \
		term == obj.nounPhrase().lower() or \
		term == obj.nounPhrase('the').lower() or \
		term in obj.aliases


# retrieves a class object with className from the modules list
# returns None if no such object exists
def strToClass(className,moduleNames):
	classObject = None
	for moduleName in moduleNames:
		try:
			classObject = getattr(sys.modules[moduleName],className)
		except:
			continue
	return classObject


# returns bool indicating whether an obj has a method with the given string name
# used as a shortcut for more readable code than the traditional method
def hasMethod(obj,methodName):
	possibleMethod = getattr(obj,methodName,None)
	if not possibleMethod:
		possibleMethod = getattr(obj.__class__,methodName,None)
	if possibleMethod != None and callable(possibleMethod):
		return True
	return False


# get key for a room in the world
def getRoomKey(room,world):
	for key,value in world.items():
		if value == room:
			return key


# clear screen on windows or unix systems
def clearScreen(delay=0.1):
	if os.name == "nt":
		os.system("cls")
		# ensure screen isn't being cleared during subsequent output
		sleep(delay)
	else:
		os.system("clear")


# clears pending keyboard input. strategy varies by operating system.
def flushInput():
	try:
		while msvcrt.kbhit():
			msvcrt.getch()
	except NameError:
		try:
			termios.tcflush(sys.stdin,termios.TCIOFLUSH)
		except termios.error:
			pass


# checks for any keyboard input in buffer
def kbInput():
	try:
		dr,dw,de = select.select([sys.stdin], [], [], 0.00001)
		return dr != []
	except:
		return msvcrt.kbhit()


# color text using ANSI formatting
def tinge(color,*args):
	if len(args) > 0 and color is not None:
		args = list(args)
		c = Data.colorCodes[color]
		args[0] = f"\033[{c}m" + args[0]
		args[-1] = args[-1] + f"\033[0m"
	return tuple(args)


# censor string based on in-text tags, denoting a required ability level
# remove sections of text that follow a tag whose criterion is not met
# allow specified inclusive ranges or thresholds
# unprefixed tags use KNWL; for instance "|5+|", "|KNWL 5+|", or "|INVS 5+|"
def censor(text):
	# this detects tags, of the form specified above
	# also consumes an optional preceding newline and following space
	tagPattern = re.compile(
		r"\n?\|[ \t]*(?:(?P<ability>KNWL|INVS)[ \t]+)?"
		r"(?P<criterion>\d+[ \t]*(?:[+-]|:[ \t]*\d+)?[ \t]*)\| ?",
		re.IGNORECASE)
	tags = list(tagPattern.finditer(text))
	if not tags:
		return text

	# determine if the selected player ability meets the tag criterion
	def playerMeets(ability,criterion):
		ability = ability.upper() if ability else "KNWL"
		value = 100 if ability in ("KNWL","INVS") and player.hasStatus("sagacity") \
			else getattr(player,ability)()
		criterion = re.sub(r"\s", "", criterion)
		if criterion.endswith("+"):
			return value >= int(criterion[:-1])
		if criterion.endswith("-"):
			return value <= int(criterion[:-1])
		if ":" in criterion:
			lower,upper = map(int,criterion.split(":"))
			return lower <= value <= upper
		return value == int(criterion)

	# accept any text before the first tag
	sections = [text[:tags[0].start()]]
	# append sections of text that meet the player's knowledge criterion
	for idx,tag in enumerate(tags):
		sectionEnd = tags[idx+1].start() if idx+1 < len(tags) else len(text)
		if playerMeets(tag.group("ability"),tag.group("criterion")):
			sections.append(text[tag.end():sectionEnd])
	return "".join(sections)


# replace inline color tags with ANSI formatting
# under insanity, each opening tag becomes a random color
def primer(text):
	tagPattern = re.compile(r"</>|<(?P<color>[^<>])>")

	def replaceTag(tag):
		if tag.group(0) == "</>":
			if player.hasStatus("apathy"):
				return f"\033[{Data.colorCodes['w']}m"
			return "\033[0m"
		color = tag.group("color")
		if color not in Data.colorCodes:
			return ""
		if player.hasStatus("apathy") and color != "k":
			color = "w"
		elif player.hasStatus("insanity"):
			color = choice(tuple(Data.colorCodes))
		return f"\033[{Data.colorCodes[color]}m"

	return tagPattern.sub(replaceTag,text)


# calculate lengths of displaying string by ignoring formatting chars
def displayLength(text):
	# Regular expression to match ANSI escape sequences
	# ansi_escape = re.compile(r"\033\[[0-9;]*m")
	l = len(ANSI_ESCAPE.sub("", text.replace("\n","")))
	return l


def formatColorCodes(text):
	for color,code in Data.colorCodes.items():
		text = text.replace(f"<{color}>",f"\033[{code}m")
	text = text.replace("<x>","\033[37m")
	return text


# print text to user, with options for color, delay, sep, end, and outfile
# also manipulates the output based on player status effects
def Print(*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,outfile=None):
	if (game.silent or player.hasStatus("asleep")) and allowSilent:
		return 0

	# preprocessing to handle conditions that affect text content
	# colors 'k' and 'y' represent interface and dialogue respectively
	args = [primer(censor(str(arg))) for arg in args]
	if not player.canNavigate() and color not in ("k","y"):
		args = [ambiguateDirections(arg) for arg in args]
	if player.hasStatus("stupidity") and color not in ("k","y"):
		args = [ambiguateNumbers(arg,grammatical=True) for arg in args]
		# don't misspell in stats sidepanel
		if outfile in (None,sys.stdout):
			args = [misspell(arg) for arg in args]

	# set outfile, color, delay, sep
	if outfile is None:
		outfile = sys.stdout
	if player.hasStatus("apathy") and color != "k":
		color = "w"
	elif player.hasStatus("insanity") and color != "k" and outfile is sys.stdout:
		color = choices(list(Data.colorCodes.keys()),[1]*7 + [28])[0]
	if delay is None:
		if player.hasStatus(("dead","slowness")): delay = 0.03
		else: delay = 0.001
	if sep is None:
		sep=" " if len(args) > 1 else ""

	# save printLength for return, add color formatting
	printLength = sum(displayLength(s) for s in args) + \
		displayLength(sep)*(len(args)-1) + displayLength(end)
	if color is not None:
		args = tinge(color,*args)
	elif any(ANSI_ESCAPE.search(arg) for arg in args):
		args[-1] += "\033[0m"

	# output text
	if game.mode == 1 or delay is None or outfile is not sys.stdout:
		print(*args,end=end,sep=sep,file=outfile)
		return printLength
	sleep(delay)
	outfile.flush()
	for arg in args:
		for char in str(arg):
			# user keyboard input speeds up text output
			if kbInput() and not player.hasStatus("slowness"):
				delay = 0
			outfile.write(char)
			outfile.flush()
			sleep(delay)
		outfile.write(sep)
		outfile.flush()
	sleep(delay)
	outfile.write(end)
	outfile.flush()
	sleep(delay)
	return printLength


# waits for any keyboard input on windows and unix
def waitInput(text=None,**kwargs):
	sys.stdout.flush()
	if text is not None:
		Print(text,allowSilent=False,**kwargs)
	# just pass if in test mode
	if game.mode == 1:
		return True
	flushInput()
	if os.name == 'nt':  # For Windows
		msvcrt.getch()
	else:  # For Unix-based systems
		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(fd)
			sys.stdin.read(1)  # Wait for a single keypress
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# moves the print cursor nlines up or down, option to clear intervening lines
def movePrintCursor(nlines,clear=False,clearLast=True,outfile=None):
	if outfile is None:
		outfile = sys.stdout
	step = 1 if nlines > 0 else -1  # direction
	for i in range(abs(nlines)):
		# Move one line in the desired direction
		if step > 0:
			outfile.write("\033[1A")  # up one line
		else:
			outfile.write("\033[1B")  # down one line
		outfile.flush()

		# Clear that line if requested
		if clear and (clearLast or i != abs(nlines)-1):
			outfile.write("\r\033[2K")
			outfile.flush()

	# Make sure cursor is at start of final destination line
	outfile.write("\r")
	outfile.flush()


# print prompt, print cue, and read in user input
def Input(prompt="",cue="\n> ",low=True,delay=None,color=None):
	sys.stdout.flush()
	# should never be silent when asking for input
	Print(prompt,end="",delay=delay,color=color,allowSilent=False)
	Print(cue,end="",delay=0,color=color,allowSilent=False)
	ret = input()
	if low:
		ret = ret.lower()
	return ret


# gets input with a prompt and a cue, locks the line and repeats until accepted
def InputLock(prompt="",cue="\n> ",acceptKey=None,low=True,delay=None,color=None):
	if acceptKey is None:
		acceptKey = lambda inp: inp.strip()
	cueLines = cue.count("\n")+1 # account for the newline from input

	Print(prompt,end="",delay=delay,color=color,allowSilent=False)

	# leave an aesthetic buffer so the cue is never at the very bottom of the screen
	print("\n"*cueLines,end="")
	movePrintCursor(cueLines,clear=True,clearLast=False)

	while True:
		sys.stdout.flush()
		inp = Input(prompt="",cue=cue,low=low,delay=delay,color=color)
		if acceptKey(inp):
			return inp
		flushInput()
		movePrintCursor(cueLines,clear=True,clearLast=False)


# loops until input is cancelled by user or accepted, provides informative messages
def InputLoop(prompt,cue="> ",acceptKey=None,escapeKey=None,refuseMsg="",
			  helpMsg="Type 'cancel' to undo.",color=None,delay=None):
	if acceptKey is None:
		acceptKey = lambda inp: inp
	if escapeKey is None:
		escapeKey = lambda inp: inp in Data.cancels
	if refuseMsg != "":
		refuseMsg += "\n"
	if helpMsg != "":
		helpMsg += "\n"

	invalid_count = 0
	inp = InputLock(prompt,"\n"+cue,color=color,delay=delay)
	while True:
		if escapeKey(inp):
			return None
		acceptInp = acceptKey(inp) 
		if acceptInp is not None:
			return acceptInp
		Print(refuseMsg,end="",color="k",delay=delay)
		invalid_count += 1
		if invalid_count == 2:
			# Print(helpMsg,color="k",delay=delay)
			refuseMsg = refuseMsg + helpMsg
		inp = InputLock("",cue,color=color,delay=delay)


# prints a question, loops until user answers yes or no, returns True/False
def yesno(question,delay=None,color=None):
	def acceptKey(inp):
		if inp in Data.yesses:
			return True
		elif inp in Data.noes:
			return False
		else:
			return None
	refuseMsg = "Enter yes or no."
	return InputLoop(question,acceptKey=acceptKey,escapeKey=None,helpMsg="",
	refuseMsg=refuseMsg,color=color,delay=delay)


# print delay and flushes any intervening input
def delay(seconds):
	flushInput()
	sleep(seconds)
	flushInput()


# prints a timed ellipsis, used for dramatic transitions
def ellipsis(n=3,color=None):
	for _ in range(n):
		delay(1)
		Print(".",color=color,delay=0,allowSilent=False)
	delay(1)


# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
# b is the number of buffer spaces between columns
def columnPrint(l,n,w=None,b=1,delay=0,color=None,inplace=False,outfile=None):
	# automatically set column width based on longest item
	termLengths = [displayLength(term)+b for term in l]
	if w is None:
		w = max(termLengths)+b
	assert w > 1

	nRowsPrinted = 1
	# k is the number of characters that have been printed in the current row
	k = 0
	# for each string element in l
	for term, length in zip(l,termLengths):
		# all terms are trailed by b buffer spaces
		buf = (" "*b)
		# if the string is longer than remaining row width
		# print on a new row
		if length > (n*w) - k:
			if inplace:
				movePrintCursor(-1,outfile=outfile)
				newline=""
			else:
				newline="\n"
				nRowsPrinted += 1
			k = Print(newline+term+buf,end="",delay=delay,color=color,outfile=outfile)
		# if the string is short enough, print it, increment k
		else:
			k += Print(term+buf,end="",delay=delay,color=color,outfile=outfile)
		# to preserve column alignment, print spaces until k is divisble by w
		spaces = (-k % w)
		k += Print(spaces * ' ',end="",delay=delay,color=color,outfile=outfile)
	if not inplace:
		Print(outfile=outfile)
	return nRowsPrinted


# capitalizes the first letter of all the words in a string
# if c is given, then only capitalize the first c words
def capWords(string,c=-1):
	listString = string.split(' ')
	cappedString = ''
	for idx,word in enumerate(listString):
		if len(word) > 0:
			if c != -1 and idx < c:
				cappedString += word[0].upper() + word[1:] + ' '
			else:
				cappedString += word + ' '
	# removes trailing space character
	return cappedString[0:-1]


# gets first index encountered of any substrings within text
# returns end of text if none found
def findFirst(text,substrs):
	idxs = [text.find(substr) for substr in substrs]
	idxs = [i for i in idxs if i != -1]
	if not idxs:
		return len(text)
	return min(idxs)


# uses first word of verbString (assumes its a verb) and conjugates it based on noun
# returns whether a word is an adverb: a known adverbial, or an -ly word
# that isn't a known -ly verb
def isAdverb(word):
	adverbials = {"no","longer","still","now","never","always","once","again",
		"almost","soon","often"}
	lyVerbs = {"fly","rely","apply","rally","ally","bully","tally","dally",
		"sully","comply","imply","reply","supply","multiply"}
	word = word.lower()
	if word in adverbials:
		return True
	return word.endswith("ly") and word not in lyVerbs


def conjugate(noun,verbString):
	irregulars = (('has','have'),('is','are'),("isn't","aren't"),('was','were'))
	sibilants = ("s","sh","ch","x","z","o")
	modals = {"can","can't","cannot","could","couldn't","may","might","must",
		"shall","shan't","should","shouldn't","will","won't","would","wouldn't"}

	# get the first word (assumed to be a verb) that begins verbString
	if verbString.startswith(" "):
		verbString = verbString[1:]
	firstWordEnd = findFirst(verbString,tuple(" .,!?"))
	supposedVerb = verbString[:firstWordEnd]
	remainder = verbString[firstWordEnd:]
	assert len(supposedVerb) > 1
	if supposedVerb.lower() in modals:
		return supposedVerb + remainder

	# leading adverbs pass through; the real verb that follows conjugates
	if isAdverb(supposedVerb) and remainder.strip(" .,!?"):
		return supposedVerb + " " + conjugate(noun,remainder)
	verb = supposedVerb

	# conjugate to infinitive form
	if noun.lower() in ("you","they"):
		# irregular verbs (is -> are)
		for thirdPerson,infinitive in irregulars:
			if verb == thirdPerson:
				return infinitive + remainder
		# flies -> fly
		if verb.endswith("ies") and len(verb) > 3:
			return verb[:-3] + "y" + remainder
		# mixes, mashes, goes -> mix, mash, go
		elif verb.endswith("es") and verb[:-2].endswith(sibilants):
			return verb[:-2] + remainder
		# runs -> run, but kiss -> kiss
		elif verb.endswith("s") and not verb.endswith("ss"):
			return verb[:-1] + remainder
		# run, fly, mix -> run, fly, mix
		else:
			return verb + remainder

	# conjugate to third-person singular form
	else:
		# irregular verbs (is -> are)
		for thirdPerson,infinitive in irregulars:
			if verb == infinitive:
				return thirdPerson + remainder
		# flies, runs, mixes -> flies, runs, mixes
		if verb.endswith("s"):
			return verb + remainder
		# fly -> flies
		if verb.endswith("y") and verb[-2] not in "aeiou":
			return verb[:-1] + "ies" + remainder
		# mix, mash, go -> mixes, mashes, goes
		elif verb.endswith(sibilants):
			return verb + "es" + remainder
		# run -> runs
		else:
			return verb + "s" + remainder


# returns the ordinal string for a number n
def ordinal(n):
	lastDigit = n % 10
	penultimateDigit = (n % 100) // 10
	if penultimateDigit == 1: return str(n) + "th"
	if lastDigit == 1: return str(n)+"st"
	elif lastDigit == 2: return str(n)+"nd"
	elif lastDigit == 3: return str(n)+"rd"
	else: return str(n)+"th"


# cleans a string by removing surrounding punctuation and lowercasing
def clean(string):
	if not string: return ""
	return string.lower().rstrip(Data.symbols).strip("'\"")


# preserve capitalization and the punctuation runs around replaced tokens
def formatReplacement(oldTokens,newToken):
	symbols = Data.symbols + "'\""
	firstToken = oldTokens[0]
	lastToken = oldTokens[-1]
	# find the run of leading punctuation symbols
	prefixLength = len(firstToken) - len(firstToken.lstrip(symbols))
	prefix = firstToken[:prefixLength]
	# and the run of trailing punctuation symbols
	suffix = lastToken[len(lastToken.rstrip(symbols)):]
	# also preserve capitalization of the first token
	coreToken = firstToken[prefixLength:]
	if coreToken and coreToken[0].isupper():
		newToken = newToken.capitalize()
	return prefix + newToken + suffix


# helper for ambiguateDirections()
# when removing strings but want to keep grammar structure
# takes a list of strings and a given index to remove
# lends the capitalization of removed string to following string,
# lends punctuation of removed string to preceding string
# then removes the string at given index
def subsume(lst,idx):
	# lend punctuation to previous string
	if idx > 0 and lst[idx][-1] in Data.symbols:
		if lst[idx-1][-1] in Data.symbols:
			lst[idx-1] = lst[idx-1][:-1]
		lst[idx-1] += lst[idx][-1]
	# lend capitalization to following string
	if idx < len(lst)-1 and lst[idx][0].isupper():
		lst[idx+1] = lst[idx+1].capitalize()
	lst.pop(idx)


# replaces directional terms in text with ambiguous alternatives
def ambiguateDirections(text):
	directions = Data.cardinals # north, northeast, southeast etc.
	wards = tuple(dir+"ward" for dir in directions) + \
		tuple(dir+"wards" for dir in directions)
	erns = tuple(dir+"ern" for dir in directions)
	unknownDirs = ("some direction","one way","in a certain direction","up ahead",
	"a ways away","far off","over yonder")
	additionalUnknownDirs = ("another direction","elsewhere","some other way","the other way",
	"behind","also ahead")
	adjectivalUnknownDirs = ("the nearby","the far","the left","the right")
	# prepositions that precede directions, e.g. "[from] the north"
	dirPreps = {"of","from","to","toward","into","on","in","at","by","across",
	"along","through"}
	# words that follow directional nouns, e.g. "Eastward, [stands] a window"
	followsNounDir = {"there","theres","is","are","await","lay","lie","sit","stand",
	"rise","begin","stretch","extend","run","rest","reside","reach","flow"}

	# Assume a token t1 is a noun if it ends the phrase, or t2 is a relevant verb
	# we assume t2 is a present-tense verb if it ends with "s"
	def dirIsNoun(t1,t2):
		return not t2 or t1[-1] in Data.symbols+"'\"" or \
		clean(t2).endswith("s") or clean(t2) in followsNounDir|dirPreps

	lastChoice = None
	replacedYet = False
	# get random string to replace old tokens, but keep the capitalization/punctuation
	# for textual flavor, include more unknownDirs after first replacement
	def getReplacement(oldTokens,newOptions):
		nonlocal replacedYet, lastChoice, unknownDirs, additionalUnknownDirs
		newToken = choice(newOptions)
		# ensure replacement is different from last
		while newToken == lastChoice:
			newToken = choice(newOptions)
		lastChoice = newToken
		newToken = formatReplacement(oldTokens,newToken)
		# after we've replaced one direction, we can use additional phrases
		if not replacedYet and newOptions is unknownDirs:
			unknownDirs += additionalUnknownDirs
			replacedYet = True
		return newToken

	# Loop over stream, three tokens tracked at a time, replacing or removing as needed
	# First we simplify the terms in the token stream; cases 0-5
	# Then replace directions with phrases depending if its noun or adjective; cases 6-7
	# Since we only iterate when no replacements are made, 
	# the triplet of tokens is fully simplified before any are replaced
	i = 0
	tokens = text.split(" ")
	while i < len(tokens):
		if i < 0: i = 0
		t0 = tokens[i]
		t1 = tokens[i+1] if i+1 < len(tokens) else None
		t2 = tokens[i+2] if i+2 < len(tokens) else None
		# print(i,t0,t1,t2)
		# 0. Remove adjectives; "the far northern" -> "the northern"
		if clean(t0) == "the" and clean(t2) in directions+wards+erns:
			subsume(tokens,i+1)
			i -= 1
		# 1. Simplify terms; "northward(s)" -> "north"
		elif clean(t2) in wards:
			tokens[i+2] = t2.replace("wards","").replace("ward","")
		# 2. Remove adjectival 'erns'; "a northern window" -> "a window"
		elif clean(t2) in erns:
			subsume(tokens,i+2)
		# 3. Reduce 'and's; "north and east" -> "north east"
		elif clean(t1) in directions and clean(t2) == "and":
			subsume(tokens,i+2)
		# 4. Reduce lists; "North, east, west" -> "West"
		elif clean(t1) in directions and clean(t2) in directions:
			if tokens[i+1][-1] in Data.symbols:
				tokens[i+1] = tokens[i+1][:-1]
			subsume(tokens,i+1)
		# 5. Remove determiner; "to the north" -> "to north"
		elif clean(t1) == "the" and clean(t2) in directions:
			subsume(tokens,i+1)

		# 6. NOUN "to north, a window..." -> "in a certain direction, a window..."
		# "to north lies a window" -> "in a certain direction lies a window"
		elif clean(t1) in directions and dirIsNoun(t1,t2):
			tokens[i+1] = getReplacement((tokens[i+1],),unknownDirs)
			if clean(t0) in dirPreps:
				subsume(tokens,i)
		# 7. ADJECTIVE "the north side" -> "a nearby side"
		elif clean(t1) in directions:
			tokens[i+1] = getReplacement((tokens[i+1],),adjectivalUnknownDirs)
		# TODO: may need a case for removing the direction when it is followed by a dirPrep
		# 'a brook flows from the east into a pond' -> 'a brook flows into a pond'
		else:
			i += 1
		# print(tokens)

	return " ".join([t for t in tokens if t is not None])


# replaces numbers in text with ambiguous quantity words
def ambiguateNumbers(text,grammatical=False):
	text = str(text)
	# capture the number and the preceding non-whitespace character (if any)
	# don't match ordinals (1st, 2nd, 3rd, 4th, etc)
	pattern = r'(?:(?P<prev>[^\d\s]))?\s*(?P<num>\d+)(?!st|nd|rd|th)'

	replacementMap = {
		"none": ("no","zero","not any"),
		"one": ("one","a single","a lone"),
		"two": ("two","a couple","a pair of"),
		"few": ("a few","not many","a small amount of"),
		"some": ("some","several","an amount of"),
		"many": ("many","a lot of","a bunch of","a big amount of"),
		"a ton": ("a ton of","a whole lot of","a really big amount of")
	}
	# when printing stats, don't use random grammatical selections
	if not grammatical:
		replacementMap = {k:(k,) for k in replacementMap}

	def repl(match):
		prev = match.group("prev")
		num = int(match.group("num"))

		# if number was in an ANSI escape sequence, ignore it
		if prev in ("[","\\",";"):
			return match.group(0)
		elif num == 0:
			replacement = choice(replacementMap["none"])
		elif num == 1:
			replacement = choice(replacementMap["one"])
		elif num == 2:
			replacement = choice(replacementMap["two"])
		elif num > 2 and num < 6:
			replacement = choice(replacementMap["few"])
		elif num >= 6 and num < 15:
			replacement = choice(replacementMap["some"])
		elif num <= 60:
			replacement = choice(replacementMap["many"])
		else:
			replacement = choice(replacementMap["a ton"])

		# capitalize only if preceding non-whitespace char is . ! ?
		if (prev is None or prev in ".!?") and grammatical:
			replacement = replacement.capitalize()
		# Â§10 -> "some money"
		if prev == "Â§" and grammatical:
			replacement += " money"
			return replacement

		# concatenate previous char, any whitespace, and replacement
		textBeforeNum = match.group(0)[:-len(match.group("num"))]
		replacement = textBeforeNum + replacement
		return replacement

	return re.sub(pattern, repl, text)


# introduces common misspellings into text
def misspell(text):
	miscReplacementMap = {
		"to":"too", "too":"to", "there":"their", "where":"wear", "sword":"sord",
		"library":"libary", "higher":"hire", "break":"brake", "window":"windo",
		"above":"abuv", "python":"pithon"
	}
	def getReplacement(oldToken):
		newToken = miscReplacementMap[clean(oldToken)]
		return formatReplacement((oldToken,),newToken)

	# chance to replace predetermined words with common misspellings
	tokens = text.split(" ")
	i = 0
	while i < len(tokens):
		if clean(tokens[i]) in miscReplacementMap and randint(0,3) == 0:
			tokens[i] = getReplacement(tokens[i])
		i += 1
	text = " ".join(tokens)

	# used to exclude None when concatenated chars
	def cat(*parts):
		return "".join(p for p in parts if p)

	# iterate, examining three tokens at a time
	# for every character, chance to make a common misspelling
	i = 0
	while i < len(text):
		if i < 0: i = 0
		t0 = text[i]
		t1 = text[i+1] if i+1 < len(text) else None
		t2 = text[i+2] if i+2 < len(text) else None

		# 25% chance of misspelling
		if randint(0,3) != 0:
			i += 1
			continue
		# print(text+"\n",i,t0,t1,t2,"\n")
		match (t0,t1,t2):
			# double letter -> single letter
			case (x,y,z) if x ==y and x in "sltfrmnbdcz": repl = cat(x,z)
			# oor -> or
			case ("o","o","r"): repl = "or"
			# ore -> or
			case ("o","r","e"): repl = "or"
			# ie -> ei
			case ("i","e",z): repl = cat("ei",z)
			# ea -> ee
			case ("e","a",z) if z not in ("d"," ",None): repl = cat("ee",z)
			# ais -> aze
			case ("a","i","s"): repl = "aze"
			# air,ain,aid -> are,ane,ade
			case ("a","i",z) if z in ("d","l","m","n","p","r"): repl = cat("a",z,"e")
			# ign -> ine
			case ("i","g","n"): repl = "ine"
			# th[End] -> the[End]
			case ("t","h",z) if z in (" ",None): repl = cat("the",z)
			# gh[Vowel] -> w[Vowel]
			case ("g","h",z) if z in Data.vowels: repl = cat("w",z)
			# ght -> te
			case ("g","h","t"): repl = "te"
			# dge -> j
			case ("d","g","e"): repl = "j"
			# dgy -> jy
			case ("d","g",z) if z in ("i","y"): repl = cat("j",z)
			# age -> aje
			case ("a","g","e"): repl = "aje"
			# ue[End] -> ew[End]
			case ("u","e",z) if z in (" ",None): repl = cat("ew",z)
			# u[Vowel] -> w[Vowel] (except not gua or nue)
			case (x,"u",z) if x not in ("t","n","g") and z in Data.vowels: 
				repl = cat(x,"w",z)
			# ou -> ow
			case ("o","u",z) if z not in ("g"," ",None): repl = cat("ow",z)
			# oi -> oy
			case ("o","i",z): repl = cat("oy",z)
			# ph -> f
			case ("p","h",z): repl = cat("f",z)
			# tio -> shu
			case ("t","i","o"): repl = "shu"
			# tch -> ch
			case ("t","c","h"): repl = "ch"
			# ce -> se
			case (a,"c","e"): repl = a+"se"
			# ck -> k
			case (a,"c","k"): repl = a+"k"
			# c -> k
			case ("c",y,z) if y not in ("e","h","k") and randint(0,1): repl = cat("k",y,z)
			# wr -> r
			case ("w","r",z): repl = cat("r",z)
			# wh -> w
			case ("w","h",z): repl = cat("w",z)
			# default case
			case (x,y,z): repl = cat(x,y,z)

		text = text[:i] + repl + text[i+3:]
		i += 1
	return text


# returns an abbreviated direction into an expanded one
# for example, converts 'nw' -> 'northwest' or 'u' -> 'up'
def expandDir(term):
	if term in Data.directions:
		return Data.directions[term]
	else:
		return term


# returns list of (obj,n) where n is the count of object in objects
# uses equivKey to determine object equivalence for counting
def bagObjects(objects,equivKey=None):
	if equivKey is None:
		equivKey = lambda obj: obj.nounPhrase()
	bag = []
	for obj in objects:
		for entry in bag:
			if equivKey(entry[0]) == equivKey(obj):
				entry[1] += 1
				break
		else:
			bag.append([obj,1])
	return bag


# takes a prepend string and list of objects
# converts list of objects to a bag of (obj,count) pairs
# returns a string that grammatically lists all strings in names
def listObjects(prepend,objects,append="",includePosture=False):
	phraseKey = lambda obj: obj.nounPhrase(includePosture=includePosture)
	objBag = bagObjects(objects,equivKey=phraseKey)
	liststring = ""
	l = len(objBag)
	for i, (obj, count) in enumerate(objBag):
		if i == l-1:
			liststring += obj.nounPhrase(n=count,includePosture=includePosture)
		elif i == l-2:
			liststring += obj.nounPhrase(n=count,
				includePosture=includePosture) + " and "
		else:
			liststring += obj.nounPhrase(n=count,
				includePosture=includePosture) + ", "
	liststring = prepend + liststring
	liststring += append

	if player.hasStatus("stupidity"):
		liststring = ambiguateNumbers(liststring,grammatical=True)
	return liststring


# return every object connected above the given descriptive roots by visible tethers
def tetherGroup(roots):
	group = []
	remaining = list(roots)
	while remaining:
		obj = remaining.pop(0)
		if obj in group:
			continue
		group.append(obj)
		remaining.extend(obj.occupants())
		if isinstance(obj,Creature):
			remaining.extend(obj.carrying())
	return group


# describe carrying separately from the noun phrases that describe occupancy
def describeCarrying(roots):
	carriers = [obj for obj in tetherGroup(roots) \
		if isinstance(obj,Creature) and obj.carrying()]
	phrases = [listObjects(f"{-carrier} is carrying ",carrier.carrying()) \
		for carrier in carriers]
	if not phrases:
		return False
	if len(phrases) > 1:
		description = ", ".join(phrases[:-1]) + " and " + phrases[-1]
	else:
		description = phrases[0]
	Print(capWords(description,1) + ".")
	return True


# canonical status list order: alphabetical by name; same-named entries
# longest-lasting first, with indefinite (None) durations foremost
def statusEntryKey(entry):
	return (entry[0], entry[2] is not None, -(entry[2] or 0))


# normalize one authored status entry to canonical [name, source, duration]:
# "name" or ["name"] -> sourceless, indefinite; [name, source] -> indefinite
def normalizeStatusEntry(entry):
	if isinstance(entry,str):
		entry = [entry]
	if len(entry) == 1:
		entry = [entry[0],None]
	if len(entry) == 2:
		entry = [entry[0],entry[1],None]
	name,source,dur = entry
	# durations are positive ints or None (indefinite)
	assert isinstance(name,str) and (dur is None or
		(isinstance(dur,int) and dur > 0))
	assert source is None or isinstance(source,str) or \
		(isinstance(source,int) and source >= 0)
	return list(entry)





# returns a number, n, with a lower bound of 0
def min0(n): return 0 if n < 0 else n


# returns a number, n, with a lower bound of 1
def min1(n): return 1 if n < 1 else n


# returns a number n, bounded by lo and hi
def bound(n,lo,hi): return lo if n < lo else (hi if n > hi else n)


# rolls n dice of range d, adds a modifier m, returns an int >= 1
def diceRoll(n,d,m=0):
	if d < 1:
		n = 0
	x = sum(randint(1,d) for _ in range(n))
	return min1(x+m)


def roll(d,m=0):
	return diceRoll(1,d,m)


# rolls a number between d//2 and d, adds m
def halfRoll(d,m=0):
	return min1(roll(d//2,m+d//2))


# has a p percent chance of returning True
def percentChance(p):
	return randint(1,100) <= p



# the Room, Creatures, and some Items can contain Items within themselves
# thus all objects within a room can be thought of as a tree
# where each node is an item or creature, and the root is the Room
# the player object can also be thought of this way where the player is the root
# this function recursively queries the tree of objects for those that pass the given key
# the object tree might look as follows:
#           _____Room_____
#         /     /    \     \
#     cat  trunk   sword  wizard
#    /     /   \         /   |   \
# bell lockbox candle potion wand scroll
#        |
#     saffron
# d is the 'degree' of the query; how thorough it is
# if d is 0: looks in objects which are not "closed" and not in creature inventories
# i.e. "visible" to the player (only cat, trunk, sword, wizard)
# if d is 1: look in objects that are not locked and not in creature inventories
# i.e. objects which are "available" to the player (also lockbox, candle)
# if d is 2: looks in all objects which are not locked
# i.e. objects which are "accessible" to the player (also bell, potion, wand, scroll)
# if d is 3: looks in all objects from the root  (also saffron)

# this function is a wrapper for objQueryRecur()
def objQuery(root,key=None,d=0):
	if key is None: key = lambda obj:True
	matches = set()
	traversed = set()
	if key(root):
		matches.add(root)
	matches = objQueryRecur(root,matches,key,d,traversed)
	return matches

# recurs through all objects within node, adds them to matches if supplied key is True
# d is the degree of the query, see objQuery() comments above for details
def objQueryRecur(node,matches,key,d,traversed):
	for obj in node:
		if obj in traversed: continue
		traversed.add(obj)
		# check if obj is a match
		if key(obj): matches.add(obj)
		# depending on the degree, dont query into closed, Creature or locked objects
		if d == 0 and hasattr(obj,"closed") and obj.closed: continue
		elif (d <= 1) and isinstance(obj,Creature): continue
		elif d <= 2 and hasattr(obj,"locked") and obj.locked: continue
		# recur the query on each object's subtree
		matches = objQueryRecur(obj,matches,key,d,traversed)
	return matches


#############
## LOGGING ##
#############


# A secondary text window used to display static text which can be updated
class SidePanel:
	# store OS type ('nt' for Windows, 'posix' for Linux/Mac)
	OSname = os.name

	def __init__(self,width=50,height=25):
		self.title = ""
		self.width = width
		self.height = height
		self.pipePath = None
		self.pipe = None
		self.process = None


	### Process Handling ###

	def isOpen(self):
		return self.process is not None and self.process.poll() is None


	def open(self, title=""):
		if self.isOpen():
			Print(f"{self.title} side panel is already open.",color="k")
			return False
		self.title = title
		if SidePanel.OSname == "nt":
			self.openWindows()
		elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
			self.openUnix()
		else:
			raise OSError("Unsupported OS")


	def openWindows(self):
		pipe_dir = tempfile.gettempdir()
		self.pipePath = os.path.join(pipe_dir, f"sidepanel_{os.getpid()}.txt")
		open(self.pipePath, "w", encoding="utf-8").close()
		self.pipe = open(self.pipePath, "w", buffering=1, encoding="utf-8")
		# escape any spaces in the path
		safe_path = f'"{self.pipePath}"'

		# write batch file with @echo off and Quick Edit disabled
		batch_cmd = (
			f'@echo off\n'
			f'chcp 65001 >nul\n'
			f'title {self.title}\n'
			f'mode con: cols={self.width} lines={self.height}\n'
			f':loop\n'
			f'cls\n'
			f'type {safe_path}\n'
			f'timeout /t 1 >nul\n'
			f'goto loop\n'
		)
		bat_file = os.path.join(pipe_dir, f"sidepanel_{os.getpid()}.bat")
		with open(bat_file, "w", encoding="utf-8") as f:
			f.write(batch_cmd)
		# launch cmd directly, not via "start"
		self.process = subprocess.Popen(
			["cmd", "/K", bat_file],
			creationflags=subprocess.CREATE_NEW_CONSOLE,
		)


	def openUnix(self):
		self.pipePath = os.path.join(tempfile.gettempdir(), 
		f"sidepanel_{os.getpid()}.txt")
		self.pipe = open(self.pipePath, "w", buffering=1, encoding="utf-8")

		cmd = (
			f"xterm -T {shlex.quote(self.title)} "
			f"-geometry {self.width}x{self.height} "
			f"-e bash -c 'clear; tail -f {shlex.quote(self.pipePath)}'"
		)
		self.process = subprocess.Popen(cmd, shell=True)
		sleep(0.5)


	def close(self):
		if not self.isOpen():
			return False
		if self.pipe:
			self.pipe.close()
			self.pipe = None
		if self.process:
			if SidePanel.OSname == "nt":
				subprocess.call(
					f'taskkill /FI "WINDOWTITLE eq {self.title}" /F >nul 2>&1',
					shell=True
				)
			else:
				self.process.terminate()
			self.process = None
		if self.pipePath and os.path.exists(self.pipePath):
			try:
				os.remove(self.pipePath)
			except Exception:
				pass


	### I/O Handling ###

	def write(self, text=""):
		if self.pipe:
			self.pipe.write(str(text))


	def flush(self):
		return
		# if self.pipe:
		# 	self.pipe.flush()


	def clear(self):
		if SidePanel.OSname == "nt":
			if self.pipe:
				self.pipe.seek(0)
				self.pipe.truncate()
		else:
			if self.pipe:
				self.pipe.seek(0)
				self.pipe.truncate()


sidepanel = SidePanel()

def cleanup():
    if sidepanel.isOpen():
        sidepanel.close()
atexit.register(cleanup)

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;?]*[ -/]*[A-Za-z]')


# Descriptor that will write both to the terminal and to a log file
class TeeLogger:
	def __init__(self,logFile,inputFile=None):
		self.terminal = sys.stdout
		self.originalStdin = sys.stdin
		self.errorTerminal = sys.stderr
		os.makedirs(os.path.dirname(logFile),exist_ok=True)
		self.log = open(logFile,"w",encoding="utf-8", errors="replace")
		self.stdin = open(inputFile,"r") if inputFile else self.originalStdin
		self.logbuffer = ""


	def setInputFile(self, inputFilename):
		if self.stdin != self.originalStdin:
			self.stdin.close()
		self.stdin = open(inputFilename,"r")


	# if the buffer gets too long for whatever reason, we try to clean it and drain
	def forceDrainBuffer(self):
		cleanBuffer = ANSI_ESCAPE.sub('', self.logbuffer)
		self.log.write(cleanBuffer)
		self.log.flush()
		self.logbuffer = ""


	# in this game, text is typically printed one-character-at-a-time
	# we don't want ansi escape sequences appearing in the log, 
	# so we accumulate characters in a buffer and flush it at every newline
	def drainBufferToNewline(self):
		newline = self.logbuffer.find('\n')
		if newline == -1:
			return
		line = self.logbuffer[:newline]
		cleanLine = ANSI_ESCAPE.sub('', line)
		self.log.write(cleanLine + '\n')
		self.log.flush()
		self.logbuffer = self.logbuffer[newline + 1:]


	# write text to terminal, accumulate text in log buffer, flush at newlines
	def write(self, message):
		self.logbuffer += message
		while '\n' in self.logbuffer:
			self.drainBufferToNewline()
		if len(self.logbuffer) > 3000:
			self.forceDrainBuffer()
		self.terminal.write(message)
		self.terminal.flush()


	def write_error(self,message):
		self.forceDrainBuffer()
		self.errorTerminal.write(message)


	def readline(self):
		self.forceDrainBuffer()
		input_text = self.stdin.readline()
		if len(input_text.strip()) > 0:
			self.log.write(input_text)
			self.log.flush()
		return input_text


	def flush(self):
		self.terminal.flush()
		self.log.flush()



######################
## DIALOGUE CLASSES ##
######################



# it is recommended to read the notes for DialogueTree below first
# in addition to having children, nodes in the tree may have a few important parameters;
# nodes may contain either a remark or a list of 'trites' from which to generate dialogue
# - a remark is a simple line of output dialogue. A trite is the name of a 'triteset'
# - tritesets are sets of predetermined remarks that can be sampled by many speakers
# the node may also contain either a list of 'cases' or 'replies' to correspond to children
# - cases is a list of boolean expressions which can access the game's global objects
# - instead of a boolean expression, a case may be an integer representing a probability
# - replies is a list of replies that the user may choose from during dialogue
# the child that is traversed is determined by the first true case or the chosen reply

# guard criteria:
# nodes may have a 'visitLimit', to ensure dialogue is not repeated in one 'parley'
# nodes may have a 'rapportReq' that requires a certain 'rapport' with the speaker
# in addition to these, nodes can have a special 'guardCase' expression preventing traversal

# side effects:
# reaching certain nodes can modify certain external values, such as:
# - modfying the listener's love, fear, or reputation stats
# - adding to the speaker's memories set or the game's events set
# nodes may be marked as checkPoints; they will be saved by the tree as a return point

# traversal:
# The Dialogue Tree object will traverse each main branch node of the tree in order,
# calling branch.visit() until one traversal yields some output
# each node visit is as follows;
# 	output this nodes output (remark or trite) if it has any
#	then try to 'hop' to each child node (using cases or replies if they're present)
#	child nodes will fail the hop if it fails any guard criteria,
#	if child passes the hop, then stop hopping and select this as next node
#	then evoke any side effects this node has
#	then return the selected child for traversal by the tree 
#	if no children were selected, None will be returned to the tree
class DialogueNode():
	def __init__(self,parent,label,idx,lastTriteRemark=None,visitLimit=None,
	rapportReq=None,guardCase="True",isCheckpoint=False,loveMod=0,fearMod=0,repMod=0,
	memories=None,events=None,remark=None,trites=None,cases=None,replies=None,
	children=[],reactTrue=False):
		self.parent = parent
		self.label = label
		# id is actually the path from root to node, stored as a tuple of indices
		self.id = self.parent.id + (idx,)
		self.lastTriteRemark = lastTriteRemark
		self.visitLimit = visitLimit
		self.guardCase = guardCase
		self.rapportReq = rapportReq
		self.isCheckpoint = isCheckpoint
		self.children = [DialogueNode(self,label,i,**childJson) for i,childJson in enumerate(children)]

		### the following are effects that visiting the node will have

		# these modify speaker stats
		self.loveMod=loveMod
		self.fearMod=fearMod
		self.repMod=repMod
		# this adds memory to speaker memories
		self.memories = set() if memories is None else memories
		if type(memories) is list:
			self.memories = set(memories)
		elif type(memories) is str:
			self.memories = {memories}
		for memory in self.memories:
			assert type(memory) is str
		# events set is used to add to game events
		self.events = set() if events is None else events
		if type(events) is list:
			self.events = set(events)
		elif type(events) is str:
			self.events = {events}
		for event in self.events:
			assert type(event) is str

		### the following are possible dialogue outputs from visiting the node

		# this is a basic output dialogue remark
		self.remark = remark
		# these are names of sets of strings in Dialogue.json, containing 'canned' dialogue
		self.trites = [] if trites is None else trites
		if type(self.trites) is not list:
			self.trites = [trites]
		for trite in self.trites:
			assert type(trite) is str
		# should only be used for terminal nodes in 'reactions' branch of tree
		# meant so dialogue tree can be used to determine if speaker's reaction is 'True'
		# e.g. if a speaker refuses or accepts a player's 'Give' action
		self.reactTrue = reactTrue
		if self.reactTrue: assert len(self.children) == 0

		### the following are mechanisms to determine which child to branch to traverse

		# these are strings of python code which should evaluate to a bool or int
		self.cases = [] if cases is None else cases
		# these are the optional Player replies to the dialogue
		self.replies = [] if replies is None else replies
		# ensure the number of child nodes matches the cases or replies
		if self.cases:
			if type(self.cases) is not list:
				self.cases = [self.cases]
			# one extra child for when all cases are false
			assert len(self.children) == len(self.cases) + 1
		elif self.replies:
			if type(self.replies) is not list:
				self.replies = [self.replies]
			assert len(self.children) == len(self.replies)

		# ensure node doesn't have both a remark and a trite set
		assert self.remark is None or self.trites == []
		# ensure node doesn't have both conditional cases and reply cases
		assert self.cases == [] or self.replies == []

		if hasattr(self.parent, 'replies'):
			assert self.visitLimit is None and self.rapportReq is None, \
			f"Child of reply node {self.parent.id} must not have visitLimit or " \
			f"rapportReq in dialogue tree {self.label}"

		# used as context to eval() guardCase and cases
		self.globals = {"player":player,"game":game,"world":world}


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlogNode {self.id}"


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["id"]
		del jsonDict["globals"]
		return jsonDict


	@classmethod
	def convertFromJSON(cls,d):
		return cls(**d)


	# ensures the following:
	# that the tree is structurally valid by determining the ID
	# that all cases (which are stored in JSON as strings) are ints or evaluate to a bool
	# that all trites (which are stored in JSON as strings) are valid sets in Data.py
	# note that speaker, player, game, and world are provided to ensure eval() is valid
	def ensureIntegrity(self,speaker,**kwargs):
		err = "Invalid guard case node condition in "
		f"{speaker.name}'s node {self.id}: {self.guardCase}"
		context = kwargs | {"speaker":speaker}
		guardCaseRes = eval(self.guardCase,self.globals,context)
		assert type(guardCaseRes) is bool, err
		for case in self.cases:
			err = f"Invalid case node condition in {speaker.name}'s node {self.id}:{case}"
			caseRes = eval(str(case),self.globals,context)
			assert type(caseRes) in (bool,int), err
		for trite in self.trites:
			triteset = game.dlogForest["pools"][trite]
			assert len(triteset) > 2
		for child in self.children:
			child.ensureIntegrity(speaker,**kwargs)


	### Operation ###

	# try to visit the child with the first true case
	# cases can be numbers, representing a probability of visiting that child
	# if all are false, try to visit the last child (like an 'else')
	def conditionalHop(self,speaker,**kwargs):
		for i, case in enumerate(self.cases):
			nextNode = self.children[i]

			context = kwargs | {"speaker":speaker}
			# cases can be boolean cases or integer probabiliies
			# note that it is an independent probability for each node
			if type(case) is int and percentChance(case):
				if nextNode.hop(speaker,**kwargs):
					return nextNode
			elif type(case) is str and eval(case,self.globals,context) is True:
				if nextNode.hop(speaker,**kwargs):
					return nextNode

		else:
			nextNode = self.children[-1]
			if nextNode.hop(speaker,**kwargs):
				return nextNode
		
		return None


	# try to visit the child corresponding to the user-chosen dialogue reply
	# users can end the dialogue by inputting a cancel command
	# note that this does NOT call nextNode.hop(); a reply hop mandates a traversal
	def replyHop(self):
		for i, reply in enumerate(self.replies):
			Print()
			Print(f'{i+1}. {reply}',end="",color='k')

		def acceptKey(inp):
			try:
				return self.children[int(inp)-1]
			except:
				return None

		refuseMsg = "That is not one of the options. Input a number or type 'cancel'."
		return InputLoop("",acceptKey=acceptKey,refuseMsg=refuseMsg)


	# test if this node can be visited using visitLimit, rapportReq, and guardCase
	def hop(self,speaker,**kwargs):
		if self.visitLimit is not None:
			if speaker.dlogTree.getVisitCount(self.id) >= self.visitLimit:
				return False
		if self.rapportReq is not None:
			if speaker.rapport != self.rapportReq:
				return False
		context = kwargs | {"speaker":speaker}
		if not eval(self.guardCase,self.globals,context):
			return False
		return True


	# attempt to branch down the tree, visiting this node
	# printing a dialogue remark if the node has one, and visiting a child node
	def visit(self,speaker,**kwargs):
		if self.isCheckpoint:
			speaker.dlogTree.checkpoint = self.id

		# output this node's remark
		if self.remark:
			waitInput(f'"{self.remark}"',color="y")
		elif self.trites:
			tritepool = set()
			for trite in self.trites:
				tritepool |= set(game.dlogForest["pools"][trite])

			samples = sample(tritepool,2)
			triteRemark = samples[0]
			if triteRemark == self.lastTriteRemark:
				triteRemark = samples[1]

			waitInput(f'"{triteRemark}"',color="y")
			self.lastTriteRemark = triteRemark

		# return next node if this node has children
		# note that it is possible for nextNode to end up as None (from conditionalHop)
		nextNode = None
		if self.cases:
			nextNode = self.conditionalHop(speaker,**kwargs)
		elif self.replies:
			nextNode = self.replyHop()
		else: # TODO: run this if nextNode is still none?
			for child in self.children:
				if child.hop(speaker,**kwargs):
					nextNode = child
					break

		# count this node as successfully visited
		speaker.dlogTree.countVisit(self.id)

		# if applicable, affect speaker or player stats
		speaker.updateLove(self.loveMod)
		speaker.updateFear(self.fearMod)
		player.updateReputation(self.repMod)
		for memory in self.memories:
			speaker.memories.add(memory)
		for event in self.events:
			game.events.add(event)

		# unmark checkpoint if this node was succesfully visited
		if nextNode and speaker.dlogTree.checkpoint == self.id:
			speaker.dlogTree.checkpoint = None
		return nextNode


	### Getters ###

	# checks that at least one path in the tree will provide dialogue
	def hasDefiniteDialogue(self):
		if self.remark or self.trites:
			return True
		if self.cases:
			if self.children[-1].hasDefiniteDialogue():
				return True
			return False
		for child in self.children:
			if child.hasDefiniteDialogue():
				return True
		return False



# a reaction node is a special type of dialogue node that heads the 'reactions' branch
# it is not traversed during normal parley, but when the speaker reacts to something
# it behaves just like a dictionary, mapping keys like 'attacked' to dialogue nodes
# any objects relevant the reaction can be supplied in the **kwargs of node.traverse()
class ReactionNode(DialogueNode):
	def __init__(self,parent,label,idx,treeJson):
		super().__init__(parent,label,idx)
		assert len(self.children) == 0, "Reaction node has non-reaction children"
		self.reactions = {key: DialogueNode(self,label,i,**childJson) for i,(key,childJson) in enumerate(treeJson.items())}
		self.children = (child for child in self.reactions.values())


	def __getitem__(self,key):
		return self.reactions[key]


	def __contains__(self,key):
		return key in self.reactions



# in order for characters to produce unique and variable dialogue with minimal repetition-
# and apparent intelligence, a character's dialogue is stored as a directed tree

# Structure:
# there are five branches from the root; surprise, quest, colloquy, chatter, and reaction
# the tree will try to traverse each branch in order until one produces dialogue output
# 1. surprise is for dialogue which a character would prioritize before anything else
# 2. quest is for dialogue that is generally important for the game or story
# 3. colloquy is for dialogue that is meant to give the character depth or individuality
# 4. chatter is for when the rest are exhausted and is sampled from specified tritesets 
# 5. reaction is not used during a normal parley, it is used to react to other actions

# Features:
# - Checkpoint
#	trees may store a node 'checkpoint' in case the user leaves and reenters the dialogue
# - Rapport
#	the speaker's rapport value is incremented when the user engages in colloquy
#	rapport is meant to give the dialogue a sense of progression throughout the game
# - Parleys
#	to give the speakers the appearance of short term memory, 
#	the tree maintains its state until a new 'parley'
#	a new parley occurs after a certain length of time since the previous dialogue
#	a new parley erases the checkpoint and the visitCounts of all nodes
class DialogueTree():
	def __init__(self,label,treeJson=None,visitCounts=None,checkpoint=None):
		if treeJson is None:
			treeJson = {"chatter":{}}
		self.label = label
		self.id = ()
		# note that chatter is required to be populated; there must be some dialogue
		self.surprise = DialogueNode(self,label,0,**treeJson.get("surprise",{}))
		self.quest = DialogueNode(self,label,1,**treeJson.get("quest",{}))
		self.colloquy = DialogueNode(self,label,2,**treeJson.get("colloquy",{}))
		self.chatter = DialogueNode(self,label,3,**treeJson["chatter"])
		self.reactions = ReactionNode(self,label,4,treeJson.get("reactions",{}))
		self.children = (self.surprise,self.quest,self.colloquy,self.chatter,self.reactions)
		self.visitCounts = {} if visitCounts is None else visitCounts
		self.visitCounts = self.deserializeTupDict(self.visitCounts)
		self.checkpoint = None


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlog tree"


	### File I/O ###

	def deserializeTupDict(self,tupDict):
		return {tuple(tupStr.split(',')): val for tupStr, val in tupDict.items()}


	# within world.json, the tree is just stored with its name and state
	# the actual tree structure should be stored in Dialogue.json and not altered
	def convertToJSON(self):
		return {
			"label": self.label,
			"visitCounts": {str(id): count for id, count in self.visitCounts.items()},
			"checkpoint": self.checkpoint
		}


	def copy(self):
		treeCopy = DialogueTree(self.label)
		treeCopy.surprise = self.surprise
		treeCopy.quest = self.quest
		treeCopy.colloquy = self.colloquy
		treeCopy.chatter = self.chatter
		treeCopy.reactions = self.reactions
		treeCopy.children = self.children
		return treeCopy


	# ensures the following;
	# that the tree is structurally valid (parents are assigned to children)
	# that the checkpoint, if there is one, is a valid node
	# that at least one path of the tree will yield dialogue in all cases
	def ensureIntegrity(self,speaker):
		# this is used for running eval (specifically reaction nodes)
		dummyContext = {"I": Item("","",0,0,""), "C": Creature("","",0,[0]*10,0)}
		for child in self.children:
			child.ensureIntegrity(speaker,**dummyContext)

		if self.checkpoint:
			assert self.findNode(self.checkpoint), \
			f"Checkpoint {self.checkpoint} not found in {speaker.name}'s dialogue tree"

		for id in self.visitCounts.values():
			assert self.findNode(id), \
			f"Visited node {id} not found in {speaker.name}'s dialogue tree"			

		assert self.chatter.hasDefiniteDialogue(), \
		f"In {speaker.room()} {speaker.name} dialogue Tree has no definite dialogue"


	### Operation ###
	
	# should only be called by node.visit() to mark that node as visited
	def countVisit(self,nodeId):
		if nodeId in self.visitCounts:
			self.visitCounts[nodeId] += 1
		else:
			self.visitCounts[nodeId] = 1


	# should only be called by node.hop() to check how many times node has been visited
	def getVisitCount(self,nodeId):
		if nodeId in self.visitCounts:
			return self.visitCounts[nodeId]
		return 0


	# visit the branch, return True if visiting any child resulted in speaker dialogue
	def visitBranch(self,node,speaker):
		had_dialogue = False
		while node:
			if node.remark or node.trites:
				had_dialogue = True
			node = node.visit(speaker)
		return had_dialogue


	# visit the corresponding reaction branch, return True if reached a 'reactTrue' node 
	def react(self,reaction,speaker,**kwargs):
		if reaction not in self.reactions:
			return False
		node = self.reactions[reaction]
		if node.hop(speaker,**kwargs):
			while node:
				nextNode = node.visit(speaker,**kwargs)
				if node.reactTrue:
					return True
				node = nextNode
		return False


	# attempt to visit each branch of the tree until one yields dialogue
	# after the surprise branch, start at the dialogue checkpoint if there is one
	# returns True if any branch successfully yielded dialogue.
	# Visiting 'chatter' should always succeed
	def visit(self,speaker):
		if self.surprise.hop(speaker):
			if self.visitBranch(self.surprise,speaker):
				return True

		if self.checkpoint:
			checkpointNode = self.findNode(self.checkpoint)
			if checkpointNode.hop(speaker):
				if self.visitBranch(checkpointNode,speaker):
					return True

		for branch in (self.quest,self.colloquy,self.chatter):
			if branch.hop(speaker):
				if self.visitBranch(branch,speaker):
					if branch is self.colloquy:
						speaker.rapport += 1
					return True

		return Print("...",color="y",delay=0.3)


	# uses a nodeId (the path to the node using child indices) to retrieve node
	def findNode(self,nodeId):
		node = self
		for idx in nodeId:
			node = node.children[idx]
		return node


	# resets all nodes for new parley
	def newParley(self):
		self.checkpoint = None
		self.visitCounts = {}




############################
## SUPERCLASS DEFINITIONS ##
############################


# base class for all "physical objects" in the world
# the three main types are Room, Item, and Creature (which is a subclass of Item)
# the methods herein are mostly for representing objects or for handling basic interactions
class GameObject():
	def __init__(self):
		self.name = "[GAME OBJECT]"
		self.weight = 0
		self.pronoun = "it"
		self.plural = "[GAME OBJECTS]"
		self.determiner = None
		self.status = set()


	### Dunder Methods ###

	def __str__(self):
		return self.name


	def __neg__(self):
		return self.nounPhrase(self.definiteDeterminer())


	def __pos__(self):
		return self.nounPhrase(self.definiteDeterminer(),cap=1)


	def __invert__(self):
		return self.nounPhrase('a')


	def __add__(self,other):
		return +self + " " + conjugate(+self,other)


	def __sub__(self,other):
		return -self + " " + conjugate(-self,other)


	def __mul__(self,other):
		pronoun = self.subjective()
		return pronoun.capitalize() + " " + conjugate(pronoun,other)


	def __truediv__(self,other):
		pronoun = self.subjective()
		return pronoun + " " + conjugate(pronoun,other)


	def __rtruediv__(self,other):
		return str(other) + " " + self.pronoun


	def __hash__(self):
		return hash(id(self))


	# Validate owned descendants after subclasses validate their local relationships.
	def validate(self):
		if getattr(self,"composition",None) not in Data.materials:
			raise ValueError(f"{self} has unregistered composition " \
				f"'{self.composition}'")
		for child in game.ownedChildren(self):
			child.validate()
		return True


	def __iter__(self):
		yield from self.contents().copy()


	def __contains__(self,obj):
		return obj in self.contents()


	def __lt__(self,other):
		if hasMethod(other,"Weight"):
			other = other.Weight()
		return self.Weight() < other


	def __gt__(self,other):
		if hasMethod(other,"Weight"):
			other = other.Weight()
		return self.Weight() > other


	def __lfshift__(self,other):
		if hasMethod(other,"Size"):
			other = other.Size()
		return self.Size() < other


	def __rshift__(self,other):
		if hasMethod(other,"Size"):
			other = other.Size()
		return self.Size() > other


	def __matmul__(self,other): # TODO: reflexive?
		return None
	

	def __mod__(self,other): # TODO: plural?
		return None


	def __and__(self,other): # TODO: not sure what to use & for
		return None


	def __or__(self,other): # TODO: not sure what to use | for
		return None


	def __xor__(self,other): # TODO: not sure what to use ^ for
		return None


	### Operation ###

	# if possible merge another item into this one
	# return merged object if successful, False if not mergeable 
	def merge(self,other):
		return False


	def canImmerse(self,obj):
		return False


	def couldImmerse(self,obj,size=None,vacancy=None):
		return False


	def canEmerge(self,obj):
		return True


	def requiredImmersion(self,obj):
		return None


	def immersionContext(self):
		return None


	# decrements the duration of each status entry on the object by t
	# removes entries whose duration is lowered past 0
	def passTime(self,t):
		for entry in self.status:
			# subtract remaining duration; None means indefinite
			if entry[2] is not None:
				entry[2] = min0(entry[2] - t)

		# remove entries with 0 duration left
		self.removeStatus(reqDuration=0)

		# fire each present condition's onTick hooks, once per conditions() element
		for cond in self.conditions():
			self.evokeStatusHooks("onTick",cond.name)


	### Getters ###

	def definiteDeterminer(self):
		if self.determiner is not None:
			return self.determiner
		if hasattr(self,"ancestors") and player in self.ancestors():
			return "your"
		return "the"


	# integral to objQuery() (see comments)
	# should be empty for objects that aren't Containers, Creatures, or Rooms
	def contents(self):
		return self.spatialContents()


	# return ordinary objects occupying space directly within this object
	def spatialContents(self):
		return []


	# the EFFECTS view of this object's statuses: what its conditions do
	# as StatusCondition records (unknown names resolve to the default).
	# A compounding condition may appear multiple times; others once per name.
	def conditions(self):
		conds = []
		seen = set()
		for name,source,duration in self.status:
			cond = Data.StatusCondition.get(name)
			if cond.compounds:
				conds.append(cond)
			elif name not in seen:
				seen.add(name)
				conds.append(cond)
		return conds


	# the name of a present condition whose record vetoes adding the given
	# name, or None if nothing blocks it
	def blocksStatus(self,name):
		for cond in self.conditions():
			if name in cond.blocks:
				return cond.name
		return None


	# the INSTANCE view of this object's statuses: count the raw entries
	# unregistered/unknown condition names are still counted
	# name may be one name, a collection (matching any), or "*" (match all)
	# reqSource/reqDuration "*" match anything; None matches unsourced
	# entries / indefinite durations respectively
	def countStatus(self,name="*",reqSource="*",reqDuration="*"):
		names = (name,) if isinstance(name,str) else name
		n = 0
		for condname,source,duration in self.status:
			if name == "*" or condname in names:
				if reqSource == "*" or reqSource == source:
					if reqDuration == "*" or reqDuration == duration:
						n += 1
		return n


	# True if any entry matches the countStatus criteria (checks for presence)
	def hasStatus(self,name="*",reqSource="*",reqDuration="*"):
		return self.countStatus(name,reqSource,reqDuration) >= 1


	# get the status entry identified by (name, source), or None if absent
	def getStatusEntry(self,name,source=None):
		for entry in self.status:
			if entry[0] == name and entry[1] == source:
				return entry
		return None


	# update an existing entry's duration upon re-application
	# fires no hooks or reports; returns whether the duration changed
	def refreshStatus(self,entry,dur,canStack):
		# re-application never shortens a duration (None means indefinite)
		newDur = None if None in (entry[2],dur) else max(entry[2],dur)
		# unstackable conditions have frozen durations
		if not canStack or newDur == entry[2]:
			return False
		entry[2] = newDur
		return True


	# run the cascade descriptors the named condition authored for one kind
	# of status event (action is one of the seven hook field names)
	# the condition name is the source, so bound statuses are stamped with it
	def evokeStatusHooks(self,action,name):
		descriptors = getattr(Data.StatusCondition.get(name),action)
		if not descriptors:
			return
		import Effects
		Effects.evokeEffects(descriptors,self,name,self)


	# a status cascade spans a status mutation and all its consequences;
	# entries removed within it may not be re-added until it fully resolves
	@contextmanager
	def statusCascade(self):
		self.statusCascadeDepth += 1
		try:
			yield
		finally:
			self.statusCascadeDepth -= 1
			if self.statusCascadeDepth == 0:
				self.alreadyRemoved.clear()


	# plain objects run no status checks; Creature overrides this
	def queueStatusCheck(self):
		return


	# plain objects have no status checks to defer; Creature overrides this
	@contextmanager
	def deferStatusChecks(self):
		yield


	# add a status entry, print message unless silent
	def addStatus(self,name,source=None,dur=None,allowStack=True,silent=False):
		assert dur is None or (isinstance(dur,int) and dur > 0), \
			f"status duration must be None or positive, got {dur}"
		# a (name, source) removed during this cascade may not be re-added
		if (name,source) in self.alreadyRemoved:
			return False
		blocker = self.blocksStatus(name)
		if blocker is not None:
			self.evokeStatusHooks("onBlock",blocker)
			return False
		canStack = allowStack and Data.StatusCondition.get(name).stackable
		# (name, source) is an entry's identity; re-adding refreshes duration
		entry = self.getStatusEntry(name,source)
		if entry is not None:
			if self.refreshStatus(entry,dur,canStack):
				self.display()
				return True
			return False
		hadStatus = self.hasStatus(name)
		if hadStatus and not canStack:
			return False
		# defer reports so the whole cascade narrates net transitions only:
		# the report is queued first to record the pre-add state, but prints
		# at the deferral's close, after any hooks have settled the outcome
		# (a hook may wake the bearer, or even remove the new condition)
		with game.deferStatusReports(), self.statusCascade():
			insort(self.status,[name,source,dur],key=statusEntryKey)
			game.queueStatusReport(self,name,hadStatus,silent=silent)
			self.evokeStatusHooks("onAdd",name)
			if not hadStatus:
				self.evokeStatusHooks("onGain",name)
			self.queueStatusCheck()
		self.display()
		return True


	# remove any status entry matching reqName, reqSource, reqDuration
	# reqName may be one name, a collection of names (matching any), or "*"
	# reqSource/reqDuration "*" match anything; None matches unsourced
	# entries / indefinite durations respectively
	def removeStatus(self,reqName="*",reqSource="*",reqDuration="*",silent=False):
		reqNames = (reqName,) if isinstance(reqName,str) else reqName
		condsRemoved = []
		with self.statusCascade():
			# copy to prevent removing-while-iterating errors
			for entry in self.status.copy():
				# cascades fired mid-loop may have already stripped this entry
				if entry not in self.status:
					continue
				name,source,duration = entry
				# PERMANENT-sourced entries are only removed by explicitly given source
				if reqSource == "*" and source == "PERMANENT":
					continue
				if (reqName == "*" or name in reqNames) and \
				reqSource in (source,"*") and reqDuration in (duration,"*"):
					self.status.remove(entry)
					condsRemoved.append(name)
					game.queueStatusReport(self,name,True,silent=silent)
					# the cascade may not re-add what it removed
					self.alreadyRemoved.add((name,source))
					self.evokeStatusHooks("onRemove",name)
					if not self.hasStatus(name):
						# only expiry matches entries with no time left
						self.evokeStatusHooks("onExpire" if reqDuration == 0
							else "onLoss",name)
			if condsRemoved:
				self.queueStatusCheck()
		self.display()
		return bool(condsRemoved)


	def nameQuery(self,term,d=2):
		term = term.lower()
		# querying  into player inventory must be explicitly demanded
		key = lambda obj: nameMatch(term,obj) and player not in obj.ancestors()
		return self.query(key=key,d=d,includeSelf=True)


	# wrapper for objQuery() (see comments)
	# get all objects in object tree
	def objTree(self,includeSelf=False):
		matches = objQuery(self,d=3)
		if not includeSelf:
			matches.remove(self)
		return matches


	# wrapper for objQuery() (see comments)
	# sets the degree of the query to 2 by default
	def query(self,key=None,d=2,includeSelf=False):
		# querying into player inventory must be explicitly demanded
		if key is None: key = lambda obj: player not in obj.ancestors()
		matches = objQuery(self,key=key,d=d)
		if not includeSelf and self in matches:
			matches.remove(self)
		return matches


	# look up the shared Material record for this object's composition
	def material(self):
		return Data.Material.get(getattr(self,"composition",None))


	# compared with Container capacity and for checking cover/hiding
	def Size(self):
		return self.weight


	# return the amount of this object's size that cannot be freed by spilling
	def minimumSize(self):
		return self.Size()


	# gets the first ancestor that isn't open, or the final ancestor (room)
	# used to determine the 'root' of a Creature's available surroundings
	def surroundings(self,includeSelf=False):
		# print(self,self.ancestors())
		ancs = self.ancestors()
		if includeSelf:
			ancs = [self] + ancs
		for anc in ancs:
			if getattr(anc,"closed",False):
				return anc
		return self.room()


	# used to compare objects mass
	def Weight(self):
		return self.weight


	### User Output ###

	# overridden by Player to refresh the side panel
	def display(self,*args):
		return

	# gets an object's name in various grammatical contexts
	# such as 'an elephant', 'the elephants', 'The elephant', '3 elephants', etc.
	# det should be given as 'a' or 'the'
	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		# if det.lower() == "the":
		strname = self.name
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		# if self.determiner is not None and det == "":
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "your" if self.definiteDeterminer() == "your" else "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname



# EmptyGear is a singleton class representing the absence of gear
# it is used as a placeholder for creatures with nothing equipped
class EmptyGear(GameObject):
	_instance = None
	name = "[EMPTY]"
	aliases = set()
	weight = 0
	durability = 0
	composition = None
	prot = 0
	might = 1
	sleight = 0
	sharpness = 0
	type = "e"
	slots = None


	### Dunder Methods ###

	# singleton instance, so all EmptyGear instances are the same
	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance


	def __repr__(self):
		return f"<empty>"


	def __setattr__(self, key, value):
		# EmptyGear may not be modified, but we don't want to throw an error
		pass


	### Getters ###

	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		return "[EMPTY GEAR]"


	def asWeapon(self):
		return self
	
	
	### User Output ###

	def displayName(self):
		return "[---]"



# The Game class stores a series of global data about the game that is not
# contained in the global world dict, W, including things like the time,
# a pointer to the current room and previous room, and a pointer to the
# Creature who is currently taking a turn.
# It also offers a series of methods for identifying the currently rendered
# rooms and finding information about them.
class Game():
	def __init__(self,mode,currentroom,prevroom,time,events,dlogForest,creatureFactory,
	itemFactory,nextObjId=0):
		### Settings

		# 0 for normal mode, 1 for testing mode, 2 for god mode
		self.mode = mode

		### Timing

		# 23 moments in an hour
		self.hourlength = 23
		self.daylength = len(Data.hours) * self.hourlength
		# 14 days in a month
		self.monthlength = 14 * self.daylength

		### General game state

		# the Room play is in now, room player was in last
		self.currentroom = currentroom
		self.prevroom = prevroom
		# the number of action loops that have elapsed since the game's start
		self.time = time
		# the time of the last save made
		self.lastSave = time
		# the creature who is currently acting
		self.whoseTurn = None
		# set of important events that have transpired in the game's progression
		# serves as the game's "memory" for story purposes
		self.events = events
		# set of all Celestial objects currently present (depends on time)
		self.celestials = set()
		self.checkDaytime(silent=True)
		self.checkAstrology(silent=True)

		### Objects Infrastructure

		# dictionaries used to generate dlog Trees, creatures, and items respectively
		self.dlogForest = dlogForest
		self.creatureFactory = creatureFactory
		self.itemFactory = itemFactory
		# references to all Items in the world, each item.id should be its key here
		self.itemRegistry = {None: None}
		# the ID watermark: always above every id ever seen, including the ids
		# of dead objects persisted across saves, so no id is ever used twice
		self.nextObjId = nextObjId
		self.reservedObjIds = set()
		### User I/O

		# used for determining whether or not to print most things 
		# usually, silent is True when the player is unconscious
		self.silent = False
		# pronoun references for objects that the player may
		# implicitly refer to with the given pronoun in their user input
		# for instance, if the user inputs "attack him", or "take it"
		self.it = None
		self.they = None
		self.he = None
		self.she = None
		# stores the last command before processing. Used for cheatcode input
		self.lastRawCommand = None
		# used to trigger a quit from the player
		self.quit = False
		# status reports may be deferred and collated during transitional states
		self.pendingStatusReports = {}
		self.statusReportDepth = 0


	### Item Registry ###

	# clear Item registry between runs of the game
	# nextObjId is deliberately NOT reset; the watermark never decreases
	def clearRegistry(self):
		self.itemRegistry = {None: None}
		self.reservedObjIds = set()


	# get next id to give an Item
	def getNextID(self):
		while self.nextObjId in self.reservedObjIds or \
		self.nextObjId in self.itemRegistry:
			self.nextObjId += 1
		objId = self.nextObjId
		self.nextObjId += 1
		return objId


	# Resolve an object specification's broad runtime type without constructing it.
	def resolveSpecClass(self,candidate):
		if not isinstance(candidate,dict):
			return None
		className = candidate.get("__class__")
		if className in (None,"set","DialogueTree") or \
		className == "Player" and len(candidate) == 1:
			return None
		if className == "factoryItem":
			if candidate.get("name") not in self.itemFactory:
				raise ValueError(f"Unknown item factory '{candidate.get('name')}'")
			return Item
		if className == "factoryCreature":
			if candidate.get("name") not in self.creatureFactory:
				raise ValueError(f"Unknown creature factory '{candidate.get('name')}'")
			return Creature
		objClass = strToClass(className,["Core","Creatures","Items"])
		if objClass is None:
			raise ValueError(f"Unknown object class '{className}'")
		return objClass


	# Reserve authored IDs before assigning new ones so generated IDs cannot collide.
	def collectObjectIDs(self,rawData):
		objectIds = set()

		def collect(dataNode):
			if isinstance(dataNode,list):
				for childNode in dataNode:
					collect(childNode)
				return
			if not isinstance(dataNode,dict):
				return
			if self.resolveSpecClass(dataNode) is not None and \
			dataNode.get("id") is not None:
				objId = dataNode["id"]
				if objId in objectIds:
					raise ValueError(f"Duplicate object ID {objId}")
				objectIds.add(objId)
			for childNode in dataNode.values():
				collect(childNode)

		collect(rawData)
		return objectIds


	# Give a nested object an identity so other specifications can refer to it by tether.
	def assignSpecID(self,objectSpec):
		if objectSpec.get("id") is None:
			objectSpec["id"] = self.getNextID()
			self.reservedObjIds.add(objectSpec["id"])
		return objectSpec["id"]


	# Place a tethered object beside its anchor because tethers connect sibling objects.
	def addSiblingSpec(self,parentSpec,sourceCollection,objectSpec):
		parentClass = parentSpec.get("__class__")
		if parentClass == "Room":
			objClass = self.resolveSpecClass(objectSpec)
			if issubclass(objClass,Creature):
				destination = "creatures"
			elif issubclass(objClass,Fixture):
				destination = "permanents"
			else:
				destination = "items"
		else:
			destination = sourceCollection
		parentSpec.setdefault(destination,[]).append(objectSpec)


	# Put an anchor's ID into an object specification to represent a tether connection.
	def setSpecReference(self,objectSpec,tetherName,anchorId,anchorSpec):
		existingTetherId = objectSpec.get(tetherName)
		if existingTetherId not in (None,anchorId):
			raise ValueError(f"{objectSpec.get('name',objectSpec.get('__class__'))} has " \
			f"conflicting {tetherName} declarations {existingTetherId} and {anchorId} " \
			f"from {anchorSpec.get('name',anchorSpec.get('__class__'))}")
		objectSpec[tetherName] = anchorId


	# Walk the containment tree so nested tether declarations are expanded at every depth.
	def normalizeCollectionRecur(self,parentSpec,parentCollectionName):
		collection = parentSpec.setdefault(parentCollectionName,[])
		idx = 0
		# for each child object in parent's collection
		# note we use a while loop, because normalization may add to collection
		while idx < len(collection):
			objectSpec = collection[idx]
			objClass = self.resolveSpecClass(objectSpec)
			if objClass is None:
				idx += 1
				continue
			# Assume the default floor of an object is the room's floor of not explicitly specified
			# This is done here because object constructors cannot handle it prior to EnmeshWorld
			if parentCollectionName in ("permanents","items","creatures") and \
			"platform" not in objectSpec and \
			objectSpec.get("riding") is None and objectSpec.get("carrier") is None:
				objectSpec["platform"] = "floor"
			# Normalize child's nested tethers first,
			# since nested gear may be moved into the child's inventory.
			self.normalizeObjectTethers(objectSpec,parentSpec,parentCollectionName)

			# if this child object has children of its own, recur into its collections
			if issubclass(objClass,Creature):
				self.normalizeCollectionRecur(objectSpec,"inv")
			elif issubclass(objClass,Container):
				self.normalizeCollectionRecur(objectSpec,"items")
			idx += 1


	# In the world, sibling objects can have 'tethers' with each other
	# tethers represent spatial relationships and have an anchor and a cargo
	# In JSON, these can flexiby be stored by nesting objects within eachother instead of using IDs
	# ex. a Horse (anchor) has a 'riders' list, which contains a whole knight object (cargo),
	# rather than simply the ID of the knight. We want to relocate these nested objects,
	# moving them into the parent's children to become a sibling, and replace
	# the original relationship with a canonical ID referencing the now-moved object
	def normalizeObjectTethers(self,anchorSpec,parentSpec,parentCollectionName):
		anchorId = None

		# Nested tether dependents become sibling references.
		for nestedField,tetherName in (("occupants","platform"),
		("riders","riding"),("covering","cover"),
		("immersedObjects","immersed")):
			tetheredSpecs = anchorSpec.pop(nestedField,[])
			if not isinstance(tetheredSpecs,list):
				tetheredSpecs = [tetheredSpecs]
			for tetheredSpec in tetheredSpecs:
				if isinstance(tetheredSpec,int):
					raise ValueError(f"{nestedField} entries must be nested object " \
						f"specifications, not ID {tetheredSpec}")
				if self.resolveSpecClass(tetheredSpec) is None:
					raise ValueError(f"Invalid object specification in {nestedField}")

				# make sure anchor has an ID
				if anchorId is None:
					anchorId = self.assignSpecID(anchorSpec)
				# give nested spec an ID
				self.assignSpecID(tetheredSpec)
				# move nested spec to be a sibling object
				self.addSiblingSpec(parentSpec,parentCollectionName,tetheredSpec)
				# replace the original tether with the given ID
				self.setSpecReference(tetheredSpec,tetherName,anchorId,anchorSpec)

		# Carrying is a special tether relationship, stored in the 'gear' dict
		# nested creature cargo becomes a sibling, while nested gear enters inventory
		gear = anchorSpec.get("gear",{})
		if not isinstance(gear,dict):
			return
		for slot,gearObjSpec in list(gear.items()):
			gearObjClass = self.resolveSpecClass(gearObjSpec)
			if gearObjClass is None:
				continue
			if anchorId is None:
				anchorId = self.assignSpecID(anchorSpec)
			gearId = self.assignSpecID(gearObjSpec)
			if issubclass(gearObjClass,Creature):
				self.setSpecReference(gearObjSpec,"carrier",anchorId,anchorSpec)
				self.addSiblingSpec(parentSpec,parentCollectionName,gearObjSpec)
			else:
				anchorSpec.setdefault("inv",[]).append(gearObjSpec)
			gear[slot] = gearId


	# Construct one normalized specification whose attributes have already been built.
	def instantiateSpec(self,className,attributes):
		# dialogue trees will be converted from JSON into objects later during enmeshWorld
		if className == "DialogueTree":
			return attributes
		# special factory objects are instantiated via their factory, and their types are validated
		if className in ("factoryItem","factoryCreature"):
			if className == "factoryCreature":
				runtimeObject = self.creatureFactory[attributes["name"]]()
				validProduct = isinstance(runtimeObject,Creature)
			else:
				runtimeObject = self.itemFactory[attributes["name"]]()
				validProduct = isinstance(runtimeObject,Item) and \
					not isinstance(runtimeObject,Creature)
			if not validProduct:
				raise TypeError(f"{className} '{attributes['name']}' returned " \
					f"{runtimeObject.__class__.__name__}")

			# for flexibility when writing the JSON, set any additional attributes to the object
			for key,attributeValue in attributes.items():
				if key != "name":
					setattr(runtimeObject,key,attributeValue)
			return runtimeObject

		# instantiate regular game objects from their modules
		objClass = strToClass(className,["Core","Creatures","Items"])
		if objClass is None:
			raise ValueError(f"Unknown object class '{className}'")
		try:
			return objClass(**attributes)
		except TypeError as error:
			attributeStr = "\n".join(f"{key}: {value}" \
				for key,value in attributes.items())
			raise TypeError(f"Failed to instantiate object '{className}' from " \
				f"attributes:\n{attributeStr}") from error


	# Define which children are owned by and therefore receive this object as parent.
	def ownedChildren(self,parentObject):
		# obj.contents() may not be used to identify its children here
		# contents() may include ephemeral or globally shared objects that aren't proper child objects
		if isinstance(parentObject,Room):
			children = parentObject.permanents + parentObject.items + parentObject.creatures
			children += [surface for surface in parentObject.surfaces if surface is not None]
			return children
		if isinstance(parentObject,Creature):
			return parentObject.inv
		if isinstance(parentObject,Container):
			return parentObject.items
		return []


	# Recursively instantiate objects from JSON specifications.
	def buildObjectRecur(self,jsonValue):
		# first recur into object children if given a list
		if isinstance(jsonValue,list):
			return [self.buildObjectRecur(childNode) for childNode in jsonValue]
		# return value as-is if not given a list or dict
		if not isinstance(jsonValue,dict):
			return jsonValue

		# if given a dict, recur into its child values first
		className = jsonValue.get("__class__")
		attributes = {}
		for key,attributeValue in jsonValue.items():
			if key != "__class__":
				attributes[key] = self.buildObjectRecur(attributeValue)

		# if dict isnt a game object spec, then return as a dict
		if className is None:
			return attributes
		# JSON doesn't natively support sets, they were given a special class label
		if className == "set":
			return set(attributes["setdata"])
		# if dict is an actual game object specification, instantiate it
		runtimeObject = self.instantiateSpec(className,attributes)
		# set object as its children's parent
		for childObject in self.ownedChildren(runtimeObject):
			childObject.parent = runtimeObject

		# if the object is a Room, register its surfaces as unique items
		if isinstance(runtimeObject,Room):
			for surface in runtimeObject.surfaces:
				if surface is None:
					continue
				if surface.id is None:
					surface.id = self.getNextID()
				self.registerItem(surface)

		# register the item if it is not already registered and return
		if isinstance(runtimeObject,Item):
			if runtimeObject.id is None:
				runtimeObject.id = self.getNextID()
			self.registerItem(runtimeObject)
		return runtimeObject


	# Instantiate all world objects before any cross-object references are connected.
	def instantiateWorld(self,worldData):
		builtWorld = {}
		# instantiate each room and insert it in world
		for roomKey,roomSpec in worldData.items():
			room = self.buildObjectRecur(roomSpec)
			if not isinstance(room,Room):
				raise ValueError(f"World entry '{roomKey}' did not build a Room")
			builtWorld[roomKey] = room

		# ensure world only contains one player
		players = [runtimeObject for runtimeObject in self.itemRegistry.values() \
			if isinstance(runtimeObject,Player)]
		if len(players) != 1:
			raise ValueError(f"World must contain exactly one Player, found {len(players)}")

		# celestials are global objects that don't belong in the world directly
		# so make sure to register them too
		for celestial in celestials:
			celestial.parent = None
			celestial.id = self.getNextID()
			self.registerItem(celestial)

		return builtWorld,players[0]


	# Connect objects by reference, replacing IDs, once all objects exists in the registry.
	def enmeshWorld(self):
		# establish links between rooms, replacing their name ids with real references
		for room in world.values():
			for direction,destination in room.links.items():
				if not isinstance(destination,str) or destination not in world:
					raise ValueError(f"Room {room.name} has unknown {direction} " \
						f"destination {destination}")
				room.links[direction] = world[destination]

		# Portal pair IDs may occur in several directions, but must join two portals.
		portalPairs = {}
		for obj in self.itemRegistry.values():
			if not isinstance(obj,Portal):
				continue
			for direction,destination in list(obj.links.items()):
				if isinstance(destination,str) and destination in world:
					obj.links[direction] = world[destination]
				elif isinstance(destination,str) and destination.startswith("port:"):
					portalPairs.setdefault(destination,[]).append((obj,direction))
				elif isinstance(destination,int):
					if destination not in self.itemRegistry or \
						self.itemRegistry[destination] is None:
						raise ValueError(f"Portal {obj} has unknown {direction} object " \
							f"destination {destination}")
					obj.links[direction] = self.itemRegistry[destination]
				elif not isinstance(destination,(Room,Item)):
					raise ValueError(f"Portal {obj} has unknown {direction} " \
						f"destination {destination}")

		for linkId,endpoints in portalPairs.items():
			Portal.resolveLinkPair(linkId,endpoints)

		# Resolve object IDs from global item registry
		def resolveId(runtimeObject,referencedId,tetherName):
			if not isinstance(referencedId,int) or referencedId not in self.itemRegistry:
				raise ValueError(f"{runtimeObject} references unknown " \
					f"{tetherName} {referencedId}")
			return self.itemRegistry[referencedId]

		# resolve all stored object references before deriving any runtime state
		for runtimeObject in self.itemRegistry.values():
			if runtimeObject is None or runtimeObject in celestials:
				continue

			# replace object's tether IDs with object references
			for tetherName in ("platform","carrier","riding","cover","immersed"):
				if not hasattr(runtimeObject,tetherName):
					continue
				referencedId = getattr(runtimeObject,tetherName)
				if isinstance(referencedId,int):
					setattr(runtimeObject,tetherName,
						resolveId(runtimeObject,referencedId,tetherName))

			if isinstance(runtimeObject,Creature):
				for slot,itemId in runtimeObject.gear.items():
					if isinstance(itemId,int):
						runtimeObject.gear[slot] = resolveId(runtimeObject,itemId,
							f"gear slot '{slot}'")


	# Some object attributes, like the object's floor, cannot be determined-
	# during instantiation, because objects don't yet have tethers or a parent.
	# So here, convert serialized sentinel values to reestablish runtime object states.
	def unpackWorld(self):
		# get all registered objects; celestials don't need any unpacking
		runtimeObjects = [runtimeObject for runtimeObject in self.itemRegistry.values() \
			if runtimeObject is not None and runtimeObject not in celestials]

		for runtimeObject in runtimeObjects:
			parent = runtimeObject.parent
			if getattr(runtimeObject,"platform",None) == "floor":
				# determine object floor from parent's floor
				runtimeObject.platform = runtimeObject.footing(parent)

			if isinstance(runtimeObject,Creature):
				# carried creatures start out restrained by their carrier
				if runtimeObject.carrier is not None and \
				not runtimeObject.hasStatus("restrained",
				reqSource=runtimeObject.carrier.id):
					insort(runtimeObject.status,
						["restrained",runtimeObject.carrier.id,None],
						key=lambda e: e[0])

				# empty gear slots become EmptyGear objects
				for slot,item in runtimeObject.gear.items():
					if item is None or item is EmptyGear():
						runtimeObject.gear[slot] = EmptyGear()

				# assign weapon and shield, and build dialogue trees
				runtimeObject.assignWeaponAndShield()
				if isinstance(runtimeObject,Speaker):
					runtimeObject.buildDialogue()

		# Immersion depends on every tether, platform, and gear reference above.
		for runtimeObject in runtimeObjects:
			parent = runtimeObject.parent
			if runtimeObject not in getattr(parent,"surfaces",()):
				runtimeObject.checkImmersion(silent=True)


	# Reject impossible world states before gameplay can depend on their relationships.
	def validateWorld(self):
		def require(condition,message):
			if not condition:
				raise ValueError(message)

		contained = set()
		visiting = set()

		def validateContainmentRecur(parent):
			require(parent not in visiting,
				f"Containment cycle reaches {parent}")
			visiting.add(parent)
			for child in self.ownedChildren(parent):
				require(isinstance(child,Item),
					f"{parent} contains non-Item {child}")
				require(child not in contained,
					f"{child} appears in multiple containment positions")
				require(child.parent is parent,
					f"{child} has parent {child.parent}, expected {parent}")
				contained.add(child)
				validateContainmentRecur(child)
			visiting.remove(parent)

		for roomKey,room in world.items():
			require(isinstance(room,Room),
				f"World entry '{roomKey}' is not a Room")
			require(room.name.lower() == roomKey,
				f"Room name '{room.name}' does not match key '{roomKey}'")
			validateContainmentRecur(room)

		require(player in contained,
			"Player does not occupy exactly one position in the world")
		for celestial in celestials:
			require(celestial.parent is None,
				f"Celestial {celestial} unexpectedly has parent {celestial.parent}")

		registryObjects = {runtimeObject for runtimeObject in self.itemRegistry.values() \
			if runtimeObject is not None}

		# suspended objects are owned by their substitutes rather than the
		# containment tree; validate their subtrees and count them as placed
		suspended = set()
		for runtimeObject in registryObjects:
			latent = getattr(runtimeObject,"latent",None)
			if latent is None:
				continue
			require(latent not in contained and latent not in suspended,
				f"Suspended {latent} occupies another world position")
			require(latent.parent is None,
				f"Suspended {latent} unexpectedly has parent {latent.parent}")
			# the latent's substitute reference must mirror the link
			require(latent.substitute is runtimeObject,
				f"Suspended {latent} does not point back at its " \
					f"substitute {runtimeObject}")
			suspended.add(latent)
			validateContainmentRecur(latent)

		# the mirror direction: a substitute reference with no suspended
		# link pointing back is a desynchronized custody record
		for runtimeObject in registryObjects:
			if runtimeObject.substitute is not None:
				require(runtimeObject in suspended,
					f"{runtimeObject} points at a substitute that does " \
						f"not hold it")

		for objId,runtimeObject in self.itemRegistry.items():
			if runtimeObject is None:
				continue
			require(isinstance(objId,int) and runtimeObject.id == objId,
				f"Registry key {objId} does not match {runtimeObject}'s ID " \
					f"{runtimeObject.id}")
		require(registryObjects == contained | set(celestials) | suspended,
			"Registry and contained world objects do not match")

		for room in world.values():
			room.validate()
		for celestial in celestials:
			celestial.validate()


	# Use the authored placeholder to put the loaded Player in the intended location.
	def insertPlayer(self,dataNode,playerSpec):
		if isinstance(dataNode,list):
			placeholderCount = 0
			for idx,childNode in enumerate(dataNode):
				if isinstance(childNode,dict) and childNode == {"__class__":"Player"}:
					dataNode[idx] = playerSpec
					placeholderCount += 1
				else:
					placeholderCount += self.insertPlayer(childNode,playerSpec)
			return placeholderCount
		if not isinstance(dataNode,dict):
			return 0
		if dataNode.get("__class__") == "Player":
			raise ValueError("World contains an embedded Player instead of a placeholder")
		return sum(self.insertPlayer(childNode,playerSpec) \
			for childNode in dataNode.values())


	# Translate author-friendly world data into the canonical form construction expects.
	def normalizeWorldData(self,worldSpec,playerSpec):
		if not isinstance(playerSpec,dict) or playerSpec.get("__class__") != "Player":
			raise ValueError("player data does not contain a Player specification")

		# The placeholder determines the player's containment position.
		playerCount = self.insertPlayer(worldSpec,playerSpec)
		if playerCount != 1:
			raise ValueError(f"World must contain one Player placeholder, found {playerCount}")

		# extract the preexisting object ids from the JSON world data so they aren't reused
		self.reservedObjIds = self.collectObjectIDs(worldSpec)

		normalizedWorld = {}
		for roomKey,roomSpec in worldSpec.items():
			if roomKey != roomKey.lower():
				raise ValueError(f"World key '{roomKey}' must be lowercase")
			if roomKey in normalizedWorld:
				raise ValueError(f"Duplicate room key '{roomKey}'")
			if roomSpec.get("__class__") != "Room":
				raise ValueError(f"World entry '{roomKey}' is not a Room")
			if roomSpec["name"].lower() != roomKey:
				raise ValueError(f"Room name '{roomSpec['name']}' does not match " \
					f"world key '{roomKey}'")
			normalizedWorld[roomKey] = roomSpec
			for collectionName in ("permanents","items","creatures"):
				self.normalizeCollectionRecur(roomSpec,collectionName)
		return normalizedWorld


	# Build a playable world in an order that prevents dangling IDs and invalid state.
	def buildWorld(self,worldSpec,playerSpec):
		# clear the registry to start fresh
		self.clearRegistry()
		# convert the flexible JSON into the canonical form expected by the builder
		normalizedWorld = self.normalizeWorldData(worldSpec,playerSpec)
		# instantiate the world and its objects
		builtWorld,playerObj = self.instantiateWorld(normalizedWorld)
		# publish the world as global objects used by enmeshWorld and validateWorld
		global world, player
		world = builtWorld
		player = playerObj
		# establish tethered relationships between objects in world
		self.enmeshWorld()
		# convert serialized sentinels and derive runtime-only state
		self.unpackWorld()
		# validate the integrity and consistency of the built world
		self.validateWorld()
		# no need to keep ids reserved anymore, they're all in the registry now
		self.reservedObjIds.clear()
		return builtWorld,playerObj


	# Give Item an ID if it doesn't have one and add it to registry
	def registerItem(self,obj):
		assert isinstance(obj,Item), f"Cannot register non-Item {obj}"
		if self.itemRegistry.get(obj.id) is obj:
			return
		elif obj.id in self.itemRegistry:
			raise Exception(f"Object ID {obj.id} from {obj.name} "
			f"already exists in registry as {self.itemRegistry[obj.id].name}")
		self.itemRegistry[obj.id] = obj
		# keep the ID watermark above every id ever seen, so each id is only
		# ever used by one object
		if isinstance(obj.id,int):
			self.nextObjId = max(self.nextObjId,obj.id + 1)


	# replace one Item with another in the registry
	# should only be called after lender has been removed from the world
	def replaceID(self,lender,borrower):
		assert isinstance(lender,Item) and isinstance(borrower,Item)
		assert lender not in self.itemRegistry.values(), \
		f"lender {lender} still in registry values when trying to give ID to {borrower}"
		# in case borrower already registered with ID, delete it
		if borrower.id is not None and borrower.id in self.itemRegistry:
			registryObj = self.itemRegistry[borrower.id]
			assert registryObj is borrower, f"ID conflict with {registryObj}" \
			f" when trying to replace {lender} with {borrower}"
			del self.itemRegistry[borrower.id]
		self.itemRegistry[lender.id] = borrower
		borrower.id = lender.id


	# Ensure a spawned object tree is registered, preserving valid existing entries.
	def registerSpawnTree(self,root):
		objects = []
		newObjects = []
		seen = set()
		visiting = set()

		def collect(obj,parent=None):
			if not isinstance(obj,Item):
				raise TypeError(f"Cannot spawn non-Item {obj}")
			if obj in visiting:
				raise ValueError(f"Containment cycle reaches {obj}")
			if obj in seen:
				raise ValueError(f"{obj} appears in multiple containment positions")
			seen.add(obj)
			visiting.add(obj)
			objects.append((obj,parent))
			for child in self.ownedChildren(obj):
				collect(child,obj)
			visiting.remove(obj)

		collect(root)
		explicitIds = set()
		for obj,parent in objects:
			if obj.id is None:
				continue
			if not isinstance(obj.id,int):
				raise TypeError(f"Object ID {obj.id} from {obj} is not an integer")
			registered = self.itemRegistry.get(obj.id)
			if registered is obj:
				continue
			if obj.id in explicitIds or registered is not None:
				raise ValueError(f"Duplicate object ID {obj.id}")
			explicitIds.add(obj.id)

		previousReservations = self.reservedObjIds.copy()
		self.reservedObjIds.update(explicitIds)
		try:
			for obj,parent in objects:
				if obj.id is not None and self.itemRegistry.get(obj.id) is obj:
					continue
				if obj.id is None:
					obj.id = self.getNextID()
				obj.parent = parent
				self.registerItem(obj)
				newObjects.append(obj)
		finally:
			self.reservedObjIds = previousReservations
		return [obj for obj,parent in objects],newObjects


	# Roll back only objects registered by the current spawn attempt.
	# Objects that were already registered are intentionally preserved.
	def unregisterSpawnTree(self,newObjects):
		for obj in newObjects:
			if self.itemRegistry.get(obj.id) is obj:
				del self.itemRegistry[obj.id]


	# spawn a new item tree, register it, and optionally enter its root into a parent
	def spawn(self,obj,parent=None):
		if isinstance(obj,str):
			if obj in self.creatureFactory:
				obj = self.creatureFactory[obj]()
			elif obj in self.itemFactory:
				obj = self.itemFactory[obj]()
			else:
				raise Exception(f"Cannot spawn unknown factory object {obj}")
		else:
			assert isinstance(obj,Item)

		if parent is not None and obj.parent is not None:
			raise ValueError(f"Cannot spawn {obj} into {parent}; it already has parent " \
				f"{obj.parent}")

		spawnedObjects,newObjects = self.registerSpawnTree(obj)
		if parent is not None:
			if isinstance(parent,Creature):
				attached = parent.ObtainItem(obj,silent=True)
			elif hasMethod(parent,"enter"):
				attached = parent.enter(obj)
			else:
				self.unregisterSpawnTree(newObjects)
				raise TypeError(f"Cannot spawn into {parent}")
			if not attached:
				self.unregisterSpawnTree(newObjects)
				return False
			try:
				obj.validate()
			except Exception:
				parent.remove(obj)
				self.unregisterSpawnTree(newObjects)
				raise
		# after attachment, so effects can resolve the spawn location
		obj.evokeEffects("spawn",None)
		return obj


	### Operation ###

	@contextmanager
	def deferStatusReports(self):
		self.statusReportDepth += 1
		try:
			yield
		finally:
			self.statusReportDepth -= 1
			if self.statusReportDepth == 0:
				self.flushStatusReports()


	def queueStatusReport(self,creature,name,hadStatus,silent=False):
		# non-creatures don't report status transitions
		if not hasMethod(creature,"reportStatusChange"):
			return False
		if self.statusReportDepth > 0:
			key = (creature,name)
			initialState,shouldReport = self.pendingStatusReports.get(key,
				(hadStatus,False))
			visibleChange = not silent and hadStatus != creature.hasStatus(name)
			self.pendingStatusReports[key] = \
				(initialState,shouldReport or visibleChange)
			return True
		if silent:
			return False
		return creature.reportStatusChange(name,hadStatus)


	def flushStatusReports(self):
		pendingReports = self.pendingStatusReports
		self.pendingStatusReports = {}
		# if pendingReports:
		# 	Print()
		for (creature,name),(initialState,shouldReport) in pendingReports.items():
			if shouldReport:
				creature.reportStatusChange(name,initialState)


	# has player exit the previous room and enter the new room
	def changeRoom(self,newroom):
		couldSeeSky = player.canSeeSky(self.currentroom)
		if newroom is self.currentroom:
			return
		# if newroom != self.currentroom:
		self.clearPronouns()
		clearScreen()
		self.prevroom = self.currentroom
		self.currentroom = newroom.room()

		# these need to happen before describeRoom; they may affect player.canNavigate()
		player.parent = newroom
		self.checkDaytime(silent=True)
		self.checkAstrology(silent=True)

		self.describeRoom()
		# then can print any celestial messages after describing the Room
		if not couldSeeSky and player.canSeeSky(self.currentroom):
			self.checkDaytime(newroom=True)
			self.checkAstrology(newroom=True)
		return True


	# when context changes, forget all implicit pronouns
	def clearPronouns(self):
		self.it = None
		self.they = None
		self.her = None
		self.him = None


	# passes time for each room, and each creature in each room
	# important for decrementing the duration counter on all status conditions
	def passTime(self,t=1):
		# print("T =",self.time)
		prevHour = self.hour()
		prevDaytime = self.daytime(prevHour)
		self.time += t
		self.silent = player.hasStatus(("asleep","dead"))

		# objs can change location during passTime;
		# flatten all object trees so we don't call passtime twice on any object
		roomObjTrees = (room.objTree(includeSelf=True) for room in self.renderedRooms())
		for obj in {o for objTree in roomObjTrees for o in objTree}:
			obj.passTime(t)

		# probably not necessary, celestials don't have status conditions
		# for celestial in celestials:
		# 	celestial.passTime(t)

		# check again, it may have changed during room.passTime
		self.silent = player.hasStatus(("asleep","dead"))
		if prevHour != self.hour():
			self.checkDaytime(prevDaytime=prevDaytime)
		self.checkAstrology()


	# sets implicit pronouns based on the type of object
	def setPronouns(self,obj):
		if not isinstance(obj,Person):
			self.it = obj
		if isinstance(obj,Creature):
			self.they = obj
		pronoun = getattr(obj,"pronoun",None)
		if pronoun == "him":
			self.he = obj
		elif pronoun == "her":
			self.she = obj


	### Getters ###

	# recursively adds all adjacent rooms to the set of found rooms
	# used by renderedRooms()
	# n is the path length at which the query stops
	# Sroom is the "source" room, or the current node in the query
	def roomFinder(self,n,Sroom,pathlen,foundrooms):
		if pathlen >= n:
			return
		adjacentRooms = (dest for dest in Sroom.allDests() if isinstance(dest,Room))

		for room in adjacentRooms:
			foundrooms.add(room)
			self.roomFinder(n,room,pathlen+1,foundrooms)


	# returns set of all rooms connected to currentroom with path length < REND_DIST
	def renderedRooms(self):
		# constant render distance of rooms in world
		REND_DIST = 3
		# the set of found rooms initially includes only the current room
		R = {self.currentroom}
		# add all rooms within a distance of REND_DIST to R
		self.roomFinder(REND_DIST,self.currentroom,0,R)
		return R


	# returns a list of objects in rendered rooms which fit a certain condition
	def queryRooms(self,key=lambda x:True,d=3):
		matchingObjects = []
		for room in self.renderedRooms():
			matchingObjects += room.query(key=key,d=d)
		return matchingObjects


	# True if there's an object in rendered rooms whose name matches objname
	# not case sensitive
	def inWorld(self,term):
		key = lambda obj: nameMatch(term,obj)
		objects = self.queryRooms(key)
		return len(objects) > 0


	# hours have names in this game, get name of the hour from the time
	def hour(self):
		return Data.hours[(self.time % self.daylength) // self.hourlength]


	def daytime(self,hour=None):
		if hour is None:
			hour = self.hour()
		if hour in ("stag","rooster","juniper"):
			return "morning"
		if hour in ("bell","sword","willow","lily"):
			return "day"
		if hour in ("hearth","cat"):
			return "evening"
		return "night"


	### Celestials ###

	# change the phase of the moon based on time, print message if not silent
	def checkMoon(self,silent=False,newroom=False):
		if getattr(getattr(player,"parent",None),"ceiling",None) is not None:
			silent=True
		self.events.discard("new moon")
		self.events.discard("full moon")
		msg = ""
		mooncycle = (self.time % self.monthlength) // self.daylength
		if mooncycle == 0:
			msg = "It is a new moon."
			self.events.add("new moon")
		elif mooncycle == 7:
			msg = "It is a full moon."
			self.events.add("full moon")
		if msg and not silent:
			Print(msg,color="b")


	# change the state of astrological objects, print message if not silent
	def checkAstrology(self,silent=False,newroom=False):
		if not silent and not player.canSeeSky():
			silent=True
		darkhours = ("hearth","cat","mouse","owl","serpent","wolf")
		aurora_cycle = self.time % 2000
		if aurora_cycle >= 0 and aurora_cycle < 100 and self.hour() in darkhours:
			if ("aurora" not in self.events or newroom) and not silent:
				Print("There is an aurora in the sky!",color="b")			
				self.setPronouns(aurora)
			self.events.add("aurora")
			self.celestials.add(aurora)
		elif "aurora" in self.events:
			self.events.remove("aurora")
			self.celestials.remove(aurora)
			if not silent:
				Print("The aurora is over.")

		meteor_cycle = self.time % 3500
		if meteor_cycle >= 0 and meteor_cycle < 300 and self.hour() in darkhours:
			if ("meteor shower" not in self.events or newroom) and not silent:
				Print("There is a meteor shower in the sky!",color="b")
				self.setPronouns(meteorshower)
			self.events.add("meteor shower")
			self.celestials.add(meteorshower)
		elif "meteor shower" in self.events:
			self.events.remove("meteor shower")
			self.celestials.remove(meteorshower)
			if not silent:
				Print("The meteor shower is over.")

		lighthours = ("rooster","juniper","bell","sword","willow","lily")
		eclipse_cycle = self.time % (self.monthlength*3+100)
		if eclipse_cycle > 0 and eclipse_cycle < 30 and self.hour() in lighthours:
			if ("eclipse" not in self.events or newroom) and not silent:
				Print("There is a solar eclipse in the sky!",color="b")
				self.setPronouns(eclipse)
			self.events.add("eclipse")
			self.celestials.add(eclipse)
		elif "eclipse" in self.events:
			self.events.remove("eclipse")
			self.celestials.remove(eclipse)
			if not silent:
				Print("The solar eclipse is over.")


	# change time of day, print message if not silent, check moon phase
	def checkDaytime(self,silent=False,newroom=False,prevDaytime=None):
		if getattr(getattr(player,"parent",None),"ceiling",None) is not None:
			silent=True
		daytime = self.daytime()
		self.celestials.add(sky)
		for daytimeEvent in ("morning","day","evening","night"):
			self.events.discard(daytimeEvent)
		self.events.add(daytime)
		for celestial in (sun,moon,stars):
			self.celestials.discard(celestial)

		if daytime == "morning":
			self.celestials.add(sun)
		elif daytime == "day":
			self.celestials.add(sun)
		elif daytime == "evening":
			self.celestials.add(sun)
			self.celestials.add(stars)
		else:
			self.celestials.add(moon)
			self.celestials.add(stars)

		if not silent:
			if newroom or prevDaytime is None:
				displayDaytime = "daytime" if daytime == "day" else daytime
				Print(f"It is {displayDaytime}.")
			elif daytime != prevDaytime:
				transitionMessages = {
					"morning":"Dawn breaks.",
					"day":"Morning gives way to afternoon.",
					"evening":"Evening approaches.",
					"night":"Night falls."
				}
				Print(transitionMessages[daytime])
		self.checkMoon(silent=(silent or daytime != "night"),newroom=newroom)


	### User Output ###		

	# begin game and set the scene
	def startUp(self):
		clearScreen()
		# if not sidepanel.isOpen():
		# 	player.openDisplay()
		self.describeRoom()
		player.printPosition()
		if self.currentroom.ceiling is None:
			game.checkDaytime()
			game.checkAstrology()


	# describe the current room
	def describeRoom(self):
		Print("\n"+self.currentroom.domain+"\n"+self.currentroom.name)
		self.currentroom.describe()
		if not isinstance(player.parent,Room):
			Print(f"You are in {-player.parent}.")
		# if player.carrying():
		# 	Print(f"You are carrying {~player.carrying()}.")


	# look up at the sky or ceiling and describe what is seen
	def LookUp(self,target):
		if target is not None and target.startswith("the "):
			target = target[4:]
		if self.currentroom.ceiling is not None:
			if target not in (None,"ceiling","roof"):
				Print("You can't see the sky from here.")
				return False
			return self.currentroom.ceiling.describe()

		if target in ("sky",None):
			target = "sun" if self.hour() in Data.dayhours else "moon"		

		if "eclipse" in self.events:
			Print(Data.eclipseDesc,color="b")
			player.takeDamage(5,"r")
		elif "eclipse" not in self.events and target in ("eclipse","solar eclipse"):
			Print("There's no eclipse happening right now.")
		elif target == "sun":
			if self.hour() in ("stag","rooster","juniper"):
				Print(Data.morningSunDesc)
			elif self.hour() in ("bell","sword","willow","lily"):
				Print(Data.highSunDesc)
			elif self.hour() in ("hearth","cat"):
				Print(Data.eveningSunDesc)
			else:
				Print("The sun isn't out right now.")
		elif target in ("moon","stars"):
			if self.hour() in Data.nighthours:
				if "full moon" in self.events:
					Print(Data.fullMoonDesc,color="b")
				elif "new moon" in self.events:
					Print(Data.newMoonDesc,color="b")
				else:
					Print(Data.moonDesc)
			elif target == "moon":
				Print("The moon isn't out right now.")
			elif target == "stars" and self.hour() in ("hearth","cat"):
				Print(Data.eveningStarsDesc,color="b")
			elif target == "stars":
				Print("The stars aren't out right now.")

		if "aurora" in self.events:
			Print(Data.auroraDesc,color="b")
		elif target in ("aurora","auroras"):
			Print("There's no aurora happening right now.")

		if "meteor shower" in self.events:
			Print(Data.meteorDesc,color="b")
		elif target in ("shower","meteors","meteor shower"):
			Print("There's no meteor shower happening right now.")
		return True



# the Room class is the fundamental unit of the game's world.
# The world dict, consists of key:value pairs of the form {"room name":Room}

# Importantly, each room contains a links dict, where keys are directions
# such as such as 'north', 'up', or 'beyond', and values are the neighboring rooms
# In this way, every Room object can be thought of like a node in a large
# directed graph, facilitated by the world dict, where the links dict specifies
# the edges from a given node to its neighboring nodes.
class Room(GameObject):
	def __init__(self,name,domain,desc,links,permanents,items,creatures,capacity=1000,
	passprep=None,composition=None,ceiling=None,walls=None,floor=None,status=None):
		# name serves as the Room's unique id
		self.name = name
		# domains are regions within the world, used for determining creatures to spawn
		# typically many rooms near eachother belong to the same domain
		self.domain = domain
		self.desc = desc
		self.links = links

		# room's contents is split between these three, mostly for convenience
		self.permanents = permanents
		self.items = items
		self.creatures = creatures
		for f in self.permanents:
			assert f.fixed and not isinstance(f,Creature), \
			f"Non-fixed permanent {f} in Room {self.name}"
		for i in self.items:
			assert not isinstance(i,Creature), \
			f"Creature {i} in Room {self.name} items list"
		for c in self.creatures:
			assert isinstance(c,Creature), \
			f"Non-creature {c} in Room {self.name} creatures list"

		# determines how much mass the Room can hold, objects too large cannot enter
		self.capacity = capacity

		self.status = [normalizeStatusEntry(entry) for entry in status] \
			if status else []
		# transient status-cascade state (never serialized)
		self.statusCascadeDepth = 0
		self.alreadyRemoved = set()

		self.passprep = "at" if passprep is None else passprep
		self.parent = None
		self.pronoun = "it"
		self.determiner = None

		self.composition = composition
		# these are the default room surfaces, 
		# given from the world json as strings of the surface's composition
		self.ceiling = None
		self.walls = None
		self.floor = None
		if ceiling:
			self.ceiling = Surface("ceiling",f"A ceiling of {ceiling}.",capacity//3,
			ceiling,aliases=["roof"])
		if walls:
			self.walls = Surface("wall",f"Walls of {walls}.",capacity//3,walls,
			aliases=["walls"])
		if Data.Material.get(floor).liquid:
			self.floor = Surface("surface",f"A surface of {floor}.",capacity//3,floor,
			aliases=[floor],determiner="the")
		elif floor:
			self.floor = Surface("ground",f"A floor of {floor}.",capacity//3,floor,
			aliases=["floor"],determiner="the")
		self.surfaces = (self.ceiling,self.walls,self.floor)


	### Dunder Methods ###

	def __repr__(self):
		return f"Room({self.name})"


	### File I/O ###

	# Validate room capacity and ensure every room link has been resolved.
	def validate(self):
		if self.vacancy() != -1 and self.vacancy() < 0:
			raise ValueError(f"Room {self.name} exceeds its capacity")
		for destination in self.links.values():
			if not isinstance(destination,Room):
				raise ValueError(f"Room {self.name} has unresolved or invalid link " \
					f"{destination}")
		return super().validate()

	# restore links dict to using strings as values for saving to json
	# restore surfaces to using strings representing their composition
	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		jsonDict["links"] = {}
		for dir, dest in self.links.items():
			assert isinstance(dest, Room), f"Trying to save room {self.name} "
			f"with exit to non-Room '{dest}'"
			jsonDict["links"][dir] = dest.name.lower()

		del jsonDict["pronoun"]
		if self.ceiling:
			jsonDict["ceiling"] = self.ceiling.composition
		if self.walls:
			jsonDict["walls"] = self.walls.composition
		if self.floor:
			jsonDict["floor"] = self.floor.composition

		del jsonDict["surfaces"], jsonDict["determiner"]
		del jsonDict["statusCascadeDepth"], jsonDict["alreadyRemoved"]
		return jsonDict


	### Operation ###

	# Add an existing registered object to this room.
	def add(self,O,allowOverflow=False):
		if not isinstance(O,Item) or game.itemRegistry.get(O.id) is not O:
			raise ValueError(f"Cannot add unregistered object {O} to {self}")
		if not self.canAdd(O):
			return False
		if not allowOverflow and self.vacancy() != -1 and O.Size() > self.vacancy():
			return False

		# set platform surface for object if it has a usable floor
		if O.anchor() is None and not O.hasStatus("flying"):
			O.platform = O.footing(self)

		# add object to appropriate content list
		if isinstance(O,Creature):
			insort(self.creatures,O)
			O.parent = self
			O.expose(None,self)
			return O
		elif isinstance(O,Item):
			# merge object if mergeable with existing item here
			for item in self.items:
				merged = O.merge(item)
				if merged:
					return merged

			insort(self.items,O)
			O.parent = self
			O.timeDespawn()
			O.expose(None,self)
			return O
		return False


	# Register and place an object in this room through Game.spawn().
	def spawn(self,obj):
		return game.spawn(obj,self)


	# add a status entry to the Room; contents are maintained with
	# matching AREA-sourced entries while the Room's status lasts
	# (calls GameObject explicitly so Container can borrow this method)
	def addStatus(self,name,source=None,dur=None,allowStack=True,silent=False):
		if not GameObject.addStatus(self,name,source,dur,allowStack,silent):
			return False
		for obj in self.query():
			obj.addStatus(name,source="AREA")
		return True


	# add one-way link to a neighboring Room
	# to ensure a bidirectional link between Rooms, call this once on each room.
	def addLink(self,dir,loc):
		self.links[dir] = loc


	# apply any room effects to the obj entering
	def enter(self,obj):
		if not self.canAdd(obj):
			return False
		isPlash = hasMethod(obj,"Spill")

		obj = self.add(obj,allowOverflow=not isPlash)
		if not obj:
			return False
		# maintain this room's statuses on the obj entering
		for cond,src,dur in self.status:
			obj.addStatus(cond,source="AREA")

		obj.checkImmersion()
		self.overflow()
		assert self.vacancy() == -1 or self.vacancy() >= 0, \
			f"{obj} caused unresolved overflow in {self}"
		obj.checkImmersion()
		return True


	# spill reducible liquid until contents no longer exceed capacity
	def overflow(self):
		if self.Capacity() == -1 or self.vacancy() >= 0:
			return False

		overflowed = False
		while self.vacancy() < 0:
			plashes = [obj for obj in self.spatialContents() \
				if hasMethod(obj,"Spill") and obj.Size() > obj.minimumSize()]
			if not plashes:
				break
			plash = max(plashes,key=lambda obj:obj.Size()-obj.minimumSize())
			spill = plash.Spill(size=-self.vacancy())
			game.spawn(spill)
			spill.displace(self.parent)
			overflowed = True

		return overflowed


	# restore capacity after an unexpected size change as a last-resort safeguard
	def checkCapacity(self):
		if self.Capacity() == -1 or self.vacancy() >= 0:
			return True

		self.overflow()

		while self.vacancy() < 0:
			permanents = getattr(self,"permanents",())
			contents = [obj for obj in self.spatialContents() if obj not in permanents]
			if not contents:
				break
			item = max(contents,key=lambda obj:obj.Size())
			item.displace(self.parent)

		assert self.vacancy() >= 0, f"{self} cannot recover enough capacity"
		return True


	# remove any room effects from the obj exiting
	def exit(self,obj):
		if obj in getattr(self,"permanents",()):
			return False
		obj.removeStatus(reqSource="AREA")
		obj.unimmerse()
		self.remove(obj)
		assert obj not in self, f"Object {obj} still in Room {self.name} after exiting"
		assert obj.parent is None, f"Object {obj} still has parent after exiting Room {self.name}"
		return True


	# pass time for the Room, chance to spawn creatures, sort creatures by MVMT speed
	def passTime(self,t):
		self.checkCapacity()
		super().passTime(t)

		# chance to spawn up to 1 creature in the Room
		# type of creature depends on the domain
		for name, prob in Data.spawnpools.get(self.domain,()):
			if len(self.creatures) > 0 or self is game.currentroom:
				continue
			# TODO: refactor this to have an event chance for creatures in spawnpools?
			# right now it is biased to earlier in the list
			if percentChance(prob):
				game.spawn(name,self)

		# sort all Creatures occupying the Room by their MVMT() value, descending
		self.creatures.sort(key=lambda x: x.MVMT(), reverse=True)


	# Try to remove object from contents, ignore if not present
	def remove(self,O):
		if O in self.permanents:
			return False
		if isinstance(O,Creature):
			if O in self.creatures:
				self.creatures.remove(O)
				O.parent = None
				return True
		elif O in self.items:
			self.items.remove(O)
			O.parent = None
			return True
		return False


	# given an object, try to replace it with another object in the Room
	# returns True if successful, False if newObj was not added
	def replaceObj(self,oldObj,newObj):
		assert oldObj in self
		if oldObj in self.permanents:
			return False
		self.remove(oldObj)

		if not self.canAdd(newObj):
			# a failed replacement must leave oldObj where it was
			self.add(oldObj)
			return False
		self.enter(newObj)
		return True


	# removes status entries from the Room; contents lose the matching
	# AREA-sourced entry when the last same-name Room entry goes
	# (calls GameObject explicitly so Container can borrow this method)
	def removeStatus(self,reqName="*",reqSource="*",reqDuration="*",silent=False):
		before = {entry[0] for entry in self.status}
		removed = GameObject.removeStatus(self,reqName,reqSource,reqDuration,silent)
		for name in before - {entry[0] for entry in self.status}:
			for obj in self.query():
				obj.removeStatus(name,reqSource="AREA")
		return removed


	### Getters ###

	# get all neighboring rooms
	def allDests(self):
		return {dest for dest in self.allLinks().values()}


	# get the set of all directions leading out of the Room
	def allDirs(self):
		return {tuple[0] for tuple in self.allLinks()}


	# get all creatures in this room's object tree, sorted by MVMT descending
	def allCreatures(self):
		creatures = objQuery(self,key=lambda obj: isinstance(obj,Creature),d=3)
		return sorted(list(creatures), key=lambda x: x.MVMT(), reverse=True)


	# returns dict of links, where keys are (direction,Portal) and values are rooms
	# portal is None if the link is direct from the Room
	# d is the degree of the portal search, see objQuery() for details
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		# for each portal, add its links to links
		for portal in self.query(key=lambda x: isinstance(x,Portal),d=d):
			for dir in portal.getLinksForParent():
				links[(dir,portal)] = portal.links[dir]
		return links


	# rooms are the roots of the obj tree, they have no ancestor
	def ancestors(self):
		return []


	# typically called before trying to add an object to the Room
	# if this fails, object will not be added
	def canAdd(self,I):
		if self.ceiling and I in celestials:
			return False
		if I in self:
			return False
		if hasMethod(I,"Spill"):
			return self.vacancy() == -1 or I.Size() <= self.vacancy()
		return self.couldSpill(I.minimumSize())


	# return whether spilling contents could accommodate additional size
	def couldSpill(self,extraSize):
		if self.Capacity() == -1:
			return True
		return self.minimumSolidSize() + extraSize <= self.Capacity()


	def canImmerse(self,obj):
		return obj in self and self.couldImmerse(obj)


	def couldImmerse(self,obj,size=None,vacancy=None):
		return self.material().liquid


	def canSubmerge(self,creature):
		if creature not in self:
			return False
		if self.material().liquid:
			return True
		if self.floor and self.floor.material().liquid:
			return True
		return False


	# return the fluid an object cannot avoid in its current spatial arrangement
	def requiredImmersion(self,obj):
		# only direct contents participate in this Room's immersion calculation
		if obj.parent is not self:
			return None
		# a Room composed of liquid has no dry region within it
		if self.material().liquid:
			return self

		# carried creatures and riders are immersed if anchor is submerged
		anchor = obj.anchor()
		if isinstance(obj,Creature) and isinstance(anchor,Creature):
			fluid = anchor.immersed
			if fluid is None:
				return None
			if anchor.hasStatus("submerged") or not fluid.canEmerge(obj):
				return fluid
			return None

		# occupants of submerged platforms share the platform's fluid
		platform = obj.platform
		if platform is not None and platform.immersed is not None and \
		platform.hasStatus("submerged",reqSource="IMMERSED") and \
		platform.immersed.canImmerse(obj):
			return platform.immersed

		# waterwalking avoids contact unless there's no dry space to be in
		if obj.hasStatus("waterwalking"):
			forcedFluids = [fluid for fluid in self.spatialContents() \
				if fluid is not obj and hasMethod(fluid,"Spill") \
				and not fluid.canEmerge(obj)]
			if not forcedFluids:
				return None
			return max(forcedFluids,
				key=lambda fluid:(fluid.immersionSpace(),fluid.Size()))

		# a liquid floor immerses grounded objects but not flying ones
		if self.floor and self.floor.material().liquid and \
		not obj.hasStatus("flying"):
			return self.floor
		# an infinite-capacity Room always has enough dry space around its Plashes
		if self.Capacity() == -1:
			return None

		# finite Rooms require immersion when Plashes consume the dry space
		fluids = [fluid for fluid in self.spatialContents() \
			if fluid is not obj and hasMethod(fluid,"Spill")]
		eligible = [fluid for fluid in fluids if fluid.canImmerse(obj)]
		if not eligible:
			return None
		unimmersed = [other for other in self.spatialContents() \
			if other not in fluids and other is not obj and other.immersed is None]
		drySpace = self.Capacity() - sum(fluid.Size() for fluid in fluids) \
			- sum(other.Size() for other in unimmersed)
		if obj.Size() < drySpace:
			return None
		return max(eligible,
			key=lambda fluid:(fluid.immersionSpace(),fluid.Size()))


	# room contents is the fixtures, items, creatures, surfaces, and celestials
	def contents(self):
		cts = self.spatialContents()
		cts += [s for s in self.surfaces if s not in (None,self)]
		if not self.ceiling: cts += game.celestials
		return cts


	def spatialContents(self):
		return self.permanents + self.items + self.creatures


	def getNewLocation(self,dir=None):
		return self.links[dir]


	# given a direction (like 'north' or 'down)
	# return the Portal with that direction in this room
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir:
				portals.append(portal)
		return portals


	# if the given room object, dest, is in one of the Rooms links,
	# then find the direction it is in from the Room.
	# not that this will return None if dest is not linked to from this room
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


	# total size of all items in the Room (note this ignores celestials and surfaces)
	def itemsSize(self):
		return sum(obj.Size() for obj in self.spatialContents())


	# return the combined size that cannot be freed by spilling contents
	def minimumSolidSize(self):
		return sum(obj.minimumSize() for obj in self.spatialContents())


	# get items that are 'mentioned' and not anchored to some other platform
	def listableItems(self):
		condition = lambda x: x.mention and x.immersed is None and \
			x.platform in (None,self.floor)
		objects = list(filter(condition,self.items+self.permanents))
		return objects


	# useful for determining what room ultimately contains an object
	# exists in this class for compatibility with other objects
	def room(self):
		return self


	# for rooms, size is their capacity
	def Size(self):
		return self.capacity


	def Capacity(self):
		return self.capacity if self.capacity is not None else self.Size()


	# get amount of empty space in the Room
	def vacancy(self):
		return -1 if self.Capacity() == -1 else self.Capacity() - self.itemsSize()


	### User Output ###

	# prints room name, description, all its items and creatures
	def describe(self):
		Print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()		


	# prints all the items of the Room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			Print(listObjects("There is ",items,"."))
			game.setPronouns(items[-1])
		for item in self.items+self.permanents:
			if hasMethod(item,"describeImmersed"):
				item.describeImmersed()


	# prints all the creatures in the Room in sentence form
	def describeCreatures(self):
		# don't directly describe creatures which are anchored to player
		# or creatures riding another creature
		select = lambda creature: creature not in \
		(player, *player.carrying(), player.riding) and \
		creature.immersed is None and \
		creature.anchor() in (creature.parent.floor,None)

		listCreatures = [creature for creature in self.creatures if select(creature)]
		if len(listCreatures) != 0:
			Print(listObjects("There is ",listCreatures,"."))

		# carrying is separate narration for every creature in a listed tether group
		describeCarrying(self.listableItems()+listCreatures)

		# set pronouns for the last creature described
		for creature in listCreatures:
			game.setPronouns(creature)



# Items are the heart of the game. Everything in a room should be an Item
# All items come with a name, description, weight, durability, and composition
class Item(GameObject):
	# valid trigger keys for authored effects; equip/unequip may be
	# slot-qualified ("equip:head", "equip:grip")
	effectTriggers = {"obtain","drop","equip","unequip","carry","uncarry",
	"open","close","spawn","destroy"}

	def __init__(self,name,desc,weight,durability,composition,aliases=None,rarity=1,
	status=None,plural=None,descname=None,determiner=None,pronoun="it",occupyprep="on",
	fixed=False,mention=True,longevity=None,despawnTimer=None,scent=None,flavor=None,
	texture=None,platform=None,immersed=None,minGripsNeeded=1,latent=None,
	effects=None,id=None):

		### Basic Properties
	
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability
		# used to determine obj density and for crafting
		self.composition = composition

		### Additional Properties

		# rarities are:
		# -1. hazardous (red) 0. worthless (grey) 1. common (white) 2. uncommon (orange)
		# 3. rare (green) 4. sterling (blue) 5. legendary (magenta) 6. unique (yellow)
		self.rarity = rarity
		assert rarity >= -1 and rarity <= 6
		self.descname = descname if descname else name
		# whether or not it can be removed from its parent
		self.fixed = fixed
		# whether or not it is mentioned when describing its parent
		self.mention = mention
		# how long it lasts in despawnable conditions
		self.longevity = longevity
		self.despawnTimer = despawnTimer
		self.scent = scent
		self.flavor = flavor
		self.texture = texture
		self.minGripsNeeded = minGripsNeeded
		assert self.minGripsNeeded >= 1

		### Grammatical Properties

		self.plural = plural
		if self.plural is None:
			self.plural = self.name + 's'
		self.determiner = determiner
		self.pronoun = Data.objectives.get(pronoun,pronoun)
		self.occupyprep = occupyprep
		# used for identifying object from player input
		self.aliases = list(set(aliases)) if aliases else []

		### World Properties -- resolved during enmeshWorld()

		# used to uniquely identify this object instance
		self.id = id
		# the parent object containing this object (usually a Room or Container)
		self.parent = None

		### Status Entries

		self.status = [normalizeStatusEntry(entry) for entry in status] \
			if status else []
		# keep status entries in canonical order (see statusEntryKey)
		self.status.sort(key=statusEntryKey)
		# transient status-cascade state (never serialized)
		self.statusCascadeDepth = 0
		self.alreadyRemoved = set()

		### Tethers

		# these describe physical position relative to other objects
		self.platform = platform
		self.immersed = immersed

		### Suspension

		# the suspended object this substitute stands in for (see replace/restore)
		# a latent object stays registered but detached, serialized nested here
		self.latent = latent
		# the substitute standing in for this object while it is suspended
		# (derived from the substitute's latent reference, never serialized)
		self.substitute = None
		if latent is not None:
			latent.substitute = self

		### Authored Effects

		# optional dict of trigger name -> effect descriptors
		# departure keys: None derives inverses, () suppresses, authored replaces
		self.effects = effects
		if effects:
			import Effects
			self.effects = {trigger: Effects.wrapEffectDescriptors(descriptors)
				for trigger,descriptors in effects.items()}
			# an unknown trigger key is never fired, so it would be silently
			# dead content; construction is the only place to catch it
			for trigger in self.effects:
				base,_,slot = trigger.partition(":")
				assert base in self.effectTriggers, f"{self.name} effects has unknown trigger '{trigger}'"


	### Dunder Methods ###

	def __repr__(self):
		return f"{self.__class__.__name__}({self.name}, {self.weight}, {self.durability})"


	### File I/O ###

	# Validate registry identity, ownership, platform relationships, and anchor cycles.
	# These shared invariants apply to every Item subclass.
	def validate(self):
		if not isinstance(self.id,int) or game.itemRegistry.get(self.id) is not self:
			raise ValueError(f"Registry does not contain {self} at its ID {self.id}")
		# suspended objects are owned by their substitute, not a parent
		if self not in celestials and self.substitute is None:
			if self.parent is None or self not in game.ownedChildren(self.parent):
				raise ValueError(f"{self} is not owned by its parent {self.parent}")
		if self.platform is not None and not isinstance(self.platform,Item):
			raise ValueError(f"{self} has invalid platform {self.platform}")
		if self.platform is not None and \
			self.platform is not getattr(self.parent,"floor",None) and \
			self.platform.parent is not self.parent:
			raise ValueError(f"{self} and platform {self.platform} are not siblings")
		if self.immersed is not None and not self.immersed.canImmerse(self):
			raise ValueError(f"{self} has invalid immersion tether to {self.immersed}")

		anchors = set()
		anchor = self.anchor()
		while anchor is not None:
			if anchor in anchors or anchor is self:
				raise ValueError(f"Anchor cycle involving {self}")
			anchors.add(anchor)
			anchor = anchor.anchor()
		return super().validate()

	# convert these references back into integer IDs
	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		if self.platform is not None and \
		self.platform is getattr(self.parent,"floor",None):
			jsonDict["platform"] = "floor"
		elif self.platform is None:
			jsonDict["platform"] = None
		else:
			jsonDict["platform"] = self.platform.id
		if self.immersed in (self.parent,getattr(self.parent,"floor",None)):
			jsonDict["immersed"] = None
		# a held latent object serializes as a full nested spec (see Menu's
		# worldEncoder, which exempts this key from Item-to-ID conversion)
		if self.latent is None:
			del jsonDict["latent"]
		# the substitute reference is rederived from the nesting on load
		del jsonDict["substitute"]
		if not self.effects:
			del jsonDict["effects"]
		del jsonDict["statusCascadeDepth"], jsonDict["alreadyRemoved"]
		return jsonDict


	### Operation ###

	# establish immersion in a liquid parent, floor, or sibling
	def immerse(self,fluid,silent=False):
		if fluid is None or not fluid.material().liquid:
			return False
		if self.parent is None:
			return False
		if fluid.parent is not self.parent and \
		fluid is not self.parent:
			return False
		requiredFluid = self.parent.requiredImmersion(self)
		if requiredFluid is not None and fluid is not requiredFluid:
			return False
		if self.hasStatus("waterwalking") and requiredFluid is not fluid:
			return False
		if not fluid.canImmerse(self):
			return False

		# make self wet
		self.immersed = fluid
		if isinstance(self,Creature) and self.anchor() is None:
			self.changePosture("standing",silent=True)
		if not self.hasStatus("wet") or self.hasStatus("asleep"):
			self.waitInput("Splash!")
		if not self.hasStatus("wet",reqSource="IMMERSED") and \
		not self.hasStatus("wet",reqSource="SUBMERGED"):
			self.addStatus("wet",source="IMMERSED")

		# check for full submersion in liquid
		self.checkSubmersion(silent=silent)

		# update dependent immersion statuses
		for dependent in self.occupants():
			dependent.checkImmersion(silent=silent)
		if isinstance(self,Creature):
			for dependent in self.carrying():
				dependent.checkImmersion(silent=silent)
		return True


	# clear immersion and leave only temporary liquid wetness behind
	def unimmerse(self,silent=False):
		if self.immersed is None:
			return False
		fluid = self.immersed
		self.immersed = None
		self.checkSubmersion(silent=silent)
		self.transferStatus("wet","IMMERSED",None,21)
		for dependent in self.occupants():
			if dependent.immersed is fluid:
				dependent.unimmerse(silent=silent)
		if isinstance(self,Creature):
			for dependent in self.carrying():
				if dependent.immersed is fluid:
					dependent.unimmerse(silent=silent)
		return True


	# try to break the item, destroying it if successful
	def breaks(self):
		# if self.id not in game.itemRegistry:
		# 	return False
		assert self.id in game.itemRegistry, f"{self} ID{self.id} not in Item registry"
		if self.durability == -1:
			# if not silent:
			# 	Print(f"{+self} cannot be broken.")
			return False
		if self.material().shatterable:
			return self.shatter()
		self.printNearby(f"{+self} breaks.")
		self.destroy()
		return True


	# destroy the item, scattering shards of its composition
	def shatter(self):
		assert self.id in game.itemRegistry, f"{self} ID{self.id} not in Item registry"
		if not self.material().shatterable:
			return False
		if self.durability == -1:
			return False
		parent = self.parent
		self.printNearby(f"{+self} shatters.")
		if self.weight > 2:
			self.printNearby(f"Shards of {self.composition} scatter everywhere.",
			color="o")
		while self.weight > 1:
			shardWeight = randint(1,min(self.weight,4))
			self.weight -= shardWeight
			game.spawn(Shard(self.composition,shardWeight),parent)
		self.destroy()
		return True


	# change location while deferring status reports until the transition is complete
	def changeLocation(self,newparent,silent=False):
		with game.deferStatusReports():
			return self._changeLocation(newparent,silent=silent)


	# change location to a new Room/Container
	def _changeLocation(self,newparent,silent=False):
		if not newparent.canAdd(self):
			if newparent.vacancy() != -1 and self.Size() > newparent.vacancy():
				self.Print(f"There's not enough space for {-self}.")
			else:
				self.Print(f"Entering {-newparent} fails.")
			return False

		# Item cant be covered by another object when changing rooms
		self.clearCovering()
		# store this, it would be empty after changing rooms
		occupants = self.occupants()
		prevparent = self.parent
		if prevparent:
			prevparent.exit(self)
		if self is player.parent:
			Print(f"{+self} rumbles...")

		entered = newparent.enter(self)
		assert entered, f"{self} failed to enter {newparent}"

		# everything on top of this item is thrown with it, landing separately
		for occupant in occupants:
			if not occupant.changeLocation(newparent):
				if occupant.platform is self:
					occupant.removePlatform(drop=True)
				continue
			occupant.fall(self.Size()//5)

		if self.hasStatus("flying") or \
		self.immersed is not None and self.canSwim():
			self.platform = None
		else:
			self.platform = self.footing(newparent)
		return True


	# Items bearing too much weight will break
	def checkOccupantsWeight(self,silent=True):
		if self.occupantsWeight() > self.durability*2 and self.durability != -1:
			self.waitInput(f"{+self} collapses under the weight!",color="o")
			self.breaks()
		elif self.occupantsWeight() > self.durability and self.durability != -1:
			if not silent:
				# TODO: this should vary based on composition
				self.Print(f"{+self} creaks under the weight...")


	# reconcile environmental immersion, platform, and submersion state
	def checkImmersion(self,silent=False):
		if self.parent is None:
			return self.unimmerse(silent=silent)
		requiredFluid = self.parent.requiredImmersion(self)

		# fall into a liquid platform when waterwalking ends
		liquidPlatform = self.platform if self.platform is not None and \
			self.platform.material().liquid else None
		if liquidPlatform is not None and \
		(not self.hasStatus("waterwalking") or requiredFluid is liquidPlatform):
			if not silent:
				fluidName = "the water" if liquidPlatform is \
					getattr(self.parent,"floor",None) else -liquidPlatform
				self.Print(self+f"fall into {fluidName}.")
				self.printNearby(self+f"falls into {fluidName}.")
			self.removePlatform()
			if liquidPlatform.canImmerse(self):
				return self.immerse(liquidPlatform,silent=silent)

		# rise onto the liquid surface when waterwalking begins while immersed
		if self.immersed is not None and self.hasStatus("waterwalking") and \
		requiredFluid is None:
			fluid = self.immersed
			self.unimmerse(silent=silent)
			if fluid is not self.parent and hasMethod(fluid,"occupy") and \
			fluid.occupy(self,silent=True):
				return True
			self.platform = self.footing()
			return True

		# remove immersion if fluid can no longer immerse us for some reason
		if self.immersed is not None and not self.immersed.canImmerse(self):
			self.unimmerse(silent=silent)

		# emerge onto any surfaced non-floor anchor
		anchor = self.anchor()
		floor = getattr(self.parent,"floor",None)
		if isinstance(self,Creature) and anchor not in (None,floor) and \
		not anchor.hasStatus("submerged",reqSource="IMMERSED") and \
		requiredFluid is None:
			return self.unimmerse(silent=silent)

		# immerse in required fluid if not already immersed there
		if requiredFluid is not None and self.immersed is not requiredFluid:
			if self.immersed is not None:
				self.unimmerse(silent=silent)
			return self.immerse(requiredFluid,silent=silent)

		# check submersion status after handling immersion
		self.checkSubmersion(silent=silent)
		# recursively check immersion for all dependents
		for dependent in self.occupants():
			dependent.checkImmersion(silent=silent)
		if isinstance(self,Creature):
			for dependent in self.carrying():
				dependent.checkImmersion(silent=silent)


	# reconcile Item submersion with its liquid and support
	def checkSubmersion(self,silent=False):
		wasSubmerged = self.hasStatus("submerged",reqSource="IMMERSED")
		fluid = self.immersed
		if fluid is None or not fluid.canSubmerge(self):
			self.removeStatus("submerged",reqSource="IMMERSED")
		else:
			platform = self.platform
			# a liquid floor (Surface) has no floor of its own beneath it
			onFluidFloor = platform is not None and \
				platform is getattr(fluid,"floor",None)
			onSubmergedPlatform = platform is not None and \
				platform.immersed is fluid and \
				platform.hasStatus("submerged",reqSource="IMMERSED")
			if onFluidFloor or onSubmergedPlatform:
				if not wasSubmerged:
					self.addStatus("submerged",source="IMMERSED")
			else:
				self.removeStatus("submerged",reqSource="IMMERSED")

		isSubmerged = self.hasStatus("submerged",reqSource="IMMERSED")
		if wasSubmerged == isSubmerged:
			return False
		if isSubmerged and not silent:
			self.printNearby(self+"begins to sink!",color="o")
		occupants = self.occupants().copy()
		if isSubmerged:
			for occupant in occupants:
				self.disoccupy(occupant)
				if occupant.immersed is fluid:
					occupant.checkSubmersion(silent=silent)
				elif fluid.canImmerse(occupant):
					if occupant.immersed is not None:
						occupant.unimmerse(silent=silent)
					occupant.immerse(fluid,silent=silent)
				occupant.fall(self.Size()//5)
		else:
			for occupant in occupants:
				occupant.checkImmersion(silent=silent)
		return True


	# reconcile spatial relationships after this Item changes size
	def checkSize(self):
		if hasMethod(self.parent,"checkCapacity"):
			self.parent.checkCapacity()
		self.checkImmersion()
		platform = self.platform
		if platform is not None and platform is not getattr(self.parent,"floor",None):
			platform.checkOccupancy(self)
			if self.platform is platform:
				platform.checkOccupantsWeight(silent=True)
		self.checkOccupancy()
		for covered in self.covering():
			covered.checkCover()


	# return whether this Item has enough space for an additional occupant
	def canOccupy(self,occupant):
		otherSize = self.occupantsSize(exclude=occupant)
		tooSmall = self.Size() < occupant.Size()//5 and otherSize == 0
		tooCrowded = otherSize > 0 and \
			self.Size() < occupant.Size() + otherSize
		return not (tooSmall or tooCrowded)


	# if there's not enough space to occupy an Item, objects fall off, biggest first
	def checkOccupancy(self,obj=None,actor=None,silent=True):
		if obj is not None:
			occupants = [obj]
		else:
			occupants = self.occupants()

		anyFell = False
		for occupant in occupants:
			if not self.canOccupy(occupant):
				if not silent:
					assert isinstance(actor,Creature)
					actor.Print(self+f"is too small for {-occupant}.",color="o")
				self.disoccupy(occupant)
				occupant.fall(self.Size()//5)
				anyFell = True
		return not anyFell


	# sever every spatial tether and leave the world tree, staying registered
	# this is a shared end state of destruction and suspension
	def detach(self,silent=True):
		self.clearCovering()
		occupants = self.occupants()
		self.clearOccupants()
		for occupant in occupants:
			occupant.fall(self.Size()//5)
		self.removePlatform()
		# may have already been removed from parent
		if self.parent and self in self.parent:
			self.parent.remove(self)
		self.parent = None


	# removes this Item and all references to it from the game
	# returns True if destruction occurred, False if refused (Room permanents)
	def destroy(self,silent=True):
		if isinstance(self.parent,Room) and self in self.parent.permanents:
			return False
		# a substitute cannot be destroyed without restoring its latent
		if self.latent is not None:
			self.restore()
			return True
		# before detach, so effects can resolve the item's location
		self.evokeEffects("destroy",None)
		if not silent:
			self.Print(f"{+self} disappears.")

		# relocate contents into parent if it has one
		parent = self.parent
		if parent is not None:
			for item in getattr(self,"items",[]).copy():
				item.changeLocation(parent)
		# TODO: find a way to preserve important items here?
		# destroy contents if no parent exists
		# use a while loop because destroyed children can dump contents into our items
		else:
			items = getattr(self,"items",None)
			while items:
				items[-1].destroy(silent=silent)

		self.detach(silent=silent)
		self.releaseBoundStatuses()

		assert game.itemRegistry[self.id] is self, \
		f"{self} ID{self.id} holds wrong Item in registry {game.itemRegistry[self.id]}"
		del game.itemRegistry[self.id]
		return True


	# strip entries sourced to this object's id from every bearer
	def releaseBoundStatuses(self):
		for obj in list(game.itemRegistry.values()):
			if obj is not None and obj.status:
				obj.removeStatus(reqSource=self.id)
		for room in world.values():
			if room.status:
				room.removeStatus(reqSource=self.id)


	# counterpart of releaseBoundStatuses
	# re-grant the bound statuses for triggers after 'nullified' ends
	def resumeBoundStatuses(self):
		# determine which triggers have ongoing effects to resume
		triggers = []
		if isinstance(self.parent,Creature):
			owner = self.parent
			triggers.append(("obtain",owner))
			slots = [s for s,i in owner.gear.items() if i is self]
			if slots:
				triggers.append(("equip",owner))
				triggers.extend((f"equip:{s}",owner) for s in slots)
		if getattr(self,"carrier",None) is not None:
			triggers.append(("carry",self.carrier))

		# evoke only bound status from selected triggers
		import Effects
		for trigger,actor in triggers:
			descriptors = (self.effects or {}).get(trigger)
			if not descriptors or isinstance(descriptors,str):
				continue
			for descriptor in descriptors:
				if descriptor[0] == "bindStatus":
					Effects.evokeEffects((descriptor,),actor,self)


	# suppress this item's effect triggers: the nullified condition strips
	# outstanding bound statuses and resumes them when its last entry ends
	def nullify(self,source=None,duration=None):
		return self.addStatus("nullified",source,duration)


	# the creature this trigger's relationship currently holds with, or None
	def triggerActor(self,trigger):
		base,_,slot = trigger.partition(":")
		if base == "obtain" and isinstance(self.parent,Creature):
			return self.parent
		if base == "equip" and isinstance(self.parent,Creature):
			if slot and self.parent.gear.get(slot) is self:
				return self.parent
			if not slot and self in self.parent.gear.values():
				return self.parent
		if base == "carry":
			return getattr(self,"carrier",None)
		return None


	# append one effect descriptor under a trigger key, firing it
	# immediately if the trigger's relationship already holds
	def addEffect(self,trigger,descriptor):
		import Effects
		descriptor = Effects.wrapEffectDescriptors((descriptor,))[0]
		base,_,slot = trigger.partition(":")
		assert base in self.effectTriggers, \
			f"{self.name} addEffect got unknown trigger '{trigger}'"
		if self.effects is None:
			self.effects = {}
		existing = self.effects.get(trigger) or ()
		assert not isinstance(existing,str), \
			f"{self.name} effects['{trigger}'] is exec code; cannot append"

		# concatenate new effect to existing effects
		self.effects[trigger] = tuple(existing) + (descriptor,)

		actor = self.triggerActor(trigger)
		if actor is not None and not self.hasStatus("nullified"):
			Effects.evokeEffects((descriptor,),actor,self,actor)
		return True


	# remove all effect descriptors matching the criteria, firing their
	# derived inverses if their trigger's relationship still holds
	# "*" matches anything; reqArgs matches a descriptor's whole args tuple
	# a whole-key exec string only matches by trigger (reqName/reqArgs "*")
	def removeEffects(self,reqTrigger="*",reqName="*",reqArgs="*"):
		if not self.effects:
			return False
		import Effects

		matches = lambda d: reqName in (d[0],"*") and reqArgs in (d[1:],"*")
		removed = False
		for trigger,descriptors in list(self.effects.items()):
			if reqTrigger not in (trigger,"*"):
				continue

			# remove special exec-string effects if they match
			if isinstance(descriptors,str):
				if reqName == reqArgs == "*":
					del self.effects[trigger]
					removed = True
				continue

			# identify descriptors that match removal criteria
			matched = tuple(d for d in descriptors if matches(d))
			if not matched:
				continue

			# evoke each inverse effect matched before removing
			actor = self.triggerActor(trigger)
			if actor is not None and not self.hasStatus("nullified"):
				inverses = Data.deriveInverses(matched,self.id)
				Effects.evokeEffects(inverses,actor,self,actor)
			
			# make sure to keep descriptors that don't match
			remaining = tuple(d for d in descriptors if not matches(d))
			if remaining:
				self.effects[trigger] = remaining
			else:
				del self.effects[trigger]
			removed = True
		return removed


	# walk up the ancestor chain from start for a place this object could
	# go, without mutating anything; returns the destination or None
	def displaceDestination(self,start):
		destination = start
		while destination is not None:
			if hasMethod(destination,"canObtain"):
				if destination.canObtain(self,silent=True):
					return destination
			elif hasMethod(destination,"canAdd"):
				if destination.canAdd(self):
					return destination
			else:
				return None
			destination = getattr(destination,"parent",None)
		return None


	# if an Item is too small for its parent, move it up the ancestor chain to
	# the first place that fits; if nothing fits, destroy it. The destination
	# is planned before any mutation so a doomed object dies in place, where
	# its parent still resolves (contents and a latent need a location)
	def displace(self,newparent=None):
		self.clearOccupants()

		# no destination exists anywhere: destroy in place
		destination = self.displaceDestination(newparent)
		if destination is None:
			self.destroy()
			return False

		# mutate: the move operations evict self from its old parent themselves
		if hasMethod(destination,"canObtain"):
			return destination.ObtainItem(self)
		if isinstance(self.parent,Creature):
			removed = self.parent.remove(self,silent=True)
			assert removed, f"Failed to remove {self} from {self.parent}"
		return self.changeLocation(destination)


	# fire this item's effect descriptors for one trigger
	# binding triggers stop granting if their relationship ends mid-batch-
	# because an effect may undo the trigger condition itself
	def evokeEffects(self,trigger,actor,target=None):
		# a nullified item's effects don't fire
		if self.hasStatus("nullified"):
			return False
		# fetch the triggered effect descriptors
		effects = self.effects or {}
		descriptors = effects.get(trigger)

		# for removal triggers, if no effects are written,
		# infer them from its opposite trigger
		base,_,slot = trigger.partition(":")
		additiveTrigger = {"drop":"obtain","unequip":"equip","uncarry":"carry",
			"close":"open"}.get(base)
		if descriptors is None and additiveTrigger is not None:
			additiveKey = f"{additiveTrigger}:{slot}" if slot else additiveTrigger
			descriptors = Data.deriveInverses(effects.get(additiveKey),self.id)

		if not descriptors:
			return False
		if target is None:
			target = actor
		import Effects

		# defer target's status checks until the whole batch has applied
		with target.deferStatusChecks() if target else nullcontext():
			# when the effect is a str, exec it directly
			if isinstance(descriptors,str):
				return Effects.evokeEffects(descriptors,actor,self,target)

			stillHolds = {
				"obtain": lambda: self.parent is actor,
				# a slot-qualified trigger holds only while the item is in that slot
				"equip": (lambda: actor.gear.get(slot) is self) if slot
					else (lambda: self in actor.gear.values()),
				"carry": lambda: getattr(self,"carrier",None) is actor,
			}.get(base,lambda: True)

			# evoke all conditions as long as trigger holds true
			for descriptor in descriptors:
				if stillHolds():
					Effects.evokeEffects((descriptor,),actor,self,target)
		return True


	# prevent despawning
	def nullDespawn(self):
		self.despawnTimer = None


	# possibly despawn Item, if it is unanchored make it fall, ensure occupants fit
	def passTime(self,t):
		super().passTime(t)

		if self.despawnTimer is not None:
			self.despawnTimer -= t
			if self.canDespawn():
				return self.destroy()

		self.checkOccupancy()
		self.checkOccupantsWeight(silent=True)

		if not isinstance(self.parent,Creature) and not self.fixed and \
		not self.hasStatus("flying"):
			if self.anchor() is None:
					self.fall()
		# happens after fall, this allows for a 1 timestep delay for creature sinking
		self.checkImmersion()


	# change an existing status entry's source and/or duration in place
	# nothing is added or removed, so no hooks, gates, or reports trigger
	# newDur "*" keeps the old duration; None sets indefinite
	def transferStatus(self,name,source,newSource,newDur="*"):
		entry = self.getStatusEntry(name,source)
		if entry is None:
			return False
		# if an entry with the new source already exists, merge into it
		# (unstackable conditions have frozen durations, so no refresh)
		existing = self.getStatusEntry(name,newSource)
		if existing is not None and existing is not entry:
			canStack = Data.StatusCondition.get(name).stackable
			self.refreshStatus(existing,entry[2] if newDur == "*" else newDur,
				canStack)
			self.status.remove(entry)
			return True
		entry[1] = newSource
		if newDur != "*":
			entry[2] = newDur
		self.status.sort(key=statusEntryKey)
		return True


	# snapshot the tethers a replacement must hand over, before any mutation
	def replacementSnapshot(self):
		return {"parent": self.parent, "covered": self.covering().copy(),
			"occupants": self.occupants()}


	# hand over type-specific tethers to newObj mid-replacement
	def transferReplacementTethers(self,newObj,snap):
		for covered in snap["covered"]:
			covered.removeCover(silent=True)
			covered.addCover(newObj)
		for occupant in snap["occupants"]:
			self.disoccupy(occupant)
			if isinstance(newObj,Creature) or newObj.parent is None:
				occupant.fall(self.Size()//5)
			else:
				newObj.occupy(occupant,silent=True)
			# newObj may be destroyed when receiving an occupant
			if newObj.parent is None:
				return
		if self.platform not in (None,self.parent) and newObj.parent:
			p = self.platform
			self.removePlatform()
			if not getattr(p,"closed",True) and hasMethod(p,"canAdd") and p.canAdd(newObj):
				newObj.changeLocation(p)
			else:
				p.occupy(newObj)


	# recalculate the tethers after a completed replacement
	def replacementChecks(self,newObj,snap):
		for covered in snap["covered"]:
			covered.checkCover()
		if isinstance(newObj,Creature):
			newObj.checkTethers()
		if newObj.parent is not None:
			newObj.checkSize()


	# substitute newObj into this object's parent and all its tethers
	# destroy=True (succession): self is destroyed and newObj inherits its ID
	# destroy=False (suspension): self persists latently, owned by newObj
	# when old obj gets replaced through suspension, it become a 'latent' object-
	# occupying no room, and only existing as newObj.latent
	# transferId=False: both objects keep their own IDs (used for restoring a latent obj)
	# returns the replacement if it exists in the world afterward, else None
	def replace(self,newObj,destroy=True,transferId=True):
		if newObj is self:
			return self
		if isinstance(self.parent,Room) and self in self.parent.permanents:
			return False
		if isinstance(newObj,str) or newObj.id is None:
			newObj = game.spawn(newObj)
		# record tethers prior to replacement
		snap = self.replacementSnapshot()

		# insert newObj into self's place and transfer tethers
		# newObj may be destroyed during tether transfer
		parent = self.parent
		placed = parent.replaceObj(self,newObj)
		# if newObj cannot exist anywhere, replacement fails
		if not placed and newObj.displaceDestination(parent) is None:
			newObj.destroy()
			return None
		if placed:
			self.transferReplacementTethers(newObj,snap)
		replacementStillExists = game.itemRegistry.get(newObj.id) is newObj

		# replacement via succession: 
		# destroy self and potentially transfer latent and id to newObj
		if destroy:
			latent = self.latent
			# if self is itself already a substitute, hand over its latent to newObj.
			if latent is not None and replacementStillExists:
				# if substitute already has a latent, it cannot accept another one
				assert newObj.latent is None, \
					f"{newObj} already holds latent {newObj.latent}"
				newObj.latent = latent
				latent.substitute = newObj
				# if self.latent is not None-
				# then destroy() will end up restoring the latent
				self.latent = None

			# replaceObj nulled self.parent; destroy needs it to relocate contents
			if self.parent is None:
				self.parent = parent
			self.destroy()

			if transferId and replacementStillExists:
				game.replaceID(self,newObj)

		# replacement via suspension: 
		# detach and store self into newObj.latent
		else:
			self.detach()
			if replacementStillExists:
				# if substitute already has a latent, it cannot accept another one
				assert newObj.latent is None, \
					f"{newObj} already holds latent {newObj.latent}"
				newObj.latent = self
				self.substitute = newObj
			else:
				# if newObj no longer exists, replacement failed
				# self should not remain suspended so it returns to the world
				self.displace(parent)

		# a newObj that was refused placement still needs a home somewhere
		if not placed:
			newObj.displace(parent)
		# ensure integrity after replacement
		self.replacementChecks(newObj,snap)
		# return newObj if it wasnt destroyed during replacement process
		return newObj if game.itemRegistry.get(newObj.id) is newObj else None


	# return a suspended object to the world in this substitute's place:
	# the reverse of replace(destroy=False); the latent reclaims the
	# substitute's current tethers, and neither object's ID changes
	# returns the restored object, or None if it did not survive restoration
	def restore(self):
		original = self.latent
		if original is None:
			return None

		# clear the link first so destroying this substitute doesn't recurse
		self.latent = None
		original.substitute = None

		# if substitute is being destroyed-
		# try to put original back into the substitute's last location
		if self.parent is None or self not in self.parent:
			lastParent = self.parent
			if game.itemRegistry.get(self.id) is self:
				self.destroy()
			original.displace(lastParent)
		else:
			self.replace(original,transferId=False)

		# return restored object if it was not destroyed during restoration
		return original if game.itemRegistry.get(original.id) is original else None


	# degrade Item durability if damage is high enough, break if durability goes to 0
	def takeDamage(self,dmg,type,silent=True):
		assert dmg >= 0, "Damage must be non-negative"
		# TODO: add damage type vulnerabilities based on composition
		# i.e. wood is extra weak to fire and slashing
		if self.material().liquid:
			self.printNearby("Splish splash...")
			return True
		if dmg > 0 or not silent:
			typeDisplay = "" if type == "e" else Data.dmgtypes[type] + " "
			self.printNearby(f"{+self} took {dmg} {typeDisplay}damage.")
		if self.durability != -1:
			dmg = min0(dmg-self.durability)
			self.durability -= dmg
			if self.durability <= 0:
				return self.breaks()


	# set the despawn timer in despawnable conditions
	def timeDespawn(self):
		self.despawnTimer = self.longevity


	# remove occupants and cover and change location
	def teleport(self,newParent):
		if newParent is self.parent:
			return False
		self.clearCovering()
		self.clearOccupants()
		if newParent.canAdd(self):
			self.Print(f"{+self} disappears!",color="w")
			self.changeLocation(newParent)


	### Interaction ###

	# Try to cover an Item, ensure theres enough space to cover it
	def addCovering(self,covered):
		assert isinstance(covered,Creature)
		assert covered.parent is self.parent
		covering = self.covering()
		if covered in covering:
			Print(f"{+self} is already covering {-covered}.")
			return False
		if self.availableCover(covered) <= 0:
			nCovered = len(covering)
			msg = f"{+self} has no space to cover {-covered}. "
			if nCovered == 0:
				addendum = self*"is too small."
			elif nCovered == 1:
				addendum = self*f"is already covering {~covering[0]}."
			elif nCovered == 2:
				addendum = self*f"is already covering {~covering[0]} " \
				f"and {~covering[1]}."
			else:
				addendum = self*f"is covering {nCovered} others."
			Print(msg+addendum)
			return False

		covered.cover = self
		# try to cover any carried creatures too
		for carried in covered.carrying():
			carried.addCover(self)
		return True


	# try to hit with projectile, have chance to miss
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		hitProb = bound(missile.aim+self.Size()+10,1,99)
		if percentChance(hitProb):
			return missile.collide(self)
		return False

	# ordinary Items cannot submerge other objects
	def canSubmerge(self,item):
		return False


	# Called when Item can no longer serve as cover for others in room
	def clearCovering(self):
		for covered in self.covering():
			self.removeCovering(covered)
		return True


	# Called generally when occupying Items drop off of self
	def clearOccupants(self):
		for occupant in self.occupants():
			self.disoccupy(occupant)
			if not isinstance(self.parent,Creature):
				occupant.platform = occupant.footing(self.parent)


	# Called by specific occupant when changing its anchor
	def disoccupy(self,occupant):
		if getattr(occupant,"platform",None) is self:
			occupant.platform = None
		elif getattr(occupant,"riding",None) is self:
			occupant.riding = None
		else:
			return False
		# departing the anchor unbinds the comfort it maintained
		occupant.removeStatus("cozy",reqSource=self.id)
		return True


	# Item falls through rooms accumulating fall height until hitting floor, 
	# then take damage and set platform to room's floor
	def fall(self,height=0,room=None):
		if isinstance(self.parent,Creature):
			return False
		self.checkImmersion()
		sinking = self.immersed is not None and not self.canSwim() and \
			self.anchor() is None
		verb = "sink" if sinking else "fall"
		if self.immersed is not None and not sinking:
			return False

		# contents could be removed if item breaks, so save this first
		contents = self.contents().copy()
		if room is None:
			room = self.room()
		self.printNearby(f"{+self} {verb}s down.")
		for occupant in self.occupants():
			occupant.fall(height,room)
		self.clearOccupants()

		immersionSource = self.immersed
		if verb == "sink" and hasMethod(immersionSource,"transferImmersed"):
			destinationFluid = immersionSource
			destinationParent = self.parent
			while hasMethod(destinationFluid,"transferImmersed") and \
			"down" in destinationFluid.links:
				height += destinationFluid.Capacity() // 5
				destinationParent = destinationFluid.getNewLocation("down")
				destinationFluid = destinationFluid.links["down"]
			if destinationFluid is not immersionSource and \
			immersionSource.transferImmersed(self,destinationParent,destinationFluid):
				self.printNearby(f"{~self} sinks from above!".capitalize())
			floor = self.footing()
			if self.anchor() is not floor:
				self.platform = floor
			self.checkSubmersion(silent=True)
			return True

		while "down" in room.links and (room.floor is None or \
		(room.floor.material().liquid and verb == "sink")):
			height += room.Capacity() // 5 # approximate vertical height of room
			room = room.links["down"]
		if room != self.room():
			self.changeLocation(room)
			self.printNearby(f"{~self} {verb}s from above!".capitalize())

		floor = self.footing()
		if self.anchor() is not floor:
			# self.parent.floor.occupy(self)
			self.platform = floor
		self.checkSubmersion(silent=True)

		# TODO: add some collision checking for composition of the floor?
		if room.floor is not None and not sinking:
			force = min(height,20*self.weight)
			self.takeDamage(force,"b")
			for item in contents:
				item.takeDamage(force//3,"b")
		return True


	# verify mounting can preserve immersion or emerge before changing tethers
	def permitsMountImmersion(self,occupant,actor,silent=False):
		fluid = occupant.immersed
		if fluid is None:
			return True
		targetSubmerged = self.immersed is not None and \
			self.hasStatus("submerged",reqSource="IMMERSED")
		if targetSubmerged:
			if self.immersed is fluid:
				return True
			if not silent:
				actor.Print(f"You can't move directly from {-fluid} onto {-self}.")
			return False
		if fluid.canEmerge(occupant):
			return True
		if not silent:
			actor.Print(f"There isn't enough room to emerge from {-fluid}.")
		return False


	# Try to assign self as occupant's platform
	def occupy(self,occupant,silent=False,actor=None,posture=None):
		assert isinstance(occupant,Item)
		assert not isinstance(self.parent,Creature)
		assert self.parent is not None and occupant.parent is self.parent
		if self.material().liquid and \
		not occupant.hasStatus("waterwalking"):
			return False
		if actor is None:
			actor = occupant if isinstance(occupant,Creature) else player
		assert isinstance(actor,Creature)
		if occupant in self.occupants():
			if not silent:
				actor.Print(occupant+f"is already on {-self}.")
			return False
		action = f"get on {-self}" if actor is occupant else \
			f"put {-occupant} on {-self}"
		if self.checkTetherLoop(occupant,actor,action,silent=silent):
			return False
		if isinstance(occupant,Creature) and \
		not self.permitsMountImmersion(occupant,actor,silent=silent):
			return False
		if isinstance(occupant,Creature) and occupant.riding is not None:
			occupant.removeRiding()
		occupant.removePlatform()

		if not self.checkOccupancy(occupant,actor=actor,silent=silent):
			return False
		occupant.platform = self
		self.checkOccupantsWeight(silent=silent)
		occupant.checkImmersion(silent=silent)

		return occupant.platform is self


	# remove tethers when being obtained by a Creature
	# obtainer given because may be used in child class overrides
	def obtain(self,obtainer):
		if self.platform:
			self.platform.disoccupy(self)
		self.clearOccupants()
		self.clearCovering()
		self.platform = None
		self.evokeEffects("obtain",obtainer)


	# counterpart of obtain, called when leaving a Creature's possession
	def drop(self,dropper):
		self.evokeEffects("drop",dropper)


	# counterpart pair, called when entering/leaving a wearer's gear slots
	def equip(self,wearer,slots=()):
		self.evokeEffects("equip",wearer)
		for slot in slots:
			self.evokeEffects(f"equip:{slot}",wearer)


	def unequip(self,wearer,slots=()):
		self.evokeEffects("unequip",wearer)
		for slot in slots:
			self.evokeEffects(f"unequip:{slot}",wearer)


	# stop covering object if it is covered by self
	def removeCovering(self,covered):
		if covered.cover is self:
			covered.cover = None
			covered.checkHidden()
			return True
		return False


	# remove platform tether, optionally falling from its height
	def removePlatform(self,drop=False):
		platform = self.platform
		if platform is None:
			return False
		removed = platform.disoccupy(self)
		if removed and drop and self.parent is not None and \
		platform is not getattr(self.parent,"floor",None):
			self.fall(platform.Size()//5)
		return removed


	# describe smell based on instance senses and composition
	def smell(self,smeller):
		if smeller.hasStatus("apathy"):
			msg = f"You have the curse of apathy; {self+'smells like nothing...'}"
		else:
			msg = self.Scent()
		smeller.Print(msg)
		return True


	# describe taste based on instance senses and composition
	def taste(self,taster):
		if taster.hasStatus("apathy"):
			msg = "You have the curse of apathy; it tastes like nothing..."
		else:
			msg = self.Flavor()
		taster.Print(msg)
		return True


	# try to use item (does nothing atm)
	def use(self,user):
		if user not in self.ancestors():
			user.Print(f"{+self} is not in your Inventory.",color="k")
			return False
		Print(f"You use {-self}")
		return True


	### Getters ###

	# get recursive chain of Item's parents, up to Room (which should have no parent)
	def ancestors(self):
		ancs = []
		ancestor = self
		while not isinstance(ancestor,Room) and ancestor is not None:
			ancestor = ancestor.parent
			ancs.append(ancestor)
		return ancs


	# for Items, anchor is always a platform (or None)
	# this differs for creatures
	def anchor(self):
		return self.platform


	# return whether assigning self as dependent's anchor would create a tether loop
	# for instance, player is riding a horse who is standing on a table, and player tries to carry the table
	def checkTetherLoop(self,dependent,actor,action,silent=False):
		assert isinstance(dependent,Item)
		assert isinstance(actor,Creature)
		current = self
		traversed = set()
		while current is not None and current not in traversed:
			if current is dependent:
				if not silent:
					if self is dependent:
						actor.Print(actor+f"can't {action}.")
					else:
						actor.Print(actor+f"can't {action}; {self.anchorDescription()}.")
				return True
			traversed.add(current)
			current = current.anchor()
		if current in traversed:
			if not silent:
				actor.Print(actor+f"can't {action}; {self.anchorDescription()}.")
			return True
		return False


	# return the chain of physical anchors below this object
	def anchors(self):
		anchors = []
		anchor = self.anchor()
		while anchor is not None and anchor not in anchors:
			anchors.append(anchor)
			anchor = anchor.anchor()
		return anchors


	# return the liquid containing or ultimately supporting this Item
	def immersionContext(self):
		if self.immersed is not None:
			return self.immersed
		for anchor in self.anchors():
			if anchor.material().liquid:
				return anchor
			if anchor.immersed is not None:
				return anchor.immersed
		return None


	# describe this Item's direct anchor relationship
	def anchorDescription(self):
		anchor = self.anchor()
		assert anchor is not None
		if getattr(self,"carrier",None) is anchor:
			return self/f"is being carried by {-anchor}"
		if getattr(self,"riding",None) is anchor:
			return self/f"is riding {-anchor}"
		assert self.platform is anchor
		return self/f"is on {-anchor}"


	# returns this object wrapped as a projectile (gives it a speed and other properties)
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,
		self.composition,min1(self.weight//4),0,"b",item=self)


	# Used to create a generic Weapon() if this item is used to attack something
	def asWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,self.composition,
		min1(self.weight//4),0,0,0,"b")


	# determine cover available for obj from this Item
	def availableCover(self,obj):
		return self.Size() - obj.Size() - \
		sum(c.Size() for c in self.covering() if c is not obj)


	# normal Items can't contain other objects
	def canAdd(self,obj):
		return False


	# Items can despawn when the despawnTimer hits 0 and theyre in a room and not fixed
	def canDespawn(self):
		return self.despawnTimer is not None and \
			self.despawnTimer <= 0 and \
			isinstance(self.parent,Room) and \
			self.parent is not game.currentroom and \
			not self.fixed


	# checks if Item can float in a fluid based on density
	def canSwim(self,fluid=None):
		if fluid is None:
			fluid = self.immersed
		fluidComposition = fluid if isinstance(fluid,str) else \
			getattr(fluid,"composition",None)
		liquidDensity = Data.Material.get(fluidComposition).density

		return self.density() <= liquidDensity


	# return the parent's floor only when it can physically support this Item
	def footing(self,parent=None):
		if parent is None:
			parent = self.parent
		floor = getattr(parent,"floor",None)
		if floor is not None and floor.material().liquid and \
		not self.hasStatus("waterwalking"):
			return None
		return floor


	# count objects with same name in parent
	# useful for knowing when to use 'a' or 'the' to describe an object
	def count(self,parent=None,key=None):
		if parent is None:
			parent = self.parent
		if key is None:
			key = lambda x: x.name == self.name
		return sum(1 for obj in parent if key(obj))


	# return sibling Creatures covered by this Item
	def covering(self):
		if self.parent is None:
			return []
		objects = self.parent.spatialContents()
		return [obj for obj in objects if getattr(obj,"cover",None) is self]


	# return sibling objects anchored to this Item, excluding virtual room floors
	def occupants(self):
		if self.parent is None or self is getattr(self.parent,"floor",None):
			return []
		objects = self.parent.spatialContents()
		occupants = [obj for obj in objects if getattr(obj,"platform",None) is self or \
			getattr(obj,"riding",None) is self]
		return sorted(occupants,key=lambda occupant:occupant.Size(),reverse=True)


	# used so we don't bog down the player asking for which item they want
	# when two items are negligibly different
	def objMatch(self,other):
		if type(self) == type(other) and \
			self.name == other.name and \
			self.weight == other.weight and \
			self.durability == other.durability and \
			self.composition == other.composition and \
			self.rarity == other.rarity and \
			self.descname == other.descname and \
			self.status == other.status and \
			self.aliases == other.aliases and \
			self.parent == other.parent:
			return True
		return False


	# get total size of all occupants, excluding 'exclude' if given
	def occupantsSize(self,exclude=None):
		return sum(o.Size() for o in self.occupants() if o is not exclude)


	# get total weight of all occupants, excluding 'exclude' if given
	def occupantsWeight(self,exclude=None):
		return sum(o.Weight() for o in self.occupants() if o is not exclude)


	# get the Room that ultimately contains this Item at the root of its object tree
	def room(self):
		room = self.ancestors()[-1]
		assert isinstance(room,Room), f"{self}'s first ancestor {room} is not a Room"
		return room


	# the local environment: the nearest enclosing closed container or
	# Creature (inventories don't share air with their surroundings), or the Room
	def enclosure(self):
		obj = self.parent
		while not isinstance(obj,Room) and obj is not None:
			if getattr(obj,"closed",False) or isinstance(obj,Creature):
				return obj
			obj = obj.parent
		return obj


	# fire this object's expose material triggers, and its contents' if it
	# is an open container
	def expose(self,actor,area=None):
		if area is None:
			area = self.enclosure()
		descriptors = self.material().expose
		if descriptors:
			import Effects
			Effects.evokeEffects(descriptors,actor,self,area)
		if not getattr(self,"closed",False):
			for obj in list(getattr(self,"items",())):
				obj.expose(actor,area)


	def density(self):
		return self.material().density


	# resolve taste: a per-instance flavor wins, then one derived from a
	# per-instance scent, then the material's taste
	def Flavor(self):
		if self.flavor is not None:
			return self.flavor
		if self.scent is not None:
			return Data.smellToTaste(self.scent)
		return self.material().taste


	# resolve scent: a per-instance scent wins, then one derived from a
	# per-instance flavor, then the material's scent
	def Scent(self):
		if self.scent is not None:
			return self.scent
		if self.flavor is not None:
			return Data.tasteToSmell(self.flavor)
		return self.material().scent


	# resolve texture: a per-instance texture wins, then the material's
	def Texture(self):
		return self.texture if self.texture is not None else self.material().texture


	# return the greatest weight that does not exceed the given size
	# useful for examining hypothetical size changes
	def maxWeightAtSize(self,size):
		assert size >= 1
		return (size + 1) * self.density() - 1


	# get object size from weight, accounting for density based on composition
	def Size(self):
		# under normal conditions, size is equal to weight
		# account for density based on composition
		return min1(self.weight // self.density())


	# get total size of Item and everything upon it
	def totalSize(self):
		return self.Size() + self.occupantsSize()


	# get grips needed to wield based on structural minimum, weight, and wielder strength
	def gripsNeeded(self,wielder):
		return max(self.minGripsNeeded, self.Weight()//(4*wielder.STR()))


	# get the total weight of Item and everything upon it
	def Weight(self):
		return self.weight + self.occupantsWeight()


	### User Output ###

	# print Item description, including occupants if any
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		occupants = self.occupants()
		if len(bagObjects(occupants)) > 2:
			Print(listObjects("On it is ",occupants,"."))


	# the name of the item colored by rarity for display in inventory
	def displayName(self,count=1):
		color = Data.rarityColors.get(self.rarity,"w")
		if player.hasStatus("apathy"): color = "w"
		displayName = self.name
		if count > 1: displayName = self.plural + f" ({count})"
		return tinge(color,displayName)[0]


	# intelligently get name of this item in various grammatical forms
	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		if det.lower() == "the":
			strname = self.name
		else:
			occupants = self.occupants()
			if len(bagObjects(occupants)) > 2:
				strname = f"{self.name} with things on it"
			elif occupants:
				strname = listObjects(f"{self.name} with ",occupants," on it")
			else:
				strname = self.descname

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		# if self.determiner is not None and det == "":
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "your" if self.definiteDeterminer() == "your" else "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# print message to self
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
	outfile=None):
		# in godmode we can see all prints
		if game.mode == 2:
			args = (f"[{self.id} {self.name}]:",) + args
			color="k"
			return Print(*args,end=end,sep=sep,delay=delay,color=color,
			allowSilent=allowSilent,outfile=outfile)
		else:
			return False


	# print message to player only if player is in its surroundings
	# non-public messages render only in godmode
	def printNearby(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
	outfile=None,public=True):
		# in godmode we can see all prints
		if game.mode == 2:
			args = (f"[{self.id} {self.name}]:",) + args
			color="k"
		elif not public:
			return
		if (player.surroundings() is self.surroundings() or game.mode == 2) and \
		self is not player:
			return Print(*args,end=end,sep=sep,delay=delay,color=color,
			allowSilent=allowSilent,outfile=outfile)
		return


	# get reflexive pronoun for this Item
	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"


	# get subjective form of stored objective pronoun
	def subjective(self):
		return Data.subjectives.get(self.pronoun,"it")


	# just like self.Print except waits for user input afterwards
	def waitInput(self,text=None,**kwargs):
		# in godmode we can see all prints
		if game.mode == 2:
			text = f"[{self.id} {self.name}]:" + text if text else ""
			color="k"
			return waitInput(text=text,**kwargs)
		return False



# The Creature class is the main class for anything in the game that can act
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
# For their contents, Creatures have an Inventory and a gear dict of equipped items
# In addition to platform anchor, Creatures can be carried or riding another Creature
class Creature(Item):
	def __init__(self,name,desc,weight,traits,hp=None,mp=0,money=0,inv=None,gear=None,
	love=0,fear=0,carrier=None,riding=None,platform=None,
	cover=None,composition="flesh",memories=None,appraisal=None,lastAte=0,lastSlept=0,
	lastBreathed=0,regenTimer=0,alert=False,lastSawPlayer=None,
	carrySlots=None,gripSlots=None,**kwargs):
		# Creatures have infinite durability, may not be fixed, and despawn after 1000
		super().__init__(name,desc,weight,-1,composition,fixed=False,longevity=1000,
		**kwargs)

		### Main Statistics

		# physical traits are strength, speed, skill, stamina, and constitution
		# mental traits are charisma, intelligence, wisdom, faith, and luck
		# traits should normally be between 1 and 20
		if type(traits) is int:
			traits = [traits]*10
		assert len(traits) == 10, "Creature traits must be a list of 10 integers"
		self.str = traits[0]
		self.spd = traits[1]
		self.skl = traits[2]
		self.stm = traits[3]
		self.con = traits[4]
		self.cha = traits[5]
		self.int = traits[6]
		self.wis = traits[7]
		self.fth = traits[8]
		self.lck = traits[9]
		self.hp = hp if hp else self.MXHP() 
		self.mp = mp if mp else self.MXMP()
		self.money = money

		### Contents

		self.inv = inv if inv else []
		# values of gear must either be EmptyGear() or an Item in the inventory
		self.gear = gear if gear else Data.initgear
		self.gear = {k:(v if v else EmptyGear()) for k,v in self.gear.items()}
		defaultCarrySlots = ("left","right")
		self.carrySlots = tuple(slot for slot in defaultCarrySlots if slot in self.gear) \
			if carrySlots is None else tuple(carrySlots)
		assert len(self.carrySlots) == len(set(self.carrySlots)), \
			f"Creature {self.name} has duplicate carry slots"
		assert all(slot in self.gear for slot in self.carrySlots), \
			f"Creature {self.name} has carry slot absent from gear"
		self.gripSlots = self.carrySlots if gripSlots is None else tuple(gripSlots)
		assert len(self.gripSlots) == len(set(self.gripSlots)), \
			f"Creature {self.name} has duplicate grip slots"
		assert all(slot in self.gear for slot in self.gripSlots), \
			f"Creature {self.name} has grip slot absent from gear"
		# when equipping gear in gear dict, these may be assigned
		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		### Behavior

		self.memories = memories if memories else set()
		self.appraisal = appraisal if appraisal else set()
		# love and fear are the creature's attraction and aversion to the player
		self.love = love
		self.fear = fear

		### Tethers

		# these represent relationships to other Items in the Creature's parent
		# during __init__(), these are given as object IDs or None
		# but are replaced with real object references in enmeshWorld()
		self.riding = riding
		self.carrier = carrier
		self.platform = platform
		self.cover = cover

		### Timers

		# health regens very slowly
		self.regenTimer = regenTimer
		# eventually creatures get hungry and sleepy
		self.lastAte = lastAte
		self.lastSlept = lastSlept
		self.lastBreathed = lastBreathed
		# these attributes remain unused in the Player subclass
		self.alert = alert
		self.lastSawPlayer = lastSawPlayer
		# transient status-check state (never serialized)
		self.statusCheckDepth = 0
		self.statusCheckPending = False


	### Dunder Methods ###

	def __repr__(self):
		traits = [self.str, self.spd, self.skl, self.stm, self.con,
		self.cha, self.int, self.wis, self.fth, self.lck]
		return f"{self.__class__.__name__}({self.name}, {traits}, " \
		f"{self.hp}, {self.mp}, {self.money})"


	def __getitem__(self, key):
		return self.gear[key]


	def __setitem__(self, key, value):
		assert key in self.gear, f"Creature {self.name} has no gear slot '{key}'"
		self.gear[key] = value


	### File I/O ###

	# Validate anchor exclusivity, sibling tethers, carrying slots, and equipped gear.
	# Also enforce the creature's inventory and carried-cargo capacity limits.
	def validate(self):
		anchors = (self.platform,self.carrier,self.riding)
		if sum(anchor is not None for anchor in anchors) > 1:
			raise ValueError(f"Creature {self} has multiple physical anchors")
		for tetherName,expectedType in (("carrier",Creature),
		("riding",Creature),("cover",Item)):
			target = getattr(self,tetherName)
			if target is not None and not isinstance(target,expectedType):
				raise ValueError(f"Creature {self} has invalid {tetherName} {target}")
			if target is not None and (target is self or target.parent is not self.parent):
				raise ValueError(f"Creature {self} and {tetherName} {target} are not siblings")

		if self.carrier is not None:
			slots = [slot for slot in self.carrier.carrySlots \
				if self.carrier[slot] is self]
			if not slots:
				raise ValueError(f"Carried creature {self} occupies no slots on " \
					f"{self.carrier}")
			if len(slots) < self.gripsNeeded(self.carrier):
				raise ValueError(f"Carried creature {self} has too few occupied slots")
			if not self.hasStatus("restrained",reqSource=self.carrier.id):
				raise ValueError(f"Carried creature {self} lacks carrying restraint")

		for slot,item in self.gear.items():
			if item is not EmptyGear() and not isinstance(item,Item):
				raise ValueError(f"Creature {self} has unresolved gear in slot '{slot}'")
			if item is EmptyGear():
				continue
			if isinstance(item,Creature):
				if slot not in self.carrySlots or item.carrier is not self:
					raise ValueError(f"Creature {item} is invalid cargo in " \
						f"{self}'s slot '{slot}'")
			elif item not in self.inv:
				raise ValueError(f"Gear item {item} is absent from {self}'s inventory")
			elif item.slots is not None and slot not in item.slots:
				raise ValueError(f"Gear item {item} cannot use slot '{slot}'")
		if self.invWeight() > 2*self.BRDN():
			raise ValueError(f"Creature {self} exceeds inventory capacity")
		if not self.canCarryWeight():
			raise ValueError(f"Creature {self} exceeds cargo capacity")
		return super().validate()

	# returns a dict which contains all the necessary information to store
	# this object instance as a JSON object when saving the game
	# replace object references with their Item IDs
	def convertToJSON(self):
		jsonGear = {}
		for slot, item in self.gear.items():
			if item is EmptyGear():
				jsonGear[slot] = None
			else:
				jsonGear[slot] = item.id

		jsonDict = super().convertToJSON()
		jsonDict["carrier"] = self.carrier.id if self.carrier else None
		jsonDict["riding"] = self.riding.id if self.riding else None
		jsonDict["cover"] = self.cover.id if self.cover else None
		jsonDict["carrySlots"] = self.carrySlots
		jsonDict["gripSlots"] = self.gripSlots

		dictkeys = list(jsonDict.keys())
		delAttrs = ("gear","weapon","weapon2","shield","shield2",
		"statusCheckDepth","statusCheckPending")
		# these attributes do not get stored between saves
		for key in dictkeys:
			if key.lower() in Data.traits or key in delAttrs:
				del jsonDict[key]
		jsonDict["gear"] = jsonGear
		# convert traits to a form more easily writable in a JSON object
		jsonDict["traits"] = [self.str,self.spd,self.skl,self.stm,self.con,
		self.cha,self.int,self.wis,self.fth,self.lck]

		# delete attributes that should be given as defaults
		del jsonDict["fixed"], jsonDict["longevity"], jsonDict["durability"]
		return jsonDict


	### Operation ###

	# Atomically insert an existing registered Item into this creature's inventory.
	def add(self,I):
		if not isinstance(I,Item) or game.itemRegistry.get(I.id) is not I:
			raise ValueError(f"Cannot add unregistered object {I} to {self}")

		# Serpens can't get added to inventory
		if isinstance(I,Serpens):
			return I

		# an inventory can't hold a loose plash; it spills into the surroundings
		if hasMethod(I,"Spill"):
			self.Print(f"{+I} seeps out of your Inventory!",color="o")
			# spill material onto creature
			material = I.material()
			spill = material.touch
			if I.Weight() > self.Weight()//10:
				spill = material.drench 
			if spill:
				import Effects
				Effects.evokeEffects(spill,None,I,self)
			I.displace(self.parent)
			return I

		alphabetical = lambda x: (x.name.lower(), x.name)
		insort(self.inv,I,key=alphabetical)
		I.parent = self
		I.nullDespawn()
		I.expose(None)
		self.display()
		return I


	# defer status checks so they never judge a half-finished operation
	@contextmanager
	def deferStatusChecks(self):
		self.statusCheckDepth += 1
		try:
			yield
		finally:
			self.statusCheckDepth -= 1
			if self.statusCheckDepth == 0:
				self.flushStatusChecks()


	# mark that status entries changed; checks run now unless deferred
	def queueStatusCheck(self):
		self.statusCheckPending = True
		if self.statusCheckDepth == 0:
			self.flushStatusChecks()


	# run the status checks once to rederive this creature's derived state
	def flushStatusChecks(self):
		if self.statusCheckDepth > 0 or not self.statusCheckPending:
			return
		self.statusCheckPending = False
		self.statusCheckDepth += 1
		try:
			# regulate status cascades caused by status checks
			with self.statusCascade():
				self.checkStatus()
				self.checkImmersion()
		finally:
			self.statusCheckDepth -= 1


	# report a net status transition: the subject sees it via Print;
	# nearby observers witness it via printNearby only if the condition is public
	# message is the condition's gain/loss predicate ("" = authored suppression)
	def reportStatusChange(self,name,hadStatus):
		hasStatus = self.hasStatus(name)
		if hadStatus == hasStatus:
			return False

		cond = Data.StatusCondition.get(name)
		if cond.name != name:
			# unregistered names share the default record; derive from the live name
			predicate = f"are {name}." if hasStatus else f"are no longer {name}."
		else:
			predicate = cond.gainMsg if hasStatus else cond.lossMsg
		if predicate == "":
			return False
		msg = self + predicate

		color = (cond.color or "w") if hasStatus else "w"
		self.Print(msg,color=color)
		# printNearby suppresses non-public reports itself (godmode sees all)
		self.printNearby(msg,color=color,public=cond.public)
		return True


	# not used for Creatures but defined for consistency with Player subclass
	def awaken(self,wellRested=True):
		pass


	# change location while deferring status reports until the transition is complete
	def changeLocation(self,newparent,silent=False):
		with game.deferStatusReports():
			return self._changeLocation(newparent,silent=silent)


	# change location to a new Room/Container, return True on success
	def _changeLocation(self,newparent,silent=False):
		assert not isinstance(newparent,Creature)
		wasSubmerged = self.hasStatus("submerged")
		# store these, they would be empty after changing rooms
		carrying = self.carrying()
		occupants = self.occupants()
		# shouldn't be changing rooms alone if riding or being carried
		if self.carrier and self.carrier.parent is not newparent:
			return False
		if self.riding and self.riding.parent is not newparent:
			return self.riding.changeLocation(newparent,silent=silent)
		if not self.canChangeLocation(newparent,silent=silent):
			return False

		self.removeCover()
		self.clearCovering()

		prevparent = self.parent
		if prevparent:
			prevparent.exit(self)
		if self is player:
			if not prevparent or \
			(newparent.room() != prevparent.room()) and \
			newparent.surroundings() is newparent.room():
				game.changeRoom(newparent)
		entered = newparent.enter(self)
		assert entered, f"{self} failed to enter {newparent}"
		if wasSubmerged and self.immersed is not None and \
		self.immersed.canSubmerge(self) and not self.hasStatus("submerged"):
			self.addStatus("submerged",source="IMMERSED",silent=True)
		# when not riding or being carried, stand on the floor or float when immersed
		if self.hasStatus("flying") or \
		self.immersed is not None and self.canSwim():
			self.platform = None
		elif self.riding is None and self.carrier is None:
			self.platform = self.footing(newparent)

		# propagate location change to creatures riding or being carried
		for carried in carrying:
			if carried.carrier is self and carried.parent is not self.parent:
				carried.changeLocation(newparent)
		for occupant in occupants:
			if occupant.parent is not self.parent:
				occupant.changeLocation(newparent)
		assert all(carried.parent is self.parent for carried in carrying)

		return True


	# check whether this creature and its tethered group can enter a new parent
	def canChangeLocation(self,newparent,silent=False):
		msg = None
		if not newparent.couldSpill(self.totalSize()):
			msg = f"There's not enough space for {-self}."
		if not newparent.canAdd(self):
			msg = f"Entering {-newparent} fails."
		if msg:
			if not silent:
				self.Print(msg)
				if self in player.anchors():
					self.printNearby(msg)
			return False
		return True


	# change posture to given posture, removing other postures
	def changePosture(self,posture,silent=False):
		if posture is None:
			posture = "standing"
		if not posture.endswith("ing"):
			posture = ("sitt" if posture == "sit" else posture) +"ing"

		validPostures = ("standing","crouching","sitting","laying")
		assert posture in validPostures
		if posture != "standing" and self.anchor() is None:
			return False
		if self.posture() == posture:
			return False
		sizeIncrease = self.Size(posture=posture) - self.Size()
		if sizeIncrease > 0 and hasMethod(self.parent,"couldSpill") and \
		not self.parent.couldSpill(sizeIncrease):
			self.Print("There's not enough space to stand up.")
			return False

		for p in validPostures:
			if p != posture:
				self.removeStatus(p,silent=silent)
		# standing is the absence of the other conditions
		if posture != "standing":
			self.addStatus(posture,silent=silent)
		if posture in ("standing","crouching"):
			self.removeStatus("cozy",silent=silent)

		self.checkSize()
		self.checkHidden()
		return self.posture() == posture


	def checkBreathing(self):
		# hunger takes longer with more endurance
		sinceLastBreathed = game.time - self.lastBreathed
		if sinceLastBreathed > self.ENDR() // 2 and self.hasStatus("breathless"):
			# add drowning before removing breathless, so the status checks
			# that run between the two calls never see someone out of breath
			# with neither condition
			self.addStatus("drowning")
			self.removeStatus("breathless",silent=True)
		elif sinceLastBreathed > self.ENDR() // 3 and \
		not self.hasStatus(("breathless","drowning")):
			self.Print("You can't hold your breath much longer...")
			self.addStatus("breathless",silent=True)
		elif sinceLastBreathed <= self.ENDR() // 3:
			self.removeStatus("breathless",silent=True)
			self.removeStatus("drowning")


	# add/remove hidden status based on cover
	def checkHidden(self):
		if getattr(self.parent,"closed",False):
			if self.parent.material().transparent:
				self.removeStatus("hidden",reqSource="CONTAINER")
			else:
				self.addStatus("hidden",source="CONTAINER")
		elif self.coverBonus() >= 5 and \
		not self.cover.material().transparent:
			self.addStatus("hidden",source="COVER")
		else:
			self.removeStatus("hidden",reqSource="COVER")


	# add/remove hindered status based on inventory and cargo weight
	# cause flavor prints first; the deferred generic report follows
	def checkHindered(self):
		with game.deferStatusReports():
			inventoryHindered = self.invWeight() > self.BRDN()
			if inventoryHindered and \
			not self.hasStatus("hindered",reqSource="INVENTORY"):
				if self.addStatus("hindered",source="INVENTORY"):
					self.Print("Your Inventory grows heavy.")
			elif not inventoryHindered and \
			self.hasStatus("hindered",reqSource="INVENTORY"):
				if self.removeStatus("hindered",reqSource="INVENTORY"):
					self.Print("Your Inventory feels lighter.")

			cargoHindered = self.carryWeight() > self.BRDN()//4
			if cargoHindered and not self.hasStatus("hindered",reqSource="CARGO"):
				if self.addStatus("hindered",source="CARGO"):
					self.Print("Your cargo weighs you down.")
			elif not cargoHindered and \
			self.hasStatus("hindered",reqSource="CARGO"):
				if self.removeStatus("hindered",reqSource="CARGO"):
					self.Print("Your cargo feels lighter.")


	# unused for Creatures, but used in Player subclass
	def checkHungry(self):
		return False


	# reconcile Creature tethers and burden after a size change
	def checkSize(self):
		super().checkSize()
		self.checkTethers()
		self.checkHindered()


	# reconcile the Creature-only submerged status with its liquid and support
	def checkSubmersion(self,silent=False):
		fluid = self.immersed
		if fluid is None:
			return self.removeStatus("submerged",silent=silent)

		# a liquid Room has no surface within the current location
		if isinstance(fluid,Room):
			if not self.hasStatus("submerged",reqSource="IMMERSED"):
				return self.addStatus("submerged",source="IMMERSED",
					silent=silent)
			return False

		# carried creatures and riders move with their anchor instead of sinking alone
		if isinstance(self.anchor(),Creature):
			if not fluid.canEmerge(self):
				if not self.hasStatus("submerged",reqSource="IMMERSED"):
					return self.addStatus("submerged",source="IMMERSED",
						silent=silent)
				return False
			return self.removeStatus("submerged",silent=silent)

		# if fluid can no longer submerge us for some reason, remove submerged
		if not fluid.canSubmerge(self):
			return self.removeStatus("submerged",silent=silent)

		platform = self.platform
		# a liquid floor (Surface) has no floor of its own beneath it
		onFluidFloor = platform is not None and \
			platform is getattr(fluid,"floor",None)
		onSubmergedPlatform = platform is not None and \
			platform.immersed is fluid and \
			platform.hasStatus("submerged",reqSource="IMMERSED")
		if onFluidFloor or onSubmergedPlatform:
			if not self.hasStatus("submerged",reqSource="IMMERSED"):
				return self.addStatus("submerged",source="IMMERSED",
					silent=silent)
			return False
		if platform is not None:
			return self.removeStatus("submerged",silent=silent)
		if self.hasStatus("submerged",reqSource="IMMERSED"):
			return False

		if not self.canSwim(fluid):
			if not silent:
				self.Print("You are too heavy to keep yourself afloat!",color="o")
		elif not fluid.canEmerge(self):
			if not silent:
				self.Print("There isn't enough room to remain surfaced!",color="o")
		else:
			return self.removeStatus("submerged",silent=silent)
		if not self.hasStatus("submerged",reqSource="IMMERSED"):
			return self.addStatus("submerged",source="IMMERSED",silent=silent)
		return False


	# remove cover which no longer shares a parent or provides enough space
	def checkCover(self):
		if self.cover is None:
			return
		if self.cover.parent is self.parent and self.cover.availableCover(self) > 0:
			self.checkHidden()
			return
		self.removeCover(silent=True)


	# fall from an invalid ordinary platform and validate valid platform occupancy
	def checkPlatform(self):
		platform = self.platform
		if platform is None or platform is getattr(self.parent,"floor",None):
			return
		if platform.parent is not self.parent:
			self.removePlatform()
			self.fall(platform.Size()//5)
			return
		platform.checkOccupancy(self)
		if self.platform is platform:
			platform.checkOccupantsWeight(silent=True)


	# drop carried creatures which no longer fit a carry slot or burden limit
	def checkCarrying(self):
		carrying = self.carrying()
		for carried in carrying:
			assert carried is not self
			# checkCarrying can be called during self.changeLocation when this is not true
			# assert carried.parent is self.parent
			assert carried.carrier is self

		cargoWeight = 0
		toDrop = []
		for carried in sorted(carrying,key=lambda carried:carried.Weight()):
			slotsUsed = [slot for slot in self.carrySlots if self[slot] is carried]
			slotsNeeded = carried.gripsNeeded(self)

			# mark any cargo thats too heavy as to-be-dropped
			if not self.canCarryWeight(carried,currentWeight=cargoWeight):
				for slot in slotsUsed:
					self[slot] = EmptyGear()
				toDrop.append(carried)
				continue

			# mark any cargo that doesn't have enough grip slots as to-be-dropped
			if len(slotsUsed) < slotsNeeded:
				availableSlots = [slot for slot in self.carrySlots if self[slot] is EmptyGear()]
				slotDeficit = slotsNeeded-len(slotsUsed)
				if len(availableSlots) < slotDeficit:
					for slot in slotsUsed:
						self[slot] = EmptyGear()
					toDrop.append(carried)
					continue
				# if we have them to spare, give cargo the additional slots it needs
				for slot in availableSlots[:slotDeficit]:
					self[slot] = carried

			cargoWeight += carried.Weight()

		for carried in toDrop:
			self.Print(f"{+carried} is too heavy! " + "You drop"/carried + ".")
			self.removeCarry(carried,silent=True,drop=True)


	# adjust occupied grip slots when strength or wielded item weight changes
	def checkGrips(self):
		items = []
		for slot in self.gripSlots:
			item = self[slot]
			if item is EmptyGear() or isinstance(item,Creature) or item in items:
				continue
			items.append(item)

		for item in items:
			occupied = [slot for slot in self.gripSlots if self[slot] is item]
			gripsNeeded = item.gripsNeeded(self)
			# move item to appropriate grip slot and trigger equip effects
			if len(occupied) < gripsNeeded:
				available = [slot for slot in self.gripSlots \
					if self[slot] is EmptyGear()]
				if len(occupied) + len(available) < gripsNeeded:
					self.Print(f"{+item} is too heavy! You unequip it.")
					self.unequip(occupied[0],silent=True)
					continue
				for slot in available[:gripsNeeded-len(occupied)]:
					self[slot] = item
					item.evokeEffects(f"equip:{slot}",self)
			elif len(occupied) > gripsNeeded:
				for slot in occupied[gripsNeeded:]:
					self[slot] = EmptyGear()
					item.evokeEffects(f"unequip:{slot}",self)

		self.assignWeaponAndShield()


	# dismount riders which no longer fit the mount's size or burden limits
	def checkRiding(self):
		riders = self.riders()
		for rider in riders:
			if rider.Size()//2 <= self.Size():
				continue
			rider.removeRiding(silent=True)
			rider.fall(self.Size()//5)

		riders = self.riders()
		while riders and self.occupantsWeight() > self.BRDN()//2:
			rider = max(riders,key=lambda rider:rider.Weight())
			rider.removeRiding(silent=True)
			rider.fall(self.Size()//5)
			riders.remove(rider)

		riders = self.riders()
		while len(riders) > 1 and self.ridingSpace() < 0:
			rider = riders[0]
			rider.removeRiding(silent=True)
			rider.fall(self.Size()//5)
			riders.remove(rider)


	# validate this creature and every carrier or mount above it
	def checkTethers(self):
		creature = self
		checked = set()
		while isinstance(creature,Creature) and creature not in checked:
			checked.add(creature)
			nextAnchor = creature.carrier or creature.riding
			creature.checkCover()
			creature.checkPlatform()
			creature.checkCarrying()
			creature.checkGrips()
			creature.checkRiding()
			creature = nextAnchor


	# check all status conditions that may need updating
	def checkStatus(self):
		# dead creatures don't update their conditions
		if self.hasStatus("dead"):
			return
		self.checkHungry()
		self.checkTired()
		self.checkCarrying()
		self.checkGrips()
		self.checkRiding()
		self.checkHindered()
		self.checkHidden()
		# these should probably be not be checked like the others
		# self.checkBreathing()
		# self.checkSubmersion()


	# unused for Creatures, but used in Player subclass
	def checkTired(self):
		return False


	# called when a creature's hp hits 0
	def death(self):
		self.timeDespawn()
		anointed = self.hasStatus("anointed")
		# add dead first: its onGain hooks clear hunger/tiredness and its
		# blocks prevent the status checks below from re-deriving them
		self.addStatus("dead")
		# death removes permanent statuses; you are refreshed
		self.removeStatus(reqSource="PERMANENT",silent=True)
		self.changePosture("laying",silent=True)
		self.printNearby(f"{+self} died.",color="o")

		if anointed:
			return self.reanimate()
		# a true death releases the statuses this creature was sustaining
		self.releaseBoundStatuses()

		self.removeRiding(silent=True)
		self.clearCarrying(silent=True)

		self.descname = f"dead {self.descname}"
		self.aliases.extend(["dead "+a for a in self.aliases])

		n = diceRoll(3,player.LOOT(),-2)
		game.spawn(Serpens(n),self.parent)
		self.printNearby(f"Dropped Â§{n}.",color="g")

		if game.whoseTurn is player:
			r = self.rating()
			# xp granted generally scales with rating
			xp = halfRoll(r)
			player.gainxp(xp)


	# sever tethers (cover, carrying both ways, riding)
	def detach(self,silent=True):
		carrying = list(self.carrying())
		if self.cover:
			self.removeCover()
		self.clearCovering()
		self.clearOccupants()
		if self.carrier:
			self.carrier.removeCarry(self,silent=True,drop=False)
		for carried in carrying:
			self.removeCarry(carried,silent=True,drop=True)
		self.removePlatform()
		self.removeRiding(silent=silent)
		super().detach(silent=silent)


	# TODO: is this function necessary?
	# drop Inventory Items if over capacity
	def ejectInventory(self):
		# drop any items over capacity
		if self.invWeight() > 2*self.BRDN():
			self.Print("Your Inventory overflows!",color="o")
		while self.invWeight() > 2*self.BRDN():
			item = max(self.inv, key=lambda x: x.Weight())
			self.remove(item)
			self.Print(f"You drop {-item}.")


	# heals hp a given amount
	def heal(self,heal,overflow=False):
		if self.hp + heal > self.MXHP() and not overflow:
			heal = self.MXHP() - self.hp
		if heal <= 0 or not self.isAlive():
			return 0
		self.hp += heal
		self.display()
		self.Print(f"You healed {heal} HP.",color="g")
		return heal


	# pass time, take damage from status conditions, regen health/mana
	def passTime(self,t):
		super().passTime(t)

		if not self.hasStatus("submerged"):
			self.lastBreathed = game.time
		self.checkBreathing()
		self.checkStatus()

		# take damage from damaging status conditions
		for condition in self.conditions():
			if condition.damage is not None:
				factor, dmgType = condition.damage
				dmg = min1(halfRoll(factor) - halfRoll(self.LCK()))
				self.takeDamage(dmg,dmgType)

		# natural healing is faster with a higher endurance
		if self.hasStatus(("hungry","starving")) and not self.hasStatus("mending"):
			self.regenTimer = 0
		elif not self.hasStatus("dead"):
			self.regenTimer += t
			if self.regenTimer >= 50 - self.ENDR() or self.hasStatus("mending"):
				self.regenTimer = 0
				h = 5 if self.hasStatus(("cozy","mending")) else 1
				self.heal(h)
				# TODO: do mana resurgence at separate rate than healing
				self.resurge(1)


	# reanimate from dead status with 1 hp
	def reanimate(self):
		if not self.hasStatus("dead"):
			return False
		if self.hasStatus("anointed"):
			self.removeStatus("anointed",silent=True)
		self.hp = 1
		self.nullDespawn()
		# reanimation refreshes your body
		self.lastAte = game.time
		self.lastSlept = game.time
		if self is player:
			delay(1)
			self.waitInput("You reawaken!",color="g")
			self.removeStatus("dead")
		else:
			Print(f"{+self} has been reanimated!")
			self.removeStatus("dead")
		return True


	# remove an Item from Inventory
	# if it was equipped, unequip it; fires the item's drop
	# check if still hindered
	def remove(self,I,silent=False):
		removed = False
		if I in self.carrying():
			removed = self.removeCarry(I,silent=silent,drop=True)
		elif I in self.inv:
			for slot,obj in self.gear.items():
				if I is obj:
					self.unequip(slot,silent=silent)
			self.inv.remove(I)
			I.parent = None
			removed = True
		# if removing an object within a child object, make sure its accessible
		elif I in self.objTree():
			invAncestors = I.ancestors()
			invAncestors = invAncestors[:invAncestors.index(self)]
			if any(getattr(ancestor,"locked",False) for ancestor in invAncestors):
				return False
			removed = I.parent.exit(I)
		if removed:
			I.drop(self)
		if removed and not silent:
			self.checkStatus()
		return removed


	# Creatures also hand over carrying, carrier, riding, and mount tethers
	def replacementSnapshot(self):
		snap = super().replacementSnapshot()
		snap["carrying"] = list(self.carrying())
		snap["carrier"] = self.carrier
		snap["riding"] = self.riding
		snap["carrySlots"] = [] if self.carrier is None else \
			[slot for slot in self.carrier.carrySlots if self.carrier[slot] is self]
		return snap


	# hand over cover, riders, cargo, carrier slots, riding, and platform
	# newObj may not survive receiving its new tethers
	def transferReplacementTethers(self,newObj,snap):
		for covered in snap["covered"]:
			covered.removeCover(silent=True)
			covered.addCover(newObj)
		for occupant in snap["occupants"]:
			occupant.replaceObj(self,newObj)
		# newObj may be destroyed when receiving an occupant
		if not newObj.parent:
			return

		# TODO: when replacing creature with creature, copy carrying and riding?
		if snap["carrying"]:
			# parent is used to removeCarry, so reassign it temporarily
			self.parent = snap["parent"]
			self.clearCarrying(silent=True,drop=False)
			self.parent = None
			for carried in snap["carrying"]:
				carried.fall(self.Size()//5)

		carrier = snap["carrier"]
		if carrier:
			carrier.clearCarrySlots(self)
			if isinstance(newObj,Creature):
				if newObj.carrier:
					newObj.carrier.removeCarry(newObj,silent=True,drop=False)
				if newObj.carry(carrier,silent=True):
					carrier.assignCarrySlots(newObj,snap["carrySlots"])
			elif carrier.canObtain(newObj,silent=True):
				carrier.ObtainItem(newObj,silent=True)
				for slot in snap["carrySlots"]:
					carrier[slot] = newObj
		elif self.riding:
			# TODO: preserve a replacement Creature as rider on the same mount
			r = self.riding
			self.removeRiding()
			newObj.fall(r.Size()//5)
		elif self.platform:
			p = self.platform
			self.removePlatform()
			if isinstance(p,Portal) and p.canPass(newObj) and p.canAdd(newObj):
				p.transfer(newObj)
			else:
				p.occupy(newObj)


	# rederive tethers for every creature a replacement may have disturbed
	def replacementChecks(self,newObj,snap):
		creatures = snap["covered"] + snap["carrying"] + \
			[snap["carrier"],snap["riding"]]
		if isinstance(newObj,Creature):
			creatures.append(newObj)
		for creature in {c for c in creatures if isinstance(c,Creature)}:
			creature.checkTethers()
		if newObj.parent is not None:
			newObj.checkSize()


	# replace a Creature in this Creature's tethers with a Creature or Item
	# replace riding with platform, carrying with inventory item
	def replaceCreature(self,oldObj,newObj):
		assert isinstance(oldObj,Creature)
		if self.riding is oldObj:
			self.removeRiding(silent=True)
			if isinstance(newObj,Creature):
				if not newObj.ride(self,silent=True):
					self.fall(oldObj.Size()//5)
			else:
				if not newObj.occupy(self,silent=True):
					self.fall(oldObj.Size()//5)

		if oldObj in self.carrying():
			slotsUsed = [slot for slot in self.carrySlots if self[slot] is oldObj]
			self.removeCarry(oldObj,silent=True,drop=False)
			if isinstance(newObj,Creature):
				if newObj.carrier:
					newObj.carrier.removeCarry(newObj,silent=True,drop=False)
				if newObj.carry(self,silent=True):
					self.assignCarrySlots(newObj,slotsUsed)
			elif self.canObtain(newObj,silent=True):
				self.ObtainItem(newObj,silent=True)
				for slot in slotsUsed:
					self[slot] = newObj
				if any(slot in self.gripSlots for slot in slotsUsed):
					self.assignWeaponAndShield()
			else:
				self.checkTethers()
				newObj.checkTethers() if isinstance(newObj,Creature) else None
				return False
		self.checkStatus()
		self.checkTethers()
		newObj.checkTethers() if isinstance(newObj,Creature) else None


	# replace an Item in this Creature's tethers with a Creature or Item
	# if newObj is creature, replaced equipped gear with carried
	def replaceItem(self,oldObj,newObj):
		assert oldObj in self and not isinstance(oldObj,Creature)
		oldObjSlot = None
		for slot,obj in self.gear.items():
			if oldObj is obj:
				oldObjSlot = slot
				break

		if isinstance(newObj,Creature):
			# if Item is in a carry slot, preserve that slot
			carriedSlot = oldObjSlot if oldObjSlot in self.carrySlots else None

			self.remove(oldObj,silent=True)
			if not self.parent.canAdd(newObj):
				self.checkTethers()
				newObj.checkTethers()
				return False
			entered = self.parent.enter(newObj)
			assert entered, f"Failed to place {newObj} after successful admission check"

			# if it was equipped in gear, carry the creature instead
			if carriedSlot and self[carriedSlot] is EmptyGear():
				if newObj.carrier:
					newObj.carrier.removeCarry(newObj,silent=True,drop=False)
				if newObj.carry(self,silent=True):
					self.assignCarrySlots(newObj,[carriedSlot])
		else:
			self.remove(oldObj,silent=True)
			if not self.canObtain(newObj):
				self.checkTethers()
				return False
			self.ObtainItem(newObj,silent=True)

			if oldObjSlot:
				self.gear[oldObjSlot] = newObj
				newObj.equip(self,[oldObjSlot])

		self.checkStatus()
		self.checkTethers()
		newObj.checkTethers() if isinstance(newObj,Creature) else None
		return True


	# replace an object in this Creature's tethers
	def replaceObj(self,old,new):
		if isinstance(old,Creature):
			return self.replaceCreature(old,new)
		elif isinstance(old,Item):
			return self.replaceItem(old,new)
		else:
			return None


	# regain mp a given amount
	def resurge(self,mana,overflow=False):
		if self.mp + mana > self.MXMP() and not overflow:
			mana = min0(self.MXMP() - self.mp)
		if mana <= 0:
			return 0
		self.mp += mana
		self.display()
		self.Print(f"You regained {mana} MP.",color="b")
		return mana


	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		assert dmg >= 0, "Damage taken must be non-negative"
		if self.hasStatus("dead"):
			return False
		prevhp = self.hp
		if self.hasStatus(f"{type} vulnerability"): dmg *= 2
		if self.hasStatus(f"{type} resistance"): dmg //= 2
		if self.hasStatus(f"{type} immunity"): dmg = 0
		# bludgeoning damage can't kill you in one hit
		if type in ("b","d") and self.hp > 1:
			self.hp = min1(self.hp-dmg)
		# hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp

		p = "!" if self.hasStatus("asleep") or total_dmg > self.MXHP()//4 else "."
		# verb escalates with damage relative to max hp
		verb = "took"
		if total_dmg > self.MXHP()//2 and total_dmg > 25:
			verb = "suffered"
		elif total_dmg > self.MXHP()//4 and total_dmg > 25:
			verb = choice(Data.dmgverbs)
		# emphasize truly large hits
		if total_dmg > 300:
			emp = choice(Data.superEmphasis)+" "
		elif total_dmg > 50 and total_dmg > self.MXHP()//2:
			emp = choice(Data.emphasis)+" "
		else:
			emp = ""
		color = "w"
		if self is player and total_dmg > 0:
			color = "r"
		typeDisplay = "" if type == "e" else Data.dmgtypes[type] + " "
		msg = f"{+self} {verb} {emp}{total_dmg} {typeDisplay}damage{p}"
		self.Print(msg,color=color)
		self.printNearby(msg,color=color)
		self.display()
		if self is player:
			delay(0.5)
		if self.hp == 0:
			return self.death()
		if total_dmg > 0 and self.hasStatus("asleep"):
			self.awaken()


	# ensure fear is within bounds
	def updateFear(self,fearMod):
		self.fear = bound(fearMod,-100,100)


	# ensure love is within bounds
	def updateLove(self,loveMod):
		self.love = bound(loveMod,-100,100)


	# update money by given amount, print new total
	def updateMoney(self,money):
		self.money += money
		color = "g" if money > 0 else "w"
		if money == 0:
			self.Print(f"You have Â§{self.money}.")
		else:
			self.Print(f"You have Â§{self.money}!",color=color)
		self.display()


	### Interaction ###

	# assign both ends of a carrying relationship to the given slots
	def assignCarrySlots(self,creature,useSlots):
		assert isinstance(creature,Creature)
		assert creature.carrier in (None,self)
		assert useSlots and len(useSlots) == len(set(useSlots))
		for slot in useSlots:
			assert slot in self.carrySlots
			assert self[slot] is EmptyGear() or self[slot] is creature

		# clear possible existing slots that are holding creature
		for slot in self.carrySlots:
			if self[slot] is creature and slot not in useSlots:
				self[slot] = EmptyGear()

		# set creature's authoritative carrier tether and assign creature to slots
		newCarry = creature.carrier is not self
		creature.carrier = self
		for slot in useSlots:
			self[slot] = creature
		# re-slotting an already-carried creature doesn't re-fire the trigger
		if newCarry:
			creature.evokeEffects("carry",self)
		self.display()


	# clear both ends of a carrying relationship
	def clearCarrySlots(self,creature):
		for slot in self.carrySlots:
			if self[slot] is creature:
				self[slot] = EmptyGear()
		if creature.carrier is self:
			creature.carrier = None
		self.display()


	# prepare carry slots, then attempt to carry and assign a Creature to them
	def Heft(self,cargo,forceUnequip=False,silent=False):
		assert isinstance(cargo,Creature)
		assert self.parent is not None
		assert cargo.parent is self.parent
		if cargo is self:
			if not silent:
				self.Print("You can't lift yourself!")
			return False
		if cargo.carrier is self:
			return False
		# get the plan of what unequips, drops, and slots are needed to carry creature
		plan = self.planCarrySlots(cargo,forceUnequip=forceUnequip)
		if plan is None:
			if not silent:
				self.Print(f"You don't have enough free slots to carry {-cargo}.")
			return False

		while plan["unequip"] or plan["drop"]:
			# finish the planned preparation before checking changed limits
			slotsNeeded = cargo.gripsNeeded(self)
			burdenLimit = self.BRDN()
			while plan["unequip"]:
				item = plan["unequip"].pop(0)
				slotUsed = next(slot for slot in self.carrySlots if self[slot] is item)
				self.unequip(slotUsed,silent=silent)
			while plan["drop"]:
				self.removeCarry(plan["drop"].pop(0),silent=silent,drop=True)

			if cargo.gripsNeeded(self) != slotsNeeded or self.BRDN() != burdenLimit:
				plan = self.planCarrySlots(cargo,forceUnequip=forceUnequip)
				if plan is None:
					return False

		if not silent:
			self.Print(f"You try to pick up {-cargo}.",color="o")
		if not cargo.carry(self,silent=silent):
			return False
		assert all(self[slot] is EmptyGear() for slot in plan["slots"])
		self.assignCarrySlots(cargo,plan["slots"])

		assert cargo.parent is self.parent and cargo in self.carrying()
		self.checkHindered()
		return True


	# place a released creature on support, in nearby fluid, or on the room floor
	def assignReleasedPlatform(self,carried):
		platform = self.platform
		floor = self.footing()
		# preserve shared floor support without treating it as ordinary occupancy
		if platform is floor and floor is not None:
			carried.platform = carried.footing()
			carried.checkImmersion(silent=True)
			if carried.platform is platform:
				return True

		# prefer the carrier's ordinary platform when it has room
		validPlatform = platform is not None and platform.parent is self.parent
		carried.platform = None
		if validPlatform and platform.canOccupy(carried) and \
		platform.occupy(carried,silent=True):
			return True

		# otherwise release into fluid surrounding the carrier or its platform
		fluid = self.immersed
		if fluid is None and validPlatform:
			fluid = platform.immersed
		if fluid is not None and fluid.canImmerse(carried):
			if carried.immersed is fluid:
				carried.checkSubmersion(silent=True)
				return True
			if carried.immersed is not None:
				carried.unimmerse(silent=True)
			if carried.immerse(fluid,silent=True):
				return True

		# use the room floor last; removeCarry() handles falling if none exists
		if carried.immersed is not None:
			carried.unimmerse(silent=True)
		carried.platform = carried.footing()
		if carried.platform is None:
			return False
		carried.checkImmersion(silent=True)
		return True


	# add cover to this Creature, attempt to hide
	def addCover(self,cover):
		if self.cover is cover:
			return False
		if cover is None:
			self.removeCover(silent=True)
			return True
		if not cover.addCovering(self):
			return False
		self.checkHidden()
		return True


	# add riding tether
	def addRiding(self,creature):
		assert isinstance(creature,Creature)
		assert self.anchor() is None
		self.riding = creature


	# only used by equip and unequip to reassign several attributes
	# specifically, weapon, weapon2, shield, shield2
	def assignWeaponAndShield(self):
		# if unassigned, attributes are empty, self.weapon is always assigned
		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		gripped = []
		for slot in self.gripSlots:
			item = self[slot]
			if item is EmptyGear() or isinstance(item,Creature) or item in gripped:
				continue
			gripped.append(item)

		weapons = [item for item in gripped if isinstance(item,Weapon)]
		if not weapons:
			weapons = [item.asWeapon() for item in gripped if hasMethod(item,"asWeapon")]
		if weapons:
			self.weapon = weapons[0]
		if len(weapons) > 1:
			self.weapon2 = weapons[1]

		shields = [item for item in gripped if isinstance(item,Shield)]
		if shields:
			self.shield = shields[0]
		if len(shields) > 1:
			self.shield2 = shields[1]


	# be bombarded by a projectile with a chance to hit
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			# TODO: determine how they'll decide if they catch here
			if percentChance(50) and hasMethod(self,"Catch"):
				dodge = -10
				if self.Catch(missile):
					return True
		if percentChance(bound(missile.aim+missile.speed-dodge,1,99)):
			return missile.collide(self)
		return False


	# permit another Creature to carry this Creature and remove old anchors
	def carry(self,carrier,silent=False):
		assert isinstance(carrier,Creature)
		if carrier is self:
			return False
		if carrier.checkTetherLoop(self,carrier,f"carry {-self}",silent=silent):
			return False
		if self.carrier:
			if not silent:
				carrier.Print(f"{+self} is already being carried by {-self.carrier}.")
			return False
		if self.gripsNeeded(carrier) > len(carrier.carrySlots):
			if not silent:
				carrier.Print(f"You aren't strong enough to carry {-self}.")
			return False
		if not carrier.canCarryWeight(self):
			if not silent:
				carrier.Print(f"{+self} is too heavy for you to carry.")
			return False

		if not self.restrain(carrier,silent=silent):
			return False

		self.removeRiding(silent=True)
		self.removePlatform()
		self.changePosture("stand",silent=True)
		if carrier.cover is not self.cover:
			self.removeCover(silent=True)
			if carrier.cover is not None:
				self.addCover(carrier.cover)
		assert self.anchor() is None
		return True


	# if the Item is armor, equip it, otherwise return False
	def equipArmor(self,I,slot=None):
		assert I in self
		if slot == None:
			slot = I.slots[0]
		if slot not in I.slots:
			return False
		if slot not in self.gear.keys():
			return False
		# a previous occupant must leave gear properly before being replaced
		self.unequip(slot,silent=True)
		self[slot] = I
		I.equip(self,[slot])
		return True


	# equip an item across as many grip slots as its weight and minimum require
	def equipInHand(self,I,slot=None):
		assert I in self or I in self.carrying()
		if slot is None:
			emptyGrips = [grip for grip in self.gripSlots if self[grip] is EmptyGear()]
			if "right" in emptyGrips:
				slot = "right"
			elif emptyGrips:
				slot = emptyGrips[0]
			else:
				slot = "right" if "right" in self.gripSlots else self.gripSlots[0]
		if slot not in self.gripSlots:
			return False
		if any(self[grip] is I for grip in self.gripSlots):
			return False

		gripsNeeded = I.gripsNeeded(self)
		if gripsNeeded > len(self.gripSlots):
			self.Print(f"{+I} is too unwieldy for you! " \
				"It requires more grips than you have.")
			return False
		grips = [slot] + [grip for grip in self.gripSlots if grip != slot]
		grips = grips[:gripsNeeded]
		for grip in grips:
			self.unequip(grip)
		for grip in grips:
			self[grip] = I
		self.assignWeaponAndShield()
		I.equip(self,grips)
		self.checkStatus()
		return True


	# Creature falls through rooms accumulating fall height until hitting floor, 
	# then take damage and set platform to room's floor
	def fall(self,height=0,room=None,removeCarrier=False):
		if self.carrier:
			if not removeCarrier:
				return False
			self.carrier.removeCarry(self,silent=True,drop=False)
		if self.riding:
			return self.riding.fall(height,room)
		if self.immersed is not None and not self.hasStatus("submerged"):
			return False

		wasSubmerged = self.hasStatus("submerged")
		self.checkImmersion()
		if not wasSubmerged and self.hasStatus("submerged"):
			return True
		verb = "sink" if self.hasStatus("submerged") else "fall"
		if self.immersed is not None and self.canSwim():
			return False

		if player in self.occupants() or player in self.carrying() or player is self:
			waitInput(self+f"{verb}s!",color="o")
		else:
			self.printNearby(self+f"{verb}s.",color="o")

		if self.hasStatus("flying"):
			self.printNearby("But"+(self*"is flying."))
			return False

		if room is None:
			room = self.room()
		immersionSource = self.immersed
		if verb == "sink" and hasMethod(immersionSource,"transferImmersed"):
			destinationFluid = immersionSource
			destinationParent = self.parent
			while hasMethod(destinationFluid,"transferImmersed") and \
			"down" in destinationFluid.links:
				height += destinationFluid.Capacity() // 5
				destinationParent = destinationFluid.getNewLocation("down")
				destinationFluid = destinationFluid.links["down"]
			if destinationFluid is not immersionSource and \
			immersionSource.transferImmersed(self,destinationParent,destinationFluid):
				self.printNearby(f"{~self} sinks from above!".capitalize())
			floor = self.footing()
			if self.anchor() is not floor:
				self.platform = floor
			return True
		while "down" in room.links and (room.floor is None or \
		(room.floor.material().liquid and verb == "sink")):
			height += room.Capacity() // 5 # approximate height of room
			room = room.links["down"]
		if room != self.room():
			if self is player:
				ellipsis()
			if self.changeLocation(room,silent=True):
				verb = "sink" if self.hasStatus("submerged") else "fall"
				self.printNearby(f"{~self} {verb}s from above!".capitalize())
				if self.hasStatus("submerged") and self.canSwim(): return False

		floor = self.footing()
		if self.anchor() is not floor:
			self.platform = floor

		force = min(height,20*self.weight)
		if not self.hasStatus(("fleetfooted","submerged")) and \
		room.floor is not None and self.immersed is None:
			if force > 0:
				self.takeDamage(force,"b")
				for rider in self.occupants():
					rider.takeDamage(force//3,"b")
				for carried in self.carrying():
					carried.takeDamage(force//3,"b")
			self.changePosture("laying")
		return True


	# occupying a Creature is equivalent to riding it
	def occupy(self,occupant,silent=False,actor=None,posture=None):
		if not isinstance(occupant,Creature):
			occupant.fall(self.Size()//5)
			return False
		return self.ride(occupant,silent=silent,actor=actor,posture=posture)


	def offer(self,I):
		self.Print(f"{+self} ignores your offer.")


	# remove carrying tether if exists
	def removeCarry(self,carried=None,silent=False,drop=False):
		carrying = self.carrying()
		if carried is None:
			if len(carrying) != 1:
				return False
			carried = next(iter(carrying))
		if carried not in carrying and carried.carrier is not self:
			return False
		slotsUsed = [slot for slot in self.carrySlots if self[slot] is carried]
		self.clearCarrySlots(carried)
		if not silent:
			self.Print(f"You drop {-carried}.")
			carried.Print(f"{+self} is no longer carrying you.")
		carried.removeStatus("restrained",reqSource=self.id,silent=True)
		carried.evokeEffects("uncarry",self)
		if drop and not self.assignReleasedPlatform(carried):
			carried.fall(self.Size()//5)
		assert carried not in self.carrying() and carried.parent is self.parent
		self.checkHindered()
		return bool(slotsUsed)


	def clearCarrying(self,silent=False,drop=True):
		carrying = self.carrying().copy()
		for carried in carrying:
			self.removeCarry(carried,silent=silent,drop=drop)
		return carrying


	# remove cover if exists
	def removeCover(self,silent=False):
		if self.cover:
			self.Print(f"You are no longer behind {-self.cover}.") if not silent else None
			self.cover.removeCovering(self)
		self.cover = None
		for carried in self.carrying():
			carried.removeCover(silent=silent)
		self.checkHidden()


	# remove riding tether if exists
	def removeRiding(self,silent=False):
		if self.riding is not None:
			# store this because dismounting affects riding.print
			wasRiding = self.riding
			self.riding.disoccupy(self)
			if not silent:
				self.Print(f"You are no longer riding {-wasRiding}.")
				wasRiding.Print(f"{+self} is no longer riding {-wasRiding}.")


	# attempt to restrain this Creature
	# the restraint is sourced to the restraining item if given, else the restrainer
	def restrain(self,restrainer,item=None,silent=False):
		if not self.isAlive():
			return True
		if not self.isFriendly() and self.canMove():
			if item != None:
				#TODO: add restraining with items? like rope??
				pass
			if self.ATHL() > restrainer.ATHL():
				if not silent:
					restrainer.Print(f"{+self} resists restraint!",color="r")
				return False
			if self.EVSN() > restrainer.ATHL():
				if not silent:
					restrainer.Print(f"{+self} evades restraint!",color="r")
				return False
		source = item.id if item is not None else restrainer.id
		self.addStatus("restrained",source=source,silent=True)
		if not silent:
			restrainer.Print(f"You restrain {-self}!",color="g")
		return True


	# attempt to ride this Creature; posture is the rider's intended posture
	def ride(self,rider,silent=False,actor=None,posture=None):
		assert isinstance(rider,Creature)
		assert self.parent is not None and rider.parent is self.parent
		if actor is None:
			actor = rider
		assert isinstance(actor,Creature)
		if rider in self.riders():
			if not silent:
				actor.Print(rider+f"is already riding {-self}.")
			return False
		action = f"ride {-self}" if actor is rider else f"put {-rider} on {-self}"
		if self.checkTetherLoop(rider,actor,action,silent=silent):
			return False
		if not self.permitsMountImmersion(rider,actor,silent=silent):
			return False
		if rider.Size()//2 > self.Size():
			if not silent:
				actor.Print(self+f"is too small for {-rider} to ride.")
			return False

		# determine if there is a rider that needs to be pushed off due to lack of space.
		riderToPush = None
		if self.riders() and rider.Size() > self.ridingSpace(rider):
			riderToPush = self.riders()[0]
		if riderToPush is not None and actor is not rider:
			if not silent:
				actor.Print("There's not enough space. " + \
					(self+f"is occupied by {-riderToPush}."))
			return False

		# a rider intending to crouch settles into it before the attempt;
		# crouching improves the mounting contest (read before the platform
		# is removed, which would read as "floating")
		if posture in ("crouch","crouching"):
			rider.changePosture("crouch",silent=silent)
		riderCrouched = rider.posture() == "crouching"
		rider.removeRiding()
		rider.removePlatform()

		# contest with existing rider to push eachother off
		if riderToPush is not None:
			if not silent:
				actor.Print(riderToPush+f"is already riding {-self}.")
			if roll(rider.ATHL()) > roll(riderToPush.ATHL()):
				if not silent:
					actor.Print(rider+f"push {-riderToPush} off of {-self}.")
				riderToPush.Print(f"{+rider} pushes you off of {-self}.",color="r")
				riderToPush.removeRiding()
				riderToPush.fall(self.Size()//5)
			else:
				if not silent:
					actor.Print(riderToPush+f"hold onto {-self}.")
					actor.Print(rider+f"does not manage to occupy {-self}.",color="r")
				rider.fall(self.Size()//5)
				return False

		# fall off if the mount cannot bear the combined occupant weight
		if rider.Weight() + self.occupantsWeight() > self.BRDN()//2:
			if not silent:
				actor.Print(rider+f"is too much additional weight for {-self}.")
			rider.fall(self.Size()//5)
			return False

		# after pushing contest, you still might fall off if theres not enough space
		if rider.Size() > self.ridingSpace(rider):
			if not silent:
				actor.Print(self+f"does not have enough space for {-rider} to ride.")
			rider.fall(self.Size()//5)
			return False

		# next the mount might try to push you off
		contest = not self.isFriendly() and self.canMove()
		if contest:
			if not silent:
				actor.Print(self+f"struggle.",color="o")
			mountPenalty = -10 if self.posture() == "laying" else 0
			riderBonus = 10 if riderCrouched else 0
			athleticsContest = self.ATHL() - rider.ATHL() - riderBonus + mountPenalty
			if athleticsContest > 0:
				if not silent:
					actor.Print(self+f"shake {-rider} off!",color="r")
				rider.fall(min0(athleticsContest) + self.Size()//5)
				return False

		rider.addRiding(self)
		rider.checkImmersion(silent=silent)
		if actor is rider:
			actor.Print(rider+f"ride {-self}.",color="g" if contest else "w")
		if actor is not player:
			rider.printNearby(rider+f"rides {-self}.")
		return True


	# sever tethers and change location to new Container or Room
	def teleport(self,newParent):
		if newParent is self.parent:
			self.Print("You are already there.",color="w")
			return
		if self.carrier:
			self.carrier.removeCarry(self,silent=True,drop=False)
		self.removePlatform()
		self.clearCarrying()
		self.removeRiding()
		self.removeCover()
		self.clearCovering()
		self.clearOccupants() # should do nothing, but just in case
		self.waitInput("You teleport!",color="b")
		if newParent.canAdd(self):
			self.changeLocation(newParent)
		else:
			self.Print("Teleportation failed...",color="r")
		self.changePosture("stand")


	# finds the slot in which item resides, sets it to EmptyGear()
	# calls the item's unequip() method if it has one
	def unequip(self,slot,silent=False):
		assert slot in self.gear, f"'{slot}' is not a valid gear slot."
		I = self[slot]
		if I is EmptyGear():
			return False
		if I in self.carrying():
			self.removeCarry(I,silent=silent,drop=True)
		else:
			slotsEquipped = [s for s,item in self.gear.items() if item is I]
			for equipSlot in slotsEquipped:
				self[equipSlot] = EmptyGear()
			self.assignWeaponAndShield()
			if not silent:
				self.Print(f"You unequip {-I}.")
			I.unequip(self,slotsEquipped)
			self.display()


	### Behavior ###

	# take an action in the game according to regimen
	def Act(self):
		pass


	# dismount from current platform or riding creature
	def Dismount(self,posture=None,silent=False):
		if self.anchor() is None or self.platform is self.parent.floor:
			self.Print("You're not on anything.") if not silent else None
			return False
			
		occupyPrep = getattr(self.anchor(),"occupyprep","on")
		disoccupyPrep = "out of" if occupyPrep == "in" else "off"
		if self.riding:
			if not silent:
				self.Print(f"You get {disoccupyPrep} {-self.riding}.")
			self.removeRiding(silent=True)
		if self.platform and self.platform != self.parent.floor:
			if not silent:
				self.Print(f"You get {disoccupyPrep} {-self.platform}.")
			self.platform.disoccupy(self)

		if not (self.hasStatus("flying") or \
		self.immersed is not None and self.canSwim()):
			# self.parent.floor.occupy(self)
			self.platform = self.footing()
		if self.anchor() in (None,self.parent.floor):
			self.changePosture(posture,silent=True)
		return True


	# eat something
	def Eat(self,food):
		if not hasMethod(food,"consume"):
			self.Print(f"You can't eat {-food}.")
			return False
		oldParent = food.parent
		if oldParent is self:
			removed = self.remove(food,silent=True)
		elif isinstance(oldParent,Creature):
			self.Print(f"You can't eat {-food} from another Creature's Inventory.")
			return False
		else:
			removed = oldParent.exit(food)
		assert removed, f"Failed to remove {food} from {oldParent}"
		food.consume()


	def Emerge(self):
		if self.riding:
			return self.riding.Emerge()
		if not self.hasStatus("submerged"):
			self.Print("You are not submerged.")
			return False
		if self.immersed is None:
			self.Print("You aren't immersed in anything.")
			return False
		if isinstance(self.anchor(),Creature):
			self.Print(f"You can't surface independently while {self.position()}.")
			return False
		if not self.canSwim():
			self.Print("You can't surface because you can't swim!")
			return False
		if not self.immersed.canEmerge(self):
			self.Print("There isn't enough room to surface!")
			return False
		self.removeStatus("submerged")
		if self is not player:
			self.printNearby(self+"emerges.")
		if self.platform is not None:
			self.removePlatform()
		self.lastBreathed = game.time
		self.checkBreathing()
		self.checkImmersion()
		return True


	# hide behind an Item if it provides cover
	def Hide(self,I,posture):
		if self.carrier:
			return False

		if self.parent is not I.parent:
			self.Print(f"You can't, you are {self.parent.passprep} {-self.parent}.")
			return False
		if I is self.cover:
			self.Print(f"You are already hidden behind {-I}.")
			return False
		tip = " Try crouching." if posture != "crouch" else ""
		if I.availableCover(self) <= 0:
			self.Print(f"{+I} is too small to hide behind.{tip}")
			return False
		if I.fixed: # can't hide behind room fixtures
			self.Print(f"You can't hide behind {-I}.")
			return False
		if hasMethod(I,"HideBehind"):
			return I.HideBehind(self)

		oldPosture = self.posture()
		self.changePosture(posture,silent=True)
		if not self.addCover(I):
			self.changePosture(oldPosture,silent=True)
			return False
		self.Print(f"You {posture} behind {-I}.")
		return True


	# lick something
	def Lick(self,licker):
		# TODO: make creatures evade this or try to
		Print("Yuck!")


	# mount an Item or Creature, add it as platform or riding tether
	# or traverse if it is an open Container
	def Mount(self,anchor,posture="sit"):
		if anchor is self.anchor():
			if not self.changePosture(posture,silent=True):
				self.Print(f"You are already {self.posture()} on {-anchor}.")
				return False
		elif anchor is self.parent.floor and self.anchor() is not None:
			floats = self.hasStatus("flying") or \
				self.immersed is not None and self.canSwim()
			if not floats:
				return self.Dismount(posture=posture)
			if not self.Dismount(posture=posture):
				return False
		elif self.anchor() not in (None,self.parent.floor):
			self.Print(f"You can't, you are {self.position()}.")
			return False
		if not hasMethod(anchor,"ride") and not hasMethod(anchor,"occupy"):
			self.Print(f"{+anchor} cannot be mounted.")
			return False

		if anchor is not self.anchor() and hasMethod(anchor,"traverse") and \
		not getattr(anchor,"closed",False):
			if not getattr(anchor,"closed",True):
				self.Print(f"{+anchor} is open.")
			return anchor.traverse(self,verb=posture,dir="on")
		if anchor is self.platform or anchor is self.riding:
			pass
		else:
			if anchor == anchor.parent.floor:
				self.platform = anchor
			elif not anchor.occupy(self,posture=posture):
				return False

		if self.platform is anchor:
			self.Print(f"You {posture} on {-anchor}.")
		if self.platform is anchor or self.riding is anchor:
			self.removeCover()
			self.changePosture(posture,silent=True)
		return True


	# takes an item from a source location
	# checks if it can be obtained, removes from old parent, adds to inventory
	def ObtainItem(self,I,silent=False):
		assert isinstance(I,GameObject)
		oldParent = I.parent
		if isinstance(oldParent,Room): suffix = ""
		elif self in I.ancestors(): suffix = " from your " + oldParent.name
		elif oldParent: suffix = f" from {-oldParent}"
		else: suffix = ""
		itemCount = I.count(oldParent) if oldParent is not None else 1
		strname = I.nounPhrase('a' if itemCount > 1 else 'the')

		if self.canObtain(I,silent=silent):
			if oldParent:
				if isinstance(oldParent,Creature):
					removed = oldParent.remove(I,silent=True)
				else:
					removed = oldParent.exit(I)
				assert removed, f"Failed to remove {I} from {oldParent}"
			added = self.add(I)
			assert added, f"Failed to add {I} after successful obtain check"
			if not silent:
				self.Print(f"You take {strname}{suffix}.")
				if self is player:
					game.setPronouns(I)
			I.obtain(self)
			# check if hindered after obtaining item
			self.checkStatus()
			return True
		return False


	def Submerge(self):
		if self.riding:
			return self.riding.Submerge()
		if self.hasStatus("submerged"):
			self.Print("You are already submerged.")
			return False
		if self.immersed is None:
			self.Print("You aren't immersed in anything.")
			return False
		if not self.immersed.canSubmerge(self):
			self.Print(f"You can't submerge in {-self.immersed}, it's too shallow.")
			return False
		if not self.canSwim():
			self.Print("You can't submerge because you can't swim!")
			return False
		self.addStatus("submerged",source="IMMERSED")
		if self is not player:
			self.printNearby(self+"submerges.")
		self.checkImmersion()
		return True


	# throw a projectile at a target
	def Throw(self,missile,target,maxspeed=None):
		if missile is target:
			return False
		if missile in self.carrying():
			self.removeCarry(missile,silent=True,drop=False)
		else:
			if not self.parent.canAdd(missile):
				return False
			# first must be equipped in hand to throw
			self.equipInHand(missile)
			self.remove(missile,silent=True)
			entered = self.parent.enter(missile)
			assert entered, f"Failed to throw {missile} after successful admission check"

		missile = missile.asProjectile()

		# force is half STR, reduced by 1 for every 4*STR in missile weight
		# basically, its just reduced for the amount of weight the missile has
		force = min1(self.STR()//2) - bound((missile.Weight()//4)//self.STR(),0,10)
		if force <= 0:
			self.Print(f"{+missile} is too heavy to throw!")
			missile.asItem().fall()
			return False

		# bound by SPD; can only throw as fast as you can move
		speed = bound(diceRoll(1,force),1,self.SPD()+2)
		if maxspeed and speed > maxspeed:
			speed = maxspeed

		aim = self.ACCU()
		return missile.launch(speed,aim,self,target)


	### Statistics ###

	# sum of all trait modifiers from present conditions
	# (compounding conditions contribute once per entry)
	def statusModifier(self,trait):
		return sum(cond.modifies.get(trait,0) for cond in self.conditions())

	# the following are the player's traits, which can be modified by conditions
	def STR(self): return max(1, self.str + self.statusModifier("STR"))

	def SPD(self): return max(1, self.spd + self.statusModifier("SPD"))

	def SKL(self): return max(1, self.skl + self.statusModifier("SKL"))

	def STM(self): return max(1, self.stm + self.statusModifier("STM"))

	def CON(self): return max(1, self.con + self.statusModifier("CON"))

	def CHA(self): return max(1, self.cha + self.statusModifier("CHA"))

	def INT(self): return max(1, self.int + self.statusModifier("INT"))

	def WIS(self): return max(1, self.wis + self.statusModifier("WIS"))

	def FTH(self): return max(1, self.fth + self.statusModifier("FTH"))

	def LCK(self): return max(1, self.lck + self.statusModifier("LCK"))

	def LOVE(self): return bound(self.love + self.statusModifier("LOVE"),-100,100)

	def FEAR(self): return bound(self.fear + self.statusModifier("FEAR"),-100,100)

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details

	# combat: accu, atck, atsp, crit, dfns, evsn
	# contest: athl, endr, mvmt, slth, tnkr
	# stats/inv: brdn, mxhp, mxmp, spls
	# magic: cast, cssp, rstn, ritl
	# social: dcpt, prsd
	# info: invs, knwl,
	# misc: loot
	def ACCU(self): return 60 + 2*self.SKL() + self.LCK() + self.weapon.sleight

	def ATCK(self): return diceRoll(self.STR(), self.weapon.might, self.atkmod())

	def ATHL(self): return self.STR() + self.SKL() + self.STM()

	def ATSP(self): return min0(self.SPD() - min0(self.gripWeight()//4-self.STR()+10))

	def BRDN(self): return 12*self.CON() + 6*self.STR() + 3*self.FTH() + self.weight

	def CAST(self): return min0(self.WIS() + self.FTH() + self.INT() - self.gearToll())

	def CRIT(self): return (self.SKL() + self.LCK() + self.weapon.sharpness) // 2

	def CSSP(self): return min0(self.WIS() - self.invToll() - self.gearToll())

	def DCPT(self): return 2*self.CHA() + self.INT()

	def DFNS(self): return 2*self.CON() + self.protection()

	def ENDR(self): return 2*self.STM() + self.CON()

	def EVSN(self): return 10 if self.hasStatus(("sitting","laying")) \
	else 2*self.ATSP() + self.LCK() + self.SPD()

	def INVS(self): return 2*self.INT() + self.WIS()

	def KNWL(self): return 2*self.INT() + self.LCK()

	def LOOT(self): return 2*self.LCK() + self.FTH()

	def MVMT(self): return min0(self.SPD() + self.STM() + 10 - \
	self.invToll() - self.gearToll()) // (2 if self.hasStatus("hindered") else 1)

	def MXHP(self): return self.level()*self.CON() + (self.level()//10+1) * self.STM() + 1

	def MXMP(self): return self.level()*self.WIS() + (self.level()//10+1) * self.STM() + 1

	def PRSD(self): return 2*self.CHA() + self.WIS()

	def RSTN(self): return 2*self.FTH() + self.STM()

	def RITL(self): return 2*self.FTH() + self.LCK()

	def SLTH(self): return min0(2*self.SKL() + self.INT() - self.invToll()) + \
	self.coverBonus()

	def SPLS(self): return 3*self.INT()

	def TNKR(self): return 2*self.INT() + self.SKL()


	# TODO: add logic here for conditions which improve atkmod
	def atkmod(self):
		return 0


	# for Creatures, level is determined by rating
	def level(self):
		return ((self.rating() - 10) // 10) + 1


	# rating is sum of all base stats
	def rating(self):
		return self.str + self.spd + self.skl + self.stm + self.con + \
		self.cha + self.int + self.wis + self.fth + self.lck


	### Getters ###

	# Creature is anchored to either riding, carrier, or platform
	# only one of these may be non-None at a time.
	def anchor(self):
		assert sum(a is not None for a in (self.riding, self.carrier, self.platform)) <= 1
		for a in (self.riding, self.carrier, self.platform):
			if a is not None:
				return a
		return None


	# return the creature wrapped in a projectile object for temporary use
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.DFNS(),self.composition,
		self.weight//4,0,"b",item=self,pronoun=self.pronoun)


	# check if item can fit in inventory, print relevant refusal msg if not
	def canObtain(self,I,silent=False):
		refusal = None
		if isinstance(I,Serpens):
			pass
		elif isinstance(I,Creature) or I.fixed:
			refusal = f"You can't put {-I} in your Inventory."
		elif I in self:
			refusal = f"You already have {-I} in your Inventory."
		elif I in self.ancestors():
			refusal = f"You can't take {-I}. You're within {I.pronoun}."
		elif I is self.anchor():
			refusal = f"You can't take {-I}. You're on {I.pronoun}."
		elif I.occupants():
			refusal = f"You can't take {-I}. It's occupied."
		elif self.invWeight() + I.Weight() > 2*self.BRDN():
			refusal = f"You can't hold {-I}. Your Inventory is too full."
		if refusal:
			if not silent:
				self.Print(refusal)
				if self is player:
					game.setPronouns(I)
			return False
		return True


	# checks if Creature can swim based on gear, weight ATHL, and MVMT
	def canSwim(self,fluid=None):
		if fluid is None:
			fluid = self.immersed
		fluidComposition = fluid if isinstance(fluid,str) else \
			getattr(fluid,"composition",None)
		liquidDensity = Data.Material.get(fluidComposition).density

		if not self.canMove():
			return False
		buoyancy = 10*liquidDensity+10
		return self.Weight()+self.gearWeight() <= self.ATHL()+self.MVMT()+buoyancy


	# Creature may despawn if it is dead, it is midnight, not in current room,
	def canDespawn(self):		
		return self.despawnTimer is not None and \
			self.despawnTimer <= 0 and \
			percentChance(-self.despawnTimer//10) and \
			game.hour() == "serpent" and \
			isinstance(self.parent,Room) and \
			self.parent is not game.currentroom and \
			not self.fixed


	# returns True if Creature can move (not restrained, paralyzed, etc)
	def canMove(self):
		if self.MVMT() == 0:
			return False
		return self.isAlive() and not any(cond.immobile for cond in self.conditions())


	# return whether current cargo plus an optional Creature fits the cargo limit
	def canCarryWeight(self,creature=None,currentWeight=None):
		assert creature is None or isinstance(creature,Creature)
		weight = self.carryWeight() if currentWeight is None else currentWeight
		if creature is not None:
			weight += creature.Weight()
		return weight <= self.BRDN()//2


	# return unique Creatures occupying carry slots
	def carrying(self):
		return list(dict.fromkeys(self[slot] for slot in self.carrySlots \
			if isinstance(self[slot],Creature)))


	# returns weight of carried creature, or 0 if none
	def carryWeight(self):
		return sum(carried.Weight() for carried in self.carrying())


	# return current riders sorted largest first
	def riders(self):
		return [occupant for occupant in self.occupants() \
			if isinstance(occupant,Creature) and occupant.riding is self]


	# return space available for riding, optionally excluding an existing rider
	def ridingSpace(self,rider=None):
		assert rider is None or isinstance(rider,Creature)
		return self.Size() - self.occupantsSize(exclude=rider)


	# for Creatures, contents is the inventory. This is used in objQuery()
	def contents(self):
		return self.inv


	# cover bonus equals how much bigger the available cover is than the creature
	def coverBonus(self):
		return min0(self.cover.availableCover(self)) if self.cover else 0


	# gear toll is 1/4 how much the gearWeight exceeds CON
	def gearToll(self):
		return min0(self.gearWeight()//4 - self.CON())


	# sum of the weight of all items in player gear
	def gearWeight(self):
		return sum(I.Weight() for I in set(self.gear.values()))


	# returns the sum of the weight of all items being held
	def gripWeight(self):
		gripped = {self[slot] for slot in self.gripSlots}
		return sum(item.Weight() for item in gripped)


	# returns number of allies creature can see
	def hasAlliesPresent(self):
		pass


	# returns number of enemies creature can see
	def hasEnemiesPresent(self):
		pass


	# looks through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inGear(self,term):
		for slot,object in self.gear.items():
			if nameMatch(term,object) or term.lower() == slot.lower():
				return slot, object
		return None, None


	# return all Items in Inventory whose name matches term, otherwise return None
	def inInv(self,term):
		if term.startswith("my "):
			term = term[3:]
		return [obj for obj in self.inv if nameMatch(term,obj)]


	# Inventory toll is how much the Inventory weight exceeds BRDN
	def invToll(self):
		return min0(self.invWeight() - self.BRDN())


	# returns sum of the weight of all Items in the Inventory
	def invWeight(self):
		return sum(item.Weight() for item in self)


	# Creature is alive if despawnTimer is None
	def isAlive(self):
		return self.despawnTimer is None


	# returns True if Creature has less than 1/3 health
	def isBloodied(self):
		pass

	
	# returns True if Creature is not wearing any pants
	def isNaked(self):
		if self['legs'] == EmptyGear():
			return True


	# returns True if Creature is friendly to player
	def isFriendly(self):
		return self.hasStatus("tamed")


	# plan the gear and cargo displaced when carrying a Creature
	def planCarrySlots(self,creature,forceUnequip=False):
		assert isinstance(creature,Creature)
		slotsNeeded = creature.gripsNeeded(self)
		if slotsNeeded > len(self.carrySlots) or \
		not self.canCarryWeight(creature,currentWeight=0):
			return None

		# use these to count what slots would be available if we unequip or drop items
		toUnequip = []
		toDrop = []
		slotAvailable = lambda slot: self[slot] is EmptyGear() \
			or self[slot] in toUnequip or self[slot] in toDrop

		# start by counting slots that are already empty
		availableSlots = [slot for slot in self.carrySlots if slotAvailable(slot)]
		if not forceUnequip and (len(availableSlots) < slotsNeeded or \
		not self.canCarryWeight(creature)):
			return None

		# determine which items need to be unequipped to free up enough carry slots
		for slot in self.carrySlots:
			if len(availableSlots) < slotsNeeded:
				item = self[slot]
				if item is EmptyGear() or isinstance(item,Creature) or item in toUnequip:
					continue
				toUnequip.append(item)
				availableSlots = [slot for slot in self.carrySlots if slotAvailable(slot)]

		# drop creatures until both the slot and total cargo limits are satisfied
		carried = sorted(self.carrying(),key=lambda obj:obj.Weight())
		plannedCargoWeight = self.carryWeight()
		for carriedCreature in carried:
			if len(availableSlots) < slotsNeeded or \
			not self.canCarryWeight(creature,currentWeight=plannedCargoWeight):
				toDrop.append(carriedCreature)
				plannedCargoWeight -= carriedCreature.Weight()
				availableSlots = [slot for slot in self.carrySlots if slotAvailable(slot)]

		# return what unequips and drops are needed and the slots made available by them
		assert len(availableSlots) >= slotsNeeded
		assert self.canCarryWeight(creature,currentWeight=plannedCargoWeight)
		return {"slots":availableSlots[:slotsNeeded],"unequip":toUnequip,"drop":toDrop}

	# use posture and tethers to determine position description
	def position(self,ignoreStanding=False,includeParent=False):
		pos = ""
		floor = getattr(self.parent,"floor",None)
		if self.immersed is not None and self.immersed is floor:
			fluidPosition = "on the surface"
		elif self.immersed not in (None,self.parent):
			fluidPosition = f"in {-self.immersed}"
		else:
			fluidPosition = ""
		# if self.carrier:
		# 	pos += f"being carried by {~self.carrier}"
		if self.riding:
			pos += f"riding {~self.riding}"
		elif self.platform:
			pos += self.posture()
			if fluidPosition:
				pos += f" {fluidPosition}"
			waterwalking = self.hasStatus("waterwalking") and \
				self.platform is floor and floor.material().liquid
			if self.platform is not floor or waterwalking:
				occupyprep = getattr(self.platform,"occupyprep","on")
				pos += f" {occupyprep} {-self.platform}"
		else:
			pos = "floating"
		if fluidPosition and self.platform is None:
			pos += f" {fluidPosition}"
		if self.cover:
			pos += f" behind {-self.cover}"
		if ignoreStanding and pos == "standing":
			pos = ""
		if includeParent and not isinstance(self.parent,Room) and \
		self.parent is not self.immersed:
			pos += f" in {-self.parent}"
		return pos


	# get posture from status and anchor
	def posture(self):
		if self.anchor() is None:
			return "floating"
		for pos in ("laying","sitting","crouching"):
			if self.hasStatus(pos):
				return pos
		return "standing"


	# returns sum of all protection values of all items in gear
	def protection(self):
		return sum(getattr(item,"prot",0) for item in set(self.gear.values()))


	# size is normally equal to weight, but halved if not standing
	def Size(self,posture=None):
		if posture is None:
			posture = self.posture()
		size = self.weight
		if posture in ("crouching","sitting","laying"):
			size //= 2
		return size


	# total size includes size of those riding and those being carried by Creature
	def totalSize(self):
		ridersSize = sum(r.totalSize() for r in self.occupants())
		carrySize = sum(carried.totalSize() for carried in self.carrying())
		return self.Size() + ridersSize + carrySize

	# returns list of all weapons in inventory
	def weapons(self):
		return [I for I in self if isinstance(I,Weapon)]


	# total weight includes those riding and those being carried by Creature
	def Weight(self):
		ridersWeight = sum(r.Weight() for r in self.occupants())
		carryWeight = sum(carried.Weight() for carried in self.carrying())
		return self.weight + ridersWeight + carryWeight


	### User Output ###

	# returns name to display in stats panel
	def displayName(self):
		return self.nounPhrase()


	def tethersDescription(self,name=None,allowRiding=True,allowCarrying=True):
		if not name:
			name = self.name
		tethersMsgs = []
		if self.carrying() and allowCarrying:
			tethersMsgs.append(listObjects("carrying ",self.carrying()))
		occupants = self.occupants()
		if occupants and allowRiding:
			if len(occupants) < 3:
				tethersMsgs.append(listObjects("being ridden by ",occupants))
			else:
				tethersMsgs.append(f"being ridden by {len(occupants)} creatures")
		return f" {' and '.join(tethersMsgs)}" if tethersMsgs else ""


	# describe the creature, including tethers
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		# tethersMsgs = []
		# if self.carrying():
		# 	tethersMsgs.append(f"carrying {-self.carrying()}")
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		# if tethersMsgs:
		# 	Print(f"It is {' and '.join(tethersMsgs)}.")


	# intelligently get name of this Item in various grammatical forms
	def nounPhrase(self,det="",n=-1,plural=False,cap=-1,includePosture=False):
		strname = self.descname
		# if self.riding and det != "the":
		# 	strname = f"{strname} on {self.riding.nounPhrase()}"
		# self.parent.floor causes error when displacing
		# elif self.platform not in (None,self.parent.floor) and det != "the":
		# 	strname = f"{strname} {self.posture()} on {-self.platform}"
		# position = self.position(ignoreStanding=True)
		indefinite = det == "a" or det == "" and n == 1 and \
			self.definiteDeterminer() != "your"
		if indefinite and self.determiner != "your":
			strname = strname + self.tethersDescription(allowCarrying=False)
			# if position == "floating":
			# 	if self.anchor() is None:
			# 		strname = "floating " + strname
			# elif position != "":
			# 	strname = f"{strname} {position}"

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if includePosture:
			strname = f"{self.posture()} {strname}"
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "your" if self.definiteDeterminer() == "your" else "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# this is used as a shortcut to show output only to the user
	# It should do nothing for any other creature
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
		   outfile=None):
		# in godmode we can see all prints
		if game.mode == 2:
			args = (f"[{self.id} {self.name}]:",) + args
			color="k"
			return Print(*args,end=end,sep=sep,delay=delay,color=color,
			allowSilent=allowSilent,outfile=outfile)
		return False


	# get reflexive pronoun
	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"



# The Player mostly behaves like a normal Humanoid Creature,
# but it has an xp to track leveling up, and RP to track reputation
class Player(Creature):
	def __init__(self,name,desc,weight,traits,xp,rp,spells=None,pronoun="him",**kwargs):
		self.xp = xp
		self.rp = rp
		self.spells = spells if spells else []
		super().__init__(name,desc,weight,traits,pronoun=pronoun,**kwargs)


	### Dunder Methods ###

	def __neg__(self):
		return "you"


	def __pos__(self):
		return "You"


	def __invert__(self):
		return "you"


	def subjective(self):
		return "you"


	def reflexive(self):
		return "yourself"


	### File I/O ###

	def convertToJSON(self):
		jsonDict = super().convertToJSON()
		if self.parent is None and self.anchor() is None:
			del jsonDict["platform"]
		# these lines seem redundant
		# (the menu functions handle parent and __class__ attributes)
		# but they are needed because player is read from its own file
		if "parent" in jsonDict:
			del jsonDict["parent"]
		jsonDict["__class__"] = self.__class__.__name__
		return jsonDict


	### Operation ###

	def awaken(self,wellRested=True):
		game.silent = False
		delay(1)
		waitInput("You wake up!",color="o")
		if wellRested:
			self.lastSlept = game.time
			self.checkTired()
		game.startUp()


	def traitMenu(self,QP,prompt="",warning="",nReturn=8):
		movePrintCursor(nReturn+1,clear=(QP+1)%10==0) # clear lingering extra digits
		nRowsPrinted = self.printTraits()
		# backtrack to clear any extra rows from printTraits
		movePrintCursor(1,clear=False)
		movePrintCursor(-2,clear=True)
		displayQP = ambiguateNumbers(QP) if self.hasStatus("stupidity") else QP
		Print(f"Quality Points:	{displayQP}",end="",delay=0)
		movePrintCursor(-1,clear=True)
		Print(prompt,end="",delay=0)
		movePrintCursor(-1,clear=True)
		Print(warning,end="",delay=0)
		movePrintCursor(-1,clear=True)
		if prompt.endswith("?"):
			return Input(cue="> ",delay=0), nRowsPrinted + 4
		waitInput()
		return "", nRowsPrinted + 4


	def gainQP(self,QP):
		Print("\n"*8)
		warning = ""
		rowsPrinted = 7
		while QP > 0:
			trait, rowsPrinted = self.traitMenu(QP,"What trait will you improve?",
			warning,rowsPrinted)
			if trait not in Data.traits:
				if trait == "":
					warning = ""
				else:
					warning = "That's not a trait you can improve."
				continue
			# increment corresponding player trait
			traitval = getattr(self,trait)
			if traitval >= 20:
				warning = f"Your {trait} cannot be raised any higher."
				continue
			warning = ""
			setattr(self,trait,traitval+1)
			QP -= 1
			self.display()
		self.traitMenu(0,"You have no more QP.","",rowsPrinted)
		movePrintCursor(8,clear=True)


	# player gets 1 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		displayLevel = "something" if self.hasStatus("stupidity") else newlv
		waitInput(f"You leveled up to level {displayLevel}!",color="g")
		clearScreen()
		self.gainQP(newlv-oldlv)
		game.startUp()
		self.checkStatus()


	def updateReputation(self,repMod):
		self.rp = bound(repMod,-100,100)


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		if self.hasStatus("apathy"):
			newxp = 0
		Print(f"You gained {newxp} xp.",color="g")
		self.xp += newxp
		# Print(f"You have {self.xp}")
		newlv = self.level()
		if oldlv != newlv:
			self.levelUp(oldlv,newlv)


	def checkHungry(self):
		# being invigorated prevents hunger but not starving
		invigorated = self.hasStatus("invigorated")
		# hunger takes longer with more endurance
		sinceLastAte = game.time - self.lastAte
		if sinceLastAte > 100 + 10*self.ENDR():
			self.removeStatus("hungry")
			self.addStatus("starving")
		elif sinceLastAte > 50 + 5*self.ENDR() and not invigorated:
			self.addStatus("hungry")
		elif sinceLastAte < 100:
			self.removeStatus("starving")
			self.removeStatus("hungry")
		elif invigorated:
			self.removeStatus("hungry")			


	def checkTired(self):
		# being invigorated prevents tired and fatigue
		invigorated = self.hasStatus("invigorated")
		# sleep deprivation takes longer with more endurance
		sinceLastSlept = game.time - self.lastSlept
		if sinceLastSlept > 300 + 40*self.ENDR() and not invigorated:
			self.removeStatus("tired")
			self.addStatus("fatigued")
		elif sinceLastSlept > 150 + 20*self.ENDR() and not invigorated:
			self.addStatus("tired")
		elif sinceLastSlept < 100 or invigorated:
			self.removeStatus("fatigued")
			self.removeStatus("tired")


	# called when player hp hits 0
	def death(self):
		self.timeDespawn()
		Print("You have died!",color="r")
		self.changePosture("laying",silent=True)
		ellipsis(color="r")

		anointed = self.hasStatus("anointed")
		# add dead first: its onGain hooks clear hunger/tiredness and its
		# blocks prevent the status checks below from re-deriving them
		self.addStatus("dead")
		# death removes any permanent statuses, you are refreshed
		self.removeStatus(reqSource="PERMANENT",silent=True)
		self.changePosture("laying",silent=True)
		if anointed:
			return self.reanimate()
		# a true death releases the statuses you were sustaining
		self.releaseBoundStatuses()

		self.removeRiding(silent=True)
		self.clearCarrying(silent=True)

		waitInput()
		return True


	def dualAttack(self,target):
		Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if percentChance(hit):
			crit = percentChance(self.CRIT())
			attack = self.ATCK()
			if crit:
				waitInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("Aw it missed.")
		waitInput()


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!",color="o")
		for i in range(n):
			if n > 1:
				waitInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if percentChance(hit):
				crit = percentChance(self.CRIT())
				attack = self.ATCK()
				if crit:
					waitInput("Critical hit!",color="o")
					self.weapon.dull(1)
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				Print("Aw it missed.")
			waitInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def attackItem(self,target):
		# TODO determine damage type here instead of always bludgeoning
		attack = self.ATCK()
		return target.takeDamage(attack,"b")


	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.Size(),1,99)
		if canCatch and percentChance(catch):
			missileItem = missile.asItem()
			Print(f"You catch {-missileItem}!",color="o")
			self.ObtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"You fail to catch {-missile}.")
			return False


	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			if yesno(f"Will you try to catch {-missile}?"):
				dodge = -10
				if self.Catch(missile):
					return True
		if percentChance(bound(missile.aim+missile.speed-dodge,1,99)):
			return missile.collide(self)
		return False


	### Getters ###

	# Player can't navigate if they are blind/stupid or
	# if the sun is not visible and they have no compass
	def canNavigate(self):
		location = self.parent
		if self.hasStatus("sagacity"):
			return True
		if location is None or self.hasStatus(("blindness","stupidity")):
			return False
		return self.countCompasses() > 0 or (self.canSeeSky() and "sun" in location)


	def canSeeSky(self,location=None):
		if location is None:
			location = self.parent
		if self.hasStatus("blind"):
			return False
		# may look from a given location rather than a real location
		if location.surroundings(includeSelf=True).ceiling:
			return False
		return True


	# count number of compasses in Inventory
	def countCompasses(self):
		return len([item for item in self.inv if isinstance(item,Compass)])


	# check status conditions and refresh stats display
	def checkStatus(self):
		super().checkStatus()
		self.display()


	# weird formula right? returns a positive number rounded down to nearest int
	# also note that the level must be between 1 and 100
	def level(self):
		return bound(floor(sqrt(self.xp/2)),1,100)


	# query is overridden here, other nameQuery() methods don't search within Player
	def nameQuery(self,term,d=2):
		term = term.lower()
		key = lambda obj: nameMatch(term,obj)
		return self.query(key=key,d=d)


	# query is overridden here, other query() methods don't search within Player
	def query(self,key=None,d=2):
		matches = objQuery(self,key=key,d=d)
		return matches


	### User Output ###

	# takes args because interpreter passes them
	def display(self,*args):
		sidepanel.clear()
		if self.hasStatus("asleep"):
			return self.Print("...",color="k",outfile=sidepanel)
		self.printStats(outfile=sidepanel)
		Print(outfile=sidepanel)

		self.printTraits(outfile=sidepanel)
		self.printGear(outfile=sidepanel)

		if len(self.status) > 0:
			self.Print(outfile=sidepanel)
			self.printStatus(outfile=sidepanel)

		tethersDisplay  = ""
		if self.parent and self.platform is not None and self.platform != self.parent.floor:
			occuprep = getattr(self.platform,"occupyprep","on")
			tethersDisplay += f"\n{occuprep.capitalize()} {self.platform.name}"
		if self.carrying():
			tethersDisplay += "\n" + listObjects("Carrying ",self.carrying())
		if self.riding is not None:
			tethersDisplay += f"\nRiding {self.riding}"
		if tethersDisplay:
			self.Print(tethersDisplay, outfile=sidepanel)

		self.Print(outfile=sidepanel)
		self.printInv(outfile=sidepanel)


	# print each trait's modified value, colored green if it's above the
	# static trait value and red if below
	def displayTrait(self,t):
		assert hasattr(self,t.lower()) and hasMethod(self,t.upper())
		displayTrait = t.upper() + ": "+ str(getattr(self,t.upper())())

		if self.hasStatus("stupidity"):
			displayTrait = ambiguateNumbers(displayTrait)
		if getattr(self,t.lower()) < getattr(self,t.upper())():
			displayTrait = tinge("g",displayTrait)[0]
		if getattr(self,t.lower()) > getattr(self,t.upper())():
			displayTrait = tinge("r",displayTrait)[0]

		return displayTrait


	def nounPhrase(self,det="",n=-1,plural=False,cap=-1,includePosture=False):
		strname = f"{self.posture()} you" if includePosture else "you"
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# takes args because interpreter passes them
	def openDisplay(self,*args):
		if not sidepanel.isOpen():
			sidepanel.open(self.name)
			self.display()
		else:
			self.display()
			self.Print(f"Your stats panel is already open.",color="k")


	# This method does nothing for non-player creatures
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
		outfile=None):
		return Print(*args,end=end,sep=sep,delay=delay,color=color,
		allowSilent=allowSilent,outfile=outfile)


	# prints a single ability or all abilities if ability is None
	def printAbility(self,ability=None):
		if ability == "ATCK":
			Print(f"ATCK: {self.weapon.might*self.STR()}")
		elif ability is not None:
			Print(f"{ability}: {getattr(self,ability)()}")
		else:
			for ability in Data.abilities:
				self.printAbility(ability.upper())


	# takes args because interpreter passes them
	def printCarrying(self,*args,silent=False,outfile=None):
		if self.carrying():
			Print(listObjects("You are carrying ",self.carrying(),"."), outfile=outfile)
		elif silent is False and outfile is None:
			Print("You aren't carrying anything.")


	# print each player gear slot and the items equipped in them
	def printGear(self,*args,outfile=None):
		Print(outfile=outfile)
		if outfile is sidepanel:
			slots = tuple(self.gear)
			midpoint = (len(slots)+1)//2
			leftSlots = slots[:midpoint]
			rightSlots = slots[midpoint:]
			labelWidth = max(len(slot) for slot in slots) + 1
			gearEntry = lambda slot: \
				f"{slot + ':':<{labelWidth}} {self[slot].displayName()}"
			gearEntries = []
			for idx,leftSlot in enumerate(leftSlots):
				gearEntries.append(gearEntry(leftSlot))
				if idx < len(rightSlots):
					rightSlot = rightSlots[idx]
					gearEntries.append(gearEntry(rightSlot))
				else:
					gearEntries.append("")
			maxColWidth = (sidepanel.width-1)//2
			colWidth = min(maxColWidth,
				max(15,max(displayLength(entry) for entry in gearEntries) + 1))
			columnPrint(gearEntries,2,w=colWidth,outfile=outfile)
			return
		for slot in self.gear:
			val = self[slot].displayName()
			Print(slot + ":\t" + val,outfile=outfile)

	# takes args because interpreter passes them
	def printHP(self,*args): Print(f"HP: {self.hp}/{self.MXHP()}",color="r")

	# prints player inventory
	def printInv(self,*args,outfile=None):
		cols = 8 if outfile is None else 4
		W = self.invWeight()
		color = "o" if W / self.BRDN() > 0.80 else "w"
		color = "r" if W > self.BRDN() else color
		displayInvWeight = f"Inv Weight: {W}/{self.BRDN()}"
		if self.hasStatus("stupidity"):
			displayInvWeight = ambiguateNumbers(displayInvWeight)
		Print(displayInvWeight, color=color, outfile=outfile)
		if len(self.inv) == 0:
			if outfile is None:
				Print("Your Inventory is empty.")
		else:
			displayInv = self.inv
			if outfile is not None:
				displayInv = [n for n in displayInv if n not in self.gear.values()]
			baggedObjects = bagObjects(displayInv, equivKey=lambda x: x.displayName())
			invDisplayNames = [I.displayName(c) for I,c in baggedObjects]
			if self.hasStatus("stupidity"):
				invDisplayNames = [ambiguateNumbers(name) for name in invDisplayNames]
			invDisplay = "   ".join(invDisplayNames)
			Print(invDisplay, outfile=outfile, delay=0)


	# takes args because interpreter passes them
	def printLV(self,*args): Print(f"LV: {self.level()}",color="o")

	# takes args because interpreter passes them
	def printMoney(self,*args): Print(f"Â§ {self.money}",color="g")

	# takes args because interpreter passes them
	def printMP(self,*args): Print(f"MP: {self.mp}/{self.MXMP()}",color="b")

	# takes args because interpreter passes them
	def printPosition(self,*args): Print(f"You are {self.position(includeParent=True)}.")

	# takes args because interpreter passes them
	def printRiding(self,silent=False,*args):
		if self.riding:
			Print(f"You are riding {~self.riding}.")
		elif silent is False:
			Print("You aren't riding anything.")

	# takes args because interpreter passes them
	def printRP(self,*args): Print(f"RP: {self.rp}/100",color="y")

	# takes args because interpreter passes them
	def printSpells(self,*args):
		Print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			Print("You don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self, *args, outfile=None):
		name = self.name
		if len(name) > 45:
			name = name[:42] + "..."
		stats = [name,f"LV: {self.level()}",f"Â§ {self.money}",
		   f"RP: {self.rp}/100",f"HP: {self.hp}/{self.MXHP()}",
		   f"MP: {self.mp}/{self.MXMP()}"]
		colors = ["w","o","g","y","r","b"]
		if self.hasStatus("insanity") and outfile is None:
			shuffle(colors)
		if self.hasStatus("apathy"):
			colors = ["w"]*len(colors)
		if self.hasStatus("stupidity"):
			stats = [ambiguateNumbers(stat) for stat in stats]
		colWidth = max(displayLength(stat) for stat in stats) + 2
		nCols = max(1,min(3,(sidepanel.width-1) // colWidth))
		stats = [tinge(colors[i],stats[i])[0] for i in range(len(stats))]
		columnPrint(stats,nCols,w=colWidth,outfile=outfile)


	# prints all status conditions and their durations in a formatted table
	# conditions with no duration (indefinite) are represented with "--"
	def printStatus(self, *args, outfile=None):
		conditions = []
		durations = []
		# populate conditions with unique, displayable condition names
		# populate durations with the highest duration for that condition
		# indefinite (None) durations take precedence over timed ones
		for cond, src, dur in sorted(self.status, key=lambda x: x[0]):
			if not Data.StatusCondition.get(cond).displayable:
				continue
			if cond in conditions:
				idx = conditions.index(cond)
				chosenDur = durations[idx]
				if chosenDur is not None:
					durations[idx] = None if dur is None else max(dur,chosenDur)
				continue
			conditions.append(cond)
			durations.append(dur)

		if len(conditions) == 0:
			Print("None")
			return

		# display indefinite durations as "--", adjust length according to max digit length
		displayDurs = ["--" if dur is None else str(dur) for dur in durations]
		if self.hasStatus("stupidity"):
			displayDurs = [ambiguateNumbers(dur) for dur in displayDurs]
		nDigits = max(len(dur) for dur in displayDurs)
		displayDurs = ["-"*nDigits if dur=="--" else dur for dur in displayDurs]

		# pad to align and color conditions and their durations for display
		nChars = max([len(condname) for condname in conditions])
		statusDisplay = []
		for i,condition in enumerate(conditions):
			padding = " "*(nChars-len(condition)+2)
			displayCondition = condition + padding + displayDurs[i]
			if self.hasStatus("stupidity"):
				displayCondition = ambiguateNumbers(displayCondition)

			color = Data.StatusCondition.get(condition).color or "w"
			if self.hasStatus("apathy") and condition != "apathy":
				color = "w"
			statusDisplay.append(tinge(color,displayCondition)[0])

		# nCols = min(3,((len(statusDisplay)-1)//5)+1)
		nCols = 2 if len(statusDisplay) > 5 else 1
		columnPrint(statusDisplay,nCols,outfile=outfile)


	# prints all 10 player traits
	# returns number of lines printed
	def printTraits(self,trait=None,outfile=None):
		if trait == None:
			traits = [self.displayTrait(t) for t in Data.traits]
			colWidth = max(displayLength(trait) for trait in traits) + 2
			nCols = max(1,min(5,(sidepanel.width-1) // colWidth))
			return columnPrint(traits,nCols,w=colWidth,outfile=outfile)

		Print(self.displayTrait(trait))
		return 1

	# takes args because interpreter passes them
	def printXP(self,*args): Print(f"XP: {self.xp}",color="o")

	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self, *args):
		if len(self.weapons()) == 0:
			Print("You have no weapons.")
		else:
			columnPrint(self.weapons(),12,12)


	# This method does nothing for non-player creatures
	def waitInput(self,text=None,**kwargs):
		return waitInput(text,**kwargs)




##########################
## SUBCLASS DEFINITIONS ##
##########################


class Humanoid(Creature):
	### Operation ###

	# attack another creature
	def attackCreature(self,target):
		Print(f"{+self} tries to attack {-target}.",color="o")

		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!")
		for i in range(n):
			if n > 1:
				target.waitInput(f"\n {+self}'s {ordinal(i+1)} attack on {target}:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if percentChance(hit):
				crit = percentChance(self.CRIT())
				attack = self.ATCK()
				if crit:
					target.waitInput("Critical hit!",color="o")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				self.Print("It missed!")
			# target.waitInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	# attack with a second hand item
	def dualAttack(self,target):
		self.Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if percentChance(hit):
			crit = percentChance(self.CRIT())
			attack = self.ATCK()
			if crit:
				self.waitInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("It missed!")
		self.waitInput()


	### Behavior ###

	# perform action on Creature's turn
	def Act(self):
		if not self.isAlive():
			return
		self.printNearby(f"\n{self.name}'s turn!",self.id,color="k")
		if self.canMove():
			self.Attack()


	# attack something
	def Attack(self):
		if not self.canMove():
			return
		select = lambda obj: isinstance(obj,Creature) and obj is not self
		targets = [obj for obj in self.parent if select(obj)]
		if self.parent is player.parent:
			targets += [player]
		if len(targets) > 0:
			target = choice(targets)
			return self.attackCreature(target)
		return False


	# try to catch a projectile
	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.Size(),1,99)
		if canCatch and percentChance(catch):
			missileItem = missile.asItem()
			Print(f"{+self} catches {-missileItem}!",color="o")
			self.ObtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"{+self} fails to catch {-missile}.")
			return False


	### Getters ###

	# returns True is monster has healing potion or food
	def hasHealing():
		pass


	# returns True if self is armed
	def isArmed():
		pass


	### User Output ###

	# describe the humanoid, including gear
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		gearKey = lambda item: not isinstance(item,(EmptyGear,Creature))
		gearitems = [item for item in self.gear.values() if gearKey(item)]
		if len(gearitems) != 0:
			self.Print(listObjects("It has ", gearitems,"."))
		# tethersMsgs = []
		# if self.carrying():
		# 	tethersMsgs.append(f"carrying {-self.carrying()}")
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		# if tethersMsgs:
		# 	Print(f"It is {' and '.join(tethersMsgs)}.")



# Speakers are Creatures that can talk
# they have a dialogue tree (taken from Dialogue.json or constructed as a default tree)
# upon meeting the player they will take a firstImpression()
# and every encounter with them after that they will perform appraise()
class Speaker(Creature):
	def __init__(self,name,desc,weight,traits,dlogName=None,dlogTree=None,rapport=0,
	lastParley=None,**kwargs):
		super().__init__(name,desc,weight,traits,**kwargs)
		self.dlogName = self.name if dlogName is None else dlogName
		self.dlogTree = dlogTree
		self.rapport = rapport
		self.lastParley = lastParley


	### File I/O ###

	# build dialogue tree from dlogName in game.dlogForest
	def buildDialogue(self):
		# dlogTree actually just records the visitCounts & checkpoint when written to json
		dlogRefs = self.dlogTree
		self.dlogTree = game.dlogForest["trees"][self.dlogName].copy()
		if dlogRefs:
			self.dlogTree.visitCounts = dlogRefs["visitCounts"]
			self.dlogTree.checkpoint = dlogRefs["checkpoint"]
		self.dlogTree.ensureIntegrity(self)


	### Operation ###

	# get an impression of the player
	def firstImpression(self,partner):
		# TODO: add this
		print(self.name, "impression")
		# adjust love, fear from person baselines
		self.memories.add("met")
		self.updateLove(partner.rp)
		self.updateFear(partner.rp)


	# appraise the player upon talking
	def appraise(self,partner):
		if self.lastParley is None:
			self.lastParley = game.time
		elif game.time - self.lastParley > 100:
			self.dlogTree.newParley()
		self.lastParley = game.time
		if partner.isNaked():
			self.appraisal.add("naked")


	### Interaction ###

	# talk to this speaker
	def converse(self,partner):
		if "met" not in self.memories:
			self.firstImpression(partner)
		self.appraise(partner)
		if not self.dlogTree.visit(self):
			Print(f"{self.name} says nothing...")


	# offer something to this speaker
	def offer(self,I):
		# Offers transfer an Item directly from one Creature's inventory to another.
		assert isinstance(I.parent,Creature), f"Offered Item {I} is not Creature-owned"
		if not self.canObtain(I):
			Print(f"{+self} can't carry any more!")	
		elif self.dlogTree.react("offer",self,I=I):
			# if we fail to obtain item for whatever reason, drop it into room
			if not self.ObtainItem(I):
				if I.parent is not game.currentroom and game.currentroom.canAdd(I):
					if I.parent:
						I.parent.remove(I)
					entered = game.currentroom.enter(I)
					assert entered, f"Failed to drop rejected offer {I}"
		else:
			Print(f"{+self} ignores your offer.")			
		return True



# People are Speakers that are Humanoid
class Person(Speaker,Humanoid):
	def __init__(self,name,descname,weight,traits,pronoun,spells=None,desc=None,
	isChild=False,**kwargs):
		super().__init__(name,"",weight,traits,descname=descname,pronoun=pronoun,**kwargs)
		self.spells = spells if spells else []
		if desc:
			self.desc = desc
		else:
			prefix = "An " if self.descname[0] in Data.vowels else "A "
			self.desc = prefix + self.descname

		if self.pronoun == "him":
			if isChild:
				self.aliases.extend(["boy","male"])
			else:
				self.aliases.extend(["man","guy","dude","male"])
		elif self.pronoun == "her":
			if isChild:
				self.aliases.extend(["girl","female"])
			else:
				self.aliases.extend(["woman","lady","dudette","female"])
		else:
			self.pronoun = "them"
		if isChild:
			self.aliases.extend(["child","kid"])
		self.aliases.append("person")


	### Operation ###

	# act on Person's turn
	def Act(self):
		pass


	### User Output ###

	# describe the Person using appropriate pronouns, including gear
	def describe(self):
		subjective = self.subjective()
		pro = "They're" if subjective == "they" else subjective.capitalize() + "'s"
		nounPhrase = ~self
		Print(f"{pro} {nounPhrase}.")
		if nounPhrase.lower() != self.desc.lower():
			Print(f"{self.desc}")
		gearKey = lambda item: not isinstance(item,(EmptyGear,Creature))
		gearitems = [item for item in self.gear.values() if gearKey(item)]
		if len(gearitems) != 0:
			Print(listObjects(self*"has ", gearitems,"."))
		tethersMsgs = []
		if self.carrying():
			tethersMsgs.append(listObjects("carrying ",self.carrying()))
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		if tethersMsgs:
			Print(self*f"is {' and '.join(tethersMsgs)}.")


	# intelligently get name of this Item in various grammatical forms
	# display a description of them (descname) if they haven't met Player yet
	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		# if self.riding and det != "the":
		# 	suffix = f" riding {self.riding.nounPhrase()}"
		# elif self.anchor() not in (None,self.parent.floor) and det != "the":
		# 	suffix = f" {self.posture()} on {self.anchor().nounPhrase()}"
		# if det == "a":
		# 	suffix = self.position(ignoreStanding=True)
		# else:
		# 	suffix = ""
		tethersSuffixes = ""
		indefinite = det == "a" or det == "" and n == 1 and \
			self.definiteDeterminer() != "your"
		if (self.carrying() or self.occupants()) and indefinite:
			tethersSuffixes = self.tethersDescription(allowCarrying=False)
		if "met" in self.memories:
			strname = self.name + tethersSuffixes
		else:
			strname = self.descname + tethersSuffixes

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if includePosture:
			strname = f"{self.posture()} {strname}"
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None and det == "":
			det = self.determiner
		if det == "" and n == 1:
			det = "your" if self.definiteDeterminer() == "your" else "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname



# Animals can only speak when player has 'wildspeaking' status
class Animal(Speaker):
	def __init__(self,name,desc,weight,traits,species=None,dlogName=None,**kwargs):
		super().__init__(name,desc,weight,traits,**kwargs)
		self.species = name if species is None else species
		# dlogName was assigned by Speaker init, but should be reassigned here
		self.dlogName = self.species if dlogName is None else dlogName


	# build dialogue tree from dictionary in game.dlogForest
	# or make a default tree based on species
	def buildDialogue(self):
		# dlogTree actually just records the visitCounts & checkpoint when written to json
		dlogRefs = self.dlogTree

		# dlogName must either be the name of a tree or a trite
		if self.dlogName in game.dlogForest["trees"]:
			self.dlogTree = game.dlogForest["trees"][self.dlogName].copy()
		else:
			defaultTree = {"chatter":{"trites":self.dlogName}}
			self.dlogTree = DialogueTree(self.dlogName,defaultTree)

		if dlogRefs:
			self.dlogTree.visitCounts = dlogRefs["visitCounts"]
			self.dlogTree.checkpoint = dlogRefs["checkpoint"]
		self.dlogTree.ensureIntegrity(self)


	# perform action on Animal's turn
	def Act(self):
		if not self.isAlive():
			return
		self.printNearby(f"\n{self.name}'s turn!",self.id,color="k")
		self.Attack()


	# eat offer if it is edible otherwise ignore
	def offer(self,I):
		if hasMethod(I,"consume"):
			I.consume(self)
			self.updateLove(1)
			self.updateFear(-1)
		else:
			Print(f"{+self} ignores your offer.")


	# talk to this Animal
	def converse(self,partner):
		if not partner.hasStatus("wildspeaking"):
			sounds = game.dlogForest["sounds"][self.species]
			sound = sample(sounds,1)[0]
			waitInput(f'*{sound}*',color="y")
			return True
		if "met" not in self.memories:
			self.firstImpression(partner)
		self.appraise(partner)
		if not self.dlogTree.visit(self):
			Print(f"{self.name} says nothing...")


	# touch this Animal
	def touch(self,toucher):
		# a per-instance texture wins, then a registered species texture,
		# then the composition's texture
		if self.texture is not None:
			Print(self.texture)
			return
		speciesMaterial = Data.materials.get(self.species)
		if speciesMaterial is not None:
			Print(speciesMaterial.texture)
		else:
			Print(self.Texture())


	def Attack(self):
		pass


	def Climb(self):
		pass


	def Go(self):
		pass


	def Steal(self):
		pass


	def Swim(self):
		pass



notes = '''
self.alive = True
self.seesPlayer = False
self.lastSawPlayer = -1

creatures can take 'actions'
they have a 'act' function, which dictates their actions

actions they can take on a turn include;
moving (swimming, climbing)
attacking
casting a spell
speaking
equipping/unequipping an item
using an item (eating food, using a key, etc.)
hiding somewhere
dropping/taking an item
stealing
throwing
heal itself
shield/defend

in their turn function, actions are dictated by several factors, including;
if they know the player is present,
if they recently saw the player,
if the player has weapons, or if the player is bloodied
if other creatures are present (and if they are allies or not)
if they have a weapon
if they have food or healing items
if their own stats are higher than a certain number
if they have a specific status condition
what the player's RP is

different types of creatures act with different limitations;
animal cannot speak, trade, or equip, take, and use items, or cast spells,
monsters cannot speak, or trade

_______________________________
TECHNICAL DESIGN

prior to taking a turn, each creature updates a series of attributes which just represent its perception of its surroundings. current values are;

all creatures:
Bool seesPlayer
Int lastSawPlayer
Bool alliesPresent()
Bool enemiesPresent()

monsters and people:
Int player.rp
Bool isArmed
Bool hasHealing
Bool playerBloodied()
Bool playerArmed()

other values utilized in taking a turn:
Set status

'''


# Item that is fixed and not mentioned by default
class Fixture(Item):
	def __init__(self,name,desc,weight,composition,durability=-1,mention=False,fixed=True,
	**kwargs):
		super().__init__(name,desc,weight,durability,composition,mention=mention,
		fixed=True,**kwargs)


	# def destroy(self):
	# 	Print(f"{+self} cannot be destroyed.")
	# 	return False


	# Fixtures shouldn't be breakable by normal means
	def breaks(self):
		Print(f"{+self} cannot be broken.")
		return False



# Surfaces are Fixtures that surround a Room or Container
class Surface(Fixture):
	def __init__(self,name,desc,weight,composition,**kwargs):
		super().__init__(name,desc,weight,composition,**kwargs)
		if any("water" in alias for alias in self.aliases):
			self.aliases.append("water")
		if any(Data.Material.get(name).liquid for name in self.aliases+[self.name]):
			self.aliases.append("liquid")


	# Surfaces can't take damage
	def takeDamage(self,dmg,type):
		pass


	def canImmerse(self,obj):
		return obj.parent is self.parent and self.couldImmerse(obj)


	def couldImmerse(self,obj,size=None,vacancy=None):
		return self.material().liquid


	def canSubmerge(self,obj):
		return self.canImmerse(obj)


	# Surfaces don't have a density, so size is just weight
	def Size(self):
		return self.weight



# Celestials are Fixtures that can be in Room contents depending on the time
class Celestial(Fixture):
	def __init__(self,name,desc,weight,composition,**kwargs):
		super().__init__(name,desc,weight,composition,**kwargs)
		self.determiner = "the"


	# Celestials have no ancestors, they don't belong in any one Room
	def ancestors(self):
		return []


moon = Celestial("moon","The glowing moon hangs in the sky, illuminating the world below.",
0,"cheese",aliases=["full moon","new moon"])
sun = Celestial("sun","The blazing sun shines down from above, its warmth felt by all.",
0,"fire",aliases=["sun"])
stars = Celestial("stars","The twinkling stars dot the night sky, each one a distant sun.",
0,"fire",aliases=["star"],pronoun="them")
eclipse = Celestial("eclipse","The sun and moon align perfectly, casting an eerie shadow" \
" over the land.",0,"fire",aliases=["solar eclipse","sun","moon"])
meteorshower = Celestial("meteor shower","A dazzling meteor shower streaks across the" \
" sky, lighting up the darkness with brief flashes of light.",0,"ylem",
aliases=["meteors","shower"])
aurora = Celestial("aurora","The sky is painted with vibrant colors as the aurora dances" \
" overhead, a mesmerizing display of nature's beauty.",0,"ylem",aliases=["auroras"])
sky = Celestial("sky","The vast expanse of the sky stretches out above, a canvas for " \
"the sun, moon, and stars.",0,"air",aliases=["heavens","firmament"],determiner="the")
celestials = (sky,sun,moon,stars,eclipse,meteorshower,aurora)


# Just as Rooms link to Rooms to allow creatures to move, Portals can link to Rooms too
# But a Portal can link to another Portals as well 
# They have traverse(), transfer(), a links dict and a passprep
class Portal(Item):
	def __init__(self,name,desc,weight,durability,composition,links,capacity=None,
	passprep="into",**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.links = links
		self.capacity = capacity
		self.passprep = passprep


	### File I/O ###

	# Resolve an authored portal-pair ID while loading the world.
	@staticmethod
	def resolveLinkPair(linkId,endpoints):
		portals = {portal for portal,direction in endpoints}
		if len(portals) != 2:
			raise ValueError(f"Portal link {linkId} joins {len(portals)} portals")
		for portal,direction in endpoints:
			portal.links[direction] = next(other for other in portals if other is not portal)

	# Validate resolved destinations; ordinary Portal targets must link back.
	# Containers may remain one-way object targets, while pair creation establishes
	# reciprocal container links through resolveLinkPair() or connect().
	def validate(self):
		for direction,destination in self.links.items():
			if not isinstance(destination,(Room,Item)):
				raise ValueError(f"Portal {self} has invalid {direction} link {destination}")
			if isinstance(destination,Portal) and not isinstance(destination,Container) and \
				self not in destination.links.values():
				raise ValueError(f"Portal link from {self} to {destination} is not reciprocal")
		return super().validate()


	# Return the portal links that should be written to a save.
	def serializableLinks(self):
		return self.links

	# replace object references in Portal Links with json-serializable values
	def convertToJSON(self,portalLinkIds=None):
		if portalLinkIds is None:
			portalLinkIds = {}
		jsonLinks = {}
		for direction,destination in self.serializableLinks().items():
			if isinstance(destination,Portal) and self in destination.links.values():
				pair = frozenset((self,destination))
				if pair not in portalLinkIds:
					portalLinkIds[pair] = len(portalLinkIds)
				jsonLinks[direction] = f"port:{portalLinkIds[pair]}"
			elif isinstance(destination,Room):
				jsonLinks[direction] = destination.name.lower()
			elif isinstance(destination,Item) and isinstance(destination.id,int):
				jsonLinks[direction] = destination.id
			else:
				raise ValueError(f"Portal {self} has invalid {direction} link {destination}")
		jsonDict = super().convertToJSON()
		jsonDict["links"] = jsonLinks
		return jsonDict


	### Operation ###

	# Create and validate one reciprocal portal pair during gameplay.
	def connect(self,direction,other,otherDirection):
		if not isinstance(other,Portal) or other is self:
			raise ValueError(f"Cannot connect {self} to {other}")
		if game.itemRegistry.get(self.id) is not self or \
			game.itemRegistry.get(other.id) is not other:
			raise ValueError("Cannot connect unregistered portals")
		if direction in self.links:
			raise ValueError(f"Portal {self} already has a {direction} link")
		if otherDirection in other.links:
			raise ValueError(f"Portal {other} already has a {otherDirection} link")

		self.links[direction] = other
		other.links[otherDirection] = self
		try:
			self.validate()
			other.validate()
		except Exception:
			del self.links[direction]
			del other.links[otherDirection]
			raise
		return True


	# for Creatures intentionally travelling through the portal
	# takes a verb because some subclasses may take verbs to traverse
	def traverse(self,traverser,dir=None,verb=None):
		if dir in Data.directions: dir = Data.directions[dir]
		if self in traverser.objTree():
			if traverser is player:
				Print(f"You can't enter {-self}. It's within your Inventory.")
			else:
				Print(f"{+traverser} can't enter {-self}. It's within {-traverser}'s" \
				" Inventory.")
			return False

		if dir == None or dir not in self.links:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = InputLoop(msg)
		if dir is None:
			return False
		if dir not in self.links:
			Print(f"The {self.name} does not go '{dir}'.")
			return False

		if traverser.riding:
			return self.traverse(traverser.riding,dir=dir,verb=verb)
		if not self.canPass(traverser):
			msg = f"{+traverser} can't fit through {-self}."
			traverser.Print(msg)
			if traverser in player.anchors():
				traverser.printNearby(msg)
			return False

		newloc = self.getNewLocation(dir)
		if not traverser.canChangeLocation(newloc):
			return False

		action = f"go {dir} {-self}."
		traverser.Print(traverser*action)
		traverser.printNearby(traverser+action)
		if traverser is player or traverser in player.anchors():
			waitInput()
		return traverser.changeLocation(newloc)


	# for Items/Creatures travelling through Portal unintentionally
	def transfer(self,item):
		if isinstance(item,Creature):
			dir = self.getDefaultDir()
			if dir == "down":
				return item.fall(1,room=self.getNewLocation("down"))
			return self.traverse(item,dir=dir)
		if self in item.objTree():
			Print(f"{+item} can't enter {-self}. It's within {-item}'s contents.")
			return False
		if not self.canPass(item):
			item.Print(f"{+item} can't fit through {-self}.")
			return False

		# fall through Portal if possible
		if "down" in self.links:
			return item.fall(room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")	
		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(item):
			return False

		item.changeLocation(newloc)


	# for Projectiles colliding with the Portal
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		if percentChance(bound(missile.aim+self.Size()+10,1,99)):
			if getattr(self,"closed",False):
				Print(f"{+missile} goes {self.passprep} {-self}.")
				self.transfer(missile.asItem())
			else:
				missile.collide(self)
			return True
		return False


	### Getters ###

	# returns dict of links, where keys are directions and values are Rooms/Portals
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		return links


	# when going through a portal without a concerted direction, pick a default one
	# if there's 1 destination, pick that. if there's "down", pick that. otherwise random
	def getDefaultDir(self):
		if len(set(self.links.values())) == 1:
			return list(self.links.keys())[0]
		elif "down" in self.links:
			return "down"
		return choice(list(self.links.keys()))


	# get the links dict to use in the parent's allLinks method
	def getLinksForParent(self):
		return self.links


	# given a direction, get the new location that the Portal leads to
	# if self links to another Portal, the new location is other Portal's parent
	def getNewLocation(self,dir=None):
		if dir is None:
			dir = self.getDefaultDir()
		newloc = self.links[dir]
		if isinstance(newloc,(Room,Container)):
			return newloc
		else:
			newloc = newloc.parent
			if isinstance(newloc,Creature):
				newloc = newloc.parent
			return newloc


	# given a direction (like 'north' or 'down)...
	# return the first portal object with that direction in its connections
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir and portal is not None:
				portals.append(portal)
		return portals


	# if the given room object dest, is in one of the Rooms links, 
	# then find the (dir,Portal) link key for it.
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


	# get all directions that this portal can lead to
	def allDirs(self):
		return (tuple[0] for tuple in self.allLinks())


	def allDests(self):
		return {dest for dest in self.allLinks().values()}


	def canPass(self,obj):
		if self.Capacity() == -1:
			return True
		return obj.totalSize() <= self.Capacity()


	def Capacity(self):
		return self.capacity if self.capacity is not None else self.Size()



# In addition to Rooms and Creatures, Containers can also contain Items and be a 'parent'
# Containers are a special case of Portals. they have traverse and transfer methods
# but they link to themselves, adding traversers into their items list
class Container(Portal):
	def __init__(self,name,desc,weight,durability,composition,items,capacity=None,
	passprep=None,exitprep="out",links=None,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.capacity = capacity
		self.passprep = passprep if passprep else "in"
		self.exitprep = exitprep if exitprep else "out"
		self.links = links if links else {}
		self.items = items
		# for containers, the surfaces surrounding it are itself
		self.ceiling = self
		self.walls = self
		self.floor = self
		self.surfaces = (self.ceiling,self.walls,self.floor)
		if self.vacancy() != -1 and self.vacancy() < 0:
			raise ValueError(f"Container {self} exceeds its capacity")


	### File I/O ###

	# Validate capacity and the generated entrance and exit relationships.
	def validate(self):
		if self.vacancy() != -1 and self.vacancy() < 0:
			raise ValueError(f"Container {self} exceeds its capacity")
		if self.links.get(self.passprep) is not self:
			raise ValueError(f"Container {self} has invalid entrance link")
		if self.links.get(self.exitprep) is not self.parent:
			raise ValueError(f"Container {self} has invalid exit link")
		if self.floor.material().liquid and \
			("down" not in self.links or \
			not isinstance(self.links["down"],(Room,Portal))):
			raise ValueError(f"Container {self} has a liquid floor but no valid down link")
		return super().validate()

	# Omit generated entrance and exit links from serialized container data.
	def serializableLinks(self):
		return {direction:destination for direction,destination in self.links.items() \
			if direction not in (self.passprep,self.exitprep)}


	# delete unneeded attributes for storing to json
	def convertToJSON(self,portalLinkIds=None):
		jsonDict = Portal.convertToJSON(self,portalLinkIds)
		del jsonDict["ceiling"]
		del jsonDict["walls"]
		del jsonDict["floor"]
		del jsonDict["surfaces"]
		del jsonDict["_parent"]
		return jsonDict


	### Operation ###

	# add Item to Container's items list
	def add(self,I,allowOverflow=False):
		if not isinstance(I,Item) or game.itemRegistry.get(I.id) is not I:
			raise ValueError(f"Cannot add unregistered object {I} to {self}")
		if not self.canAdd(I):
			return False
		if not allowOverflow and self.vacancy() != -1 and I.Size() > self.vacancy():
			return False

		# ensure only one bunch of Gold exists here
		if isinstance(I,Serpens):
			for item in self.items:
				if isinstance(item,Serpens):
					item.merge(I)
					return item

		insort(self.items,I)
		I.parent = self
		I.nullDespawn()
		I.expose(None)
		return I


	# Register and place an object in this container through Game.spawn().
	def spawn(self,obj):
		return game.spawn(obj,self)


	# add a status condition to the Container with a name and duration
	def addStatus(self,name,source=None,dur=None,allowStack=True,silent=False):
		return Room.addStatus(self,name,source,dur,allowStack=allowStack,
		silent=silent)


	def overflow(self):
		return Room.overflow(self)


	def checkCapacity(self):
		return Room.checkCapacity(self)


	def passTime(self,t):
		self.checkCapacity()
		return super().passTime(t)


	# try to break the Container, spill its contents into parent
	def breaks(self):
		# self.parent may get deleted during super().breaks()
		parent = self.parent
		if not super().breaks():
			return False
		if len(self.items) > 0:
			if self in player.surroundings():
				Print("Its contents spill out.")
		# drop things it contains into parent
		for item in self.items.copy():
			item.waitInput(f"You are no longer in {-self}.")
			item.changeLocation(parent)
			item.printNearby(f"{+item} comes out of {-self}.")
		return True


	# remove Item
	def remove(self,I):
		self.items.remove(I)
		I.parent = None


	# removes all status entries with the given name(s), source, and duration
	# when nothing given, remove all removable entries
	def removeStatus(self,reqName="*",reqSource="*",reqDuration="*",silent=False):
		return Room.removeStatus(self,reqName=reqName,reqSource=reqSource,
		reqDuration=reqDuration,silent=silent)


	### Interaction ###

	# try to bombard the Container with a Projectile
	# if it hits, go in it if possible, otherwise collide with it
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		if roll(100) < bound(missile.aim+self.Size()+10,1,99):
			if getattr(self,"closed",False):
				self.printNearby(f"{+self} is closed.")
				missile.collide(self)
			elif missile.item.parent is self:
				missile.collide(self)				
			elif not self.canAdd(missile):
				self.printNearby(f"{+self} is too full.")
				missile.collide(self)
			else:
				self.printNearby(f"{+missile} goes into {-self}.")
				missile = missile.asItem()
				missile.changeLocation(self)
			return True
		return False


	# try to enter the Container, applying any relevant status effects
	def enter(self,traverser):
		return Room.enter(self,traverser)


	# be looked at be a looking Creature and show description of contents
	def examine(self,looker):
		# exclude player if they are inside the box
		displayItems = [item for item in self.items if item is not looker]
		if len(displayItems) == 0:
			text = "It is empty"
			if looker in self.items:
				text += ", apart from you"
			looker.Print(f"{text}.")
		else:
			looker.Print(listObjects("Inside there is ", displayItems,"."))
			if looker is player:
				game.setPronouns(self.items[-1])
		return True


	# try to exit the Container, removing any relevant status effects
	def exit(self,traverser):
		if traverser not in self:
			return False
		traverser.removeStatus("hidden",reqSource="CONTAINER")
		return Room.exit(self,traverser)


	# replace oldItem in items with newItem if possible
	def replaceObj(self,oldItem,newItem):
		assert oldItem in self.items
		if not self.canAdd(newItem):
			return False
		index = self.items.index(oldItem)
		self.items[index] = newItem
		newItem.parent = self
		oldItem.parent = None
		return True


	# for Creatures intentionally travelling into/out of the Container
	def traverse(self,traverser,dir=None,verb=None):
		# unabbreviate/simplify direction
		if dir in Data.directions: dir = Data.directions[dir]
		if self in traverser.objTree():
			traverser.Print(f"You can't enter {-self}. It's within your Inventory.")
			return False
		if traverser.riding:
			return self.traverse(traverser.riding,dir=dir,verb=verb)
		if traverser in self.occupants():
			traverser.Print(f"You can't, you are {traverser.position()}.")
			return False

		# exit the container
		if dir == self.exitprep:
			if self is traverser.parent:
				if hasMethod(self,"open") and getattr(self,"closed",False):
					if not self.open(traverser,silent=False):
						return False
				if not traverser.canChangeLocation(self.parent):
					return False
				action = f"get out of {-self}."
				traverser.Print(traverser*action)
				traverser.printNearby(traverser+action)
				if traverser is player or traverser in player.anchors():
					waitInput()
				return traverser.changeLocation(self.parent)
			else:
				traverser.Print(f"You're not in {-self}.",color="k")
				return False

		# try to enter the container
		if traverser.parent is self:
			traverser.Print(f"You're already in {-self}.")
			return False
		if dir not in (self.passprep,None):
			traverser.Print(f"{+self} does not go {dir}.",color="k")
			return False

		if getattr(self,"closed",False):
			if not self.open(traverser,silent=False):
				return False
		if not traverser.canChangeLocation(self):
			return False

		if dir is None: dir = "into"
		if verb is None: verb = "get"
		action = f"{verb} {dir} {-self}."
		traverser.Print(traverser*action)
		traverser.printNearby(traverser+action)
		if traverser is player or traverser in player.anchors():
			waitInput()
		return traverser.changeLocation(self)


	### Getters ###

	# returns dict of links, where keys are directions and values are Rooms/Portals
	def allLinks(self,d=3):
		links = super().allLinks(d=d)
		# get a list of Portals in this Container
		portals = self.query(key=lambda x: isinstance(x,Portal),d=d)
		# for each Portals, add its links to links
		for portal in portals:
			for dir in portal.getLinksForParent():
				if dir not in links:
					links[(dir,portal)] = portal.links[dir]
		return links


	# check if item fits within Container's capacity
	def canAdd(self,I):
		if I is self or self in I.objTree():
			return False
		if hasMethod(I,"Spill"):
			return self.vacancy() == -1 or I.Size() <= self.vacancy()
		return self.couldSpill(I.minimumSize())


	def couldSpill(self,extraSize):
		return Room.couldSpill(self,extraSize)


	def canImmerse(self,obj):
		return Room.canImmerse(self,obj)


	def couldImmerse(self,obj,size=None,vacancy=None):
		return Room.couldImmerse(self,obj,size=size,vacancy=vacancy)


	def canSubmerge(self,creature):
		return Room.canSubmerge(self,creature)


	def requiredImmersion(self,obj):
		return Room.requiredImmersion(self,obj)


	# return spatial contents plus surfaces that are not None or self
	def contents(self):
		cts = self.spatialContents()
		cts += [s for s in self.surfaces if s not in (None,self)]
		return cts


	def spatialContents(self):
		return self.items


	# when getting a random direction to go, always go 'into' the Container
	def getDefaultDir(self):
		return self.passprep


	# get the links dict to use in the parent's allLinks method
	# we don't want to include the exit link, that is not accessible from the parent
	def getLinksForParent(self):
		return {dir:dest for dir,dest in self.links.items() if dest is self}


	# get total size of all items in Container
	def itemsSize(self):
		return sum(i.Size() for i in self.items)


	def minimumSolidSize(self):
		return Room.minimumSolidSize(self)


	# get total weight of all items in Container
	def itemsWeight(self):
		return sum(i.weight for i in self.items)


	# get available capacity in Container
	def vacancy(self):
		return -1 if self.Capacity() == -1 else self.Capacity() - self.itemsSize()


	# get total weight of Container plus its Items
	def Weight(self):
		return self.weight + self.itemsWeight()


	### Special Overrides ###

	@property
	def parent(self):
		return self._parent


	@parent.setter
	def parent(self,value):
		self._parent = value
		if hasattr(self,'links') and hasattr(self,'exitprep'):
			self.links[self.exitprep] = value
			self.links[self.passprep] = self



# convenience Portal subclass that is fixed and not mentioned by default
class Passage(Portal):
	def __init__(self,name,desc,weight,composition,links,passprep="into",mention=False,
	durability=-1,fixed=True,**kwargs):
		super().__init__(name,desc,weight,durability,composition,links,passprep=passprep,
		mention=mention,fixed=True,**kwargs)




# Serpens are piles of gold coins
# they must be merged together if they're in the same contents
class Serpens(Item):
	def __init__(self,value,**kwargs):
		desc = f"{str(value)} glistening coins made of an ancient metal."
		Item.__init__(self,"gold",desc,value,-1,"gold",**kwargs)
		self.aliases = ["coin","coins","money","serpens",str(value)+" gold"]
		self.plural = "gold"
		self.descname = str(value) + " gold"
		self.value = value


	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
			"value": self.value,
			"status": self.status
		}


	### Operation ###

	# don't obtain normally, just increase obtainer's money
	def obtain(self,obtainer):
		super().obtain(obtainer)
		obtainer.updateMoney(self.value)


	# absorb value of other into self, then update description
	def merge(self,other):
		if not isinstance(other,Serpens):
			return False

		self.status += other.status
		self.value += other.value
		self.desc = f"{str(self.value)} glistening coins made of an ancient metal."


	### User Output ###

	# intelligently get phrase to represent this in different grammatical contexts
	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		strname = "Gold"
		if det:
			# "a" only applies if there's 1, otherwise use indefinite plural
			if det == "a" and self.value != 1:
				det = "some"
			strname = det + " " + strname
		else:
			strname = str(self.value) + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


# Projectiles are Items that can be launched at targets
# it can be a standalone "true" Item when Projectile.item is None
# or it could be a temporary wrapper for another Item stored in Projectile.item
# __getattribute__ and __setattr__ pass through any attribute access to self.item first
# if it exists, otherwise to self
class Projectile(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sharpness,type,speed=0,item=None,**kwargs):
		# must be first or setattr will fail
		object.__setattr__(self,"item",item)
		if self.item is None:
			Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		object.__setattr__(self,"might",might)
		object.__setattr__(self,"sharpness",sharpness)
		object.__setattr__(self,"type",type)
		object.__setattr__(self,"speed",speed)
		# self.parent may be borrowed from self.item
		# in this case, the Projectile instance won't show up in parent's contents
		object.__setattr__(self,"parent",getattr(self.item,"parent",None))


	### Dunder Methods ###

	def __str__(self):
		return str(self.item) if self.item else self.name


	def __neg__(self):
		return super().__neg__() if self.item else "the " + self.name


	def __pos__(self):
		return super().__pos__() if self.item else "The " + self.name


	def __invert__(self):
		return super().__invert__() if self.item else "a " + self.name


	# if accessing .item or .asProjectile(), get from self
	# otherwise always try to get attributes from self.item first,
	# and then only get attribute from self if not found on self.item
	def __getattribute__(self, attr):
		if attr in ("item","asProjectile"):
			return object.__getattribute__(self, attr)
		try:
			return getattr(object.__getattribute__(self, "item"), attr)
		except AttributeError:
			return object.__getattribute__(self, attr)


	# if setting .item, always set on self
	# otherwise, set it in self.item if it exists and has that attribute
	# else set it on self
	def __setattr__(self, attr, value):
		# always allow setting the wrapped item itself
		if attr == "item":
			object.__setattr__(self, attr, value)
			return

		item = object.__getattribute__(self, "item")
		if item is not None and hasattr(item, attr):
			setattr(item, attr, value)
		else:
			object.__setattr__(self, attr, value)


	### Operation ###

	# launch the Projectile at target from launcher with given speed and aim accuracy
	def launch(self,speed,aim,launcher,target):
		self.speed = speed
		self.aim = 90 if self.hasStatus("homing") and aim < 90 else aim

		# when launching into another Room, just change location
		if isinstance(target,Room):
			self = self.asItem()
			if self.parent is not target:
				self.changeLocation(target)
			return self.fall(speed//4)
		# if has occupants, then make them fall off
		if isinstance(self.item,Item):
			for occupant in self.occupants():
				occupant.fall(speed//4)
			self.item.clearOccupants()

		# when launching from within in a Container at something outside the Container
		if self.parent not in (target,target.parent):
			# if parnet is closed, bombard the parent
			if getattr(self.parent,"closed",False):
				return self.parent.bombard(self)
			# otherwise change location to parent first
			self.asItem().changeLocation(target.parent)

		# try to bombard the target
		if not target.bombard(self):
			Print(f"{self.subjective().title()} misses!")
			self.miss(launcher,target)

		# if not a true projectile, then fall to ground
		if self.item:
			if not self.hasStatus("flying") and target is not target.parent.floor:
				if target is None or target.anchor() is None:
					self.fall(speed//4)
		return True


	# when missed the target, have a chance to hit another object in the room
	def miss(self,launcher,target):
		self.aim = -10 if self.asItem().hasStatus("homing") else min1(self.aim-10)

		# can't hit itself, the launcher, or the intended target
		otherObjs = [obj for obj in self.parent if obj not in \
		(self,self.item,launcher,target)]
		# having the curse of calamity makes ricocheting objects hit oneself
		if launcher.hasStatus("calamity"):
			otherObjs.append(launcher)
		if any(obj.hasStatus("calamity") for obj in otherObjs):
			otherObjs = [o for o in otherObjs if o.hasStatus("calamity")]
		sizes = [obj.Size() for obj in otherObjs]

		# more likely to hit larger objects
		victim = choices(otherObjs,sizes)[0]
		if victim is None:
			return False
		if victim is target.parent:
			return victim.bombard(self)
		Print(f"{self.subjective().title()} whizzes toward {-victim}!", color="o")
		if not victim.bombard(self):
			Print(f"{self.subjective().title()} misses...")


	# when colliding with target, deal damage and take self damage
	def collide(self,target):
		if target is player:
			Print(f"{+self} hits you!",color="o")
		else:
			Print(f"{+self} hits {-target}.")

		# deal damage to target
		d = self.might * self.speed
		if percentChance(self.sharpness):
			d *= 2
			Print("Critical hit!",color="o")
			self.dull(1)
		damage = diceRoll(0,d,d)
		target.takeDamage(damage,self.type)

		# take self damage
		if self.item:
			selfdmg = 0
			# if hits a creature, take damage according to one of the creature's gear
			if isinstance(target,Creature):
				gearItems = [item for item in target.gear.values()]
				sizes = [min1(item.Size()) for item in gearItems]
				target = choices(gearItems,sizes)[0]
			if target.durability == -1:
				selfdmg = self.speed * 3
			elif target.durability > self.durability:
				selfdmg = self.speed * (target.durability // self.durability)
			if selfdmg > 0:
				self.item.takeDamage(selfdmg,"b")
		else:
			self.parent.remove(self)
		return True


	# get the wrapped Item if it exists, otherwise return self
	def asItem(self):
		return self.item if self.item else self


	# its already a projectile!
	def asProjectile(self):
		return self



# Weapons are Items that can be used to attack
# they have might, sleight, sharpness, range, type and minimum grip requirements
class Weapon(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sleight,sharpness,
	range,type,minGripsNeeded=1,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,
		minGripsNeeded=minGripsNeeded,**kwargs)
		# amount of damage weapon deals
		self.might = might
		# accuracy of weapon
		self.sleight = sleight
		# chance of critical hits, degrades over time
		self.sharpness = sharpness
		# effective distance weapon can reach
		self.range = range
		# damage type
		self.type = type


	# decrease sharpness by dec unless keen
	def dull(self,dec):
		if not self.hasStatus("keen"):
			self.sharpness = min0(self.sharpness - dec)


	# display weapon and stats
	def show(self):
		Print(f"{self.name} {self.might} {self.sleight}")
		Print(f"{self.sharpness} {self.minGripsNeeded} {self.range}")


	# licking sharp weapons hurts!
	def lick(self,licker):
		# TODO: don't check for composition, check for if its sharp?
		if self.composition in ("glass","bronze","iron","steel"):
			Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True
		Print(self.Flavor())


	# wrap as Projectile for temporary use while launching
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,
		self.composition,self.might,self.sharpness,self.type,item=self)


	# if given keen status, maximize sharpness
	def addStatus(self,name,source=None,dur=None,allowStack=True,silent=False):
		added = super().addStatus(name,source,dur,allowStack=allowStack,
			silent=silent)
		if added and name == "keen" and self.hasStatus("keen"):
			self.sharpness = 20
		return added



# Shards are sharp fragments spawned when a shatterable Item shatters
# stats are derived from composition and weight unless explicitly overridden
class Shard(Weapon):
	def __init__(self,composition,weight,name=None,desc=None,durability=1,
	might=None,sleight=0,sharpness=None,range=0,type="s",**kwargs):
		if name is None:
			name = f"{composition} shard"
		if desc is None:
			desc = f"A sharp shard of {composition}."
		if might is None:
			might = min1(weight//2)
		if sharpness is None:
			sharpness = 6 if composition == "glass" else 2
		kwargs.setdefault("aliases",["shard"])
		super().__init__(name,desc,weight,durability,composition,might,sleight,
		sharpness,range,type,**kwargs)



class Shield(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot



class Armor(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,slots=None,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot
		self.slots = slots if slots else []
		if type(slots) is not list:
			self.slots = [slots]



class Compass(Item):
	def orient(self):
		Print("Orienting you northward!")




#############
## GLOBALS ##
#############


player = Player("","",0,[0]*10,0,0)
defaultRoom = Room("","","",{},[],[],[])
game = Game(-1,defaultRoom,defaultRoom,-1,set(),{},{},{})
world = {}