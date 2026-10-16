# Climbing openGym fork — tired-night build guide

Oct 15, 2026 · @Matt

## Mac or server?

Write code on the MacBook. Run the finished thing on the Linux server.

- **Faster.** Edit, save, refresh the browser. No SSH lag, no copying files around.
- **Safer.** You can break your Mac copy at 1am and your live training data on the server is untouched.
- **Bluetooth.** Chrome on macOS supports Web Bluetooth, and `localhost` counts as secure. You can test the force gauge on the Mac without setting up HTTPS.
- **Simple flow.** GitHub sits in the middle. Mac pushes, server pulls. You never edit files on the server.

The one thing you can't test on the Mac is passkey login from your phone. That needs HTTPS on a real domain, so you test it on the server.

## Ground rules for tired nights

1. One night = one section. Stop when you hit its **Done when** line, even if you feel like going on.
2. Before you start, open a terminal and run `cd ~/code/climb-gym && git status`. It should say "nothing to commit". If not, see the last section.
3. Before you stop, save your work to GitHub: `git add -A && git commit -m "night N: what I did" && git push`
4. Never type your Garmin password into a file. It goes in `.env`, which git ignores.
5. Stuck for more than 15 minutes? Write down the exact error, close the laptop, and paste it to Claude tomorrow.

## Night 1: get stock openGym running on the Mac

**Done when:** openGym's home screen loads at http://localhost:8080 and your copy is on GitHub.

