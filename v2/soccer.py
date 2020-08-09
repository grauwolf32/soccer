import re
import time
import requests
from datetime import datetime

from requests.sessions import Session
from lxml.html import HtmlElement
#from fuzzywuzzy import fuzz
from lxml import html

def requestHandler(func):
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            err = False
            
        except Exception as e:
            print(str(e), *args)
            
            res = None
            err = True
        return res, err
            
    return wrapper

class League(object):
    def __init__(self, name:str, country:str):
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
    def __init__(self, name:str, country:str):
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
    def __init__(self, year1, year2): #leagues=set(), teams=set(), leaguesTeams=list()):
        self.name = "/".join((str(year1), str(year2)[2:]))
        self.year1 = year1 
        self.year2 = year2
        self.leagues = set()#leagues
        self.teams = set()#teams
        self.leaguesTeams = list()#leaguesTeams
        
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
    def __init__(self, team1: Team, team2: Team, date:datetime, team1Score:int, team2Score:int, flags=0):
        self.team1 = team1
        self.team2 = team2
        self.date = date
        self.team1Score = team1Score
        self.team2Score = team2Score
        self.flags = flags
        
    def __str__(self):
        return ".".join((str(self.team1), str(self.team2), str(self.date.strftime("%Y-%m-%d")), str(self.team1Score), str(self.team2Score)))
    
    def __hash__(self):
        return hash(self.__str__())
    
    def __eq__(self, other):
        selfTuple  = (self.team1, self.team2, self.date, self.team1Score, self.team2Score, self.flags)
        selfTuple2 = (self.team2, self.team1, self.date, self.team2Score, self.team1Score, self.flags)
        otherTuple = (other.team1, other.team2, other.date, other.team1Score, other.team2Score, other.flags)
        return (selfTuple == otherTuple) or (selfTuple2 == otherTuple)
    
    def __ne__(self, other):
        return not __eq__(self, other)
        
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

def checkLeague(league: League) -> bool:
    if "лига" in league.name.lower():
        return True
    return False

def checkCup(league: League) -> bool:
    if "кубок" in league.name.lower():
        return True
    return False

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

def FindTeamByName(teamName:str, teams: list, country=None) -> list:
    candidates = list()
    
    if country:
        candidates = filter(lambda x: teamName.lower() == x.name.lower() and x.country.lower() == country.lower(), teams)
        return list(set(candidates))
    
    candidates = filter(lambda x: teamName.lower() == x.name.lower(), teams)
    return list(set(candidates))
    
def FindLeagueByName(leagueName: str, leagues:list, country=None) -> list:
    candidates = list()
    
    if country:
        candidates = filter(lambda x: x.name.lower() == leagueName.lower() and x.country.lower() == country.lower(), leagues)
        return list(set(candidates))
    
    candidates = filter(lambda x: x.name.lower() == leagueName.lower(), leagues)
    return list(set(candidates))

def FindLeagueByTeam(team: Team, season: Season) -> list:
    result = filter(lambda x: x[1] == team, season.leaguesTeams)
    result = [i[0] for i in result]
    return list(set(result))
    
requests.packages.urllib3.disable_warnings()
userAgent = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0"
sess = requests.Session()
sess.headers.update({"User-Agent":userAgent})
sess.get = requestHandler(sess.get)

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
    
    r, err = sess.get(url, verify=False, timeout=timeout)
    if err:
        return leagues, leaguesPathes
    
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
        
        if checkLeague(league): # TODO Remove this check with something appropriate
            leaguesPathes[league] = leagueLink
            leagues.append(league)
    
    return leagues, leaguesPathes

extractDataKeyRe = re.compile('''\"data_key\"\s*\:\s*\"([^\"]+)\"''')
baseUrl = "https://24score.pro/"
backendLoadPageDataUrl = JoinUrlPath(baseUrl, "/backend/load_page_data.php")

