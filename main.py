import os
import re
import sys
import json
import requests

from datetime import datetime
from lxml import etree, html
from settings import *

def _league_get_seasons(league_uri):
    data = html.fromstring(requests.get(league_uri).text)
    anchors = data.xpath(".//div[@class='dropdown-content']/a")
    season_refs = dict()
    
    for anchor in anchors:
        text = anchor.text
        season = re.findall(season_re, text)

        if len(season):
            season = season[0]
            season_refs[season] = anchor.attrib["href"]
            
    return season_refs

def load_leagues_info():
    data = html.fromstring(requests.get(leagues_uri).text)
    rows = data.xpath(".//table[@class='sortable']/tbody/tr")
    leagues = dict()
    
    for row in rows:
        try:
        #if True:
            row = row.xpath("./td")[0]
            anchor = row.xpath("./a")[0]
            href = anchor.attrib["href"]
            country = anchor.text.strip(" -")
            league  = row.xpath("./a/font")[0].text
            
            leagues.setdefault(country, dict())
            league_uri = "/".join((base_uri, href))

            season_refs = _league_get_seasons(league_uri)
            leagues[country][league] = {"url" : league_uri,
                                        "seasons" : season_refs}
            
        except Exception as e:
            infologger.info(str(e))

    return leagues

def season2date(date, season):
    year = get_season_year(season)
    date = date.strip().split(" ")
    month = date[-1]
    day  = date[-2]
    
    if month in second_half_months:
        year += 1

    date = " ".join((str(year), month, day))
    
    return datetime.strptime(date, "%Y %b %d").strftime("%Y-%m-%d")

def date2season(date):
    year = date.year
    if date.month > 0 and date.month < 6:
        season = "/".join((str(year - 1), str(year)[-2:]))
        return season
    
    season = "/".join((str(year), str(year + 1)[-2:]))
    return season

def _is_current_season(season):
    return date2season(datetime.now()) == season

def _future_column_map(columns, season):
    if len(columns) != 4:
        error = "Something went wrong!\n\
                 Got {} columns for the future match record!\n\
                 Expected: 4 columns".format(len(columns))
        raise Exception(error)

    date = columns[0].xpath(".//font")[0].text.strip()
    date = season2date(date, season)
    comands = columns[2].text.strip()

    return (date, comands, season)

def _past_column_map(columns, season):
    if len(columns) != 5:
        error = "Something went wrong!\n\
                 Got {} columns for the future match record!\n\
                 Expected: 5 columns".format(len(columns))
        raise Exception(error)

    date = columns[0].xpath(".//font")[0].text.strip()
    date = season2date(date, season)
    comands = columns[2].text.strip()
    score = columns[3].xpath(".//font/b")[0].text.strip()

    return (date, comands, score, season)

def _leagues_get_matches(leagues, season):
    infologger.info("Loading matches for {} season...".format(season))
    is_current_season = _is_current_season(season)

    for country in leagues:
        for league in leagues[country]:
            league_seasons = leagues[country][league]["seasons"]
            if season not in league_seasons:
                infologger.info("Season {} not in league country {} seasons!".format(season, country, league))
                infologger.info(json.dumps(league_seasons))
                continue

            league_tag = re.findall(league_tag_re, league_seasons[season])
            if not len(league_tag):
                infologger.info("Could not extract league tag from uri")
                infologger.info(league_seasons[season])
                continue

            league_tag = league_tag[0]
            matches_uri = get_match_uri(league_tag)
            data = html.fromstring(requests.get(matches_uri).text)

            if is_current_season:
                future_matches = list()
                rows = data.xpath(".//table[@id='btable']/tr[@class='trow3']")
            else:
                rows = data.xpath(".//table[@id='btable']/tr[@class='odd']")
            
            matches = list()
            for row in rows:
                columns = row.xpath(".//td")
                n_columns = len(columns)

                try:
                    if n_columns == 5:
                        match_data = _past_column_map(columns, season)
                        matches.append(match_data)
                    
                    elif n_columns == 4 and is_current_season:
                        future_data = _future_column_map(columns, season)
                        future_matches.append(future_data)
                except:
                    infologger.info("Columns doesn't match defined pattern!")
                    infologger.info(etree.tostring(row,  pretty_print=True))

            if is_current_season:
                leagues[country][league]["future"] = future_matches
            
            leagues[country][league].setdefault("matches", list())
            leagues[country][league]["matches"] += matches

def get_comands_info(leagues):
    comands = dict()

    for country in leagues:
        for league in leagues[country]:
            if "matches"  in leagues[country][league]:
                matches = sorted(leagues[country][league]["matches"], key=lambda x:x[0], reverse=True)
                for match in matches:
                    comand = match[1].split("-")
                    comand1 = comand[0].strip()
                    comand2 = comand[-1].strip()
                    scores  = match[2].split("-")
                    score1  = scores[0].strip()
                    score2  = scores[-1].strip()

                    data1 = (league, country, comand2, (score1, score2), match[3], match[0])
                    data2 = (league, country, comand1, (score2, score1), match[3], match[0])

                    comands.setdefault(comand1, {"matches" : list()})
                    comands.setdefault(comand2, {"matches" : list()})
                    comands[comand1].setdefault("matches", list())
                    comands[comand2].setdefault("matches", list())

                    comands[comand1]["matches"].append(data1)
                    comands[comand2]["matches"].append(data2)
            
            else:
                infologger.info("{} {} league has no matches yet ?!".format(country, league))

            if "future" in leagues[country][league]:
                future_matches = sorted(leagues[country][league]["future"], key=lambda x:x[0], reverse=True)
                for match in future_matches:
                    comand = match[1].split("-")
                    comand1 = comand[0].strip()
                    comand2 = comand[-1].strip()

                    comands.setdefault(comand1, {"future" : list()})
                    comands.setdefault(comand2, {"future" : list()})
                    comands[comand1].setdefault("future", list())
                    comands[comand2].setdefault("future", list())

                    data1 = (league, country, comand2, match[2], match[0])
                    data2 = (league, country, comand2, match[2], match[0])

                    comands[comand1]["future"].append(data1)
                    comands[comand2]["future"].append(data2)

    return comands

