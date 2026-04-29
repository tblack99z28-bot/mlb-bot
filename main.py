import requests
import time
from datetime import datetime
import os

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

alerted = set()

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

def is_top_of_order_next(live_data, batting_team):
    try:
        offense = live_data["liveData"]["linescore"]["offense"]
        batting_order = live_data["liveData"]["boxscore"]["teams"][batting_team]["battingOrder"]

        current = offense.get("batter", {})
        current_id = current.get("id")

        if current_id not in batting_order:
            return False

        idx = batting_order.index(current_id)
        next_idx = (idx + 1) % len(batting_order)

        lineup_position = next_idx + 1

        return lineup_position in [1, 2, 3]

    except:
        return False

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

            half = linescore.get("inningHalf")

            if half == "Bottom":
                next_team = "away"
            else:
                next_team = "home"

            key = f"{gamePk}-{next_team}"
            if key in alerted:
                continue

            if is_top_of_order_next(live, next_team):

                home = game["teams"]["home"]["team"]["name"]
                away = game["teams"]["away"]["team"]["name"]

                home_runs = linescore["teams"]["home"]["runs"]
                away_runs = linescore["teams"]["away"]["runs"]

                total_runs = home_runs + away_runs

                send_alert(
                    f"🔥 TOP OF ORDER COMING UP\n"
                    f"{away} vs {home}\n"
                    f"Inning {inning+1} ({next_team} batting)\n\n"
                    f"Score: {away_runs} - {home_runs}\n"
                    f"Total Runs: {total_runs}"
                )

                alerted.add(key)

while True:
    try:
        check_games()
    except Exception as e:
        print("Error:", e)

    time.sleep(60)
