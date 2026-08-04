# Executive Summary  
FACEIT provides a RESTful Data API (v4) for public esports data. To use it, you must have a **FACEIT account** (any personal or team account) and register an “App” in the FACEIT Developer Portal (developers.faceit.com). In the portal’s **App Studio**, create a new App, then generate a **Server-side API Key** under the “API Keys” panel【5†L27-L34】. The key (a long token string) is used as a Bearer token in all requests (see below). The API has no additional OAuth scopes; a valid key grants access to all publicly available data【10†L24-L31】. FACEIT does *not* publish explicit rate limits; in practice you will see HTTP 429 “Too Many Requests” if you exceed the undocumented quota【23†L771-L780】. (User reports indicate limits on the order of a few hundred requests per 30 seconds【32†L249-L258】.) All data (championships, tournaments, teams, matches, etc.) is fetched from FACEIT’s endpoints. Sensitive operations (storing the key) should be done locally: e.g. read the key from an environment variable or a protected config file (600 permissions or use a system key store), and never hard-code it in code or commit it to source. The key can be rotated or revoked at any time from the Developer Portal【5†L27-L34】【42†L35-L43】. In code, include proper error handling for 4xx/5xx errors. 

# Obtaining and Using the FACEIT API Key  
- **FACEIT Account:** First, register a free FACEIT user account (via [faceit.com] or the Developer Portal login)【1†L28-L34】. No special “company” status is required – a normal player account suffices.  
- **Developer Portal:** Visit **https://developers.faceit.com** and **Login** with your FACEIT credentials【1†L28-L34】. This opens the App Studio (JavaScript-based web UI).  
- **Create an App:** In the portal, create a new App (give it a name/description).  
- **Generate Key:** Within your App’s settings, go to the **API Keys** section. Click “+” or “Create” to add a new key. Choose *Server-side* as the key type (since our code runs on your local machine)【5†L27-L34】. Faceit will generate a new key string.  
- **Record the Key:** Copy and save this key; treat it like a password. The Developer Portal lets you revoke/regenerate keys at any time【5†L27-L34】.  

All FACEIT Data API calls require setting an HTTP header: `Authorization: Bearer <API_KEY>`【10†L24-L31】 (make sure there is a space after “Bearer”). No other “scope” or token format is needed. Also set `Content-Type: application/json` or accept JSON by default. If the key is missing or invalid, calls will return 401 Unauthorized or 403 Forbidden【21†L4918-L4927】. 

# Rate Limits and Quotas  
FACEIT’s official docs do **not specify exact rate limits**【23†L771-L780】. All endpoints list 429 as a possible response. In practice, heavy usage can trigger a rate limit. For example, community tests found ~400 requests in 30s triggered a block with “retry after” timeout【32†L249-L258】. If you exceed the limit, the API returns **429 Too Many Requests**【23†L771-L780】. Upon a 429, back off and retry after some delay (reports suggest up to 1 hour penalty【32†L249-L258】). To avoid limits, batch and throttle requests, and cache results when possible. Treat all endpoints as sharing a single quota. In summary, **assume ~400 requests/30s** and monitor 429 responses.

# Key Storage & Security Best Practices  
Since this app runs locally, **store the API key securely on your machine**. Do **not** hard-code it in source. Recommended methods:  
- **Environment Variable:** E.g. set `FACEIT_API_KEY` in your shell (bash/zsh) profile. Then in Python: `api_key = os.getenv("FACEIT_API_KEY")`. Environment variables keep keys out of code and out of version control【42†L35-L43】【42†L44-L52】.  
- **Config File:** Alternatively, use a local config file (e.g. `~/.config/faceit/config.yaml` or `/etc/faceit/config.yaml`) that is **chmod 600** (owner-read/write only). Example YAML:
  ```yaml
  faceit:
    api_key: "YOUR_FACEIT_API_KEY"
  ```
  Ensure this file is never checked into version control【42†L35-L43】.  
- **Keychain/Manager:** For higher security, use OS keyrings or a secrets manager, though for a single-user app this is optional【42†L119-L127】.  

Rotate the key periodically and revoke unused keys in the FACEIT dev portal【5†L27-L34】【42†L128-L134】. Immediately rotate/revoke if the key is compromised. The portal’s UI lets you revoke any key at will【5†L27-L34】.

# Endpoints for Championships, Teams, Matches  

FACEIT’s Data API v4 uses base URL `https://open.faceit.com/data/v4/`. Below are key endpoints:

