import re
import time
import requests
import datetime

from requests.sessions import Session
from lxml.html import HtmlElement
from fuzzywuzzy import fuzz
from lxml import html

class League(object):
    def __init__(self, name, country):
        self.name = name
        self.country = country
        
    def __hash__(self):
        return hash(self.__str__())
    
    def __str__(self):
        return ".".join((str(self.name), str(self.country), "league"))
    
    def __eq__(self, other):
        return self.name == other.name and self.country == other.country
    
    def __ne__(self, other):
        return not __eq__(self, other)
        
class Team(object):
    def __init__(self, name, country):
        self.name = name
        self.country = country
        
    def __hash__(self):
        return hash(self.__str__())
    
    def __str__(self):
        return ".".join((str(self.name), str(self.country), "team"))
    
    def __eq__(self, other):
        return self.name == other.name and self.country == other.country
    
    def __ne__(self, other):
        return not __eq__(self, other)
        
        
class Season(object):
    def __init__(self, year1, year2, leagues=set(), teams=set(), leaguesTeams=list()):
        self.name = "/".join((str(year1)[:2], str(year2)[:2]))
        self.year1 = year1 
        self.year2 = year2
        self.leagues = leagues
        self.teams = teams
        self.leaguesTeams = leaguesTeams
        
    def AddTeam(self, team: Team, league: League):
        self.teams.add(team)
        self.leagues.add(league)
        self.leaguesTeams.append((league, team))
        
    def Check(self) -> (bool, str):
        for item in self.leaguesTeams:
            league, team = item
            if league not in self.leagues:
                return False, "{} not in leagues".format(league)
            
            if team not in self.teams:
                return False, "{} not in teams".format(team)
            
        for league in self.leagues:
            if len([i[0] for i in self.leaguesTeams if i[0] == league]) != 1:
                return False, ""
            
        for team in self.teams:
            if len([i[1] for i in self.leaguesTeams if i[1] == team]) != 1:
                return False
            

class Match(object):
    def __init__(self, team1, team2, date, score, flags=0):
        self.team1 = team1
        self.team2 = team2
        self.date = date
        self.score = score
        self.flags = flags
        
def packMatchFlags(isLeague, isCup, isPlayoff, isFriendly, isUpperDivision, isLowerDivision):
    flags = 1 # lower bit always set to 1, to check that flags was initialized
    flags |= int(isLeague) << 1
    flags |= int(isCup) << 2
    flags |= int(isPlayoff) << 3
    flags |= int(isFriendly) << 4
    flags |= int(isUpperDivision) << 5
    flags |= int(isLowerDivision) << 6
    return flags

def isLeague(match):
    if 1 & match.flags:
        return (1 << 1) & flags
    
    return -1

def isCup(match):
    if 1 & match.flags:
        return (1 << 2) & flags
    return -1

def isPlayoff(match):
    if 1 & match.flags:
        return (1 << 3) & flags
    return -1

def isFriendly(match):
    if 1 & match.flags:
        return (1 << 4) & flags
    return -1

def isUpperDivision(match):
    if 1 & match.flags:
        return (1 << 5) & flags
    return -1

def isLowerDivision(match):
    if 1 & match.flags:
        return (1 << 6) & flags
    return -1

def isInternational(match):
    return int(match.team1.country != match.team2.country)

def getSeason(date):
    currentYear = date.year
    if date.month <= 6:
        return "/".join((str(currentYear-1)[2:],str(currentYear)[2:]))
    return "/".join((str(currentYear)[2:],str(currentYear+1)[2:]))

def AddUrlParams(url:str, **kwargs) -> str:
    sep = "?"
    if url.find("?") != -1:
        sep = "&"
        
    params = "&".join(["{}={}".format(k,kwargs[k]) for k in kwargs])
    return sep.join((url, params))

def JoinUrlPath(url: str, path:str) -> str:
    assert(url.find("?") == -1)
    assert(url.find("&") == -1)
    
    sep = ""
    if url[-1] != "/" and path[0] != "/":
        sep = "/"
    
    if url[-1] == "/" and path[0] == "/":
        url = url[:-1]
        
    return sep.join((url, path))

seasonNameDigitsRe = re.compile("\s*(\d{4})\s*")
seasonName2Re = re.compile("\s*\d{4}\s*-\s*\d{4}\s*")

def NormalizeSeasonName(name: str) -> str:
    if "-" in name:
        assert(re.match(seasonName2Re, name))
        year1,year2 = name.split("-")
        return "/".join((year1,year2[2:]))
            
    if "/" not in name:
        year = re.findall(seasonNameDigitsRe, name)        
        assert(len(year) == 1)
        year = int(year[0])
        
        return "/".join((str(year),str(year+1)[2:]))
    
    return name

