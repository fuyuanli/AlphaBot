# -*- coding: utf-8 -*-

import time

class BattleAction(object):
	def __init__(self, gym, info, pokemon, repeat, target_index, server_ms):
		self.battle_id = info.get('battle_id', '')
		self.gym_id = gym.id,
		self.action_start_ms = 0,
		self.duration_ms = 500,
		self.target_index = target_index,
		self.server_ms = server_ms,
		self.repeat = repeat,
		self.active_pokemon_id = pokemon.id,
		self.damage_windows_start_timestamp_mss = 0,
		self.damage_windows_end_timestamp_mss = 0,
		self.target_pokemon_id = info.get('defender', {}).get('active_pokemon', {}).get('pokemon_data', {}).get('id', 0)
		self.last_retrieved_actions = info.get('battle_log', {}).get('battle_actions', {})[-1]

		self.generate_action_time()

	def generate_action_time(self):
		self.action_start_ms = self.server_ms[0] + 100 * self.repeat[0]
		self.damage_windows_end_timestamp_mss = self.action_start_ms + self.duration_ms[0]
		self.damage_windows_start_timestamp_mss = self.action_start_ms + self.duration_ms[0] - 200

	def get_action(self):
		action_dict = {
            "action_start_ms": self.action_start_ms,
            "target_index": self.target_index[0],
            "damage_windows_start_timestamp_mss": self.damage_windows_start_timestamp_mss,
            "damage_windows_end_timestamp_mss": self.damage_windows_end_timestamp_mss,
            "active_pokemon_id": self.active_pokemon_id,
            "target_pokemon_id": self.target_pokemon_id,
            "duration_ms": self.duration_ms[0],
            "Type": 1
		}

		return action_dict