| Name                     | Method | Endpoint Path                                              | Required Params (path/query)                                     | Notes & Rate Limit  |
|--------------------------|:------:|------------------------------------------------------------|------------------------------------------------------------------|---------------------|
| **List Championships**   | GET    | `/championships`                                           | `game` (string, game ID, required)                               | Supports `type` (all/upcoming/ongoing/past), `offset`, `limit`【27†L119-L128】. No published rate limit. |
| **Championship Details** | GET    | `/championships/{championship_id}`                         | `championship_id` (string, path)                                 | Optional `expanded` array (organizer, game)【29†L440-L449】. |
| **Championship Matches** | GET    | `/championships/{championship_id}/matches`                | `championship_id` (string, path); `type` (`all`/`upcoming`/etc.), `offset`, `limit`【23†L729-L737】 | Returns paginated list of matches in that championship. |
| **Match Details**        | GET    | `/matches/{match_id}`                                     | `match_id` (string, path)                                        | Returns full match info JSON【21†L4898-L4906】. |
| **Team Details**         | GET    | `/teams/{team_id}`                                        | `team_id` (string, path)                                         | Returns team info (name, players, etc.)【19†L9028-L9036】. |
| **Team Stats**           | GET    | `/teams/{team_id}/stats/{game_id}`                        | `team_id` (string); `game_id` (string, path)                     | Lifetime stats of a team in a game【19†L9159-L9167】. |
| **Search Teams**         | GET    | `/search/teams`                                           | `nickname` (string, required); `game` (string)                   | Search by team name and game【25†L8768-L8776】. |
| **(Others)**             |        | *(e.g. `/players/{player_id}`, `/organizers`, etc.)*     |                                                                  | The API has many endpoints (see full docs). |

Each request must include the header `Authorization: Bearer <API_KEY>`. For example, to get a match:  
```http
GET https://open.faceit.com/data/v4/matches/{match_id}
Authorization: Bearer YOUR_API_KEY
```
A successful response is HTTP 200 with JSON. The docs list standard error codes: **400** (bad parameters), **401** (no/invalid key), **403** (forbidden), **404** (not found), **429** (rate limit) and **503** (service unavailable)【21†L4918-L4927】【23†L771-L780】. Your code should check `response.status_code` and handle these (e.g. retry on 429 after delay, log or fail on 4xx).

# Python Example: Fetching and Storing Data  

Below is a minimal Python script demonstrating authenticated requests to FACEIT and saving raw JSON to a local SQLite DB. You can adapt it for matches, teams, etc.

```python
import os, requests, sqlite3, json

# --- Configuration and Setup ---
# Load API key from environment or config (example using env)
api_key = os.getenv("FACEIT_API_KEY")
if not api_key:
    raise RuntimeError("Set FACEIT_API_KEY environment variable!")

headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

# SQLite setup (stores raw data)
conn = sqlite3.connect('faceit.db')  # stored in current folder
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_match (
        match_id TEXT PRIMARY KEY,
        json TEXT
    )
''')
conn.commit()

# --- Example: Fetch recent match data ---
match_id = "some-match-id"  # replace with a real match ID
url = f"https://open.faceit.com/data/v4/matches/{match_id}"
resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    # Store raw JSON (as text) in SQLite
    cursor.execute('INSERT OR REPLACE INTO raw_match (match_id, json) VALUES (?,?)',
                   (data.get("match_id"), json.dumps(data)))
    conn.commit()
else:
    print(f"Error {resp.status_code}: {resp.text}")

conn.close()
```

**Running the script:**  
- Install dependencies: `pip install requests pyyaml` (or just `requests` if not using YAML).  
- Use a virtual environment (e.g. `python3 -m venv venv && source venv/bin/activate`) to isolate packages.  
- Set the API key in the environment before running, e.g. on Unix:
  ```bash
  export FACEIT_API_KEY="YOUR_KEY_HERE"
  python fetch_match.py
  ```  
- Alternatively, read from a `config.yaml`:  

```yaml
faceit:
  api_key: "YOUR_FACEIT_API_KEY"
  database: "./faceit.db"
```

and in Python use `import yaml` to load it. Ensure the config file is protected (chmod 600) and not in version control.

# Filesystem Paths & Permissions  

For a single-user local app, we suggest:

- **Configuration file:** e.g. `~/.config/faceit/config.yaml` (mode `600`, owner-only). This stores the API key (and other settings). Example permissions: `chmod 600 ~/.config/faceit/config.yaml`.  
- **Database & logs:** e.g. in `~/faceit_app/faceit.db` and `~/faceit_app/logs/`, also with permissions so only your user can read/write.  
- **Environment variable:** You can set `FACEIT_API_KEY` in your shell startup (not world-readable).  

Never put the key in a shared or public directory. If using Git, be sure to add config files or `.env` to `.gitignore`【42†L35-L43】.

# Citations 

Key FACEIT docs and sources used: FACEIT Developer Docs on API Keys (how to create/revoke)【5†L27-L34】, FACEIT Data API documentation for authentication and endpoints【10†L24-L31】【23†L771-L780】【21†L4898-L4906】【27†L119-L128】【29†L440-L449】【19†L9028-L9036】【25†L8768-L8776】. Community reports on rate limits【32†L249-L258】. Best practices on API key storage (env vars, rotation) from OpenAI guidance【42†L35-L43】【42†L44-L52】【42†L128-L134】. 

