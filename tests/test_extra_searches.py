from main import Search


def test_dym():
	html = '''
		<h2>Did you mean:</h2>
		<div class="row">
			<div class="col-lg-6">
				<div class="list-group">
	
					<a href="/warmane/Icecrown_Alliance?search=Accurate+Huge+Citrine&amp;time=all" class="list-group-item list-group-item-action">Accurate Huge Citrine</a>
	
					<a href="/warmane/Icecrown_Alliance?search=Perfect+Accurate+Huge+Citrine&amp;time=all" class="list-group-item list-group-item-action">Perfect Accurate Huge Citrine</a>
	
				</div>
			</div>
		</div>
	'''

	extra_searches = list(Search.find_searches(html))
	assert extra_searches == [
		{'_faction': 'Alliance',
			'_realm': 'Icecrown',
			'_server': 'warmane',
			'_term': 'Accurate Huge Citrine'
		},
	    {
		 '_faction': 'Alliance',
		  '_realm': 'Icecrown',
		  '_server': 'warmane',
		  '_term': 'Perfect Accurate Huge Citrine'
	    }
	]


	log = '2021-02-27 23:20:36.831 | INFO     | __main__:store:115 - {"url": "https://localhost/dalaran-wow/Algalon_Horde?search=Venomshroud%20Belt&time=all", "times": ["2018-12-04 03:12:56", "2018-12-04 14:08:02", "2018-12-05 04:00:24", "2018-12-05 14:03:12", "2018-12-06 03:40:16", "2018-12-06 13:56:17", "2018-12-07 03:47:10", "2018-12-07 13:58:01", "2018-12-09 13:33:10", "2018-12-10 03:53:42", "2018-12-23 13:46:50", "2018-12-24 04:41:44", "2018-12-24 13:50:08", "2019-02-17 04:23:32", "2019-02-19 04:16:05", "2019-02-19 14:41:48", "2019-02-21 04:06:20", "2019-02-21 13:42:21", "2019-04-15 13:26:17", "2019-04-16 03:42:06", "2019-08-18 23:48:43", "2019-08-19 09:35:54", "2019-08-20 00:33:56", "2019-08-20 09:44:43", "2019-08-31 09:23:30", "2019-08-31 23:16:40", "2019-09-01 09:39:35", "2019-09-01 23:08:25", "2019-09-03 09:07:07", "2019-09-03 23:10:49", "2019-09-04 09:16:46", "2019-09-04 23:13:51"]}'
	searches = Search.find_searches(log)
	print(searches)