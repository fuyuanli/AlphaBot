# -*- coding: utf-8 -*-

from bot.pokemon import Pokemon

TEAM_BLUE = 1
TEAM_RED = 2
TEAM_YELLOW = 3

class Gym(object):
	def __init__(self, gym_data, pokemon_list):
		self.name = gym_data.get('name', None)
		self.owned_team = gym_data.get('gym_state', {}).get('fort_data', {}).get('owned_by_team', 0)
		self.id = gym_data.get('gym_state', {}).get('fort_data', {}).get('id', 0)
		self.lat = gym_data.get('gym_state', {}).get('fort_data', {}).get('latitude', 0)
		self.lng = gym_data.get('gym_state', {}).get('fort_data', {}).get('longitude', 0)
		self.point = gym_data.get('gym_state', {}).get('fort_data', {}).get('gym_points', 0)
		self.pokemons = self.get_member_pokemons(gym_data, pokemon_list)

	def get_member_pokemons(self, gym_data, pokemon_list):
		pokemons = []
		members = gym_data.get('gym_state', {}).get('memberships', {})
		for member in members:
			pokemon = member.get('pokemon_data', {})
			if pokemon:
				pokemons.append(Pokemon(pokemon_list, pokemon, None))

		return pokemons