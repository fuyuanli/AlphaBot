# -*- coding: utf-8 -*- 

import os
import logging
import json
import time

from bot.base_dir import _base_dir
from bot import Bot

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger('init')
logger.setLevel(logging.INFO)

def main():
	logger.info('Alpha Bot v1.0')
	config = init_config()
	setup_logging()
	bot = Bot(config)
	bot.start()

def init_config():
	config_file = os.path.join(_base_dir, 'configs', 'config.json')

	config = {}

	if os.path.isfile(config_file):
		logger.info('Load config from /configs/config.json')
		with open(config_file, 'rb') as data:
			config.update(json.load(data))
	else:
		logger.error('No /configs/config.json or specified config')

	if config['auth_service'] not in ['ptc', 'google']:
		logging.error("Invalid Auth service specified! ('ptc' or 'google')")
		return None

	return config

def setup_logging():
	logging.getLogger("requests").setLevel(logging.ERROR)
	logging.getLogger("websocket").setLevel(logging.ERROR)
	logging.getLogger("socketio").setLevel(logging.ERROR)
	logging.getLogger("engineio").setLevel(logging.ERROR)
	logging.getLogger("socketIO-client").setLevel(logging.ERROR)
	logging.getLogger("pgoapi").setLevel(logging.ERROR)
	logging.getLogger("rpc_api").setLevel(logging.ERROR)


if __name__ == '__main__':
	main()