'''
	@ Harris Christiansen (code@HarrisChristiansen.com)
	Generals.io Automated Client - https://github.com/harrischristiansen/generals-bot
	Tile: Objects for representing Generals IO Tiles
'''

from queue import Queue

from .constants import *

class Tile(object):
	def __init__(self, gamemap, x, y):
		# Public Properties
		self.x = x					# Integer X Coordinate
		self.y = y					# Integer Y Coordinate
		self.tile = TILE_FOG		# Integer Tile Type (TILE_OBSTACLE, TILE_FOG, TILE_MOUNTAIN, TILE_EMPTY, or player_ID)
		self.turn_captured = 0		# Integer Turn Tile Last Captured
		self.turn_held = 0			# Integer Last Turn Held
		self.army = 0				# Integer Army Count
		self.isCity = False			# Boolean isCity
		self.isSwamp = False		# Boolean isSwamp
		self.isGeneral = False		# Boolean isGeneral

		# Private Properties
		self._map = gamemap			# Pointer to Map Object
		self._general_index = -1	# Player Index if tile is a general

	def __repr__(self):
		return "(%d,%d) %d (%d)" % (self.x, self.y, self.tile, self.army)

	'''def __eq__(self, other):
			return (other != None and self.x==other.x and self.y==other.y)'''

	def __lt__(self, other):
			return self.army < other.army

	def setNeighbors(self, gamemap):
		self._map = gamemap
		self._setNeighbors()

	def setIsSwamp(self, isSwamp):
		self.isSwamp = isSwamp

	def update(self, gamemap, tile, army, isCity=False, isGeneral=False):
		self._map = gamemap

		if self.tile < 0 or tile >= TILE_MOUNTAIN or (tile < TILE_MOUNTAIN and self.isSelf()): # Tile should be updated
			if (tile >= 0 or self.tile >= 0) and self.tile != tile: # Remember Discovered Tiles
				self.turn_captured = gamemap.turn
				if self.tile >= 0:
					gamemap.tiles[self.tile].remove(self)
				if tile >= 0:
					gamemap.tiles[tile].append(self)
			if tile == gamemap.player_index:
				self.turn_held = gamemap.turn
			self.tile = tile
		if self.army == 0 or army > 0 or tile >= TILE_MOUNTAIN or self.isSwamp: # Remember Discovered Armies
			self.army = army

		if isCity:
			self.isCity = True
			self.isGeneral = False
			if self not in gamemap.cities:
				gamemap.cities.append(self)
			if self._general_index != -1 and self._general_index < 8:
				gamemap.generals[self._general_index] = None
				self._general_index = -1
		elif isGeneral:
			self.isGeneral = True
			gamemap.generals[tile] = self
			self._general_index = self.tile

	################################ Tile Properties ################################

	def distance_to(self, dest):
		if dest != None:
			return abs(self.x - dest.x) + abs(self.y - dest.y)
		return 0

	def neighbors(self, includeSwamps=False, includeCities=True):
		neighbors = []
		for tile in self._neighbors:
			if (tile.tile != TILE_OBSTACLE or tile.isCity or tile.isGeneral) and tile.tile != TILE_MOUNTAIN and (includeSwamps or not tile.isSwamp) and (includeCities or not tile.isCity):
				neighbors.append(tile)
		return neighbors

	def isValidTarget(self): # Check tile to verify reachability
		if self.tile < TILE_EMPTY:
			return False
		for tile in self.neighbors(includeSwamps=True):
			if tile.turn_held > 0:
				return True
		return False

	def isSelf(self):
		return self.tile == self._map.player_index

	def isOnTeam(self):
		if self.isSelf():
			return True
		return False

	def shouldNotAttack(self):
		if self.isOnTeam():
			return True
		if self.tile in self._map.do_not_attack_players:
			return True
		return False

	################################ Select Other Tiles ################################

	def nearest_tile_in_path(self, path):
		dest = None
		dest_distance = 9999
		for tile in path:
			distance = self.distance_to(tile)
			if distance < tile_distance:
				dest = tile
				dest_distance = distance

		return dest

	def nearest_target_tile(self):
		max_target_army = self.army * 2 + 14

		dest = None
		dest_distance = 9999
		for x in range(self._map.cols): # Check Each Square
			for y in range(self._map.rows):
				tile = self._map.grid[y][x]
				if not tile.isValidTarget() or tile.shouldNotAttack() or tile.army > max_target_army: # Non Target Tiles
					continue

				distance = self.distance_to(tile)
				if tile.isGeneral: # Generals appear closer
					distance = distance * 0.09
				elif tile.isCity: # Cities vary distance based on size, but appear closer
					distance = distance * sorted((0.17, (tile.army / (3.2*self.army)), 20))[1]

				if tile.tile == TILE_EMPTY: # Empties appear further away
					distance = distance * 4.3
				if tile.army > self.army: # Larger targets appear further away
					distance = distance * (1.5*tile.army/self.army)
				if tile.isSwamp: # Swamps appear further away
					distance = distance * 10
					if tile.turn_held > 0: # Swamps which have been held appear even further away
						distance = distance * 20

				if distance < dest_distance:
					dest = tile
					dest_distance = distance

		return dest

	################################ Pathfinding ################################

	def path_to(self, dest, includeCities=False):
		if dest == None:
			return []

		frontier = Queue()
		frontier.put(self)
		came_from = {}
		came_from[self] = None
		army_count = {}
		army_count[self] = self.army

		while not frontier.empty():
			current = frontier.get()

			if current == dest: # Found Destination
				break

			for next in current.neighbors(includeSwamps=True, includeCities=includeCities):
				if next not in came_from and (next.isOnTeam() or next == dest or next.army < army_count[current]):
					#priority = self.distance(next, dest)
					frontier.put(next)
					came_from[next] = current
					if next.isOnTeam():
						army_count[next] = army_count[current] + (next.army - 1)
					else:
						army_count[next] = army_count[current] - (next.army + 1)

		if dest not in came_from: # Did not find dest
			if includeCities:
				return []
			else:
				return self.path_to(dest, includeCities=True)

		# Create Path List
		path = _path_reconstruct(came_from, dest)

		return path

	################################ PRIVATE FUNCTIONS ################################

	def _setNeighbors(self):
		x = self.x
		y = self.y

		neighbors = []
		for dy, dx in DIRECTIONS:
			if self._map.isValidPosition(x+dx, y+dy):
				tile = self._map.grid[y+dy][x+dx]
				neighbors.append(tile)

		self._neighbors = neighbors
		return neighbors

def _path_reconstruct(came_from, dest):
	current = dest
	path = [current]
	try:
		while came_from[current] != None:
			current = came_from[current]
			path.append(current)
	except KeyError:
		None
	path.reverse()

	return path