def LoadLeagueTeams(url: str, timeout=5) -> (list, list):
    teamNames = list()
    teamPathes = list()
    
    r, err = sess.get(url, verify=False, timeout=timeout)
    if err:
        return [], []
    
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
    
    r, err = sess.get(newUrl, headers=headers, verify=False, timeout=timeout)
    if err:
        return [], []
    
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
    seasonLeaguesPathes = dict()

    seasonName = season.name
    teamPathes = dict()

    for league in leaguesPathes:
        leagueUrl = JoinUrlPath(baseUrl, leaguesPathes[league])
        r, err = sess.get(leagueUrl, verify=False, timeout=timeout)
        if err:
            continue
            
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
            
        seasonLeaguesPathes[league] = seasonLinkPath           
        seasonLink = JoinUrlPath(baseUrl, seasonLinkPath)
        leagueTeamNames, teamLinks = LoadLeagueTeams(seasonLink)
        time.sleep(delay)
        
        assert(len(leagueTeamNames) == len(teamLinks))
        for i in range(len(leagueTeamNames)):
            teamName = leagueTeamNames[i]
            team = Team(teamName, league.country)
            teamPathes[team] = teamLinks[i]
            season.AddTeam(team, league)
            
    return season, teamPathes, seasonLeaguesPathes

    matchRe = re.compile("(\d{2}\.\d{2}\.\d{4})\s*([^\-]+)\-\s*([^\d]+)\s*(\d)\:(\d)")

def GetAllTextFromHtmlElement(node: HtmlElement, filterFunc=None) -> list:
    text = list()
    nodeText = node.text
    
    if filterFunc:
        nodeText = filterFunc(nodeText)
    
    text.append(nodeText)
    
    for childNode in node.getchildren():
        childNodeText = GetAllTextFromHtmlElement(childNode, filterFunc)
        if filterFunc:
            childNodeText = filterFunc(childNodeText)
        text.append(childNodeText)
      
    nodeTail = node.tail
    
    if filterFunc:
        nodeTail = filterFunc(nodeTail)
    
    text.append(nodeTail)
    
    return " ".join(text)

def MatchFilterFunc(text):
    if text:
        filteredText = text.strip("\n\t ")
        filteredText = text.replace("\n"," ")
        filteredText = text.replace("\t"," ")
        filteredText = ' '.join([i.strip("\t\n ") for i in filteredText.split(" ") if i != ""])
        return filteredText.strip("\n\t ")
    
    return ""

def ParseLeagueMatchTable(table: HtmlElement, teams: list) -> list:
    matches = set()
    
    for match in table.xpath(".//tr"):
        nodes = match.xpath(".//td")
        if len(nodes) == 0:
            continue
      
        nodeTexts = list()
        for node in nodes:
            nodeTexts.append(GetAllTextFromHtmlElement(node, MatchFilterFunc))
    
        matchText = "".join(nodeTexts)
        matchParams = re.findall(matchRe, matchText)
        
        if len(matchParams) != 1:
            print("Could not parse \"{}\"".format(matchText))
            continue
            
        assert(len(matchParams) == 1)
        matchParams = matchParams[0]
    
        date, team1Name, team2Name, team1Score, team2Score = [i.strip() for i in matchParams]
        date = datetime.strptime(date, "%d.%m.%Y")
        
        team1Score = int(team1Score)
        team2Score = int(team2Score)
        
        team1 = FindTeamByName(team1Name, teams)
  
        if len(team1) != 1:
            print("Could not find team1:", team1Name, " ", matchText)
            continue
                    
        # assert(len(team1) == 1)
        team1 = team1[0]
                
        team2 = FindTeamByName(team2Name, teams)
        if len(team2) != 1:
            print("Could not find team2:", team2Name, " ", matchText)
            continue
                    
        # assert(len(team2) == 1)
        team2 = team2[0]    
        matchFlag = packMatchFlags(True, *([False]*5)) # assume league
        
        m = Match(team1, team2, date, team1Score, team2Score, matchFlag)
        matches.add(m)
        
    return list(matches)
    
