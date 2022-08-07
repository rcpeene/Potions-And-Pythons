
import os
import sys

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
sys.path.append("../src")

import PoPy



# test the main menu
def testMenu():
	sys.stdin = open("test/testMenu.txt")
	if os.path.exists("saves/testsave"):
		for filename in os.listdir("saves/testsave"):
			os.remove("saves/testsave/" + filename)
		os.rmdir("saves/testsave")
	PoPy.main(skipIntro=True)
	PoPy.main(skipIntro=True)
	PoPy.main(skipIntro=True)


# tests each of the cheatcodes
def testCheatcodes():
	sys.stdin = open("test/testCheatcodes.txt")
	PoPy.main(skipIntro=True)


# tests look, listen, and actions which don't alter the world state
def testInfo():
	sys.stdin = open("test/testInfo.txt")
	PoPy.main(skipIntro=True)

# tests go, govertical, go through passages multi/single directionally, open/closing doors,
def testNavigation():
	sys.stdin = open("test/testNavigation.txt")
	PoPy.main(skipIntro=True)

# tests open, close, take/grab, put, and drop actions
def testInventory():
	sys.stdin = open("test/testInventory.txt")
	PoPy.main(skipIntro=True)

# tests use, eat, equip, lock, pour and related actions
def testBasicItems():
	sys.stdin = open("test/testInventory.txt")
	PoPy.main(skipIntro=True)

# tests attacking and breaking, cut
def testCombat():
	sys.stdin = open("test/testCombat.txt")
	PoPy.main(skipIntro=True)

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
	testMenu()
	testInfo()
	testCheatcodes()
	testNavigation()
	testInventory()
	testBasicItems()
	testCombat()
	testSpells()
	print("\nAll test passed without error\n")
