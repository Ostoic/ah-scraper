import datetime
import random
import re

import requests
import trio
from loguru import logger

address_pattern = re.compile('([0-9][0-9\.]*):([0-9]+)')

def load_proxies():
	proxies = []
	with open('socks5.csv', 'r') as f:
		matches = address_pattern.findall(f.read())
		for match in matches:
			address = (match[0], int(match[1]))
			proxies.append([address, 0])

	logger.info(f'{len(proxies)} proxies loaded')
	return proxies

class ProxyBank:
	def __init__(self, proxies):
		self._proxies = proxies
		random.shuffle(self._proxies)
		self._blacklist_lock = trio.Lock()
		self._blacklist = []

	def __len__(self):
		return len(self._proxies)

	def is_blacklisted(self, index):
		for i, entry in enumerate(self._blacklist):
			if entry['value'] == index:
				return True

		return False

	async def update_blacklist(self, timeout):
		for i, entry in enumerate(self._blacklist):
			if datetime.datetime.now() > entry['timestamp'] + timeout:
				async with self._blacklist_lock:
					self._blacklist.pop(i)
				await self.update_blacklist(timeout=timeout)
				break

	async def blacklist(self, index, timeout=datetime.timedelta(seconds=360)):
		await self.update_blacklist(timeout=timeout)
		async with self._blacklist_lock:
			self._blacklist.append(dict(timestamp=datetime.datetime.now(), value=index))
		logger.warning(f'{self._proxies[index]} blacklisted, {len(self._proxies) - len(self._blacklist)} proxies active')

	def rank_proxies(self):
		self._proxies.sort(key=lambda entry: entry[1], reverse=True)

	async def get(self, url, timeout=datetime.timedelta(seconds=36000)):
		while True:
			await self.update_blacklist(timeout=timeout)
			choice = int(random.random() * len(self))
			if (choice // len(self)) < 0.4:
				while self.is_blacklisted(choice):
					choice = int(random.random() * len(self))
			else:
				choice = 0

			try:
				entry = self._proxies[choice]
				proxy = entry[0]
				result = await trio.to_thread.run_sync(
					lambda: requests.get(
						url,
						proxies=dict(http=f'socks5://{proxy[0]}:{proxy[1]}', https=f'socks5://{proxy[0]}:{proxy[1]}'),
						timeout=10
					)
				)

				entry[1] += 1
				self.rank_proxies()
				return result

			except requests.exceptions.Timeout:
				await self.blacklist(choice, timeout=timeout)
				await trio.sleep(1)