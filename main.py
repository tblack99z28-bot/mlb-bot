import requests
import time
from datetime import datetime
import os

# Get webhook from Railway Variables
WEBHOOK = os.getenv("DISCORD_WEBHOOK")

alerted_games = set()

def send_alert(message):
    if WEBHOOK:
        requests.post(WEBHOOK, json={"content": message})

def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    return requests.get(url).json()

def get_live(gamePk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
    return requests.get(url).json()

def check_games():
    print("Checking games...")
send_alert("🔥 BOT IS WORKING")
    schedule = get_schedule()

    for date in schedule.get("dates", []):
        for game in date.get("games", []):
            gamePk = game["gamePk"]

            live = get_live(gamePk)
            inning = live["liveData"]["linescore"].get("currentInning", 0)

            # Only 4th inning or later
            if inning < 4:
                continue

            # Avoid duplicate alerts
            if gamePk not in alerted_games:
                home = game["teams"]["home"]["team"]["name"]
                away = game["teams"]["away"]["team"]["name"]

                send_alert(
                    f"⚾ {away} vs {home}\n"
                    f"Inning {inning}\n"
                    f"Top of order likely coming up"
                )

                alerted_games.add(gamePk)

while True:
    try:
        check_games()
    except Exception as e:
        print("Error:", e)

    time.sleep(60)
