import io
import os
import sys
import unittest
from types import MethodType
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,"src"))

import Core
import Items
import Interpreter


class CensorTests(unittest.TestCase):
	def setUp(self):
		self.originalPlayer = Core.player
		self.originalGame = Core.game
		Core.player = Core.Player("Tester","",1,[1]*10,0,0)
		Core.game = Core.Game(1,Core.defaultRoom,Core.defaultRoom,0,set(),{}, {}, {})

	def tearDown(self):
		Core.player = self.originalPlayer
		Core.game = self.originalGame

	def setKnowledge(self,knowledge):
		Core.player.KNWL = lambda: knowledge

	def setInvestigation(self,investigation):
		Core.player.INVS = lambda: investigation

	def testThresholdsAndRanges(self):
		text = "always|3+|three|5:10|middle|11+|high"
		for knowledge,expected in ((2,"always"),(3,"alwaysthree"),
		(7,"alwaysthreemiddle"),(11,"alwaysthreehigh")):
			with self.subTest(knowledge=knowledge):
				self.setKnowledge(knowledge)
				self.assertEqual(Core.censor(text),expected)

	def testColonSyntaxExactValueAndWhitespace(self):
		self.setKnowledge(7)
		text = "| 7 |exact| 8 - |low| 7 + |high| 6 : 8 |range"
		self.assertEqual(Core.censor(text),"exactlowhighrange")

	def testExplicitKnowledgeAndInvestigationTags(self):
		self.setKnowledge(7)
		self.setInvestigation(4)
		text = "always|KNWL 7+|known|INVS 5+|hidden|invs 4+|noticed"
		self.assertEqual(Core.censor(text),"alwaysknownnoticed")

	def testTagAdjacentWhitespaceIsRemoved(self):
		self.setKnowledge(5)
		self.assertEqual(Core.censor("A |5+| B"),"A B")
		self.assertEqual(Core.censor("A\n|5+| B"),"AB")
		self.assertEqual(Core.censor("A \n|5+| B"),"A B")
		self.assertEqual(Core.censor("A  |5+| B"),"A  B")
		self.assertEqual(Core.censor("A\n\n|5+| B"),"A\nB")
		self.setKnowledge(4)
		self.assertEqual(Core.censor("A\n|5+| B"),"A")

	def testSagacityUsesKnowledgeOfOneHundred(self):
		self.setKnowledge(1)
		Core.player.status = [["sagacity",None,None]]
		self.assertEqual(Core.censor("|100|known|101+|hidden"),"known")

	def testSagacityUsesInvestigationOfOneHundred(self):
		self.setKnowledge(1)
		self.setInvestigation(1)
		Core.player.status = [["sagacity",None,None]]
		text = "|KNWL 100|known|INVS 100|noticed|INVS 101+|hidden"
		self.assertEqual(Core.censor(text),"knownnoticed")

	def testPrintCensorsBeforeLengthAndColor(self):
		self.setKnowledge(5)
		output = io.StringIO()
		printedLength = Core.Print("known |5+|detail |6+|hidden",
			color="r",outfile=output)
		self.assertEqual(output.getvalue(),"\033[31mknown detail \033[0m\n")
		self.assertEqual(printedLength,len("known detail "))

	def testPrimerExpandsColorsAndResetsToTerminalDefault(self):
		self.assertEqual(Core.primer("plain <b>blue</> plain"),
			"plain \033[34mblue\033[0m plain")

	def testPrimerConsumesUnknownSingleCharacterTags(self):
		self.assertEqual(Core.primer("before <z>after <?>done"),
			"before after done")
		self.assertEqual(Core.primer("keep <blue>literal"),"keep <blue>literal")

	def testPrimerRandomizesKnownTagsDuringInsanity(self):
		Core.player.status = [["insanity",None,None]]
		with patch("Core.choice",return_value="g") as chooseColor:
			self.assertEqual(Core.primer("<b>text</>"),
				"\033[32mtext\033[0m")
		chooseColor.assert_called_once()

	def testApathyMakesInlineColorsWhiteExceptBlack(self):
		Core.player.status = [["apathy",None,None]]
		self.assertEqual(Core.primer("<r>red</> plain <k>black</> end"),
			"\033[37mred\033[37m plain \033[90mblack\033[37m end")

	def testPrintResetsUnclosedInlineColor(self):
		output = io.StringIO()
		printedLength = Core.Print("<b>blue",outfile=output)
		self.assertEqual(output.getvalue(),"\033[34mblue\033[0m\n")
		self.assertEqual(printedLength,len("blue"))

	def testStupidityTraitsFitWithinSidePanel(self):
		Core.player.status = [["stupidity",None,None]]
		Core.player.str = 11
		output = io.StringIO()
		Core.player.printTraits(outfile=output)
		lines = Core.ANSI_ESCAPE.sub("",output.getvalue()).splitlines()

		self.assertEqual(len(lines),3)
		self.assertTrue(all(len(line) < Core.sidepanel.width for line in lines))

	def testLongPlayerNameUsesSingleStatColumn(self):
		Core.player.name = "A player name deliberately approaching panel width"
		output = io.StringIO()
		Core.player.printStats(outfile=output)
		lines = Core.ANSI_ESCAPE.sub("",output.getvalue()).splitlines()

		self.assertEqual(len(lines),6)
		self.assertTrue(all(len(line) < Core.sidepanel.width for line in lines))

	def testSidePanelGearUsesRequestedTwoColumnGrouping(self):
		originalPanel = Core.sidepanel
		Core.sidepanel = Core.SidePanel(width=50,height=25)
		Core.sidepanel.pipe = io.StringIO()
		try:
			Core.player.printGear(outfile=Core.sidepanel)
			output = Core.ANSI_ESCAPE.sub("",Core.sidepanel.pipe.getvalue())
		finally:
			Core.sidepanel = originalPanel

		lines = output.splitlines()[1:]
		colWidth = 15
		self.assertEqual(len(lines),4)
		self.assertTrue(lines[0].startswith("over:"))
		self.assertTrue(lines[0][colWidth:].startswith("right:"))
		self.assertTrue(lines[1].startswith("head:"))
		self.assertTrue(lines[1][colWidth:].startswith("legs:"))
		self.assertTrue(lines[2].startswith("torso:"))
		self.assertTrue(lines[2][colWidth:].startswith("feet:"))
		self.assertTrue(lines[3].startswith("left:"))
		self.assertTrue(all(line.find("[---]") == 7 for line in lines))
		self.assertTrue(all(line.find("[---]",colWidth) == colWidth+7 \
			for line in lines[:3]))


