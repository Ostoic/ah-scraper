import datetime
import json
import os
import random
import trio
from itertools import product
from loguru import logger

from proxy import ProxyBank, load_proxies
from search import Search, Realm

def exists_already(data, search):
	for existing_search in Search.find_searches(data):
		if search == existing_search:
			return True

	return False

def load_searches(realms, factions, search_terms):
	searches = []

	if os.path.exists('searches.txt'):
		with open('searches.txt', 'r') as f:
			search_data = json.load(f)
			for data in search_data:
				searches.append(Search(**{k.replace('_', ''): v for k, v in data.items()}))
			print(len(searches))
	else:
		for realm, faction, term in product(realms, factions, search_terms):
			searches.append(Search(realm.server, realm.realm, faction, term))

		random.shuffle(searches)
		with open('searches.txt', 'w') as f:
			json.dump(searches, f)

	print(f'length before {len(searches)}')
	with open('ah-data-big.log', 'r') as f:
		data = f.read()

	final_searches = []
	for search in searches:
		found = data.find(search.url)
		if found == -1:
			continue

		# context = data[found - len("ERROR    | __main__:search:store:115 - ") : found + len(search.url)]
		# print(f'{context=}')
		if not search.url in data:
			final_searches.append(search)

	print(f'length after {len(final_searches)}')
	return final_searches

async def crawl_website(process_new_data=False):
	search_terms = []
	with open('items.txt', 'r') as f:
		for term in f:
			search_terms.append(term.rstrip())

	factions = ['Alliance', 'Horde']
	realms = [Realm('Icecrown', 'warmane'), Realm('Algalon', 'dalaran-wow')]
	if process_new_data:
		leftover_searches = load_searches(realms, factions, search_terms)
		with open('new-searches.txt', 'w') as f:
			json.dump(leftover_searches, f)

	else:
		leftover_searches = []
		with open('new-searches.txt', 'r') as f:
			search_data = json.load(f)
			for data in search_data:
				leftover_searches.append(Search(**{k.replace('_', ''): v for k, v in data.items()}))

	proxy = ProxyBank(load_proxies())
	concurrency = 60
	logger.add('ah-data.log')
	logger.info(f'{len(leftover_searches)} searches loaded')

	active_lock = trio.Lock()
	random.shuffle(leftover_searches)
	total_size = len(leftover_searches)
	start_time = datetime.datetime.now()
	async with trio.open_nursery() as n:
		active = []
		while len(leftover_searches) > 0:
			# Pool of `concurrency` number of tasks that are active at any given time. When a task is complete,
			# a new one is pulled from one of the leftover searches. If our pool is saturated then we wait.
			while len(active) >= concurrency:
				await trio.sleep(1)

			while len(leftover_searches) > 0 and len(active) < concurrency:
				search = leftover_searches.pop(0)
				async with active_lock:
					active.append(search)
				n.start_soon(search.store, n, proxy, active_lock, search, active)
				await trio.sleep(1)

			i = total_size - len(leftover_searches)
			time_elapsed = (datetime.datetime.now() - start_time)
			logger.info(f'{100 * i / total_size}% complete')
			logger.info(f'Time elapsed: {time_elapsed}')
			logger.info(f'{len(active)} active tasks')

			if time_elapsed.seconds > 0:
				speed = i / time_elapsed.seconds
				time_left = datetime.timedelta(seconds=len(leftover_searches) // speed)
				logger.info(f'Estimated time left: {time_left}')

if __name__ == '__main__':
	trio.run(crawl_website)