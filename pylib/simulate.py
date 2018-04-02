'''
    Season Simulation
    
    2017 Jacob Grishey

    For the purpose of simulating sports seasons
    and determining regular season standings.
'''

# IMPORTS

import json
import statistics
import numpy
from operator import itemgetter
import copy
from pathlib import Path
import datetime
from multiprocessing import Process

# Read JSON file

with open("./../data/season2017-18.json") as jsonfile:
    SEASON = json.load(jsonfile)

# Teams of the NHL

METRO = ["Carolina Hurricanes", "Columbus Blue Jackets", "New Jersey Devils",
        "New York Islanders", "New York Rangers", "Philadelphia Flyers",
        "Pittsburgh Penguins", "Washington Capitals"]

ATLANTIC = ["Boston Bruins", "Buffalo Sabres", "Detroit Red Wings",
            "Florida Panthers", "Montr\u00e9al Canadiens", "Ottawa Senators",
            "Tampa Bay Lightning", "Toronto Maple Leafs"]

CENTRAL = ["Chicago Blackhawks", "Colorado Avalanche", "Dallas Stars",
            "Minnesota Wild", "Nashville Predators", "St. Louis Blues",
            "Winnipeg Jets"]

PACIFIC = ["Anaheim Ducks", "Arizona Coyotes", "Calgary Flames",
            "Edmonton Oilers", "Los Angeles Kings", "San Jose Sharks",
            "Vancouver Canucks", "Vegas Golden Knights"]

teamsData = [{'name': team, 'w': 0, 'l': 0, 'otl': 0, 'row': 0, 'elo': 1500, 'aw': 0,
        'al': 0, 'aotl': 0, 'd1': 0, 'd2': 0, 'd3': 0, 'wc1': 0, 'wc2': 0,
        'pres': 0, 'conf': 0, 'r2': 0, 'r3': 0, 'r4': 0, 'cup': 0}
         for team in METRO + ATLANTIC + CENTRAL + PACIFIC]

today = datetime.date.today().strftime("%Y-%m-%d")

todaysGames = {
    "date": today,
    "data": []
}

playoffMarker = False

# Get last season's results.

if Path("./../data/results2016-17.json").is_file():
    with open("./../data/results2016-17.json") as lastSeason:
        lastSeason = json.load(lastSeason)
        for team in lastSeason:
            lastElo = team['elo']
            nowElo = (lastElo - 1500) * (2 / 3) + 1500
            next(item for item in teamsData if item["name"] == team["name"])['elo'] = nowElo

# Separate past from future games

past = [game for game in SEASON if game["resultType"] == "REG" or game['resultType'] == "OT" or game["resultType"] == "SO"]
pastReg = [game for game in past if game['gameType'] == "R"]
pastPO = [game for game in past if game['gameType'] == "P"]

future = [game for game in SEASON if game['resultType'] == "TBD"]
futureReg = [game for game in future if game['gameType'] == "R"]
futurePO = [game for game in future if game['gameType'] == "P"]

# Expected Score function
#
# Given elo of team A and team B, calculate expected score of team A.

def expectedScoreA (eloA, eloB):
    return 1 / (1 + 10 ** ((eloB - eloA) / 400))

# New Rating Function
#
# Given Elo, actual score, expected score, and goal differential and calculate the team's new Elo rating.

def newRating (eloA, eloB, scoreActual, scoreExpected, goalDifferential, gameType):
    # K-Factor
    K = 8

    # Importance
    I = 1.5 if gameType == "P" else 1.0
    
    # Calculate for goal differential and autocorrelation
    marginMult = numpy.log(goalDifferential + 1) * (2.2 / (abs(eloA - eloB) * 0.01 + 2.2))

    # Return new rating
    return eloA + (marginMult * K * I) * (scoreActual - scoreExpected)

# Process Game Function

def processGame (game, teamList, future):
    homeTeam = next(item for item in teamList if item["name"] == game['homeTeam'])
    awayTeam = next(item for item in teamList if item["name"] == game['awayTeam'])

    # Current Elo ratings
    currentEloA = homeTeam['elo']
    currentEloB = awayTeam['elo']

    # Get Expected Scores
    eA = expectedScoreA(currentEloA, currentEloB)
    eB = 1 - eA

    if game['date'] == today:
        newGame = {
            'homeTeam': game['homeTeam'],
            'awayTeam': game['awayTeam'],
            'homeProb': eA,
            'awayProb': eB
        }
        todaysGames["data"].append(newGame) if newGame not in todaysGames["data"] else ()

    # Get scores
    homeGoals = game['homeGoals']
    awayGoals = game['awayGoals']
    goalDifferential = abs(homeGoals - awayGoals)

    if not future:
        # Get Actual Scores
        if homeGoals > awayGoals:
            if game['resultType'] != "REG":
                sA = 1.0
                sB = 0.5
                if game['resultType'] == "SO":
                    homeTeam['w'] += 1
                    awayTeam['otl'] += 1
                else:
                    homeTeam['w'] += 1
                    homeTeam['row'] += 1
                    awayTeam['otl'] += 1
            else:
                sA = 1.0
                sB = 0.0
                homeTeam['w'] += 1
                homeTeam['row'] += 1
                awayTeam['l'] += 1
        else:
            if game['resultType'] != "REG":
                sB = 1.0
                sA = 0.5
                if game['resultType'] == "SO":
                    homeTeam['otl'] += 1
                    awayTeam['w'] += 1
                else:
                    homeTeam['otl'] += 1
                    awayTeam['row'] += 1
                    awayTeam['w'] += 1
            else:
                sB = 1.0
                sA = 0.0
                awayTeam['w'] += 1
                awayTeam['row'] += 1
                homeTeam['l'] += 1

        # Calculate new Elo ratings
        newA = newRating(currentEloA, currentEloB, sA, eA, goalDifferential, "R")
        newB = newRating(currentEloB, currentEloA, sB, eB, goalDifferential, "R")

        # Apply Elo ratings
        homeTeam['elo'] = newA
        awayTeam['elo'] = newB
    
    else:
        # Random number between 0 and 1 to decide who wins.
        decideWin = numpy.random.random()

        # Random number between 0 and 1 to decide if it goes into Overtime.
        decideOT = numpy.random.random()
        decideSO = numpy.random.random()

        if decideOT <= 0.233:
            if decideSO <= 0.579:
                if decideWin <= eA:
                    homeTeam['w'] += 1
                    awayTeam['otl'] += 1
                else:
                    homeTeam['otl'] += 1
                    awayTeam['w'] += 1
            else:
                if decideWin <= eA:
                    homeTeam['w'] += 1
                    homeTeam['row'] += 1
                    awayTeam['otl'] += 1
                else:
                    homeTeam['otl'] += 1
                    awayTeam['w'] += 1
                    awayTeam['row'] += 1
        else:
            if decideWin <= eA:
                homeTeam['w'] += 1
                homeTeam['row'] += 1
                awayTeam['l'] += 1
            else:
                homeTeam['l'] += 1
                awayTeam['w'] += 1
                awayTeam['row'] += 1

