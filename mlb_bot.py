import requests
import time
from datetime import datetime

WEBHOOK = "https://discord.com/api/webhooks/1498505186237350122/UblzkcAfiGU9S8w6SuSYSW-KjZUmPcL7uwI1-fxR898lj7vVcuqxRUJb8Y5ZPU5uuGk_"

alerted_games = set()

def send_alert(message):
    requests.post(WEBHOOK, json={"content": message})

def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"
    return requests.get(url).json()

def get_live(gamePk):
    url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
    return requests.get(url).json()

def get_next_batter_position(team_data):
    # Get batting order sorted
    players = team_data["players"]
    lineup = []

    for p in players.values():
        if "battingOrder" in p:
            lineup.append((int(p["battingOrder"]), p))

    lineup.sort(key=lambda x: x[0])
    lineup = [p for _, p in lineup]

    if not lineup:
        return None

    # Find current batter
    current_batter_id = team_data.get("currentBatter", {}).get("id")

    for i, player in enumerate(lineup):
        if player["person"]["id"] == current_batter_id:
            return (i + 1) % len(lineup)  # next batter index

    return 0

def top_of_order_due(next_index, lineup_size):
    order = [(next_index + i) % lineup_size + 1 for i in range(3)]
    return any(x in [1, 2, 3] for x in order)

def check_games():
 send_alert("✅ TEST: Bot is working")
    schedule = get_schedule()

    for date in schedule.get("dates", []):
        for game in date.get("games", []):
            gamePk = game["gamePk"]

            live = get_live(gamePk)
            linescore = live["liveData"]["linescore"]

            inning = linescore.get("currentInning", 0)

            if inning < 4:
                continue

            box = live["liveData"]["boxscore"]["teams"]

            home = box["home"]
            away = box["away"]

            home_next = get_next_batter_position(home)
            away_next = get_next_batter_position(away)

            if home_next is None or away_next is None:
                continue

            home_ok = top_of_order_due(home_next, 9)
            away_ok = top_of_order_due(away_next, 9)

            if home_ok and away_ok:
                if gamePk not in alerted_games:
                    home_name = game["teams"]["home"]["team"]["name"]
                    away_name = game["teams"]["away"]["team"]["name"]

                    msg = (
                        f"⚾ {away_name} vs {home_name}\n"
                        f"Inning: {inning}\n"
                        f"🔥 Top of order due next inning for BOTH teams"
                    )

                    send_alert(msg)
                    alerted_games.add(gamePk)

def main():
    while True:
        try:
            check_games()
        except Exception as e:
            print("Error:", e)

        time.sleep(60)

if __name__ == "__main__":
    main()