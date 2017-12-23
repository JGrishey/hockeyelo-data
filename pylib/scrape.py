"""
    Script for getting NHL game results
"""

# Imports

import json
import argparse
import urllib.request

parser = argparse.ArgumentParser()

parser.add_argument('--dfrom')
parser.add_argument('--dto')
parser.add_argument('--out')

args = parser.parse_args()

def getGames (dfrom, dto):
    url = "https://statsapi.web.nhl.com/api/v1/schedule?startDate={0}&endDate={1}&expand=schedule.linescore&site=en_nhl".format(dfrom, dto)
    jsondata = json.loads(urllib.request.urlopen(url).read().decode())
    dates = jsondata['dates']
    games = []
    for date in dates:
        for game in date['games']:
            if game['status']['detailedState'] != "Scheduled":
                linescore = game['linescore']
                gameType = game['gameType']
                print(linescore)
                endPeriod = linescore['currentPeriodOrdinal']
                if "name" in linescore['teams']['home']['team']:
                    homeTeam = linescore['teams']['home']['team']['name']
                else:
                    homeTeam = "Atlanta Thrashers" if linescore['teams']['home']['team']['id'] == 11 else ()
                homeGoals = linescore['teams']['home']['goals']
                if "name" in linescore['teams']['away']['team']:
                    awayTeam = linescore['teams']['away']['team']['name']
                else:
                    awayTeam = "Atlanta Thrashers" if linescore['teams']['away']['team']['id'] == 11 else ()
                awayGoals = linescore['teams']['away']['goals']
                games.append({'date': date['date'], 'gameType': gameType, 'resultType': "REG" if endPeriod == "3rd" else endPeriod,
                            'homeTeam': homeTeam, 'awayTeam': awayTeam, 'homeGoals': homeGoals, 'awayGoals': awayGoals})
            else:
                games.append({'date': date['date'], 'gameType': game['gameType'], 'resultType': "TBD",
                            'homeTeam': game['teams']['home']['team']['name'], 'awayTeam': game['teams']['away']['team']['name'],
                            'homeGoals': 0, 'awayGoals': 0})
    return games

schedule = getGames(args.dfrom, args.dto)

with open('./../data/' + args.out, 'w') as outfile:
    json.dump(schedule, outfile, indent=4)
