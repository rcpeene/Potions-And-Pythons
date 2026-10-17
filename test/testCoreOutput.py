import io
import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,"src"))

import Core


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
		Core.player.status = [["sagacity",-1]]
		self.assertEqual(Core.censor("|100|known|101+|hidden"),"known")

	def testSagacityUsesInvestigationOfOneHundred(self):
		self.setKnowledge(1)
		self.setInvestigation(1)
		Core.player.status = [["sagacity",-1]]
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
		Core.player.status = [["insanity",-1]]
		with patch("Core.choice",return_value="g") as chooseColor:
			self.assertEqual(Core.primer("<b>text</>"),
				"\033[32mtext\033[0m")
		chooseColor.assert_called_once()

	def testApathyMakesInlineColorsWhiteExceptBlack(self):
		Core.player.status = [["apathy",-1]]
		self.assertEqual(Core.primer("<r>red</> plain <k>black</> end"),
			"\033[37mred\033[37m plain \033[90mblack\033[37m end")

	def testPrintResetsUnclosedInlineColor(self):
		output = io.StringIO()
		printedLength = Core.Print("<b>blue",outfile=output)
		self.assertEqual(output.getvalue(),"\033[34mblue\033[0m\n")
		self.assertEqual(printedLength,len("blue"))

	def testStupidityTraitsFitWithinSidePanel(self):
		Core.player.status = [["stupidity",-1]]
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


if __name__ == "__main__":
	unittest.main()