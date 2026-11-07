# DiscordBot (NlaBot)
TTKLabrat

Voice-time tracker with levels and a leaderboard, plus a music player and link/code redirects.

## AFK time is not counted
A voice session is split into active and AFK segments, and every voice state change re-evaluates
the member. Only active time adds to your total time and XP (1 XP per active minute).
These count as **AFK**:

| State | Default | Setting |
|---|---|---|
| In the server's AFK channel | always AFK | Server Settings → Overview → Inactive Channel |
| Deafened (self or server) | AFK | `COUNT_DEAFENED` |
| Muted | counted | `COUNT_MUTED` |
| Alone in a channel | counted | `COUNT_ALONE` |

AFK time is still recorded separately (`afk_ms`) and shown in `!level`.
In-progress time is saved every `CHECKPOINT_SECONDS`, so a crash loses at most that much,
and a restart no longer creates phantom time.

## Running
1. Create a bot at https://discord.com/developers/applications. Under **Bot**, enable
   **Server Members Intent** and **Message Content Intent**.
2. Install Python 3.10+ and FFmpeg (for music).
3. Set up and run:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env             # then put your token in DISCORD_TOKEN
   python main.py
   ```
Tests: `pip install -r requirements-dev.txt && pytest`

## Commands (prefix `!`)
| Command | What it does |
|---|---|
| `!level [@user]` | Level, XP, active time, AFK time, rank, current call |
| `!leaderboard` | Top 10 by active time |
| `!settime @user <hours>` | (Admin) Correct someone's active time; level follows automatically |
| `!play <url or search>`, `!skip`, `!queue`, `!pause`, `!resume`, `!stop`, `!leave` | Music |
| `!resetall vahvista` | (Admin) Zero everyone's time and levels; calls in progress count from the reset |
| `!clear <n>` | (Manage Messages) Delete the last n messages (max 100) |
| `!invite`, `!tableflip`, `!apua` | Misc |

Automatic features: progression post in `#progression` after each call (with level-up notice),
"crowded channel" announcement in `#generalpopulation` (with cooldown), and moving Nettix links /
code snippets to their own channels (`NETTIAUTO_CHANNEL_ID`, `CODE_CHANNEL_ID`).

## Data
`data/users/<id>.json`. Old (v1) files are migrated on load: their stored total becomes active
time. All totals were reset to zero on 2026-11-07 because the old ones included AFK time;
the pre-reset numbers are still in git history (commit `4cc5b63`) if you ever need them.
