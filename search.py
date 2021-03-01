import json
import random
import re
import requests
import requests.utils
import trio

from loguru import logger
from urllib.parse import unquote, quote

class CaptchaError(Exception):
	pass

class Realm:
	def __init__(self, realm, server):
		self.server = server
		self.realm = realm

search_link_pattern = re.compile('([a-z-]+)/([a-zA-Z-]+)_([a-zA-Z-]+)\?search=([a-zA-Z0-9-_+%]+)')

class Search(dict):
	def __init__(self, server, realm, faction, term):
		super().__init__(dict(_server=server, _realm=realm, _faction=faction, _term=term))
		self._server = server
		self._realm = realm
		self._faction = faction
		self._term = term

	def __str__(self):
		return f'{{"_server": "{self._server}", "_realm": "{self._realm}", "_faction": "{self._faction}", "_term": "{self._term}"}}'

	def __eq__(self, other):
		if type(other) is dict:
			other = Search(**{k.replace('_', ''): v for k, v in other.items()})
		return self._server == other._server and \
			self._realm == other._realm and \
			self._faction == other._faction and \
			self._term == other._term

	@staticmethod
	def load_data_from_html(html: str):
		x_pos = html.find('[{"type": "scattergl", "x": ')
		x_start = x_pos + len('[{"type": "scattergl", "x": ')

		y_pos = html.find('"], "y": ')
		y_start = y_pos + len('"], "y": ')
		x_text = html[x_start:y_pos + 2]

		end_pos = html.find(', "text":', y_start)
		y_text = html[y_start:end_pos]

		try:
			times = json.loads(x_text)
			prices = json.loads(y_text)
			return times, prices

		except Exception as e:
			if 'Oops! ' in str(e):
				raise ValueError(e)
			if 'Please complete the ReCaptcha' in html:
				raise CaptchaError()
			if 'Internel Server Error' in html:
				raise ValueError(e)
			raise e

	@staticmethod
	def find_searches(html):
		return [Search(s, r, f, unquote(t.replace('+', ' '))) for s, r, f, t in search_link_pattern.findall(html)]

	@property
	def uri(self):
		return f'{self._server}/{self._realm}_{self._faction}?search={quote(self._term)}&time=all'

	@property
	def url(self):
		return f'https://localhost/{self.uri}'

	def randomize_user_agent(self):
		user_agents = [
			'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
			'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.16; rv:85.0) Gecko/20100101 Firefox/85.0',
			'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36',
			'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'
			'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/85.0',
			'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/85.0'
		]

		requests.utils.default_user_agent = lambda: random.choice(user_agents)

	async def store(self, n, proxy, lock, search, active):
		try:
			self.randomize_user_agent()
			with trio.fail_after(30):
				html = (await proxy.get(self.url)).text

			if '500 Internal Server Error' in html:
				logger.warning(f'{self._term} server error')
				await trio.sleep(5)
				await self.store(n, proxy, lock, search, active)
				async with lock:
					try:
						active.remove(search)
					except ValueError:
						pass
				return

			oops = html.find('Oops!')
			next_line = html.find('\n', oops)
			if oops != -1:
				if 'ReCaptcha' in html[oops:next_line]:
					raise CaptchaError(html[oops:next_line])

				logger.error(f'{self.url}')
				logger.error(f'{html[oops:next_line]}')
				logger.error(f'{self._term} was not found in the database')
				async with lock:
					try:
						active.remove(search)
					except ValueError:
						pass
				return

			extra_searches = Search.find_searches(html)
			if len(extra_searches) > 0:
				for search in extra_searches:
					n.start_soon(search.store, n, proxy, lock, search, active)
					await trio.sleep(1)

			times, prices = Search.load_data_from_html(html)
			times_str = str(times).replace("'", "\"")
			logger.info(f'{{"url": "{self.url}", "times": {times_str}}}')
			logger.info(f'{{"url": "{self.url}", "prices": {prices}}}')
		except CaptchaError as e:
			logger.warning(f'{self._term} captcha required')
			await trio.sleep(15)
			await self.store(n, proxy, lock, search, active)

		except Exception as e:
			logger.warning(f'{self._term} retrying')
			logger.warning(e)
			await trio.sleep(5)
			await self.store(n, proxy, lock, search, active)

		async with lock:
			try:
				active.remove(search)
			except ValueError:
				pass