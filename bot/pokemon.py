# -*- coding: utf-8 -*-

import base64

class Pokemon(object):
	def __init__(self, pokemon_list, pokemon_data, encounter):
		self.id = pokemon_data.get('id', 0)
		self.num = int(pokemon_data.get('pokemon_id', 0))
		self.name = pokemon_list[int(self.num) - 1]['Name']
		self.cp = pokemon_data.get('cp', 0)
		self.attack = pokemon_data.get('individual_attack', 0)
		self.defense = pokemon_data.get('individual_defense', 0)
		self.stamina = pokemon_data.get('individual_stamina', 0)
		self.encounter_id = long(base64.b64decode(encounter.get('encounter_id', 0))) if encounter else None,
		self.spawn_point_id = encounter.get('spawnpoint_id', 0) if encounter else None
		self.is_egg = False

	def iv(self):
		return round((self.attack + self.defense + self.stamina) / 45.0, 2)

	def iv_display(self):
		return '{}/{}/{}'.format(self.attack, self.defense, self.stamina)