def runSeason (teams, pastPO):
    # Update elo from regular season games

    for game in pastReg:
        processGame(game, teams, False)

    def simRound (roundSeries, roundGames):
        # Simulate scheduled games
        for game in roundGames:
            homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
            awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

            # Current Elo ratings of both teams
            homeElo = homeTeam['elo']
            awayElo = awayTeam['elo']

            # Win probabilities
            eA = expectedScoreA(homeElo, awayElo)
            eB = 1 - eA

            # Random number between 0 and 1 to decide who wins.
            decideWin = numpy.random.random()

            # Random number between 0 and 1 to decide if it goes into Overtime.
            decideOT = numpy.random.random()

            # Get series data
            series = next(item for item in roundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

            homeCorrect = series['home'] == game['homeTeam']

            # For scheduling purposes
            previousLow = min(series['hWins'], series['aWins'])

            # Simulate game
            if decideOT <= 0.233:
                if decideWin <= eA:
                    if homeCorrect:
                        series['hWins'] += 1
                    else:
                        series['aWins'] += 1
                    if min([series['hWins'], series['aWins']]) > previousLow:
                        roundGames.append({
                            'homeTeam': game['homeTeam'],
                            'awayTeam': game['awayTeam']
                        })
                    sA = 1.0
                    sB = 0.5
                else:
                    if homeCorrect:
                        series['aWins'] += 1
                    else:
                        series['hWins'] += 1
                    if min([series['hWins'], series['aWins']]) > previousLow:
                        roundGames.append({
                            'homeTeam': game['homeTeam'],
                            'awayTeam': game['awayTeam']
                        })
                    sA = 0.5
                    sB = 1.0
            else:
                if decideWin <= eA:
                    if homeCorrect:
                        series['hWins'] += 1
                    else:
                        series['aWins'] += 1
                    if min([series['hWins'], series['aWins']]) > previousLow:
                        roundGames.append({
                            'homeTeam': game['homeTeam'],
                            'awayTeam': game['awayTeam']
                        })
                    sA = 1.0
                    sB = 0.0
                else:
                    if homeCorrect:
                        series['aWins'] += 1
                    else:
                        series['hWins'] += 1
                    if min([series['hWins'], series['aWins']]) > previousLow:
                        roundGames.append({
                            'homeTeam': game['homeTeam'],
                            'awayTeam': game['awayTeam']
                        })
                    sA = 0.0
                    sB = 1.0

    # Sim rest of regular season, if necessary

    if len(futureReg) > 0:
        
        for team in teams:
            next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']
            next(item for item in teamsData if item["name"] == team['name'])['w'] = team['w']
            next(item for item in teamsData if item["name"] == team['name'])['l'] = team['l']
            next(item for item in teamsData if item["name"] == team['name'])['otl'] = team['otl']
            next(item for item in teamsData if item["name"] == team["name"])['row'] = team['row']

        for game in futureReg:
            processGame(game, teams, True)
        
        # Sort teams into divisions
        atlantic = []
        pacific = []
        metro = []
        central = []

        # Collect teams, calculate points.
        for team in teams:
            if team['name'] in METRO:
                metro.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            elif team['name'] in ATLANTIC:
                atlantic.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            elif team['name'] in PACIFIC:
                pacific.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            else:
                central.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
        
        # Sort by points
        metro = sorted(metro, key=itemgetter('pts', 'row'), reverse=True)
        atlantic = sorted(atlantic, key=itemgetter('pts', 'row'), reverse=True)
        pacific = sorted(pacific, key=itemgetter('pts', 'row'), reverse=True)
        central = sorted(central, key=itemgetter('pts', 'row'), reverse=True)
        west = sorted(central + pacific, key=itemgetter('pts', 'row'), reverse=True)
        east = sorted(atlantic + metro, key=itemgetter('pts', 'row'), reverse=True)
        league = sorted(west + east, key=itemgetter('pts', 'row'), reverse=True)

        # Add conference champ and president's trophy
        next(item for item in teamsData if item["name"] == west[0]['name'])['conf'] += 1
        next(item for item in teamsData if item["name"] == east[0]['name'])['conf'] += 1
        next(item for item in teamsData if item["name"] == league[0]['name'])['pres'] += 1

        # Get top 3 in each division
        metroPlayoffs = metro[:3]
        atlanticPlayoffs = atlantic[:3]
        pacificPlayoffs = pacific[:3]
        centralPlayoffs = central[:3]

        # Add Results
        for i in range(1, 4):
            next(item for item in teamsData if item["name"] == metroPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == atlanticPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == pacificPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == centralPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
        
        # Get wild cards
        wildCardsEast = sorted(metro[3:] + atlantic[3:], key=itemgetter('pts', 'row'), reverse=True)[:2]
        wildCardsWest = sorted(pacific[3:] + central[3:], key=itemgetter('pts', 'row'), reverse=True)[:2]

        # Add Results
        for i in range(1, 3):
            next(item for item in teamsData if item["name"] == wildCardsEast[i-1]['name'])['wc{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == wildCardsWest[i-1]['name'])['wc{0}'.format(i)] += 1

        # Assign wild cards
        if metroPlayoffs[0]['pts'] >= atlanticPlayoffs[0]['pts']:
            metroPlayoffs.append(wildCardsEast[1])
            atlanticPlayoffs.append(wildCardsEast[0])
        else:
            metroPlayoffs.append(wildCardsEast[0])
            atlanticPlayoffs.append(wildCardsEast[1])

        if centralPlayoffs[0]['pts'] >= pacificPlayoffs[0]['pts']:
            centralPlayoffs.append(wildCardsWest[1])
            pacificPlayoffs.append(wildCardsWest[0])
        else:
            centralPlayoffs.append(wildCardsWest[0])
            pacificPlayoffs.append(wildCardsWest[1])
        
        # Schedule First Round
        firstRoundSeries = []
        firstRoundGames = []

        for division in [atlanticPlayoffs, centralPlayoffs, metroPlayoffs, pacificPlayoffs]:
            for i in range(0, 2):
                firstRoundSeries.append({
                    'home': division[i]['name'],
                    'away': division[3-i]['name'],
                    'hWins': 0,
                    'aWins': 0
                })
                for k in range(0, 4):
                    firstRoundGames.append({
                        'homeTeam': division[i]['name'],
                        'awayTeam': division[3-i]['name']
                    })
        
        # Simulate Round
        simRound(firstRoundSeries, firstRoundGames)
        
        # Get winners
        winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], firstRoundSeries))
        atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
        centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
        metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
        pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))

        # Add Results
        for winner in winners:
            next(item for item in teamsData if item["name"] == winner)['r2'] += 1

        # Schedule Second Round
        secondRoundSeries = []
        secondRoundGames = []

        for division in [atlanticPlayoffs, centralPlayoffs, metroPlayoffs, pacificPlayoffs]:
            for i in range(0, 1):
                secondRoundSeries.append({
                    'home': division[i]['name'],
                    'away': division[1-i]['name'],
                    'hWins': 0,
                    'aWins': 0
                })
                for k in range(0, 4):
                    secondRoundGames.append({
                        'homeTeam': division[i]['name'],
                        'awayTeam': division[1-i]['name']
                    })
        
        # Simulate round
        simRound(secondRoundSeries, secondRoundGames)
        
        # Get winners
        winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], secondRoundSeries))
        atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
        centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
        metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
        pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))
        eastPlayoffs = sorted(atlanticPlayoffs + metroPlayoffs, key=itemgetter('pts', 'row'), reverse=True)
        westPlayoffs = sorted(centralPlayoffs + pacificPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

        # Add Results
        for winner in winners:
            next(item for item in teamsData if item["name"] == winner)['r3'] += 1

        # Schedule Third Round
        thirdRoundSeries = []
        thirdRoundGames = []

        for conference in [eastPlayoffs, westPlayoffs]:
            for i in range(0, 1):
                thirdRoundSeries.append({
                    'home': conference[i]['name'],
                    'away': conference[1-i]['name'],
                    'hWins': 0,
                    'aWins': 0
                })
                for k in range(0, 4):
                    thirdRoundGames.append({
                        'homeTeam': conference[i]['name'],
                        'awayTeam': conference[1-i]['name']
                    })
        
        # Simulate Round
        simRound(thirdRoundSeries, thirdRoundGames)
        
        # Get winners
        winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], thirdRoundSeries))
        westPlayoffs = list(filter(lambda team: team['name'] in winners, westPlayoffs))
        eastPlayoffs = list(filter(lambda team: team['name'] in winners, eastPlayoffs))
        finalPlayoffs = sorted(westPlayoffs + eastPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

        # Add Results
        for winner in winners:
            next(item for item in teamsData if item["name"] == winner)['r4'] += 1

        # Schedule Final Round
        finalRoundSeries = []
        finalRoundGames = []

        for i in range(0, 1):
            finalRoundSeries.append({
                'home': finalPlayoffs[i]['name'],
                'away': finalPlayoffs[1-i]['name'],
                'hWins': 0,
                'aWins': 0
            })
            for k in range(0, 4):
                finalRoundGames.append({
                    'homeTeam': finalPlayoffs[i]['name'],
                    'awayTeam': finalPlayoffs[1-i]['name']
                })
        
        # Simulate Round
        simRound(finalRoundSeries, finalRoundGames)

        # Get winner
        winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

        next(item for item in teamsData if item["name"] == winner)['cup'] += 1

    else:
        playoffMarker = True
        # Sort teams into divisions
        atlantic = []
        pacific = []
        metro = []
        central = []

        # Collect teams, calculate points.
        for team in teams:
            if team['name'] in METRO:
                metro.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['w'] = team['w']
                next(item for item in teamsData if item["name"] == team['name'])['l'] = team['l']
                next(item for item in teamsData if item["name"] == team['name'])['otl'] = team['otl']
                next(item for item in teamsData if item["name"] == team['name'])['row'] = team['row']
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            elif team['name'] in ATLANTIC:
                atlantic.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['w'] = team['w']
                next(item for item in teamsData if item["name"] == team['name'])['l'] = team['l']
                next(item for item in teamsData if item["name"] == team['name'])['otl'] = team['otl']
                next(item for item in teamsData if item["name"] == team['name'])['row'] = team['row']
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            elif team['name'] in PACIFIC:
                pacific.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['w'] = team['w']
                next(item for item in teamsData if item["name"] == team['name'])['l'] = team['l']
                next(item for item in teamsData if item["name"] == team['name'])['otl'] = team['otl']
                next(item for item in teamsData if item["name"] == team['name'])['row'] = team['row']
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
            else:
                central.append({"name": team['name'], "pts": team['w'] * 2 + team['otl'], "row": team['row']})
                next(item for item in teamsData if item["name"] == team['name'])['w'] = team['w']
                next(item for item in teamsData if item["name"] == team['name'])['l'] = team['l']
                next(item for item in teamsData if item["name"] == team['name'])['otl'] = team['otl']
                next(item for item in teamsData if item["name"] == team['name'])['row'] = team['row']
                next(item for item in teamsData if item["name"] == team['name'])['aw'] += team['w']
                next(item for item in teamsData if item["name"] == team['name'])['al'] += team['l']
                next(item for item in teamsData if item["name"] == team['name'])['aotl'] += team['otl']
        
        # Sort by points
        metro = sorted(metro, key=itemgetter('pts', 'row'), reverse=True)
        atlantic = sorted(atlantic, key=itemgetter('pts', 'row'), reverse=True)
        pacific = sorted(pacific, key=itemgetter('pts', 'row'), reverse=True)
        central = sorted(central, key=itemgetter('pts', 'row'), reverse=True)
        west = sorted(central + pacific, key=itemgetter('pts', 'row'), reverse=True)
        east = sorted(atlantic + metro, key=itemgetter('pts', 'row'), reverse=True)
        league = sorted(west + east, key=itemgetter('pts', 'row'), reverse=True)

        # Add conference champ and president's trophy
        next(item for item in teamsData if item["name"] == west[0]['name'])['conf'] += 1
        next(item for item in teamsData if item["name"] == east[0]['name'])['conf'] += 1
        next(item for item in teamsData if item["name"] == league[0]['name'])['pres'] += 1

        # Get top 3 in each division
        metroPlayoffs = metro[:3]
        atlanticPlayoffs = atlantic[:3]
        pacificPlayoffs = pacific[:3]
        centralPlayoffs = central[:3]

        # Add Results
        for i in range(1, 4):
            next(item for item in teamsData if item["name"] == metroPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == atlanticPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == pacificPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == centralPlayoffs[i-1]['name'])['d{0}'.format(i)] += 1
        
        # Get wild cards
        wildCardsEast = sorted(metro[3:] + atlantic[3:], key=itemgetter('pts', 'row'), reverse=True)[:2]
        wildCardsWest = sorted(pacific[3:] + central[3:], key=itemgetter('pts', 'row'), reverse=True)[:2]

        # Add Results
        for i in range(1, 3):
            next(item for item in teamsData if item["name"] == wildCardsEast[i-1]['name'])['wc{0}'.format(i)] += 1
            next(item for item in teamsData if item["name"] == wildCardsWest[i-1]['name'])['wc{0}'.format(i)] += 1

        # Assign wild cards
        if metroPlayoffs[0]['pts'] > atlanticPlayoffs[0]['pts']:
            metroPlayoffs.append(wildCardsEast[1])
            atlanticPlayoffs.append(wildCardsEast[0])
        elif metroPlayoffs[0]['pts'] == atlanticPlayoffs[0]['pts']:
            if metroPlayoffs[0]['row'] > atlanticPlayoffs[0]['row']:
                metroPlayoffs.append(wildCardsEast[0])
                atlanticPlayoffs.append(wildCardsEast[1])
            else:
                atlanticPlayoffs.append(wildCardsEast[0])
                metroPlayoffs.append(wildCardsEast[1])
        else:
            atlanticPlayoffs.append(wildCardsEast[1])
            metroPlayoffs.append(wildCardsEast[0])

        if centralPlayoffs[0]['pts'] > pacificPlayoffs[0]['pts']:
            centralPlayoffs.append(wildCardsWest[1])
            pacificPlayoffs.append(wildCardsWest[0])
        elif centralPlayoffs[0]['pts'] == pacificPlayoffs[0]['pts']:
            if centralPlayoffs[0]['row'] > pacificPlayoffs[0]['row']:
                centralPlayoffs.append(wildCardsWest[1])
                pacificPlayoffs.append(wildCardsWest[0])
            else:
                pacificPlayoffs.append(wildCardsWest[1])
                centralPlayoffs.append(wildCardsWest[0])
        else:
            pacificPlayoffs.append(wildCardsWest[1])
            centralPlayoffs.append(wildCardsWest[0])
        
        # Schedule first round games
        firstRoundGames = []
        firstRoundSeries = []

        for division in [centralPlayoffs, pacificPlayoffs, metroPlayoffs, atlanticPlayoffs]:
            for i in range(0, 2):
                firstRoundSeries.append({
                    'home': division[i]['name'],
                    'away': division[3-i]['name'],
                    'hWins': 0,
                    'aWins': 0
                })

        def checkFinished (series):
            for serie in series:
                if serie['hWins'] != 4 and serie['aWins'] != 4:
                    return False
            return True
        
        def checkSeriesExists (series, home, away):
            for serie in series:
                if serie['home'] == home or serie['home'] == away:
                    if serie['away'] == home or serie['away'] == away:
                        return True
            return False
        
        for game in pastPO:
            homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
            awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

            if checkSeriesExists(firstRoundSeries, game['homeTeam'], game['awayTeam']):
                # Current Elo ratings of both teams
                homeElo = homeTeam['elo']
                awayElo = awayTeam['elo']

                # Win probabilities
                eA = expectedScoreA(homeElo, awayElo)
                eB = 1 - eA

                # Get scores
                homeGoals = game['homeGoals']
                awayGoals = game['awayGoals']
                goalDifferential = abs(homeGoals - awayGoals)

                # Get series data
                series = next(item for item in firstRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                isHomeTrue = game['homeTeam'] == series['home']

                # Simulate game
                if game['resultType'] != "REG":
                    if homeGoals > awayGoals:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        sA = 1.0
                        sB = 0.5
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        sA = 0.5
                        sB = 1.0
                else:
                    if homeGoals > awayGoals:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        sA = 1.0
                        sB = 0.0
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        sA = 0.0
                        sB = 1.0

                # Calculate new Elo ratings
                newA = newRating(homeElo, awayElo, sA, eA, goalDifferential, "P")
                newB = newRating(awayElo, homeElo, sB, eB, goalDifferential, "P")

                # Apply Elo ratings
                homeTeam['elo'] = newA
                awayTeam['elo'] = newB

                pastPO = [gm for gm in pastPO if (gm['date'] != game['date'] or gm['homeTeam'] != homeTeam['name'])]
        
        # If first round finished with past games
        if checkFinished(firstRoundSeries):

            # Get winners
            winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], firstRoundSeries))
            atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
            centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
            metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
            pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))

            # Add results
            for winner in winners:
                next(item for item in teamsData if item["name"] == winner)['r2'] += 1

            # Schedule second round
            secondRoundGames = []
            secondRoundSeries = []

            for division in [atlanticPlayoffs, centralPlayoffs, metroPlayoffs, pacificPlayoffs]:
                for i in range(0, 1):
                    secondRoundSeries.append({
                        'home': division[i]['name'],
                        'away': division[1-i]['name'],
                        'hWins': 0,
                        'aWins': 0
                    })

            # Go through past games of second round
            for game in pastPO:
                homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                if checkSeriesExists(secondRoundSeries, game['homeTeam'], game['awayTeam']):
                    # Current Elo ratings of both teams
                    homeElo = homeTeam['elo']
                    awayElo = awayTeam['elo']

                    # Win probabilities
                    eA = expectedScoreA(homeElo, awayElo)
                    eB = 1 - eA

                    # Get scores
                    homeGoals = game['homeGoals']
                    awayGoals = game['awayGoals']
                    goalDifferential = abs(homeGoals - awayGoals)

                    # Get series data
                    series = next(item for item in secondRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                    isHomeTrue = game['homeTeam'] == series['home']

                    # Simulate game
                    if game['resultType'] != "REG":
                        if homeGoals > awayGoals:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            sA = 1.0
                            sB = 0.5
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            sA = 0.5
                            sB = 1.0
                    else:
                        if homeGoals > awayGoals:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            sA = 1.0
                            sB = 0.0
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            sA = 0.0
                            sB = 1.0

                    # Calculate new Elo ratings
                    newA = newRating(homeElo, awayElo, sA, eA, goalDifferential, "P")
                    newB = newRating(awayElo, homeElo, sB, eB, goalDifferential, "P")

                    # Apply Elo ratings
                    homeTeam['elo'] = newA
                    awayTeam['elo'] = newB

                    pastPO = [gm for gm in pastPO if (gm['date'] != game['date'] or gm['homeTeam'] != homeTeam['name'])]

            # If second round finished with past games
            if checkFinished(secondRoundSeries):
                # Get winners
                winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], secondRoundSeries))
                atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
                centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
                metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
                pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))
                eastPlayoffs = sorted(atlanticPlayoffs + metroPlayoffs, key=itemgetter('pts', 'row'), reverse=True)
                westPlayoffs = sorted(centralPlayoffs + pacificPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

                # Add results
                for winner in winners:
                    next(item for item in teamsData if item["name"] == winner)['r3'] += 1

                # Schedule third round
                thirdRoundGames = []
                thirdRoundSeries = []

                for conference in [eastPlayoffs, westPlayoffs]:
                    for i in range(0, 1):
                        thirdRoundSeries.append({
                            'home': conference[i]['name'],
                            'away': conference[1-i]['name'],
                            'hWins': 0,
                            'aWins': 0
                        })
                
                # Go through past games of third round
                for game in pastPO:
                    homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                    awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                    if checkSeriesExists(thirdRoundSeries, game['homeTeam'], game['awayTeam']):
                        # Current Elo ratings of both teams
                        homeElo = homeTeam['elo']
                        awayElo = awayTeam['elo']

                        # Win probabilities
                        eA = expectedScoreA(homeElo, awayElo)
                        eB = 1 - eA

                        # Get scores
                        homeGoals = game['homeGoals']
                        awayGoals = game['awayGoals']
                        goalDifferential = abs(homeGoals - awayGoals)

                        # Get series data
                        series = next(item for item in thirdRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                        isHomeTrue = game['homeTeam'] == series['home']

                        # Simulate game
                        if game['resultType'] != "REG":
                            if homeGoals > awayGoals:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                sA = 1.0
                                sB = 0.5
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                sA = 0.5
                                sB = 1.0
                        else:
                            if homeGoals > awayGoals:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                sA = 1.0
                                sB = 0.0
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                sA = 0.0
                                sB = 1.0

                        # Calculate new Elo ratings
                        newA = newRating(homeElo, awayElo, sA, eA, goalDifferential, "P")
                        newB = newRating(awayElo, homeElo, sB, eB, goalDifferential, "P")

                        # Apply Elo ratings
                        homeTeam['elo'] = newA
                        awayTeam['elo'] = newB

                        pastPO = [gm for gm in pastPO if (gm['date'] != game['date'] or gm['homeTeam'] != homeTeam['name'])]
                
                # If third round finished with past games
                if checkFinished(thirdRoundSeries):
                    # Get winners
                    winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], thirdRoundSeries))
                    westPlayoffs = list(filter(lambda team: team['name'] in winners, westPlayoffs))
                    eastPlayoffs = list(filter(lambda team: team['name'] in winners, eastPlayoffs))
                    finalPlayoffs = sorted(westPlayoffs + eastPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

                    # Add results
                    for winner in winners:
                        next(item for item in teamsData if item["name"] == winner)['r4'] += 1

                    # Schedule final round
                    finalRoundGames = []
                    finalRoundSeries = []

                    for i in range(0, 1):
                        finalRoundSeries.append({
                            'home': finalPlayoffs[i]['name'],
                            'away': finalPlayoffs[1-i]['name'],
                            'hWins': 0,
                            'aWins': 0
                        })
                    
                    # Go through past games of final round
                    for game in pastPO:
                        homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                        awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                        if checkSeriesExists(finalRoundSeries, game['homeTeam'], game['awayTeam']):
                            # Current Elo ratings of both teams
                            homeElo = homeTeam['elo']
                            awayElo = awayTeam['elo']

                            # Win probabilities
                            eA = expectedScoreA(homeElo, awayElo)
                            eB = 1 - eA

                            # Get scores
                            homeGoals = game['homeGoals']
                            awayGoals = game['awayGoals']
                            goalDifferential = abs(homeGoals - awayGoals)

                            # Get series data
                            series = next(item for item in finalRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                            isHomeTrue = game['homeTeam'] == series['home']

                            # Simulate game
                            if game['resultType'] != "REG":
                                if homeGoals > awayGoals:
                                    if isHomeTrue:
                                        series['hWins'] += 1
                                    else:
                                        series['aWins'] += 1
                                    sA = 1.0
                                    sB = 0.5
                                else:
                                    if isHomeTrue:
                                        series['aWins'] += 1
                                    else:
                                        series['hWins'] += 1
                                    sA = 0.5
                                    sB = 1.0
                            else:
                                if homeGoals > awayGoals:
                                    if isHomeTrue:
                                        series['hWins'] += 1
                                    else:
                                        series['aWins'] += 1
                                    sA = 1.0
                                    sB = 0.0
                                else:
                                    if isHomeTrue:
                                        series['aWins'] += 1
                                    else:
                                        series['hWins'] += 1
                                    sA = 0.0
                                    sB = 1.0

                            # Calculate new Elo ratings
                            newA = newRating(homeElo, awayElo, sA, eA, goalDifferential, "P")
                            newB = newRating(awayElo, homeElo, sB, eB, goalDifferential, "P")

                            # Apply Elo ratings
                            homeTeam['elo'] = newA
                            awayTeam['elo'] = newB

                            pastPO = [gm for gm in pastPO if (gm['date'] != game['date'] or gm['homeTeam'] != homeTeam['name'])]
                    
                    # If final round finished with past games
                    if checkFinished(finalRoundSeries):

                        # Get winner
                        winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

                        # Add results
                        next(item for item in teamsData if item["name"] == winner)['cup'] += 1
                        
                        for team in teams:
                            next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']
                
                    # If final round partially finished
                    else:
                        for team in teams:
                            next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']

                        for series in finalRoundSeries:
                            if series['hWins'] != 4 or series['aWins'] != 4:
                                # Schedule needed games
                                numToBeScheduled = min(series['hWins'], series['aWins']) + 4 - (series['hWins'] + series['aWins'])
                                for i in range(numToBeScheduled):
                                    finalRoundGames.append({'homeTeam': series['home'], 'awayTeam': series['away']})
                        
                        # Simulate scheduled games
                        for game in finalRoundGames:
                            homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                            awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                            # Current Elo ratings of both teams
                            homeElo = homeTeam['elo']
                            awayElo = awayTeam['elo']

                            # Win probabilities
                            eA = expectedScoreA(homeElo, awayElo)
                            eB = 1 - eA

                            # Random number between 0 and 1 to decide who wins.
                            decideWin = numpy.random.random()

                            # Random number between 0 and 1 to decide if it goes into Overtime.
                            decideOT = numpy.random.random()

                            # For scheduling purposes
                            previousLow = min(series['hWins'], series['aWins'])

                            # Get series data
                            series = next(item for item in finalRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                            isHomeTrue = game['homeTeam'] == series['home']

                            previousLow = min(series['hWins'], series['aWins'])

                            # Simulate game
                            if decideOT <= 0.233:
                                if decideWin <= eA:
                                    if isHomeTrue:
                                        series['hWins'] += 1
                                    else:
                                        series['aWins'] += 1
                                    if min([series['hWins'], series['aWins']]) > previousLow:
                                        finalRoundGames.append({
                                            'homeTeam': game['homeTeam'],
                                            'awayTeam': game['awayTeam']
                                        })
                                    sA = 1.0
                                    sB = 0.5
                                else:
                                    if isHomeTrue:
                                        series['aWins'] += 1
                                    else:
                                        series['hWins'] += 1
                                    if min([series['hWins'], series['aWins']]) > previousLow:
                                        finalRoundGames.append({
                                            'homeTeam': game['homeTeam'],
                                            'awayTeam': game['awayTeam']
                                        })
                                    sA = 0.5
                                    sB = 1.0
                            else:
                                if decideWin <= eA:
                                    if isHomeTrue:
                                        series['hWins'] += 1
                                    else:
                                        series['aWins'] += 1
                                    if min([series['hWins'], series['aWins']]) > previousLow:
                                        finalRoundGames.append({
                                            'homeTeam': game['homeTeam'],
                                            'awayTeam': game['awayTeam']
                                        })
                                    sA = 1.0
                                    sB = 0.0
                                else:
                                    if isHomeTrue:
                                        series['aWins'] += 1
                                    else:
                                        series['hWins'] += 1
                                    if min([series['hWins'], series['aWins']]) > previousLow:
                                        finalRoundGames.append({
                                            'homeTeam': game['homeTeam'],
                                            'awayTeam': game['awayTeam']
                                        })
                                    sA = 0.0
                                    sB = 1.0

                        # Get winner
                        winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

                        next(item for item in teamsData if item["name"] == winner)['cup'] += 1

                # If third round partially finished
                else:
                    for team in teams:
                        next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']

                    for series in thirdRoundSeries:
                        if series['hWins'] != 4 or series['aWins'] != 4:
                            # Schedule needed games
                            numToBeScheduled = min(series['hWins'], series['aWins']) + 4 - (series['hWins'] + series['aWins'])
                            for i in range(numToBeScheduled):
                                thirdRoundGames.append({'homeTeam': series['home'], 'awayTeam': series['away']})

                    # Simulate scheduled games
                    for game in thirdRoundGames:
                        homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                        awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                        # Current Elo ratings of both teams
                        homeElo = homeTeam['elo']
                        awayElo = awayTeam['elo']

                        # Win probabilities
                        eA = expectedScoreA(homeElo, awayElo)
                        eB = 1 - eA

                        # Random number between 0 and 1 to decide who wins.
                        decideWin = numpy.random.random()

                        # Random number between 0 and 1 to decide if it goes into Overtime.
                        decideOT = numpy.random.random()

                        # Get series data
                        series = next(item for item in thirdRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                        isHomeTrue = game['homeTeam'] == series['home']

                        previousLow = min(series['aWins'], series['hWins'])

                        # Simulate game
                        if decideOT <= 0.233:
                            if decideWin <= eA:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    thirdRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 1.0
                                sB = 0.5
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    thirdRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 0.5
                                sB = 1.0
                        else:
                            if decideWin <= eA:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    thirdRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 1.0
                                sB = 0.0
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    thirdRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 0.0
                                sB = 1.0
                    
                    # Get winners
                    winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], thirdRoundSeries))
                    westPlayoffs = list(filter(lambda team: team['name'] in winners, westPlayoffs))
                    eastPlayoffs = list(filter(lambda team: team['name'] in winners, eastPlayoffs))
                    finalPlayoffs = sorted(westPlayoffs + eastPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

                    # Add results
                    for winner in winners:
                        next(item for item in teamsData if item["name"] == winner)['r4'] += 1

                    # Schedule Final Round
                    finalRoundSeries = []
                    finalRoundGames = []

                    for i in range(0, 1):
                        finalRoundSeries.append({
                            'home': finalPlayoffs[i]['name'],
                            'away': finalPlayoffs[1-i]['name'],
                            'hWins': 0,
                            'aWins': 0
                        })
                        for k in range(0, 4):
                            finalRoundGames.append({
                                'homeTeam': finalPlayoffs[i]['name'],
                                'awayTeam': finalPlayoffs[1-i]['name']
                            })
                    
                    # Simulate scheduled games
                    for game in finalRoundGames:
                        homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                        awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                        # Current Elo ratings of both teams
                        homeElo = homeTeam['elo']
                        awayElo = awayTeam['elo']

                        # Win probabilities
                        eA = expectedScoreA(homeElo, awayElo)
                        eB = 1 - eA

                        # Random number between 0 and 1 to decide who wins.
                        decideWin = numpy.random.random()

                        # Random number between 0 and 1 to decide if it goes into Overtime.
                        decideOT = numpy.random.random()

                        # Get series data
                        series = next(item for item in finalRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                        isHomeTrue = game['homeTeam'] == series['home']

                        previousLow = min(series['aWins'], series['hWins'])

                        # Simulate game
                        if decideOT <= 0.233:
                            if decideWin <= eA:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    finalRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 1.0
                                sB = 0.5
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    finalRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 0.5
                                sB = 1.0
                        else:
                            if decideWin <= eA:
                                if isHomeTrue:
                                    series['hWins'] += 1
                                else:
                                    series['aWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    finalRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 1.0
                                sB = 0.0
                            else:
                                if isHomeTrue:
                                    series['aWins'] += 1
                                else:
                                    series['hWins'] += 1
                                if min([series['hWins'], series['aWins']]) > previousLow:
                                    finalRoundGames.append({
                                        'homeTeam': game['homeTeam'],
                                        'awayTeam': game['awayTeam']
                                    })
                                sA = 0.0
                                sB = 1.0

                    # Get winner
                    winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

                    next(item for item in teamsData if item["name"] == winner)['cup'] += 1

            # If second round partially finished
            else:
                for team in teams:
                    next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']

                for series in secondRoundSeries:
                    if series['hWins'] != 4 or series['aWins'] != 4:
                        # Schedule needed games
                        numToBeScheduled = min(series['hWins'], series['aWins']) + 4 - (series['hWins'] + series['aWins'])
                        for i in range(numToBeScheduled):
                            secondRoundGames.append({'homeTeam': series['home'], 'awayTeam': series['away']})

                # Simulate scheduled games
                for game in secondRoundGames:
                    homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                    awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                    # Current Elo ratings of both teams
                    homeElo = homeTeam['elo']
                    awayElo = awayTeam['elo']

                    # Win probabilities
                    eA = expectedScoreA(homeElo, awayElo)
                    eB = 1 - eA

                    # Random number between 0 and 1 to decide who wins.
                    decideWin = numpy.random.random()

                    # Random number between 0 and 1 to decide if it goes into Overtime.
                    decideOT = numpy.random.random()

                    # Get series data
                    series = next(item for item in secondRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                    isHomeTrue = game['homeTeam'] == series['home']

                    previousLow = min(series['aWins'], series['hWins'])

                    # Simulate game
                    if decideOT <= 0.233:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                secondRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.5
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                secondRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.5
                            sB = 1.0
                    else:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                secondRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.0
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                secondRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.0
                            sB = 1.0
                
                # Get winners
                winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], secondRoundSeries))
                atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
                centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
                metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
                pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))
                eastPlayoffs = sorted(atlanticPlayoffs + metroPlayoffs, key=itemgetter('pts', 'row'), reverse=True)
                westPlayoffs = sorted(centralPlayoffs + pacificPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

                # Add results
                for winner in winners:
                    next(item for item in teamsData if item["name"] == winner)['r3'] += 1

                # Schedule Third Round
                thirdRoundSeries = []
                thirdRoundGames = []

                for conference in [eastPlayoffs, westPlayoffs]:
                    for i in range(0, 1):
                        thirdRoundSeries.append({
                            'home': conference[i]['name'],
                            'away': conference[1-i]['name'],
                            'hWins': 0,
                            'aWins': 0
                        })
                        for k in range(0, 4):
                            thirdRoundGames.append({
                                'homeTeam': conference[i]['name'],
                                'awayTeam': conference[1-i]['name']
                            })
                
                # Simulate scheduled games
                for game in thirdRoundGames:
                    homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                    awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                    # Current Elo ratings of both teams
                    homeElo = homeTeam['elo']
                    awayElo = awayTeam['elo']

                    # Win probabilities
                    eA = expectedScoreA(homeElo, awayElo)
                    eB = 1 - eA

                    # Random number between 0 and 1 to decide who wins.
                    decideWin = numpy.random.random()

                    # Random number between 0 and 1 to decide if it goes into Overtime.
                    decideOT = numpy.random.random()

                    # Get series data
                    series = next(item for item in thirdRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                    isHomeTrue = game['homeTeam'] == series['home']

                    previousLow = min(series['aWins'], series['hWins'])

                    # Simulate game
                    if decideOT <= 0.233:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                thirdRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.5
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                thirdRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.5
                            sB = 1.0
                    else:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                thirdRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.0
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                thirdRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.0
                            sB = 1.0
                
                # Get winners
                winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], thirdRoundSeries))
                westPlayoffs = list(filter(lambda team: team['name'] in winners, westPlayoffs))
                eastPlayoffs = list(filter(lambda team: team['name'] in winners, eastPlayoffs))
                finalPlayoffs = sorted(westPlayoffs + eastPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

                # Add results
                for winner in winners:
                    next(item for item in teamsData if item["name"] == winner)['r4'] += 1

                # Schedule Final Round
                finalRoundSeries = []
                finalRoundGames = []

                for i in range(0, 1):
                    finalRoundSeries.append({
                        'home': finalPlayoffs[i]['name'],
                        'away': finalPlayoffs[1-i]['name'],
                        'hWins': 0,
                        'aWins': 0
                    })
                    for k in range(0, 4):
                        finalRoundGames.append({
                            'homeTeam': finalPlayoffs[i]['name'],
                            'awayTeam': finalPlayoffs[1-i]['name']
                        })
                
                # Simulate scheduled games
                for game in finalRoundGames:
                    homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                    awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                    # Current Elo ratings of both teams
                    homeElo = homeTeam['elo']
                    awayElo = awayTeam['elo']

                    # Win probabilities
                    eA = expectedScoreA(homeElo, awayElo)
                    eB = 1 - eA

                    # Random number between 0 and 1 to decide who wins.
                    decideWin = numpy.random.random()

                    # Random number between 0 and 1 to decide if it goes into Overtime.
                    decideOT = numpy.random.random()

                    # Get series data
                    series = next(item for item in finalRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                    isHomeTrue = game['homeTeam'] == series['home']

                    previousLow = min(series['hWins'], series['aWins'])

                    # Simulate game
                    if decideOT <= 0.233:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                finalRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.5
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                finalRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.5
                            sB = 1.0
                    else:
                        if decideWin <= eA:
                            if isHomeTrue:
                                series['hWins'] += 1
                            else:
                                series['aWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                finalRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 1.0
                            sB = 0.0
                        else:
                            if isHomeTrue:
                                series['aWins'] += 1
                            else:
                                series['hWins'] += 1
                            if min([series['hWins'], series['aWins']]) > previousLow:
                                finalRoundGames.append({
                                    'homeTeam': game['homeTeam'],
                                    'awayTeam': game['awayTeam']
                                })
                            sA = 0.0
                            sB = 1.0

                # Get winner
                winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

                next(item for item in teamsData if item["name"] == winner)['cup'] += 1

        # If first round partially finished
        else:
            for team in teams:
                next(item for item in teamsData if item["name"] == team['name'])['elo'] = team['elo']

            for series in firstRoundSeries:
                if series['hWins'] != 4 or series['aWins'] != 4:
                    # Schedule needed games
                    numToBeScheduled = min(series['hWins'], series['aWins']) + 4 - (series['hWins'] + series['aWins'])
                    for i in range(numToBeScheduled):
                        firstRoundGames.append({'homeTeam': series['home'], 'awayTeam': series['away']})

            # Simulate scheduled games
            for game in firstRoundGames:
                homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                # Current Elo ratings of both teams
                homeElo = homeTeam['elo']
                awayElo = awayTeam['elo']

                # Win probabilities
                eA = expectedScoreA(homeElo, awayElo)
                eB = 1 - eA

                # Random number between 0 and 1 to decide who wins.
                decideWin = numpy.random.random()

                # Random number between 0 and 1 to decide if it goes into Overtime.
                decideOT = numpy.random.random()

                # Get series data
                series = next(item for item in firstRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                isHomeTrue = game['homeTeam'] == series['home']

                previousLow = min(series['aWins'], series['hWins'])

                # Simulate game
                if decideOT <= 0.233:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            firstRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.5
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            firstRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.5
                        sB = 1.0
                else:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            firstRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.0
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            firstRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.0
                        sB = 1.0
            
            # Get winners
            winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], firstRoundSeries))
            atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
            centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
            metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
            pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))

            # Add results
            for winner in winners:
                next(item for item in teamsData if item["name"] == winner)['r2'] += 1

            # Schedule Second Round
            secondRoundSeries = []
            secondRoundGames = []

            for division in [atlanticPlayoffs, centralPlayoffs, metroPlayoffs, pacificPlayoffs]:
                for i in range(0, 1):
                    secondRoundSeries.append({
                        'home': division[i]['name'],
                        'away': division[1-i]['name'],
                        'hWins': 0,
                        'aWins': 0
                    })
                    for k in range(0, 4):
                        secondRoundGames.append({
                            'homeTeam': division[i]['name'],
                            'awayTeam': division[1-i]['name']
                        })
            
            # Simulate scheduled games
            for game in secondRoundGames:
                homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                # Current Elo ratings of both teams
                homeElo = homeTeam['elo']
                awayElo = awayTeam['elo']

                # Win probabilities
                eA = expectedScoreA(homeElo, awayElo)
                eB = 1 - eA

                # Random number between 0 and 1 to decide who wins.
                decideWin = numpy.random.random()

                # Random number between 0 and 1 to decide if it goes into Overtime.
                decideOT = numpy.random.random()

                # Get series data
                series = next(item for item in secondRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                isHomeTrue = game['homeTeam'] == series['home']

                previousLow = min(series['aWins'], series['hWins'])

                # Simulate game
                if decideOT <= 0.233:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            secondRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.5
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            secondRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.5
                        sB = 1.0
                else:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            secondRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.0
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            secondRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.0
                        sB = 1.0
            
            # Get winners
            winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], secondRoundSeries))
            atlanticPlayoffs = list(filter(lambda team: team['name'] in winners, atlanticPlayoffs))
            centralPlayoffs = list(filter(lambda team: team['name'] in winners, centralPlayoffs))
            metroPlayoffs = list(filter(lambda team: team['name'] in winners, metroPlayoffs))
            pacificPlayoffs = list(filter(lambda team: team['name'] in winners, pacificPlayoffs))
            eastPlayoffs = sorted(atlanticPlayoffs + metroPlayoffs, key=itemgetter('pts', 'row'), reverse=True)
            westPlayoffs = sorted(centralPlayoffs + pacificPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

            # Add results
            for winner in winners:
                next(item for item in teamsData if item["name"] == winner)['r3'] += 1

            # Schedule Third Round
            thirdRoundSeries = []
            thirdRoundGames = []

            for conference in [eastPlayoffs, westPlayoffs]:
                for i in range(0, 1):
                    thirdRoundSeries.append({
                        'home': conference[i]['name'],
                        'away': conference[1-i]['name'],
                        'hWins': 0,
                        'aWins': 0
                    })
                    for k in range(0, 4):
                        thirdRoundGames.append({
                            'homeTeam': conference[i]['name'],
                            'awayTeam': conference[1-i]['name']
                        })
            
            # Simulate scheduled games
            for game in thirdRoundGames:
                homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                # Current Elo ratings of both teams
                homeElo = homeTeam['elo']
                awayElo = awayTeam['elo']

                # Win probabilities
                eA = expectedScoreA(homeElo, awayElo)
                eB = 1 - eA

                # Random number between 0 and 1 to decide who wins.
                decideWin = numpy.random.random()

                # Random number between 0 and 1 to decide if it goes into Overtime.
                decideOT = numpy.random.random()

                # Get series data
                series = next(item for item in thirdRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                isHomeTrue = game['homeTeam'] == series['home']

                previousLow = min(series['aWins'], series['hWins'])

                # Simulate game
                if decideOT <= 0.233:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            thirdRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.5
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            thirdRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.5
                        sB = 1.0
                else:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            thirdRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.0
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            thirdRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.0
                        sB = 1.0
            
            # Get winners
            winners = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], thirdRoundSeries))
            westPlayoffs = list(filter(lambda team: team['name'] in winners, westPlayoffs))
            eastPlayoffs = list(filter(lambda team: team['name'] in winners, eastPlayoffs))
            finalPlayoffs = sorted(westPlayoffs + eastPlayoffs, key=itemgetter('pts', 'row'), reverse=True)

            # Add results
            for winner in winners:
                next(item for item in teamsData if item["name"] == winner)['r4'] += 1

            # Schedule Final Round
            finalRoundSeries = []
            finalRoundGames = []

            for i in range(0, 1):
                finalRoundSeries.append({
                    'home': finalPlayoffs[i]['name'],
                    'away': finalPlayoffs[1-i]['name'],
                    'hWins': 0,
                    'aWins': 0
                })
                for k in range(0, 4):
                    finalRoundGames.append({
                        'homeTeam': finalPlayoffs[i]['name'],
                        'awayTeam': finalPlayoffs[1-i]['name']
                    })
            
            # Simulate scheduled games
            for game in finalRoundGames:
                homeTeam = next(item for item in teams if item["name"] == game['homeTeam'])
                awayTeam = next(item for item in teams if item["name"] == game['awayTeam'])

                # Current Elo ratings of both teams
                homeElo = homeTeam['elo']
                awayElo = awayTeam['elo']

                # Win probabilities
                eA = expectedScoreA(homeElo, awayElo)
                eB = 1 - eA

                # Random number between 0 and 1 to decide who wins.
                decideWin = numpy.random.random()

                # Random number between 0 and 1 to decide if it goes into Overtime.
                decideOT = numpy.random.random()

                # Get series data
                series = next(item for item in finalRoundSeries if item['home'] == game['homeTeam'] or item['home'] == game['awayTeam'])

                isHomeTrue = game['homeTeam'] == series['home']

                previousLow = min(series['aWins'], series['hWins'])

                # Simulate game
                if decideOT <= 0.233:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            finalRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.5
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            finalRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.5
                        sB = 1.0
                else:
                    if decideWin <= eA:
                        if isHomeTrue:
                            series['hWins'] += 1
                        else:
                            series['aWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            finalRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 1.0
                        sB = 0.0
                    else:
                        if isHomeTrue:
                            series['aWins'] += 1
                        else:
                            series['hWins'] += 1
                        if min([series['hWins'], series['aWins']]) > previousLow:
                            finalRoundGames.append({
                                'homeTeam': game['homeTeam'],
                                'awayTeam': game['awayTeam']
                            })
                        sA = 0.0
                        sB = 1.0

            # Get winner
            winner = list(map(lambda s: s['home'] if s['hWins'] == 4 else s['away'], finalRoundSeries))[0]

            next(item for item in teamsData if item["name"] == winner)['cup'] += 1
        
# Run simulation 100,000 times.

blankData = copy.deepcopy(teamsData)

for i in range(0, 100000):
    print(str(i / 1000) + " %")
    runSeason(copy.deepcopy(blankData), copy.deepcopy(pastPO))

# Calculate average season.
for team in teamsData:
    team['aw'] /= 100000
    team['al'] /= 100000
    team['aotl'] /= 100000
    if team['name'] in ATLANTIC:
        team['division'] = "Atlantic"
    elif team['name'] in METRO:
        team['division'] = "Metropolitan"
    elif team['name'] in PACIFIC:
        team['division'] = "Pacific"
    else:
        team['division'] = "Central"

# Output data to file.

with open("./../data/results2017-18.json", "r+") as resultsFile:
    previous = json.loads(resultsFile.read())
    previous.append({
        "date": today,
        "playoffs": playoffMarker,
        "data": teamsData
    })
    resultsFile.seek(0)
    resultsFile.truncate()
    json.dump(previous, resultsFile, indent=4)

with open("./../data/today.json", "w") as todayFile:
    json.dump(todaysGames, todayFile, indent=4)