class DeferredStatusReportTests(unittest.TestCase):
	def setUp(self):
		self.originalPlayer = Core.player
		self.originalGame = Core.game
		Core.player = Core.Player("Tester","",1,[1]*10,0,0)
		Core.game = Core.Game(1,Core.defaultRoom,Core.defaultRoom,0,set(),{}, {}, {})
		self.creature = Core.Creature("goblin","",10,[1]*10)

	def tearDown(self):
		Core.player = self.originalPlayer
		Core.game = self.originalGame

	def testNestedDeferralReportsOnlyNetStatusChange(self):
		with patch.object(self.creature,"printNearby") as nearby:
			with Core.game.deferStatusReports():
				self.creature.addStatus("burning")
				with Core.game.deferStatusReports():
					self.creature.removeStatus("burning")
					self.creature.addStatus("burning")
				self.assertFalse(nearby.called)

		nearby.assert_called_once()
		self.assertEqual(nearby.call_args.args[0],"The goblin is burning.")

	def testDeferralSuppressesNoNetChangeAndPrivateStatus(self):
		with patch.object(self.creature,"printNearby") as nearby:
			with Core.game.deferStatusReports():
				self.creature.addStatus("wet",dur=1)
				self.creature.removeStatus("wet")
				self.creature.addStatus("hidden")
			# the wet flicker nets to nothing; the private status routes
			# through printNearby as non-public (so godmode can still see it)
			nearby.assert_called_once()
			self.assertEqual(nearby.call_args.args[0],"The goblin is hidden.")
			self.assertFalse(nearby.call_args.kwargs["public"])

	def testDeferralTracksSilentMutationWithoutReportingIt(self):
		with patch.object(self.creature,"printNearby") as nearby:
			with Core.game.deferStatusReports():
				self.creature.addStatus("submerged",source="IMMERSED",silent=True)
			self.assertFalse(nearby.called)
		self.assertTrue(self.creature.hasStatus("submerged"))

	def testSilentTemporaryStatusDoesNotCauseFalseRemovalReport(self):
		with patch.object(self.creature,"printNearby") as nearby:
			with Core.game.deferStatusReports():
				self.creature.addStatus("submerged",source="IMMERSED",silent=True)
				self.creature.removeStatus("submerged")
			self.assertFalse(nearby.called)

	def testMovementReportsStatusAfterTransitionOutput(self):
		events = []
		with patch.object(self.creature,"printNearby",
			side_effect=lambda message,**kwargs: events.append(message)):
			def transition(creature,destination,silent=False):
				creature.addStatus("submerged",source="IMMERSED")
				events.append("room description")
				return True
			self.creature._changeLocation = MethodType(transition,self.creature)
			self.assertTrue(self.creature.changeLocation(None))

		self.assertEqual(events,
			["room description","The goblin is submerged."])

	def testItemMovementDefersAffectedCreatureStatus(self):
		events = []
		item = Core.Item("barrel","",10,-1,"wood")
		with patch.object(self.creature,"printNearby",
			side_effect=lambda message,**kwargs: events.append(message)):
			def transition(movingItem,destination,silent=False):
				self.creature.addStatus("submerged",source="IMMERSED")
				events.append("item transition complete")
				return True
			item._changeLocation = MethodType(transition,item)
			self.assertTrue(item.changeLocation(None))

		self.assertEqual(events,
			["item transition complete","The goblin is submerged."])