def LoadLeagues(url: str, sess:Session, timeout=5) -> (list, dict):
    leagues = list()
    leaguesPathes = dict()
    
    r = sess.get(url, verify=False, timeout=timeout)
    doc = html.fromstring(r.text)
    
    items = doc.xpath(".//ul[@class=\"countries\"]/li")
    for item in items:
        if "title" in item.attrib:
            country = item.attrib["title"]
            continue
        
        anchor = item.xpath("./a")
        assert(len(anchor) == 1)
        assert("href" in anchor[0].attrib)
        
        anchor = anchor[0]
        leagueName = anchor.text
        leagueLink = anchor.attrib["href"]
        league = League(leagueName, country)
        leaguesPathes[league] = leagueLink
        leagues.append(league)
    
    return leagues, leaguesPathes
    
extractDataKeyRe = re.compile('''\"data_key\"\s*\:\s*\"([^\"]+)\"''')
baseUrl = "https://24score.pro/"
backendLoadPageDataUrl = JoinUrlPath(baseUrl, "/backend/load_page_data.php")

def LoadLeagueTeams(url: str, timeout=5) -> (list, list):
    teamNames = list()
    teamPathes = list()
    
    r = sess.get(url, verify=False, timeout=timeout)
    dataKey = re.findall(extractDataKeyRe, r.text)
    if len(dataKey) == 0:
        print("Could not load data from page {}".format(url))
        return [], []
        
    assert(len(dataKey) == 1)
    dataKey = dataKey[0]
    newUrl = AddUrlParams(backendLoadPageDataUrl, data_key=dataKey)
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url, 
    }
    
    r = sess.get(newUrl, headers=headers, verify=False, timeout=timeout)
    doc = html.fromstring(r.text)
    standingsTable = doc.xpath(".//div[contains(@class,\"data_0_all\")]")

    if len(standingsTable) == 0:
        print("Could not get teams for the league on page {}".format(url))
        return [], []
        
    assert(len(standingsTable) == 1)
    standingsTable = standingsTable[0]
    standingsTable = standingsTable.xpath(".//table[contains(@class, \"standings\")]")

    assert(len(standingsTable) == 1)
    standingsTable = standingsTable[0]
    
    for team in standingsTable.xpath(".//td[@class=\"left\"]/a"):
        assert("href" in team.attrib)
        teamPathes.append(team.attrib["href"])
        teamNames.append(team.text)
        
    return teamNames, teamPathes
    
    
def LoadSeason(leaguesPathes: dict, year1: int, year2:int, timeout=5, delay=1) -> (Season, dict):
    assert(year2 > year1)
    season = Season(year1, year2)
    seasonName = "/".join((str(year1), str(year2)[2:]))
    teamPathes = dict()

    for league in leaguesPathes:
        leagueUrl = JoinUrlPath(base_url, leaguesPathes[league])
        r = sess.get(leagueUrl, verify=False, timeout=timeout)
        doc = html.fromstring(r.text)
        
        seasonLinkPath = ""
        options = doc.xpath(".//select[@class=\"sel_season\"]/option")
        for opt in options:
            if seasonName == NormalizeSeasonName(opt.text):
                assert("value" in opt.attrib)
                seasonLinkPath = opt.attrib["value"]

        if seasonLinkPath == "":
            print("Could not get link for {} on page {}".format(seasonName, leagueUrl))
            continue 
            
        seasonLink = JoinUrlPath(baseUrl, seasonLinkPath)
        leagueTeamNames, teamLinks = LoadLeagueTeams(seasonLink)
        time.sleep(delay)
        
        assert(len(leagueTeamNames) == len(teamLinks))
        for i in range(len(leagueTeamNames)):
            teamName = leagueTeamNames[i]
            team = Team(teamName, league.country)
            teamPathes[team] = teamLinks[i]
            season.AddTeam(team, league)
            
    return season, teamPathes

def ParseMatchTable(table: HtmlElement) -> list:
    return []
    
def LoadTeamMatches(season:Season, teamPathes:dict, leaguesPathes:dict, timeout=5, delay=0.0):
    for team in teamPathes:
        if team not in season.teams:
            continue
            
        league = list(filter(lambda x: x[1] == team, season.leaguesTeams))
        assert(len(league) > 0)
            
        url = JoinUrlPath(baseUrl, teamPathes[team])
        r = sess.get(leagueUrl, verify=False, timeout=timeout)
        doc = html.fromstring(r.text)
        
        seasonLinkPath = ""
        options = doc.xpath(".//select[@class=\"sel_season\"]/option")
        for opt in options:
            if seasonName == NormalizeSeasonName(opt.text):
                assert("value" in opt.attrib)
                seasonLinkPath = opt.attrib["value"]

        if seasonLinkPath == "":
            print("Could not get link for {} on page {}".format(seasonName, leagueUrl))
            continue 

        seasonLink = JoinUrlPath(baseUrl, seasonLinkPath)
        if seasonLink != url:
            r = sess.get(seasonLink, verify=False, timeout=timeout)
            doc = html.fromstring(r.text)
            
        matchTables = doc.xpath(".//table/")
        for table in matchTables:
            anchor = table.xpath(".//tr/th/a/")
            assert("href" in anchor.attrib)
            tLink = anchor.attrib["href"]
            tName = anchor.text
            
            if tLink == leaguesPathes[league]:  
                pass
    