1. Install the tools (skip any you already have): `brew install git python@3.12 node` Then install [OrbStack](https://orbstack.dev) or Docker Desktop, and open it once so Docker is running.
2. On GitHub, create a new **private** repo called `climb-gym`. Leave it empty: no README, no licence.
3. Clone openGym and point it at your repo. Replace `YOUR-REPO-URL` with the URL GitHub shows you:

   ```
   mkdir -p ~/code && cd ~/code
   git clone https://github.com/DuarteSantos8/openGym climb-gym
   cd climb-gym
   git remote rename origin upstream
   git remote add origin YOUR-REPO-URL
   git push -u origin main
   ```

   `upstream` is the original project, so you can pull its updates later. `origin` is yours.
4. Make a branch for your changes: `git checkout -b climbing && git push -u origin climbing`
5. Check that secrets and data won't get committed. Both commands should print a line: `grep -n '^\.env$' .gitignore` and `grep -n 'data' .gitignore` If either prints nothing, add the missing line to `.gitignore`.
6. Start it:

   ```
   cp .env.example .env
   docker compose up -d --build
   ```

   The first build takes a few minutes.
7. Open http://localhost:8080 in Chrome, tap **Create profile**, and pick a name.

To stop it: `docker compose down`. Your data stays in `./data`.

## Night 2: see what openGym saves

**Done when:** you know which key in the JSON holds your logged workouts.

1. In the app, add any timed exercise (search "dead hang") to today's routine, start the workout and log two sets. Finish it.
2. In the terminal, list the data files: `ls data/` You should see a `state-SOMETHING.json`.
3. Make a scratch folder for throwaway scripts (git ignores it if you add it to `.gitignore`): `mkdir -p scratch && echo scratch/ >> .gitignore`
4. Create `scratch/peek.py`:

   ```python
   import json, glob
   
   path = glob.glob("data/state-*.json")[0]
   state = json.load(open(path))
   
   print("File:", path)
   for key, value in state.items():
       size = len(value) if hasattr(value, "__len__") else ""
       print(f"{key:25} {type(value).__name__:6} {size}")
   ```
5. Run it: `python3 scratch/peek.py`
6. Pick the key that looks like workouts or history and print one entry: `python3 -c "import json,glob; s=json.load(open(glob.glob('data/state-*.json')[0])); print(json.dumps(s['PUT_KEY_HERE'], indent=2)[:3000])"`
7. Write down in a notes file what a logged set looks like (field names for exercise, reps, duration, date). You'll need this on Night 8.

## Night 3: pull one Garmin session into a file

**Done when:** you have a JSON dump of one strength session and one bouldering session, and you've found the sets and the grades inside them.

1. Add your Garmin login to the end of `.env`:

   ```
   GARMIN_EMAIL=you@example.com
   GARMIN_PASSWORD=your-password
   ```
2. Make the folder and a Python environment:

   ```
   mkdir garmin-sync && cd garmin-sync
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install garminconnect curl_cffi python-dotenv
   echo .venv/ >> ../.gitignore
   ```
3. Create `garmin-sync/garmin_login.py`. Every other script imports this:

   ```python
   import os
   from pathlib import Path
   from dotenv import load_dotenv
   from garminconnect import Garmin
   
   load_dotenv(Path(__file__).parent.parent / ".env")
   TOKEN_DIR = os.environ.get("GARMIN_TOKEN_DIR", str(Path("~/.garminconnect").expanduser()))
   
   def get_client():
       g = Garmin(
           os.environ["GARMIN_EMAIL"],
           os.environ["GARMIN_PASSWORD"],
           prompt_mfa=lambda: input("Garmin MFA code: "),
       )
       g.login(TOKEN_DIR)
       return g
   ```
4. Create `garmin-sync/list_recent.py`:

   ```python
   from garmin_login import get_client
   
   g = get_client()
   for a in g.get_activities(0, 30):
       print(a["activityId"], a["startTimeLocal"], a["activityType"]["typeKey"], a.get("activityName"))
   ```
5. Run it: `python list_recent.py`. The first run may ask for an MFA code. After that, tokens are saved and it won't ask again.
6. Note down the `typeKey` for your strength sessions and your bouldering sessions, and copy one activity id of each.
7. Create `garmin-sync/dump_one.py`:

   ```python
   import json, sys
   from pathlib import Path
   from garmin_login import get_client
   
   activity_id = sys.argv[1]
   g = get_client()
   
   out = {"summary": g.get_activity(activity_id)}
   for name, fn in [("splits", g.get_activity_splits), ("exercise_sets", g.get_activity_exercise_sets)]:
       try:
           out[name] = fn(activity_id)
       except Exception as e:
           out[name] = f"ERROR: {e}"
   
   folder = Path("../scratch/dumps")
   folder.mkdir(parents=True, exist_ok=True)
   (folder / f"{activity_id}.json").write_text(json.dumps(out, indent=2))
   print("Saved", folder / f"{activity_id}.json")
   ```
8. Run it once per activity: `python dump_one.py 1234567890`
9. Open the dumps in VS Code. Search the strength one for `"reps"` and the bouldering one for `grade`. Write down where each lives.

If login fails: check the [python-garminconnect README](https://github.com/cyberjunky/python-garminconnect). Garmin changed its login in March 2026 and the library has changed with it.

If the bouldering grades aren't in the JSON: they will be in the original FIT file. That's a separate small job with the `fitdecode` library; leave it for another night.

## Night 4: a sync script that writes data/garmin.json

**Done when:** running `python sync.py` creates `data/garmin.json` with your last four weeks of climbing and strength sessions.

1. Create `garmin-sync/sync.py`. Change the `WANTED` set to the typeKeys you wrote down on Night 3:

   ```python
   import json, os
   from datetime import date, timedelta
   from pathlib import Path
   from garmin_login import get_client
   
   WANTED = {"strength_training", "bouldering", "indoor_climbing"}
   DAYS_BACK = 28
   DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent.parent / "data"))
   OUT_FILE = DATA_DIR / "garmin.json"
   
   
   def load_existing():
       if OUT_FILE.exists():
           return json.loads(OUT_FILE.read_text())
       return {"activities": {}}
   
   
   def fetch_details(g, activity_id, type_key):
       if type_key == "strength_training":
           return {"exercise_sets": g.get_activity_exercise_sets(activity_id)}
       return {"splits": g.get_activity_splits(activity_id)}
   
   
   def sync():
       g = get_client()
       store = load_existing()
       start = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
       new_count = 0
   
       for a in g.get_activities_by_date(start, date.today().isoformat()):
           type_key = a["activityType"]["typeKey"]
           activity_id = str(a["activityId"])
           if type_key not in WANTED or activity_id in store["activities"]:
               continue
           store["activities"][activity_id] = {
               "date": a["startTimeLocal"][:10],
               "type": type_key,
               "name": a.get("activityName"),
               "duration_min": round(a.get("duration", 0) / 60),
               "details": fetch_details(g, activity_id, type_key),
           }
           new_count += 1
   
       store["last_sync"] = date.today().isoformat()
       OUT_FILE.write_text(json.dumps(store, indent=2))
       print(f"Synced: {new_count} new, {len(store['activities'])} total")
   
   
   if __name__ == "__main__":
       sync()
   ```
2. Run it: `python sync.py`
3. Run it again. It should say `0 new`, because it skips sessions it already has.
4. Look at `data/garmin.json` and check that it makes sense.

It only keeps what you need, and it never touches openGym's own state file.

## Night 5: run the sync in Docker next to openGym

**Done when:** `docker compose logs garmin-sync` shows a "Synced" line, and it repeats every 30 minutes.

1. Create `garmin-sync/run_forever.py`:

   ```python
   import time, traceback
   from sync import sync
   
   while True:
       try:
           sync()
       except Exception:
           traceback.print_exc()
       time.sleep(30 * 60)
   ```
2. Create `garmin-sync/requirements.txt`:

   ```
   garminconnect
   curl_cffi
   python-dotenv
   ```
3. Create `garmin-sync/Dockerfile`:

   ```
   FROM python:3.12-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY *.py .
   CMD ["python", "-u", "run_forever.py"]
   ```
4. Copy your saved Garmin tokens into the project, so the container doesn't need an MFA code:

   ```
   cd ~/code/climb-gym
   cp -r ~/.garminconnect garmin-tokens
   echo garmin-tokens/ >> .gitignore
   ```
5. Create `docker-compose.override.yml` in the project root. Docker reads this automatically on top of openGym's own compose file, so you never edit theirs (fewer clashes when you pull their updates):

   ```yaml
   services:
     garmin-sync:
       build: ./garmin-sync
       env_file: .env
       environment:
         DATA_DIR: /data
         GARMIN_TOKEN_DIR: /tokens
       volumes:
         - ./data:/data
         - ./garmin-tokens:/tokens
       restart: unless-stopped
   ```
6. Start it: `docker compose up -d --build garmin-sync`
7. Watch it: `docker compose logs -f garmin-sync` (Ctrl+C to stop watching).

If the log shows it waiting for an MFA code, the tokens didn't load. Check that `garmin-tokens/` has a file in it.

## Night 6: set up your climbing plan in the app (no code)

**Done when:** your week of sessions exists in the app and you've exported a backup.

openGym already lets you make your own exercises, so you don't need to touch the 5,600-exercise library yet. Easy night.

1. In the app, create your own exercises. Set hangs and timed work as **timed**:
   - **Fingers:** max hangs, repeaters (7:3), density hangs, one-arm hang (left/right)
   - **Climbing:** limit bouldering, 4x4s, board session
   - **Pull:** weighted pull-ups, lock-offs, front lever progression
   - **Antagonists and core:** push-ups, overhead press, reverse wrist curls, hanging leg raises
2. Build one routine per session type: for example *Fingers + Pull*, *Limit bouldering*, *Antagonists*.
3. In Settings, switch the plan to **rotation**. The next session is then just the next one you haven't done, which copes with missed days.
4. Export everything as JSON from Settings and save it somewhere outside the project. This is your backup before the coding nights.

Hiding the screens you don't use (plate math, body map, 1RM) is a later job. It's cosmetic, so leave it until the useful parts work.

## Night 7: let the app read garmin.json

**Done when:** opening http://localhost:8080/api/external/garmin in Chrome (while signed in) shows your Garmin JSON.

The API is plain Node with no framework. Think of it like a Python `http.server` handler: one function looks at `req.url` and decides what to send back. You're adding one more `if` branch.

1. Find how existing routes are written:

   ```
   grep -n "^  /" api/openapi.yaml
   grep -rn "pathname\|req.url" api --include=*.js | grep -v test | head -30
   ```
2. Open the file the routes live in. Find a simple GET route that needs you to be signed in. Note two things: how it gets the signed-in user, and how it sends a "not signed in" error.
3. Next to that route, add a branch shaped like this. Fill in the two commented lines by copying from the route you found:

   ```js
   if (req.method === 'GET' && pathname === '/api/external/garmin') {
     // const user = ...copy how the neighbouring route gets the user
     // if (!user) ...copy its "not signed in" response
     const file = path.join(DATA_DIR, 'garmin.json');
     const body = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '{"activities":{}}';
     res.writeHead(200, { 'Content-Type': 'application/json' });
     res.end(body);
     return;
   }
   ```

   Check the file already imports `fs` and `path` at the top, and what it calls the data folder (it may not be `DATA_DIR`).
4. Rebuild just the API: `docker compose up -d --build api`
5. Test in Chrome while signed in. Then test in a private window: you should get the "not signed in" error.

**Shortcut:** the repo has a `CLAUDE.md`, so Claude Code already knows its layout. You can ask it: *"Add a GET /api/external/garmin route that returns data/garmin.json to signed-in users, following the pattern of the existing routes. Keep it minimal."* Then read the diff before committing.

## Night 8: show your Fenix sessions on the home screen

**Done when:** the home screen has a "From your Fenix this week" card listing your sessions.

React in Python terms: a component is a function that returns HTML-like markup. `useState` is a variable that redraws the screen when you change it. `useEffect(..., [])` runs once when the component first appears.

1. Check whether the frontend uses JavaScript or TypeScript: `ls frontend/src/components | head`. Files ending `.tsx` mean TypeScript; `.jsx` means JavaScript.
2. Create `frontend/src/components/GarminWeek.jsx` (or `.tsx`):

   ```jsx
   import { useEffect, useState } from 'react';
   
   export default function GarminWeek() {
     const [activities, setActivities] = useState([]);
   
     useEffect(() => {
       fetch('/api/external/garmin', { credentials: 'include' })
         .then((r) => r.json())
         .then((data) => {
           const weekAgo = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
           const recent = Object.values(data.activities).filter((a) => a.date >= weekAgo);
           recent.sort((a, b) => b.date.localeCompare(a.date));
           setActivities(recent);
         })
         .catch(() => setActivities([]));
     }, []);
   
     return (
       <div>
         <h3>From your Fenix this week</h3>
         {activities.length === 0 && <p>Nothing synced yet.</p>}
         <ul>
           {activities.map((a) => (
             <li key={a.date + a.name}>
               {a.date} · {a.type} · {a.name} · {a.duration_min} min
             </li>
           ))}
         </ul>
       </div>
     );
   }
   ```
3. Find the home screen file: `grep -rln "Home" frontend/src --include=*.jsx --include=*.tsx | head`
4. In that file, add `import GarminWeek from '../components/GarminWeek';` at the top (adjust the `../` to match the folder), and put `<GarminWeek />` somewhere in what it returns.
5. Rebuild: `docker compose up -d --build web`, then refresh the browser.

If it's TypeScript and the build complains about types, ask Claude Code to fix the types in that one file.

Unstyled is fine tonight. Making it look right and auto-ticking planned sessions from Garmin data come after this works.

## Night 9: talk to the force gauge from Chrome

**Done when:** numbers on the screen change live when you pull on the gauge.

Test it in a single throwaway HTML page first, outside openGym. Once you know which data fields come through, building it into the app is much easier.

1. Create `scratch/hang-test.html`. Change `Progressor` to your device's class name if you have something else (the [Grip Connect README](https://github.com/Stevie-Ray/hangtime-grip-connect) lists them, e.g. `WHC06`, `ForceBoard`):

   ```html
   <!doctype html>
   <button id="go">Connect</button>
   <pre id="out">Not connected</pre>
   
   <script type="module">
     import { Progressor } from "https://cdn.jsdelivr.net/npm/@hangtime/grip-connect/+esm";
   
     const device = new Progressor();
     const out = document.getElementById("out");
   
     device.notify((data) => {
       out.textContent = JSON.stringify(data, null, 2);
     });
   
     document.getElementById("go").onclick = () =>
       device.connect(
         async () => { await device.stream(); },
         (err) => { out.textContent = "Error: " + err; }
       );
   </script>
   ```
2. Serve it with Python: `cd scratch && python3 -m http.server 8000`
3. Open http://localhost:8000/hang-test.html in **Chrome** (Safari has no Web Bluetooth). Wake the gauge, click Connect, pick it from the list.
4. Pull on it. Write down which field holds the current force and what unit it's in.

If Chrome doesn't list the device, check System Settings → Privacy & Security → Bluetooth and allow Chrome.

**Next nights from here:** detect a hang (force goes above about 5 kg = start, drops back below = end), record peak and average force and duration per hang, then move it into openGym as a Hang screen.

## Putting it on the Linux server

Do this any time after Night 5, once something works on the Mac.

**First time:**

1. SSH in and clone your repo (the server needs read access: add a GitHub deploy key, or use `gh auth login`):

   ```
   cd ~ && git clone YOUR-REPO-URL climb-gym
   cd climb-gym && git checkout climbing
   ```
2. From the Mac, copy over the files git doesn't carry: `scp -r .env garmin-tokens YOUR-SERVER:~/climb-gym/`
3. On the server, edit `.env` and set `RP_ID` and `ORIGIN` to your real domain.
4. Set up HTTPS by following openGym's [self-hosting guide](https://github.com/DuarteSantos8/openGym/blob/main/docs/SELF_HOSTING.md). Cloudflare Tunnel or Caddy are the least fiddly.
5. Start it: `docker compose up -d --build`
6. On your phone, open your domain, sign in with a passkey, and add it to the home screen.

**Every update after that:**

1. On the Mac: commit and `git push`.
2. On the server: `cd ~/climb-gym && git pull && docker compose up -d --build`

**Backups:** everything is in `~/climb-gym/data`. A nightly cron line is enough: `0 3 * * * tar czf ~/backups/climb-gym-$(date +\%F).tgz -C ~/climb-gym data`

**Pulling openGym's own updates** (do this on a fresh evening, not a tired one): `git fetch upstream && git merge upstream/main`. If it reports conflicts, `git merge --abort` puts everything back and you can deal with it another day.

## When something breaks

| Symptom | Try this |
| --- | --- |
| App won't load at localhost:8080 | `docker compose ps` to see what's running, then `docker compose logs -f api` (or `web`) |
| You changed code but nothing changed | You forgot to rebuild: `docker compose up -d --build api` or `web` |
| Everything is a mess and you want last night's version back | `git stash` hides tonight's changes. `git stash pop` brings them back if you change your mind |
| `git status` shows files you don't recognise | `git diff` to see what changed. If unsure, `git stash` and look tomorrow |
| Garmin login keeps failing | `pip install -U garminconnect curl_cffi`, then check the library's GitHub issues for the last week |
| Garmin sync worked, now asks for MFA | Tokens expired. Run `python list_recent.py` on the Mac, then copy `~/.garminconnect` into `garmin-tokens/` again |
| Passkey login fails on the server | `RP_ID` and `ORIGIN` in `.env` don't match the domain you're visiting |
| Port 8080 already in use | Set `WEB_PORT=8081` in `.env` and use that |
