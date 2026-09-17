import os, json, sys, requests
from datetime import datetime, timezone, timedelta

API_KEY = os.environ.get('SPORTSRC_API_KEY', '35cb7b6157ba67ecbb8f5fbff0086a28')
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'api'))
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.json')

MAJOR_LEAGUES = ['premier league', 'champions league', 'la liga', 'serie a', 'bundesliga', 'europa league', 'ligue 1', 'world cup', 'euro', 'copa america', 'libertadores', 'fa cup', 'carabao']

def is_major_league(league_name: str) -> bool:
    lower = league_name.lower()
    if not any(kw in lower for kw in MAJOR_LEAGUES):
        return False
    return True

def fetch_sportsrc_matches():
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    url = f'https://api.sportsrc.org/v2/?type=matches&sport=football&date={today}'
    print(f'Fetching {url}')
    res = requests.get(url, headers={'X-API-KEY': API_KEY})
    res.raise_for_status()
    return res.json().get('data', [])

def fetch_stream_details(match_id: str):
    url = f'https://api.sportsrc.org/v2/?type=detail&id={match_id}'
    print(f'   -> Fetching streams for {match_id}')
    res = requests.get(url, headers={'X-API-KEY': API_KEY})
    if res.status_code == 200:
        data = res.json().get('data', {})
        if isinstance(data, dict):
            return data.get('sources', [])
    return []

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load history DB
    db = {}
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r', encoding='utf-8') as f:
                db = json.load(f)
        except:
            pass

    raw_leagues = fetch_sportsrc_matches()
    processed = []
    api_calls_made = 1 # We just made 1

    for league in raw_leagues:
        lname = league.get('league', {}).get('name', '')
        if not is_major_league(lname):
            continue
        for match in league.get('matches', []):
            match_id = match.get('id')
            status = match.get('status', '')
            # If finished, skip detail fetching unless we really want it
            # We fetch streams if upcoming or live
            streams = []
            if status in ['live', 'inprogress', 'upcoming']:
                if match_id in db and len(db[match_id]) > 0:
                    streams = db[match_id]
                else:
                    # Limit calls per run to avoid huge spikes if something goes wrong
                    if api_calls_made < 150:
                        streams = fetch_stream_details(match_id)
                        db[match_id] = streams
                        api_calls_made += 1
            
            processed.append({
                'id': match_id,
                'title': match.get('title', ''),
                'homeTeam': match.get('teams', {}).get('home', {}).get('name', ''),
                'awayTeam': match.get('teams', {}).get('away', {}).get('name', ''),
                'homeLogo': match.get('teams', {}).get('home', {}).get('badge', ''),
                'awayLogo': match.get('teams', {}).get('away', {}).get('badge', ''),
                'league': lname,
                'leagueLogo': league.get('league', {}).get('logo', ''),
                'matchTime': match.get('timestamp', 0),
                'status': status,
                'streams': streams,
                'streamCount': len(streams)
            })

    # Save DB
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f)

    # Save Matches
    out_path = os.path.join(OUTPUT_DIR, 'matches.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'updatedAt': datetime.now(timezone.utc).isoformat(), 'matches': processed}, f, indent=2)
    print(f'Done! Processed {len(processed)} matches. API calls: {api_calls_made}')

if __name__ == '__main__':
    main()

