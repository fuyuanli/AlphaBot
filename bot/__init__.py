# -*- coding: utf-8 -*-

import os
import logging
import json

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

from bot.base_dir import _base_dir
from bot.item_list import Item


logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

class Bot(object):
	def __init__(self, config):
		self.config = config
		self.pokemon_list = json.load(
			open(os.path.join(_base_dir, 'data', 'pokemon.json'))
		)
		self.item_list = json.load(
			open(os.path.join(_base_dir, 'data', 'items.json'))	
		)
		self.recent_forts = [None]
		self.api = None
		self.lat = None
		self.lon = None
		self.latest_inventory = None

	def start(self):
		self.api = pgoapi.PGoApi()

		self.get_location()
		self.set_location()
		self.api.set_authentication(
			provider = self.config['auth_service'], 
			username = self.config['username'],
			password = self.config['password']
		)
		self.api.activate_signature(self.config['encrypt_location'])

		self.trainer_info()

	def trainer_info(self):
		player = self.get_player_data()
		items_stock = self.current_inventory()
		
		pokecoins = 0
		stardust = 0

		if 'amount' in player['currencies'][0]:
			pokecoins = player['currencies'][0]['amount']

		if 'amount' in player['currencies'][1]:
			stardust = player['currencies'][1]['amount']

		logger = logging.getLogger(player['username'])
		logger.setLevel(logging.INFO)

		logger.info(
			'Stardust: {}'.format(stardust) +
			' | Pokecoins: {}'.format(pokecoins)
		)

		logger.info(
			'PokeBalls: ' + str(items_stock[1]) +
			' | GreatBalls: ' + str(items_stock[2]) +
			' | UltraBalls: ' + str(items_stock[3]) +
			' | MasterBalls: ' + str(items_stock[4]))

		logger.info(
			'RazzBerries: ' + str(items_stock[701]) +
			' | BlukBerries: ' + str(items_stock[702]) +
			' | NanabBerries: ' + str(items_stock[703]))

		logger.info(
			'LuckyEgg: ' + str(items_stock[301]) +
			' | Incubator: ' + str(items_stock[902]) +
			' | TroyDisk: ' + str(items_stock[501]))

		logger.info(
			'Potion: ' + str(items_stock[101]) +
			' | SuperPotion: ' + str(items_stock[102]) +
			' | HyperPotion: ' + str(items_stock[103]) +
			' | MaxPotion: ' + str(items_stock[104]))

		logger.info(
			'Incense: ' + str(items_stock[401]) +
			' | IncenseSpicy: ' + str(items_stock[402]) +
			' | IncenseCool: ' + str(items_stock[403]))

		logger.info(
			'Revive: ' + str(items_stock[201]) +
			' | MaxRevive: ' + str(items_stock[202]))

	def get_player_data(self):
		player_data = self.api.get_player()['responses']['GET_PLAYER']['player_data']
		#logger.info('Trainer Name - ' + player_data['username'])
		return player_data

	def set_location(self):
		logger.info('Set location - ' + str(self.lat) + ', ' + str(self.lon))
		self.api.set_position(self.lat, self.lon, 0.0)

	def get_location(self):
		lat, lon = self.config['location'].split(',')
		self.lat = float(lat.strip())
		self.lon = float(lon.strip())

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
		if self.latest_inventory is None:
			self.latest_inventory = self.api.get_inventory()

		return self.latest_inventory
