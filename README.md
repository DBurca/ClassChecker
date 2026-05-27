# ClassChecker

Monitors Texas A&M College Scheduler course availability, sends Discord notifications, and can attempt registration when a desired section opens.

## Setup

1. Copy environment and config templates:

   ```bash
   cp .env.example .env
   cp config.example.py config.py
   ```

2. Edit `.env` — `USERID`, `TERMCODE`, `DISCORD_WEBHOOK`, and the four cookie values (from your browser session).
* `USERID` is the ID that collegescheduler uses to schedule classes, it is not the UIN.
* `TERMCODE` is the specific term you are registering for.
* `DISCORD_WEBHOOK` allows you to send registration notifications to a Discord server.
* When pasting your cookies, log in first, then use a cookie extension to copy the exact values. This will allow the script to authenticate.

3. Edit `config.py` — `ROOT_URL`, `DESIRED`, `TRACKED`, and optional `SWAP_MATRIX`.
* Do not edit `ROOT_URL`
* `DESIRED` holds the classes that you would like to register for.
* `TRACKED` can track specific sections or courses and send you a Discord message, but it won't register.
* `SWAP_MATRIX` is an advanced feature that will drop a current section before attempting to register for a desired section. This is best used for time conflicts.

5. Install and run:

   ```bash
   pip install -r requirements.txt
   python course_checker.py
   ```

## Docker

Ensure `.env` and `config.py` exist locally, then:

```bash
docker compose up --build
```

## Files

| File | Purpose |
|------|---------|
| `.env` | Secrets: user id, term code, webhook, cookies (gitignored) |
| `config.py` | Course dicts and term API URL (gitignored; copy from `config.example.py`) |
| `course_checker.py` | Monitor logic |
| `settings.py` | Loads `.env` into runtime variables |

`getcookie.py`, `test1.py`, and `discord_bot.py` are local WIP scripts and are not tracked in git.

Refresh `COOKIE_ASPNET` and `COOKIE_REQUEST_VERIFICATION` when the script reports auth failures. These are the most important.

<sub>Part of the repository was created with the use of AI</sub>
