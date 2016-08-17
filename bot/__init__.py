# -*- coding: utf-8 -*-

import os
import logging
import json
import time
import gpxpy.geo
import requests
import base64
from random import uniform

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

from bot.base_dir import _base_dir
from bot.item_list import Item
from bot.pokemon import Pokemon

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger('init')
logger.setLevel(logging.INFO)

SPIN_REQUEST_RESULT_SUCCESS = 1
SPIN_REQUEST_RESULT_OUT_OF_RANGE = 2
SPIN_REQUEST_RESULT_IN_COOLDOWN_PERIOD = 3
SPIN_REQUEST_RESULT_INVENTORY_FULL = 4

CATCH_STATUS_SUCCESS = 1
CATCH_STATUS_FAILED = 2
CATCH_STATUS_VANISHED = 3

ENCOUNTER_STATUS_SUCCESS = 1
ENCOUNTER_STATUS_NOT_IN_RANGE = 5
ENCOUNTER_STATUS_POKEMON_INVENTORY_FULL = 7

ITEM_POKEBALL = 1
ITEM_GREATBALL = 2
ITEM_ULTRABALL = 3
ITEM_RAZZBERRY = 701

URL = 'http://p.cve.tw:5566/'

class Bot(object):
	def __init__(self, config):
		self.config = config
		self.pokemon_list = json.load(
			open(os.path.join(_base_dir, 'data', 'pokemon.json'))
		)
		self.item_list = json.load(
			open(os.path.join(_base_dir, 'data', 'items.json'))	
		)
		self.catched_pokemon = [None]
		self.fort = None
		self.api = None
		self.lat = None
		self.lng = None
		self.latest_inventory = None
		self.logger = logger
		self.level = 0
		self.farming_mode = False

	def start(self):
		self.api = pgoapi.PGoApi()

		self.get_location()

		self.logger.info('Set location - ' + str(self.lat) + ', ' + str(self.lng))
		self.set_location(self.lat, self.lng)
		self.api.set_authentication(
			provider = self.config['auth_service'], 
			username = self.config['username'],
			password = self.config['password']
		)
		self.api.activate_signature(self.config['encrypt_location'])

		self.trainer_info()
		self.check_inventory()
		self.check_all_pokemon_if_transfer()

		while True:
			self.spin_fort()
			if not self.farming_mode:
				self.snipe_pokemon()
				self.check_awarded_badges()

	def check_all_pokemon_if_transfer(self):
		pokemons = self.current_pokemons_inventory()
		for pokemon_data in pokemons:
			if not pokemon_data.get('is_egg', None):
				pokemon = Pokemon(self.pokemon_list, pokemon_data, None)
				self.pokemon_if_transfer(pokemon)
			
	def pokemon_if_transfer(self, pokemon):
		if self.config['transfer_filter']['logic'] == 'or':
			if pokemon.cp < self.config['transfer_filter']['below_cp'] and pokemon.iv() < self.config['transfer_filter']['below_iv']:
				self.release_pokemon(pokemon)
				self.logger.info(
					'Tranferred %s [CP %s] [IV %s] [A/D/S %s]',
					pokemon.name,
					pokemon.cp,
					pokemon.iv(),
					pokemon.iv_display()
				)
		else:
			if pokemon.cp < self.config['transfer_filter']['below_cp'] or pokemon.iv() < self.config['transfer_filter']['below_iv']:
				self.release_pokemon(pokemon)
				self.logger.info(
					'Tranferred %s [CP %s] [IV %s] [A/D/S %s]',
					pokemon.name,
					pokemon.cp,
					pokemon.iv(),
					pokemon.iv_display()
				)

	def release_pokemon(self, pokemon):
		time.sleep(1)
		self.api.release_pokemon(
			pokemon_id = pokemon.id
		)

	def snipe_pokemon(self):
		pokemons = self.get_pokemons()

		snipe_count = 0
		for pokemon_encounter in pokemons:
			if pokemon_encounter['encounter_id'] not in self.catched_pokemon:
				if snipe_count >= self.config['catch_time_every_run']:
					break

				self.set_location(pokemon_encounter['latitude'], pokemon_encounter['longitude'])
				response = self.create_encounter_call(pokemon_encounter)

				pokemon_data = response['wild_pokemon']['pokemon_data'] if 'wild_pokemon' in response else None
				if not pokemon_data:
					self.logger.warning(
						'The pokemon maybe disappeared.'
					)
					self.set_location(self.lat, self.lng)
					snipe_count += 1
					continue


				pokemon = Pokemon(self.pokemon_list, pokemon_data, pokemon_encounter)

				self.logger.info(
					'%s Appeared! [CP %s] [IV %s] [A/D/S %s]',
					pokemon.name,
					pokemon.cp,
					pokemon.iv(),
					pokemon.iv_display()
				)

				self.set_location(self.lat, self.lng)

				catch_rate = [0] + response['capture_probability']['capture_probability']
				self.do_catch(pokemon, catch_rate)
				self.catched_pokemon.append(pokemon_encounter['encounter_id'])
				
				snipe_count += 1
				

	def do_catch(self, pokemon, catch_rate_by_ball):
		berry_id = ITEM_RAZZBERRY
		maximum_ball = ITEM_ULTRABALL
		ideal_catch_rate_before_throw = 0.35

		items_stock = self.current_inventory()

		while True:
			current_ball = ITEM_POKEBALL
			while items_stock[current_ball] == 0 and current_ball < maximum_ball:
				current_ball += 1
			if items_stock[current_ball] == 0:
				self.logger.warning(
					'No usable pokeball found.'
				)

			num_next_balls = 0
			next_ball = current_ball
			while next_ball < maximum_ball:
				next_ball += 1
				num_next_balls += items_stock[next_ball]

			best_ball = current_ball
			while best_ball < maximum_ball:
				best_ball += 1
				if catch_rate_by_ball[current_ball] < ideal_catch_rate_before_throw and items_stock[best_ball] > 0:
					current_ball = best_ball

			reticle_size_parameter = self.normalized_reticle_size(self.config['catch_randomize_reticle_factor'])
			spin_modifier_parameter = self.spin_modifier(self.config['catch_randomize_spin_factor'])

			self.logger.info(
				'Used %s, with chance %s - %s left.',
				self.item_list[str(current_ball)],
				'{0:.2f}%'.format(catch_rate_by_ball[current_ball] * 100),
				str(items_stock[current_ball])
			)

			time.sleep(1)
			response_dict = self.api.catch_pokemon(
				encounter_id = pokemon.encounter_id[0],
				pokeball = int(current_ball),
				normalized_reticle_size=float(reticle_size_parameter),
				spawn_point_id = str(pokemon.spawn_point_id),
				hit_pokemon = 1,
				spin_modifier = float(spin_modifier_parameter),
				normalized_hit_position = 1.0
			)

			try:
				catch_pokemon_status = response_dict['responses']['CATCH_POKEMON']['status']
			except KeyError:
				break

			if catch_pokemon_status == CATCH_STATUS_FAILED:
				self.logger.info(
					'%s capture failed.. trying again!',
					pokemon.name
				)
				time.sleep(2)
				continue

			elif catch_pokemon_status == CATCH_STATUS_VANISHED:
				self.logger.warning(
					'%s vanished!',
					pokemon.name
				)

			elif catch_pokemon_status == CATCH_STATUS_SUCCESS:
				self.logger.info(
					'Captured %s! [CP %s] [IV %s] [%s] [+%d exp]',
					pokemon.name,
					pokemon.cp,
					pokemon.iv(),
					pokemon.iv_display(),
					sum(response_dict['responses']['CATCH_POKEMON']['capture_award']['xp'])
				)
				self.pokemon_if_transfer(pokemon)

			break

	def normalized_reticle_size(self, factor):
		minimum = 1.0
		maximum = 1.950
		return uniform(
			minimum + (maximum - minimum) * factor,
			maximum)

	def spin_modifier(self, factor):
		minimum = 0.0
		maximum = 1.0
		return uniform(
			minimum + (maximum - minimum) * factor,
			maximum)



	def get_pokemons(self):
		self.logger.info(
			'Now do some magic to get pokemons..'
		)

		responses = requests.get(URL + 'raw_data?pokemon=true&pokestops=false&gyms=false&scanned=false&spawnpoints=false').json()['pokemons']
		pokemons = sorted(responses, key=lambda k: k['disappear_time']) 

		return pokemons

	def create_encounter_call(self, pokemon):		
		time.sleep(1)
		response_dict = self.api.encounter(
			encounter_id = long(base64.b64decode(pokemon['encounter_id'])),
			spawn_point_id = pokemon['spawnpoint_id'],
			player_latitude = self.lat,
			player_longitude = self.lng
		)['responses']['ENCOUNTER']

		return response_dict

	def spin_fort(self):
		self.walk_to_fort()

		time.sleep(1)
		response_dict = self.api.fort_search(
			fort_id = self.fort['id'],
			fort_latitude = self.fort['latitude'],
			fort_longitude = self.fort['longitude'],
			player_latitude = self.lat,
			player_longitude = self.lng
		)

		if 'responses' in response_dict and 'FORT_SEARCH' in response_dict['responses']:
			spin_details = response_dict['responses']['FORT_SEARCH']
			spin_result = spin_details.get('result', -1)
			if spin_result == SPIN_REQUEST_RESULT_SUCCESS:
				experience_awarded = spin_details.get('experience_awarded', 0)


				items_awarded = self.get_items_awarded_from_fort_spinned(response_dict)

				if experience_awarded or items_awarded:
					self.logger.info(
						"Spun pokestop! Experience awarded: %d. Items awarded: %s",
						experience_awarded,
						items_awarded
					)

					self.check_inventory()
					self.check_level()

	def walk_to_fort(self):
		self.nearst_fort()
		fort_detail = self.fort_detail()

		olatitude = fort_detail['latitude']
		olongitude = fort_detail['longitude']

		dist = closest = gpxpy.geo.haversine_distance(
			self.lat, 
			self.lng, 
			olatitude, 
			olongitude
		)

		self.logger.info(
			"Walk to %s at %f, %f. (%d seconds)",
			fort_detail['name'],
			olatitude,
			olongitude,
			int(dist / self.config['step_diameter'])
		)

		divisions = closest / self.config['step_diameter']
		if divisions == 0:
			divisions = 1

		dLat = (self.lat - olatitude) / divisions
		dLon = (self.lng - olongitude) / divisions

		epsilon = 10
		delay = 10
		
		steps = 1
		while dist > epsilon:
			self.lat -= dLat
			self.lng -= dLon
			steps %= delay
			if steps == 0:
				self.set_location(
					self.lat,
					self.lng
				)
			time.sleep(1)
			dist = gpxpy.geo.haversine_distance(
				self.lat,
				self.lng,
				olatitude,
				olongitude
			)
			steps += 1

			if steps % 10 == 0:
				self.logger.info(
					"Walk to %s at %f, %f. (%d seconds)",
					fort_detail['name'],
					olatitude,
					olongitude,
					int(dist / self.config['step_diameter'])
				)

		steps -= 1
		if steps % delay > 0:
			time.sleep(delay - steps)
			self.set_location(
				self.lat,
				self.lng
			)

	def fort_detail(self):
		time.sleep(1)

		response_dict = self.api.fort_details(
			fort_id = self.fort['id'],
			latitude = self.fort['latitude'],
			longitude = self.fort['longitude']
		)

		return response_dict['responses']['FORT_DETAILS']

	def nearst_fort(self):
		cells = self.get_map_objects()
		forts = []

		for cell in cells:
			if 'forts' in cell and len(cell['forts']):
				forts += cell['forts']

		for fort in forts:
			if 'cooldown_complete_timestamp_ms' not in fort:
				self.fort = fort
				break

	def get_map_objects(self):
		time.sleep(1)

		cell_id = util.get_cell_ids(self.lat, self.lng)
		timestamp = [0, ] * len(cell_id) 

		map_dict = self.api.get_map_objects(
			latitude = self.lat,
			longitude = self.lng,
			since_timestamp_ms = timestamp,
			cell_id = cell_id
		)

		map_objects = map_dict.get(
			'responses', {}
		).get('GET_MAP_OBJECTS', {})
		status = map_objects.get('status', None)

		map_cells = []
		if status and status == 1:
			map_cells = map_objects['map_cells']
			map_cells.sort(
				key=lambda x: gpxpy.geo.haversine_distance(
					self.lat, 
					self.lng, 
					x['forts'][0]['latitude'], 
					x['forts'][0]['longitude']
				) if x.get('forts', []) else 1e6
			)
		
		return map_cells


	def trainer_info(self):
		player = self.get_player_data()
		items_stock = self.current_inventory()
		
		self.check_level()
		info = self.get_stats()
		
		pokecoins = 0
		stardust = 0

		if 'amount' in player['currencies'][0]:
			pokecoins = player['currencies'][0]['amount']

		if 'amount' in player['currencies'][1]:
			stardust = player['currencies'][1]['amount']

		self.logger = logging.getLogger(player['username'])
		self.logger.setLevel(logging.INFO)

		self.logger.info('')

		self.logger.info(
			'Trainer Name: ' + str(player['username']) +
			' | Lv: ' + str(info['level']) + 
			' (' + str(info['experience']) + '/' + str(info['next_level_xp']) + ')'
		)

		self.logger.info(
			'Stardust: ' + str(stardust) +
			' | Pokecoins: ' + str(pokecoins)
		)

		self.logger.info(
			'PokeBalls: ' + str(items_stock[1]) +
			' | GreatBalls: ' + str(items_stock[2]) +
			' | UltraBalls: ' + str(items_stock[3]) +
			' | MasterBalls: ' + str(items_stock[4]))

		self.logger.info(
			'RazzBerries: ' + str(items_stock[701]) +
			' | BlukBerries: ' + str(items_stock[702]) +
			' | NanabBerries: ' + str(items_stock[703]))

		self.logger.info(
			'LuckyEgg: ' + str(items_stock[301]) +
			' | Incubator: ' + str(items_stock[902]) +
			' | TroyDisk: ' + str(items_stock[501]))

		self.logger.info(
			'Potion: ' + str(items_stock[101]) +
			' | SuperPotion: ' + str(items_stock[102]) +
			' | HyperPotion: ' + str(items_stock[103]) +
			' | MaxPotion: ' + str(items_stock[104]))

		self.logger.info(
			'Incense: ' + str(items_stock[401]) +
			' | IncenseSpicy: ' + str(items_stock[402]) +
			' | IncenseCool: ' + str(items_stock[403]))

		self.logger.info(
			'Revive: ' + str(items_stock[201]) +
			' | MaxRevive: ' + str(items_stock[202]))

	def get_player_data(self):
		time.sleep(1)
		player_data = self.api.get_player()['responses']['GET_PLAYER']['player_data']
		
		return player_data

	def set_location(self, lat, lng):
		time.sleep(1)
		self.api.set_position(lat, lng, 0.0)

	def get_location(self):
		lat, lon = self.config['location'].split(',')
		self.lat = float(lat.strip())
		self.lng = float(lon.strip())

	def current_pokemons_inventory(self):
		inventory_dict = self.get_inventory()['responses']['GET_INVENTORY'][
			'inventory_delta']['inventory_items']

		pokemons_stock = []

		for pokemons in inventory_dict:
			pokemon_dict = pokemons.get('inventory_item_data', {}).get('pokemon_data', {})

			if pokemon_dict:
				pokemons_stock.append(pokemon_dict)

		return pokemons_stock

	def current_inventory(self):
		inventory_dict = self.get_inventory()['responses']['GET_INVENTORY'][
			'inventory_delta']['inventory_items']

		items_stock = {x.value: 0 for x in list(Item)}

		for item in inventory_dict:
			item_dict = item.get('inventory_item_data', {}).get('item', {})
			item_count = item_dict.get('count')
			item_id = item_dict.get('item_id')

			if item_count and item_id:
				if item_id in items_stock:
					items_stock[item_id] = item_count

		return items_stock

	def get_inventory(self):
		time.sleep(1)
		self.latest_inventory = self.api.get_inventory()

		return self.latest_inventory

	def check_inventory(self):
		time.sleep(1)
		inventory_dict = self.get_inventory()['responses']['GET_INVENTORY'][
			'inventory_delta']['inventory_items']

		for item in inventory_dict:
			item_dict = item.get('inventory_item_data', {}).get('item', {})
			item_count = item_dict.get('count')
			item_id = item_dict.get('item_id')
			
			if item_count and item_id:
				item_limit = self.config['item_limit'].get(self.item_list[str(item_id)])

				if item_limit and item_count > item_limit:
					self.recycle_inventory(item_id, item_count - item_limit)
					self.logger.info(
						'Recycled: %s x%d',
						self.item_list[str(item_id)],
						item_count - item_limit
					)

	def recycle_inventory(self, item_id, count):
		time.sleep(1)
		self.api.recycle_inventory_item(
			item_id = item_id,
			count = count
		)

	def get_stats(self):
		stats = {}

		time.sleep(1)
		response_dict = self.api.get_inventory()['responses']['GET_INVENTORY'][
			'inventory_delta']['inventory_items']

		for items in response_dict:
			stats = items.get('inventory_item_data', {}).get('player_stats', {})

			if stats:
				return stats

		return stats

	def check_level(self):
		stats = self.get_stats()

		if stats['level'] > self.level:
			time.sleep(1)
			self.api.level_up_rewards(
				level = stats['level']
			)

			if self.level != 0:
				self.logger.info(
					'Level up from %d to %d.',
					self.level,
					stats['level']
				)

			self.level = stats['level']

	def get_items_awarded_from_fort_spinned(self, response_dict):
		items_awarded = response_dict['responses']['FORT_SEARCH'].get('items_awarded', {})
		items = {}

		if items_awarded:
			for item_awarded in items_awarded:
				item_awarded_id = item_awarded['item_id']
				item_awarded_name = self.item_list[str(item_awarded_id)]
				item_awarded_count = item_awarded['item_count']

				if not item_awarded_name in items:
					items[item_awarded_name] = item_awarded_count
				else:
					items[item_awarded_name] += item_awarded_count
		
		items_format_strings = ''
		for key, val in items.items():
			items_format_strings += key + ' x' + str(val) + ' '
		
		return items_format_strings

	def check_awarded_badges(self):
		time.sleep(1)
		self.api.check_awarded_badges()



