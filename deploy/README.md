# deploy

The online parser runs on a server as a systemd service. This directory holds the unit
file it runs under and the script that ships a new version to a machine already running
one.

| | |
| --- | --- |
| `cadence-parser.service` | the unit: what runs, as whom, and that it comes back after a fall |
| `ship.sh` | on the server: bring the checkout up to date and restart the service |

## A new version

On the server, as the account that owns the checkout:

```
deploy/ship.sh
```

It fast-forwards the checkout, installs what the requirements ask for, restarts the
service and shows what systemd says about it. A restart loses nothing: every source
keeps its place in the database, so the parser resumes where it stopped.

## The first time on a machine

1. Put the checkout where the unit expects it, and make a virtualenv beside it:

   ```
   git clone <repository> /opt/cadence
   cd /opt/cadence
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in both halves — the connection string and the
   database to write to, and the Telegram application the parser signs in as.

3. Sign the account in. It asks for the phone number and the code Telegram sends, and
   leaves a session file behind; after this the parser never asks again:

   ```
   .venv/bin/python -m parsers.telegram_live --login
   ```

4. Create the collections the parser needs:

   ```
   .venv/bin/python -m storage.setup cards sources
   ```

5. Add the channels to read, one command each:

   ```
   .venv/bin/python -m storage.add_source t.me/a_channel
   ```

6. Install the service. Set `User=` in the unit to the account that owns the checkout
   first, and `WorkingDirectory=` if the checkout is not at `/opt/cadence`:

   ```
   sudo cp deploy/cadence-parser.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now cadence-parser
   ```

## Looking at it

```
systemctl status cadence-parser
journalctl -u cadence-parser -f
```

The parser writes a line per source that had something, and a line for a source it could
not read. A quiet channel says nothing in the journal; when it was last asked is in its
`sources` document, as `lastPolledAt`.