def _last_n_season_matches(comands, comand, n_seasons, datefrom=None):
    if not datefrom:
        datefrom = datetime.now()

    data = []
    season = date2season(datefrom)
    target_year = get_season_year(season) - n_seasons

    for match in comands[comand]["matches"]:
        mseason = match[-2]
        mdate = datetime.strptime(match[-1], "%Y-%m-%d")

        if datefrom < mdate:
            continue

        if get_season_year(mseason) < target_year:
            break

        data.append(match)

    return data

def load_data_n_seasons(leagues, n_seasons):
    season = date2season(datetime.now())
    year = get_season_year(season)

    _leagues_get_matches(leagues, season)

    for y in range(1, n_seasons):
        season =  "/".join((str(year-y), str(year-y+1)[-2:]))
        _leagues_get_matches(leagues, season)

def update_data(leagues):
    existed_matches = set()
    last_date = ""
    
    for country in leagues:
        for league in leagues[country]:
            matches = sorted(leagues[country][league]["matches"], key=lambda x: x[0], reverse=True)
            existed_matches.update(set(matches))
            if matches[0][0] > last_date:
                last_date = matches[0][0]

    season = date2season(datetime.now())
    last_season = date2season(datetime.strptime(last_date,"%Y-%m-%d"))
    new_leagues = load_leagues_info()

    if season != last_season:
        year = get_season_year(season)
        last_year = get_season_year(last_season)
        _load_data_n_seasons(new_leagues, year-last_year)
    
    else:
        _leagues_get_matches(new_leagues, season)

    new_countries = set(new_leagues.keys()).difference(set(leagues.keys()))
    for country in new_countries:
        leagues.setdefault(country, dict())

    for country in leagues:
        new_league = set(new_leagues[country].keys()).difference(set(leagues[country].keys()))
        for league in new_league:
            leagues[country][league] = new_leagues[country][league]

    for country in leagues:
        for league in leagues[country]:
            leagues[country][league]["future"] = new_leagues[country][league]["future"]
            if not len(leagues[country][league]["matches"]):
                leagues[country][league]["matches"] = new_leagues[country][league]["matches"]
                continue

            for match in new_leagues[country][league]["matches"]:
                if match not in existed_matches:
                    leagues[country][league]["matches"].append(match)

            leagues[country][league]["matches"] = sorted(leagues[country][league]["matches"], key=lambda x: x[0], reverse=True)

def filter_comands(comands):
    core_comands = set()
    for comand in comands:
        if "matches" not in comands[comand]:
            continue

        matches = comands[comand]["matches"]
        leagues = set([" ".join((match[0], match[1])) for match in matches])
        seasons = set([match[-2] for match in matches]) 

        if len(leagues) == 1:
            core_comands.add(comand)
    return core_comands

def calc_draw_stat(comands, n_seasons=4):
    cc = filter_comands(comands)
    draw_stat = list()

    for comand in cc:
        data = _last_n_season_matches(comands, comand, n_seasons)
        data = sorted(data, key=lambda x:x[-1], reverse=True)

        if not len(data):
            infologger.info("No data for comand {}!".format(comand))

        curr_series = 0
        n_draws  = 0.0
        draw_series = []

        for match in data:
            score1, score2 = match[-3]
            if score1 == score2:
                draw_series.append(curr_series)
                curr_series = 0
                n_draws += 1
            else:
                curr_series += 1
        
        if curr_series:
            draw_series.append(curr_series)
            curr_series = 0
        
        curr_series = draw_series[0]
        draw_series = draw_series[1:]

        if len(draw_series):
            max_series = max(draw_series)
            mean_series = sum(draw_series) / len(draw_series)
        else:
            max_series = 0.0
            mean_series = 0.0

        league = data[0][0]
        country = data[0][1]

        if "future" in comands[comand]:
            n_future_matches = len(comands[comand]["future"])
        else:
            n_future_matches = 0

        delta = max_series - curr_series
        mean_draws = float(n_draws)/len(data)
        dstat = (country, league, max_series, mean_series, curr_series, n_future_matches, delta)

        draw_stat.append(dstat)

    return draw_stat

def write_stat(stat, stat_file):
    with open(stat_file, "w") as f:
        f.write("Лига, Команда, Максимальная серия, Средняя серия, Текущая серия, Дельта, Игр до конца сезона\n")
        
        for s in stat:
            f.write(", ".join([str(i) for i in s]))

def main():
    if os.path.exists(json_file):
        leagues = json.loads(json_file)
        update_data(leagues)

    else:
        leagues = load_leagues_info()
        load_data_n_seasons(leagues, load_n_seasons)
        
        with open(json_file, "w") as f:
            f.write(json.dumps(leagues))

    comands = get_comands_info(leagues)
    draw_stat = calc_draw_stat(comands)
    write_stat(draw_stat, stat_file)

if __name__ == "__main__":
    main()