import re
import logging

infologger = logging.getLogger("soccer-loader")
infologger.setLevel(logging.INFO)
infologger.addHandler(logging.FileHandler(filename="soccer-loader.log"))
infologger.addHandler(logging.StreamHandler())

base_uri = "https://www.soccerstats.com"
leagues_uri = "/".join((base_uri, "leagues.asp"))
second_half_months = set(["May", "Apr", "Mar", "Feb", "Jan"])

get_season_year = lambda x: int(x.split("/")[0])
get_match_uri = lambda x: "/".join((base_uri, "results.asp?league={}&pmtype=bydate".format(x)))

league_tag_re = re.compile("league=([^&]+)")
season_re = re.compile("\d{4}\/\d{2}")

json_file = "soccer.json"
stat_file = "soccer.csv"
load_n_seasons = 4

is_debug = True