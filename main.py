import requests
import time
from datetime import datetime
import os

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

alerted = set()
ops_cache = {}
team_cache = set()  # track which teams we've loaded

def send_alert(msg):
    if WEBHOOK:
        requests.post(WEBHOOK, json={"content": msg})

def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    return requests.get(url).json()

def get_live(gamePk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
    return requests.get(url).json()

def get_player_ops(player_id):
    if player_id in ops_cache:
        return ops_cache[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season"
        data = requests.get(url).json()

        splits = data["stats"][0]["splits"]
        if not splits:
            ops = 0
        else:
            ops = float(splits[0]["stat"].get("ops", "0"))

    except:
        ops = 0

    ops_cache[player_id] = ops
    return ops

def preload_team_ops(live_data, team, gamePk):
    # only load once per team per game
    key = f"{gamePk}-{team}"
    if key in team_cache:
        return

    try:
        batting_order = live_data["liveData"]["boxscore"]["teams"][team]["battingOrder"]

        for player_id in batting_order:
            get_player_ops(player_id)

        team_cache.add(key)

    except:
        pass

def is_top_of_order_next(live_data, team):
    try:
        offense = live_data["liveData"]["linescore"]["offense"]
        batting_order = live_data["liveData"]["boxscore"]["teams"][team]["battingOrder"]

        current = offense.get("batter", {})
        current_id = current.get("id")

        if current_id not in batting_order:
            return False

        idx = batting_order.index(current_id)
        next_idx = (idx + 1) % len(batting_order)

        return (next_idx + 1) in [1, 2, 3]

    except:
        return False

def get_next_three_hitters(live_data, team):
    try:
        offense = live_data["liveData"]["linescore"]["offense"]
        batting_order = live_data["liveData"]["boxscore"]["teams"][team]["battingOrder"]
        players = live_data["liveData"]["boxscore"]["teams"][team]["players"]

        current = offense.get("batter", {})
        current_id = current.get("id")

        if current_id not in batting_order:
            return [], []

        idx = batting_order.index(current_id)

        hitters = []
        elite_flags = []

        for i in range(1, 4):
            next_idx = (idx + i) % len(batting_order)
            player_id = batting_order[next_idx]
            player_key = f"ID{player_id}"

            name = players[player_key]["person"]["fullName"]
            ops = ops_cache.get(player_id, 0)

            hitters.append(f"{name} ({ops:.3f})")
            elite_flags.append(ops >= 0.850)

        return hitters, elite_flags

    except:
        return [], []

def check_games():
    print("Checking games...")

    schedule = get_schedule()

    for date in schedule.get("dates", []):
        for game in date.get("games", []):
            gamePk = game["gamePk"]

            live = get_live(gamePk)

            linescore = live["liveData"]["linescore"]
            inning = linescore.get("currentInning", 0)

            if inning < 4:
                continue

            # preload lineup stats (🔥 big optimization)
            preload_team_ops(live, "home", gamePk)
            preload_team_ops(live, "away", gamePk)

            # only trigger at inning end
            if not linescore.get("isInningBreak"):
                continue

            key = f"{gamePk}-inning-{inning}"
            if key in alerted:
                continue

            # check BOTH teams
            home_top = is_top_of_order_next(live, "home")
            away_top = is_top_of_order_next(live, "away")

            if not (home_top and away_top):
                continue

            # hitters + elite check
            away_hitters, away_elite = get_next_three_hitters(live, "away")
            home_hitters, home_elite = get_next_three_hitters(live, "home")

            if not (any(away_elite) and any(home_elite)):
                continue

            home = game["teams"]["home"]["team"]["name"]
            away = game["teams"]["away"]["team"]["name"]

            home_runs = linescore["teams"]["home"]["runs"]
            away_runs = linescore["teams"]["away"]["runs"]

            total_runs = home_runs + away_runs

            send_alert(
                f"🚨 ELITE TOP OF ORDER SPOT 🚨\n"
                f"{away} vs {home}\n"
                f"End of {inning}\n\n"
                f"Score: {away_runs} - {home_runs}\n"
                f"Total Runs: {total_runs}\n\n"
                f"{away} due up:\n" + "\n".join(away_hitters) + "\n\n"
                f"{home} due up:\n" + "\n".join(home_hitters)
            )

            alerted.add(key)

while True:
    try:
        check_games()
    except Exception as e:
        print("Error:", e)

    time.sleep(60)
