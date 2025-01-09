
import os
import sys

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
sys.path.append("../src")

import PoPy
from Core import TeeLogger


# test the main menu
def testMenu():
	sys.stdin.setInputFile("test/testMenu.txt")
	if os.path.exists("saves/testsave"):
		for filename in os.listdir("saves/testsave"):
			os.remove("saves/testsave/" + filename)
		os.rmdir("saves/testsave")
	PoPy.main(testing=True)
	PoPy.main(testing=True)
	PoPy.main(testing=True)


# tests each of the cheatcodes
def testCheatcodes():
	sys.stdin.setInputFile("test/testCheatcodes.txt")
	PoPy.main(testing=True)


# tests look, listen, and actions which don't alter the world state
def testInfo():
	sys.stdin.setInputFile("test/testInfo.txt")
	PoPy.main(testing=True)


# tests go, govertical, go through passages multi/single directionally, open/closing doors,
def testNavigation():
	sys.stdin.setInputFile("test/testNavigation.txt")
	PoPy.main(testing=True)


# tests open, close, take/grab, put, and drop actions
def testInventory():
	sys.stdin.setInputFile("test/testInventory.txt")
	PoPy.main(testing=True)


# tests use, eat, equip, lock, pour and related actions
def testBasicItems():
	sys.stdin.setInputFile("test/testInventory.txt")
	PoPy.main(testing=True)


# tests attacking and breaking, cut
def testCombat():
	sys.stdin.setInputFile("test/testCombat.txt")
	PoPy.main(testing=True)


# tests crawl, hide, stealth, mount, laying, flying, jump, climb, swim
def testMobility():
	pass


# tests push, pull, catch, throw, tie, fish, press, ignite
def testMiscItems():
	pass


# tests pray, wave, point, touch, rub, play, pet, rest
def testGesturing():
	pass


# craft, cook,
def testCraft():
	pass


# tests basic spell usage
def testSpells():
	pass



if __name__ == "__main__":
	os.chdir("..")
	logger = TeeLogger("test/test.log")
	sys.stdin = logger
	sys.stdout = logger
	sys.stderr = logger
	testMenu()
	testInfo()
	testCheatcodes()
	testNavigation()
	testInventory()
	testBasicItems()
	testCombat()
	testSpells()
	print("\nAll tests passed without error\n")