class DistanceRefusalTests(unittest.TestCase):
	def setUp(self):
		self.originalPlayer = Core.player
		Core.player = Core.Player("Tester","",1,[1]*10,0,0)
		self.cask = Core.Item("wine cask","",30,20,"wood",determiner="the")

	def tearDown(self):
		Core.player = self.originalPlayer

	def testDryTargetIsOmittedFromImmersionRefusal(self):
		with patch.object(Core.player,"position",return_value="standing in the puddle"), \
		patch("Core.Print") as output:
			self.assertTrue(Interpreter.refuseVerbDistance("close",self.cask,
				describeTarget=False))
		output.assert_called_once_with(
			"You can't close the wine cask; you're standing in the puddle.")

	def testPositionRefusalNamesTargetExplicitly(self):
		ground = Core.Item("ground","",100,-1,"stone",determiner="the")
		self.cask.platform = ground
		with patch.object(Core.player,"position",return_value="standing nearby"), \
		patch("Core.Print") as output:
			self.assertTrue(Interpreter.refuseVerbDistance("close",self.cask))
		output.assert_called_once_with("You can't close the wine cask; "
			"you're standing nearby, and it is on the ground.")


class LiquidDescriptionTests(unittest.TestCase):
	def setUp(self):
		self.originalPlayer = Core.player
		self.originalGame = Core.game
		Core.player = Core.Player("Tester","",1,[1]*10,0,0)
		Core.game = Core.Game(1,Core.defaultRoom,Core.defaultRoom,0,set(),{}, {}, {})

	def tearDown(self):
		Core.player = self.originalPlayer
		Core.game = self.originalGame

	def makeRoom(self,items,creatures):
		room = Core.Room("test room","test","",{},[],items,creatures)
		for obj in room.spatialContents():
			obj.parent = room
		return room

	def describeRoomContents(self,room):
		output = io.StringIO()
		with patch("sys.stdout",output):
			room.describeItems()
			room.describeCreatures()
		return output.getvalue()

	def testPlashUsesMassNounIndefiniteDeterminer(self):
		wine = Items.Plash(70,name="wine",composition="wine")
		cask = Items.Box("cask","",30,-1,"wood",[wine],capacity=70)
		wine.parent = cask
		self.assertEqual(wine.fillPercent(),100)
		self.assertEqual(wine.nounPhrase(n=1),"some wine")
		self.assertEqual(wine.nounPhrase("a"),"some wine")
		self.assertEqual(wine.nounPhrase("the"),"the wine")

		wine.weight = 2
		self.assertLess(wine.fillPercent(),10)
		self.assertEqual(wine.nounPhrase(n=1),"a droplet of wine")

		spill = Items.Plash(50,composition="wine")
		self.assertEqual(spill.name,"wine")
		self.assertIn("small pool",spill.aliases)
		self.assertIn("small pool of wine",spill.aliases)
		self.assertEqual(spill.nounPhrase(n=1),"a small pool of wine")
		self.assertEqual(spill.nounPhrase(n=2),"2 small pools of wine")

		droplet = Items.Plash(2,composition="wine")
		self.assertEqual(Core.listObjects("There is ",[spill,droplet],"."),
			"There is a small pool of wine and a droplet of wine.")
		self.assertEqual(Core.listObjects("There are ",[spill,
			Items.Plash(50,composition="wine")],"."),
			"There are 2 small pools of wine.")

	def testRoomListsFloatingObjectsThroughMentionedPlash(self):
		pond = Items.Plash(100,name="pond")
		lilyPad = Core.Item("lily pad","",5,-1,"wood")
		frog = Core.Creature("frog","",1,[1]*10)
		room = self.makeRoom([pond,lilyPad],[frog])
		lilyPad.immersed = pond
		lilyPad.platform = None
		frog.platform = lilyPad

		self.assertEqual(self.describeRoomContents(room),
			"There is a pond.\n"
			"Floating in the pond is a lily pad with a frog on it.\n")

	def testRoomSeparatesFloatingAnchoredAndSurfaceGroups(self):
		pond = Items.Plash(100,name="pond")
		boat = Core.Item("wooden boat","",5,-1,"wood")
		rock = Core.Item("rock","",20,-1,"stone")
		athlete = Core.Creature("athlete","",5,[1]*10)
		wizard = Core.Creature("wizard","",5,[1]*10)
		room = Core.Room("test room","test","",{},[],[pond,boat,rock],
			[athlete,wizard],floor="stone")
		for obj in room.spatialContents()+[room.floor]:
			obj.parent = room
		boat.immersed = pond
		boat.platform = None
		rock.immersed = pond
		rock.platform = None
		athlete.immersed = pond
		athlete.platform = room.floor
		athlete.addStatus("sitting",silent=True)
		wizard.platform = pond

		self.assertEqual(self.describeRoomContents(room),
			"There is a pond.\n"
			"Floating in the pond are a rock and a wooden boat.\n"
			"In the pond is a sitting athlete.\n"
			"On the pond's surface is a wizard.\n")

	def testUnmentionedPlashUsesDefiniteNameAndLimitsEachGroup(self):
		pond = Items.Plash(100,name="pond",mention=False)
		floats = [Core.Item(f"float {idx}","",1,-1,"wood") for idx in range(4)]
		room = self.makeRoom([pond]+floats,[])
		for obj in floats:
			obj.immersed = pond
			obj.platform = None

		self.assertEqual(self.describeRoomContents(room),
			"There are many things floating in the pond.\n")

	def testImmersedTetherGroupDescribesCarryingSeparately(self):
		pond = Items.Plash(100,name="pond")
		frog = Core.Creature("frog","",5,[10]*10)
		fly = Core.Creature("fly","",1,[1]*10)
		room = self.makeRoom([pond],[frog,fly])
		frog.immersed = pond
		frog.platform = None
		frog.assignCarrySlots(fly,["left"])

		self.assertEqual(self.describeRoomContents(room),
			"There is a pond.\nFloating in the pond is a frog.\n"
			"The frog is carrying a fly.\n")

	def testExaminingPlashRevealsSubmergedRoots(self):
		pond = Items.Plash(100,name="pond")
		shark = Core.Creature("shark","",10,[10]*10)
		surfer = Core.Creature("surfer","",5,[10]*10)
		room = self.makeRoom([pond],[shark,surfer])
		shark.immersed = pond
		shark.platform = None
		shark.addStatus("submerged",source="IMMERSED",silent=True)
		surfer.riding = shark

		output = io.StringIO()
		with patch("sys.stdout",output):
			pond.examine(Core.player)

		self.assertEqual(output.getvalue(),
			"Under the surface, there appears to be "
			"a shark being ridden by a surfer.\n")

	def testSubmergedLookerSeesSurfacedRootsAbove(self):
		pond = Items.Plash(100,name="pond")
		lilyPad = Core.Item("lily pad","",5,-1,"wood")
		room = self.makeRoom([pond,lilyPad],[Core.player])
		lilyPad.immersed = pond
		lilyPad.platform = None
		Core.player.immersed = pond
		Core.player.platform = None
		Core.player.addStatus("submerged",source="IMMERSED",silent=True)

		output = io.StringIO()
		with patch("sys.stdout",output):
			pond.examine(Core.player)

		self.assertEqual(output.getvalue(),
			"Above the surface, there appears to be a lily pad.\n")


if __name__ == "__main__":
	unittest.main()
