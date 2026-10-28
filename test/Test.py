
import os
import sys
import traceback

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
sys.path.append("../src")

import PoPy
import Core


def runLoggedTest(testFunc):
	originalStdin = sys.stdin
	originalStdout = sys.stdout
	originalStderr = sys.stderr
	logPath = os.path.join(dname,"logs",f"{testFunc.__name__}.log")
	logger = Core.TeeLogger(logPath)
	sys.stdin = logger
	sys.stdout = logger
	sys.stderr = logger
	try:
		testFunc()
	except Exception:
		logger.forceDrainBuffer()
		logger.log.write("\n" + traceback.format_exc())
		logger.log.flush()
		raise
	finally:
		logger.forceDrainBuffer()
		if logger.stdin is not logger.originalStdin:
			logger.stdin.close()
		logger.log.close()
		sys.stdin = originalStdin
		sys.stdout = originalStdout
		sys.stderr = originalStderr


# test the main menu
def testMenu():
	sys.stdin.setInputFile("test/testMenu.txt")
	if os.path.exists("saves/testsave"):
		for filename in os.listdir("saves/testsave"):
			os.remove("saves/testsave/" + filename)
		os.rmdir("saves/testsave")
	Core.game.mode = 1 # set to test mode to speed input
	PoPy.main(testing=True)
	PoPy.main(testing=True)
	PoPy.main(testing=True)
	Core.game.mode = 1 # set to test mode to speed input


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


# tests carrying creatures, carry slots, burden, and dynamic tether correction
def testCarrying():
	sys.stdin.setInputFile("test/testCarrying.txt")
	PoPy.main(testing=True)


# tests ordinary platform occupancy, movement, displacement, and replacement
def testPlatforms():
	sys.stdin.setInputFile("test/testPlatforms.txt")
	PoPy.main(testing=True)


# tests mounting, multiple riders, crowding contests, burden, and riding loops
def testRiding():
	sys.stdin.setInputFile("test/testRiding.txt")
	PoPy.main(testing=True)


# tests use, eat, equip, lock, pour and related actions
def testBasicItems():
	sys.stdin.setInputFile("test/testBasicItems.txt")
	PoPy.main(testing=True)


# tests attacking and breaking, cut
def testCombat():
	sys.stdin.setInputFile("test/testCombat.txt")
	PoPy.main(testing=True)


# tests tethered group movement, traversal, climbing, flying, jumping, and swimming
def testMovement():
	sys.stdin.setInputFile("test/testMovement.txt")
	PoPy.main(testing=True)


# tests Plash traversal, immersion, submersion, and liquid displacement
def testLiquids():
	sys.stdin.setInputFile("test/testLiquids.txt")
	PoPy.main(testing=True)


# tests admission, displacement recovery, replacement tethers, and registry identity
def testSpatialIntegrity():
	sys.stdin.setInputFile("test/testSpatialIntegrity.txt")
	PoPy.main(testing=True)


# tests throwing, lobbing, collision, ricochet, catching, and container admission
def testProjectiles():
	sys.stdin.setInputFile("test/testProjectiles.txt")
	PoPy.main(testing=True)


# tests effect spawning, parent admission, cleanup, IDs, and timed room spawning
def testEffects():
	sys.stdin.setInputFile("test/testEffects.txt")
	PoPy.main(testing=True)


# tests a minimal player conversation and persistent social state
def testDialogue():
	sys.stdin.setInputFile("test/testDialogue.txt")
	PoPy.main(testing=True)


# tests status duration, survival clocks, and celestial event transitions
def testTime():
	sys.stdin.setInputFile("test/testTime.txt")
	PoPy.main(testing=True)


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
	tests = (testMenu,testInfo,testCheatcodes,testNavigation,testInventory,
		testCarrying,testPlatforms,testRiding,testMovement,testLiquids,testSpatialIntegrity,
		testProjectiles,testEffects,testDialogue,testTime,testBasicItems,testCombat,
	)
	failures = []
	for testFunc in tests:
		try:
			runLoggedTest(testFunc)
		except Exception:
			failures.append((testFunc.__name__,traceback.format_exc()))
		else:
			print(f"[PASS] {testFunc.__name__}")
	if failures:
		print("\nTest failures:\n", file=sys.stderr)
		for testName,error in failures:
			print(f"[FAIL] {testName}\n{error}", file=sys.stderr)
		failedNames = ", ".join(testName for testName,error in failures)
		print(f"{len(failures)} test script(s) failed: {failedNames}\n", file=sys.stderr)
		sys.exit(1)
	print("\nAll test scripts passed without error\n")