def LoadTeamMatches(season:Season, teamPathes:dict, leaguesPathes:dict, timeout=5, delay=0.2) -> list:
    matches = set()
    seasonName = season.name # YYYY/YY
    
    for team in teamPathes:
        if team not in season.teams:
            continue
            
        league = FindLeagueByTeam(team, season)
        #print([str(i) for i in league])
        
        assert(len(league) == 1)
        league = league[0]
            
        url = JoinUrlPath(baseUrl, teamPathes[team])
        r, err = sess.get(url, verify=False, timeout=timeout)  
        if err:
            continue
            
        doc = html.fromstring(r.text)
        time.sleep(delay)
                
        seasonLinkPath = ""
        options = doc.xpath(".//select[@class=\"sel_season\"]/option")
        for opt in options:
            if seasonName == NormalizeSeasonName(opt.text):
                assert("value" in opt.attrib)
                seasonLinkPath = opt.attrib["value"]

        if seasonLinkPath == "":
            print("Could not get link for {} on page {}".format(seasonName, url))
            continue 

        seasonLink = JoinUrlPath(baseUrl, seasonLinkPath)
        if seasonLink != url:
            print(url, seasonLink)
            r, err = sess.get(seasonLink, verify=False, timeout=timeout)
            if err:
                continue
                
            doc = html.fromstring(r.text)
            time.sleep(delay)
            
        matchTables = doc.xpath(".//div[@id=\"all0\"]/table")
        
        for table in matchTables:
            anchor = table.xpath(".//tr/th/a")
            if len(anchor) == 0:
                continue
        
            assert(len(anchor) == 1)
            anchor = anchor[0]
            
            assert("href" in anchor.attrib)
            tLink = anchor.attrib["href"]
            tName = anchor.text
            
            if tLink != leaguesPathes[league]:
                print(tLink, leaguesPathes[league])
                continue
                
            # assert(tLink == leaguesPathes[league])
            teamLeagueMatches = ParseLeagueMatchTable(table, season.teams)
            
            for m in teamLeagueMatches:
                print(m)
                
            if teamLeagueMatches == None:
                print("Some strange error happened on", tLink," for ", tName)
                continue
                
            matches.update(set(teamLeagueMatches))
                
    return list(matches)

def LoadSeasonMatches(year1:int, year2:int, leagues:list, leaguesPathes:dict) -> (Season, list):
    season, teamPathes, seasonLeaguePathes = LoadSeason(leaguesPathes, year1, year2)
    print(seasonLeaguePathes)

    matches = LoadTeamMatches(season, teamPathes, seasonLeaguePathes)
    
    return matches, season

def GetDrawSeries(teamMatches: list) -> (list, tuple):
    teamMatches = sorted(teamMatches, key=lambda x: x.date)
    drawSeries = list()   
    currentSeries = 0 # TODO: Get data from past season
    
    for tm in teamMatches:
        if tm.team1Score == tm.team2Score:
            drawSeries.append((currentSeries, tm.date, tm.team1Score))
            print(drawSeries[-1])
            currentSeries = 0
        else:
            currentSeries += 1
        
    return drawSeries, (currentSeries, teamMatches[-1].date)
    
def GetTeamsDrawSeries(seasons, matches) -> (dict, list):
    selectedTeams = set()
    selectedLeagues = set()
    teamsDrawSeries = dict()
    teamsLastSeries = list()
    
    # sort seasons by years, first is the last
    seasons = sorted(seasons, key=lambda x: x.year2, reverse=True)
    
    for s in seasons:
        selectedLeagues.update(s.leagues)
        
    for league in selectedLeagues:
        leagueTeams = set([i[1] for i in filter(lambda x: x[0] == league, seasons[0].leaguesTeams)])
        
        for s in seasons[1:]:
            leagueTeams = leagueTeams.intersection(set([i[1] for i in filter(lambda x: x[0] == league, s.leaguesTeams)]))
        
        selectedTeams.update(leagueTeams)
        
    for team in selectedTeams:
        teamMatches = list(set(filter(lambda x: x.team1 == team or x.team2 == team, matches)))
        
        if len(teamMatches) == 0:
            print("No team matches for: ", team)
            continue
        
        teamDrawSeries, lastSeries = GetDrawSeries(teamMatches)
        teamsDrawSeries[team] = teamDrawSeries + [lastSeries]
        
    return teamsDrawSeries

def main():
    matches1, s1 = LoadSeasonMatches(2019, 2020, selectedLeagues, selectedLeaguesPathes)
    matches2, s2 = LoadSeasonMatches(2018, 2019, selectedLeagues, selectedLeaguesPathes)
    matches3, s3 = LoadSeasonMatches(2017, 2018, selectedLeagues, selectedLeaguesPathes)

    allMatches = set()
    allMatches.update(matches1)
    allMatches.update(matches2)
    allMatches.update(matches3)

    seasons=[s1, s2, s3]
    tds = GetTeamsDrawSeries([s1,s2,s3], list(allMatches))

    for team in tds:
        ls = tds[team][-1]
        ds = tds[team][:-1]
        league = FindLeagueByTeam(team, seasons[0])
        league = league[0]
    
        print("\t".join((team.country,league.name, team.name, str(max([i[0] for i in ds])), str(ls[0]))))

if __name__ == "__main__":
    main()