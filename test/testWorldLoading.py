import json
import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,os.path.join(ROOT,"src"))

import Core
import Creatures
import Items
import Menu


class WorldLoadingTests(unittest.TestCase):
	def makeGame(self):
		game = Core.Game(1,Core.defaultRoom,Core.defaultRoom,0,set(),{},
			Creatures.factory,Items.factory)
		Core.game = game
		return game

	def makeRoomSpec(self,name,items=None,hasPlayer=False):
		creatures = [{"__class__":"Player"}] if hasPlayer else []
		return {"__class__":"Room","name":name.title(),"domain":"","desc":"",
			"links":{},"permanents":[],"items":items or [],"creatures":creatures,
			"ceiling":"stone","walls":"stone","floor":"stone"}

	def makePortalSpec(self,name,links):
		return {"__class__":"Portal","name":name,"desc":"","weight":1,
			"durability":10,"composition":"stone","links":links}

	def testRawWorldRemainsData(self):
		raw = Menu.readWorldJSON(os.path.join(ROOT,"gamedata","World.json"))
		self.assertIsInstance(raw["cave"],dict)
		self.assertEqual(raw["cave"]["__class__"],"Room")

	def testNewGameStartsPlayerLayingOnFloor(self):
		worldSpec = {"cave":self.makeRoomSpec("cave",hasPlayer=True)}
		newPlayer = Core.Player("Tester","",29,[1]*10,0,0)
		with patch.object(Menu,"readDialogue",return_value={}), \
		patch.object(Menu,"readWorldJSON",return_value=worldSpec), \
		patch.object(Menu,"createCharacter",return_value=newPlayer), \
		patch.object(Menu,"sleep"), patch.object(Core,"clearScreen"), \
		patch.object(Core,"flushInput"), patch.object(Core.Player,"display"), \
		patch.object(Core.Game,"startUp"):
			Menu.newGame()

		self.assertIs(Core.player.platform,Core.world["cave"].floor)
		self.assertEqual(Core.player.posture(),"laying")

	def testRoomKeysAreLowercaseDisplayNames(self):
		game = self.makeGame()
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()
		room = {"__class__":"Room","name":"Grand Hall","domain":"",
			"desc":"","links":{},"permanents":[],"items":[],
			"creatures":[{"__class__":"Player"}]}
		normalized = game.normalizeWorldData({"grand hall":room},playerSpec)
		self.assertIs(normalized["grand hall"],room)
		self.assertEqual(room["name"],"Grand Hall")

	def testUppercaseRoomKeyFails(self):
		game = self.makeGame()
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()
		room = {"__class__":"Room","name":"Cave","domain":"","desc":"",
			"links":{},"permanents":[],"items":[],
			"creatures":[{"__class__":"Player"}]}
		with self.assertRaisesRegex(ValueError,"World key 'Cave' must be lowercase"):
			game.normalizeWorldData({"Cave":room},playerSpec)

	def testNormalizeNestedTethers(self):
		game = self.makeGame()
		frog = {"__class__":"Creature","id":42,"name":"frog"}
		mouse = {"__class__":"Creature","name":"mouse"}
		hat = {"__class__":"Item","name":"hat"}
		damsel = {"__class__":"Creature","name":"damsel","inv":[],
			"gear":{"left":frog,"right":42,"tail":mouse,"head":hat},
			"carrySlots":["left","right","tail"]}
		coin = {"__class__":"Item","name":"coin"}
		table = {"__class__":"Item","name":"table","occupants":[coin]}
		rider = {"__class__":"Creature","name":"rider"}
		horse = {"__class__":"Creature","name":"horse","riders":[rider]}
		covered = {"__class__":"Creature","name":"covered"}
		blanket = {"__class__":"Item","name":"blanket","covering":[covered]}
		room = {"__class__":"Room","name":"Cave","permanents":[],
			"items":[table,blanket],"creatures":[damsel,horse]}
		world = {"cave":room}

		world["cave"]["creatures"].append({"__class__":"Player"})
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()
		game.normalizeWorldData(world,playerSpec)

		self.assertIn(frog,room["creatures"])
		self.assertIn(mouse,room["creatures"])
		self.assertIn(rider,room["creatures"])
		self.assertIn(covered,room["creatures"])
		self.assertIn(coin,room["items"])
		self.assertIn(hat,damsel["inv"])
		self.assertEqual(frog["carrier"],damsel["id"])
		self.assertEqual(mouse["carrier"],damsel["id"])
		self.assertEqual(damsel["gear"]["left"],42)
		self.assertEqual(damsel["gear"]["right"],42)
		self.assertEqual(damsel["gear"]["tail"],mouse["id"])
		self.assertEqual(coin["platform"],table["id"])
		self.assertEqual(rider["riding"],horse["id"])
		self.assertNotIn("platform",rider)
		self.assertNotIn("platform",frog)
		self.assertNotIn("platform",mouse)
		self.assertEqual(covered["cover"],blanket["id"])

	def testPermanentsDefaultToFloorUnlessExplicitlyFloating(self):
		game = self.makeGame()
		grounded = {"__class__":"Fixture","name":"grounded"}
		floating = {"__class__":"Fixture","name":"floating","platform":None}
		room = {"__class__":"Room","name":"Cave","permanents":[grounded,floating],
			"items":[],"creatures":[{"__class__":"Player"}]}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		game.normalizeWorldData({"cave":room},playerSpec)

		self.assertEqual(grounded["platform"],"floor")
		self.assertIsNone(floating["platform"])

	def testDuplicateIDsFailDuringReservation(self):
		game = self.makeGame()
		world = [{"__class__":"Item","id":7,"name":"one"},
			{"__class__":"Item","id":7,"name":"two"}]
		with self.assertRaisesRegex(ValueError,"Duplicate object ID 7"):
			game.collectObjectIDs(world)

	def testFactoryTypeResolutionDoesNotConstruct(self):
		calls = []
		game = self.makeGame()
		game.itemFactory = {"test item":lambda: calls.append(True) or \
			Core.Item("test item","",1,1,"wood")}
		spec = {"__class__":"factoryItem","name":"test item"}

		self.assertIs(game.resolveSpecClass(spec),Core.Item)
		self.assertEqual(calls,[])
		self.assertIsInstance(game.buildObjectRecur(spec),Core.Item)
		self.assertEqual(len(calls),1)

	def testFactoryProductTypeIsValidated(self):
		game = self.makeGame()
		game.creatureFactory = {"bad creature":lambda: \
			Core.Item("not a creature","",1,1,"wood")}
		spec = {"__class__":"factoryCreature","name":"bad creature"}

		self.assertIs(game.resolveSpecClass(spec),Core.Creature)
		with self.assertRaisesRegex(TypeError,
		"factoryCreature 'bad creature' returned Item"):
			game.buildObjectRecur(spec)

	def testNestedTetherFieldsRejectIDs(self):
		for field in ("occupants","riders","covering"):
			with self.subTest(field=field):
				game = self.makeGame()
				owner = {"__class__":"Creature","name":"owner",field:[42]}
				dependent = {"__class__":"Creature","id":42,"name":"dependent"}
				room = {"__class__":"Room","name":"Cave","permanents":[],
					"items":[],"creatures":[owner,dependent,{"__class__":"Player"}]}
				world = {"cave":room}
				playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()
				with self.assertRaisesRegex(ValueError,
				f"{field} entries must be nested object specifications"):
					game.normalizeWorldData(world,playerSpec)

	def testLockRejectsUnknownKeyID(self):
		game = self.makeGame()
		room = {"__class__":"Room","name":"Cave","domain":"","desc":"",
			"links":{},"permanents":[],"items":[{"__class__":"Lockbox",
			"name":"chest","desc":"","weight":1,"durability":1,
			"composition":"wood","items":[],"capacity":10,"keyids":[999],
			"locked":True}],"creatures":[{"__class__":"Player"}],
			"ceiling":"stone","walls":"stone","floor":"stone"}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		with self.assertRaisesRegex(ValueError,
		"Lock chest references unknown key ID 999"):
			game.buildWorld({"cave":room},playerSpec)

	def testLockAllowsReservedSkeletonKeyID(self):
		game = self.makeGame()
		room = {"__class__":"Room","name":"Cave","domain":"","desc":"",
			"links":{},"permanents":[],"items":[{"__class__":"Lockbox",
			"name":"chest","desc":"","weight":1,"durability":1,
			"composition":"wood","items":[],"capacity":10,"keyids":[-1],
			"locked":True}],"creatures":[{"__class__":"Player"}],
			"ceiling":"stone","walls":"stone","floor":"stone"}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		game.buildWorld({"cave":room},playerSpec)

	def testPermanentPlashMustBeInfinite(self):
		game = self.makeGame()
		plash = {"__class__":"Plash","name":"spring","weight":20,
			"composition":"freshwater"}
		room = {"__class__":"Room","name":"Cave","domain":"","desc":"",
			"links":{},"permanents":[plash],"items":[],
			"creatures":[{"__class__":"Player"}],"floor":"stone"}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		with self.assertRaisesRegex(ValueError,
		"Permanent Plash spring must be infinite"):
			game.buildWorld({"cave":room},playerSpec)

	def testInfinitePermanentPlashLoads(self):
		game = self.makeGame()
		plash = {"__class__":"Plash","name":"spring","weight":20,
			"composition":"freshwater","infinite":10}
		room = {"__class__":"Room","name":"Cave","domain":"","desc":"",
			"links":{},"permanents":[plash],"items":[],
			"creatures":[{"__class__":"Player"}],"floor":"stone"}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		world,player = game.buildWorld({"cave":room},playerSpec)

		self.assertIn(next(obj for obj in world["cave"].permanents \
			if isinstance(obj,Items.Plash)),world["cave"].permanents)

	def testPortalDirectionsResolveDistinctPairsAndAliases(self):
		game = self.makeGame()
		worldSpec = {
			"alpha":self.makeRoomSpec("alpha",[
				self.makePortalSpec("crossroads",{"east":"port:ab",
					"through":"port:ab","north":"port:ac"})],hasPlayer=True),
			"beta":self.makeRoomSpec("beta",[
				self.makePortalSpec("beta gate",{"west":"port:ab"})]),
			"gamma":self.makeRoomSpec("gamma",[
				self.makePortalSpec("gamma gate",{"south":"port:ac"})])}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		world,player = game.buildWorld(worldSpec,playerSpec)
		crossroads = world["alpha"].items[0]
		betaGate = world["beta"].items[0]
		gammaGate = world["gamma"].items[0]

		self.assertIs(crossroads.links["east"],betaGate)
		self.assertIs(crossroads.links["through"],betaGate)
		self.assertIs(betaGate.links["west"],crossroads)
		self.assertIs(crossroads.links["north"],gammaGate)
		self.assertIs(gammaGate.links["south"],crossroads)

	def testPortalResolvesOneWayRoomAndObjectTargets(self):
		game = self.makeGame()
		target = {"__class__":"Item","name":"beacon","desc":"","weight":1,
			"durability":1,"composition":"stone","id":42}
		container = {"__class__":"Box","name":"vault","desc":"","weight":5,
			"durability":10,"composition":"iron","id":43,"items":[],
			"capacity":20,"closed":False}
		worldSpec = {
			"alpha":self.makeRoomSpec("alpha",[
				self.makePortalSpec("one-way gate",{"room":"beta","object":42,
					"container":43})],hasPlayer=True),
			"beta":self.makeRoomSpec("beta",[target,container])}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		world,player = game.buildWorld(worldSpec,playerSpec)
		portal = world["alpha"].items[0]
		beacon = world["beta"].items[0]
		vault = world["beta"].items[1]

		self.assertIs(portal.links["room"],world["beta"])
		self.assertIs(portal.links["object"],beacon)
		self.assertIs(portal.links["container"],vault)
		self.assertIs(portal.getNewLocation("room"),world["beta"])
		self.assertIs(portal.getNewLocation("object"),world["beta"])
		self.assertIs(portal.getNewLocation("container"),vault)

	def testPortalPairRejectsThreeEndpoints(self):
		game = self.makeGame()
		worldSpec = {
			"alpha":self.makeRoomSpec("alpha",[
				self.makePortalSpec("alpha gate",{"in":"port:shared"})],
				hasPlayer=True),
			"beta":self.makeRoomSpec("beta",[
				self.makePortalSpec("beta gate",{"in":"port:shared"})]),
			"gamma":self.makeRoomSpec("gamma",[
				self.makePortalSpec("gamma gate",{"in":"port:shared"})])}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		with self.assertRaisesRegex(ValueError,
		"Portal link port:shared joins 3 portals"):
			game.buildWorld(worldSpec,playerSpec)

	def testPortalPairAllowsContainerEndpoint(self):
		game = self.makeGame()
		container = {"__class__":"Box","name":"box","desc":"","weight":5,
			"durability":10,"composition":"wood","items":[],"capacity":20,
			"links":{"beyond":"port:shared"}}
		worldSpec = {
			"alpha":self.makeRoomSpec("alpha",[container],hasPlayer=True),
			"beta":self.makeRoomSpec("beta",[
				self.makePortalSpec("gate",{"in":"port:shared"})])}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		world,player = game.buildWorld(worldSpec,playerSpec)
		box = world["alpha"].items[0]
		gate = world["beta"].items[0]
		self.assertIs(box.links["beyond"],gate)
		self.assertIs(gate.links["in"],box)

		portalLinkIds = {}
		boxLinks = box.convertToJSON(portalLinkIds)["links"]
		gateLinks = gate.convertToJSON(portalLinkIds)["links"]
		self.assertEqual(boxLinks["beyond"],"port:0")
		self.assertEqual(gateLinks["in"],"port:0")

	def testPortalSerializationUsesFreshTypedReferences(self):
		game = self.makeGame()
		target = {"__class__":"Item","name":"beacon","desc":"","weight":1,
			"durability":1,"composition":"stone","id":42}
		worldSpec = {
			"alpha":self.makeRoomSpec("alpha",[
				self.makePortalSpec("alpha gate",{"east":"port:pair",
					"room":"beta","object":42})],hasPlayer=True),
			"beta":self.makeRoomSpec("beta",[target,
				self.makePortalSpec("beta gate",{"west":"port:pair"})])}
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()
		world,player = game.buildWorld(worldSpec,playerSpec)
		alphaGate = world["alpha"].items[0]
		betaGate = world["beta"].items[1]

		firstSave = json.loads(json.dumps(world,cls=Menu.worldEncoder))
		firstLinks = firstSave["alpha"]["items"][0]["links"]
		self.assertEqual(firstLinks["east"],"port:0")
		self.assertEqual(firstLinks["room"],"beta")
		self.assertEqual(firstLinks["object"],42)

		Core.Portal.resolveLinkPair("runtime",[(alphaGate,"east"),
			(alphaGate,"through"),(betaGate,"west")])
		secondSave = json.loads(json.dumps(world,cls=Menu.worldEncoder))
		secondLinks = secondSave["alpha"]["items"][0]["links"]
		self.assertEqual(secondLinks["east"],"port:0")
		self.assertEqual(secondLinks["through"],"port:0")
		self.assertFalse(hasattr(alphaGate,"compressedLinks"))

	def testWorldEncoderUsesPlayerPlaceholder(self):
		player = Core.Player("Tester","",29,[1]*10,0,0)
		encoded = json.loads(json.dumps(player,cls=Menu.worldEncoder))
		self.assertEqual(encoded,{"__class__":"Player"})

	def testNewPlayerUsesRawPipeline(self):
		game = self.makeGame()
		player = Core.Player("Tester","",29,[1,2,3,4,5,6,7,8,9,10],0,0,
			inv=[Items.factory["compass"]()])
		playerSpec = json.loads(json.dumps(player.convertToJSON(),cls=Menu.worldEncoder))
		game.dlogForest = Menu.readDialogue(os.path.join(ROOT,"gamedata","Dialogue.json"))
		worldData = Menu.readWorldJSON(os.path.join(ROOT,"gamedata","World.json"))
		world,builtPlayer = game.buildWorld(worldData,playerSpec)
		self.assertIsNot(builtPlayer,player)
		self.assertIs(builtPlayer.parent,world["cave"])
		self.assertEqual((builtPlayer.spd,builtPlayer.skl),(2,3))
		self.assertEqual(builtPlayer.inv[0].name,"compass")
		self.assertTrue(all(item is Core.EmptyGear() \
			for item in builtPlayer.gear.values()))

	def testRawPlayerPipeline(self):
		game = self.makeGame()
		game.dlogForest = Menu.readDialogue(os.path.join(ROOT,"gamedata","Dialogue.json"))
		playerData = Core.Player("Loaded","",29,[2]*10,0,0).convertToJSON()
		worldData = Menu.readWorldJSON(os.path.join(ROOT,"gamedata","World.json"))
		world,player = game.buildWorld(worldData,playerData)
		self.assertEqual(player.name,"Loaded")
		self.assertIs(player.parent,world["cave"])
		self.assertIs(player.platform,world["cave"].floor)

	def testOmittedPlatformGroundsButExplicitNullFloats(self):
		game = self.makeGame()
		grounded = {"__class__":"Item","name":"grounded","desc":"",
			"weight":1,"durability":1,"composition":"stone"}
		groundedFlying = {"__class__":"Item","name":"grounded flying","desc":"",
			"weight":1,"durability":1,"composition":"stone",
			"status":[["flying",-1]]}
		floating = {"__class__":"Item","name":"floating","desc":"",
			"weight":1,"durability":1,"composition":"stone","platform":None}
		roomSpec = self.makeRoomSpec("cave",[grounded,groundedFlying,floating],
			hasPlayer=True)
		playerSpec = Core.Player("Tester","",29,[1]*10,0,0).convertToJSON()

		world,player = game.buildWorld({"cave":roomSpec},playerSpec)

		self.assertIs(world["cave"].items[0].platform,world["cave"].floor)
		self.assertIs(world["cave"].items[1].platform,world["cave"].floor)
		self.assertIsNone(world["cave"].items[2].platform)

	def testCurrentSaveRoundTrip(self):
		game = self.makeGame()
		dialogue = Menu.readDialogue(os.path.join(ROOT,"gamedata","Dialogue.json"))
		game.dlogForest = dialogue
		playerSpec = Core.Player("Round Trip","",29,[3]*10,0,0).convertToJSON()
		worldData = Menu.readWorldJSON(os.path.join(ROOT,"gamedata","World.json"))
		world,player = game.buildWorld(worldData,playerSpec)

		savedWorld = json.loads(json.dumps(world,cls=Menu.worldEncoder))
		savedPlayer = json.loads(json.dumps(player.convertToJSON(),cls=Menu.worldEncoder))
		reloadedGame = self.makeGame()
		reloadedGame.dlogForest = dialogue
		reloadedWorld,reloadedPlayer = reloadedGame.buildWorld(savedWorld,savedPlayer)

		self.assertEqual(reloadedPlayer.name,"Round Trip")
		self.assertIs(reloadedPlayer.parent,reloadedWorld["cave"])
		self.assertIs(reloadedPlayer.platform,reloadedWorld["cave"].floor)


if __name__ == "__main__":
	unittest.main()