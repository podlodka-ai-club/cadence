#!/bin/sh
# Bring the checkout to the current main and restart the parser.
#
#     deploy/ship.sh
#
# Run it on the server, as the account that owns the checkout. Restarting
# costs nothing: every source keeps its place in the database, so the parser
# comes back where it stopped.
set -e

cd "$(dirname "$0")/.."
git pull --ff-only
.venv/bin/pip install --quiet --requirement requirements.txt
sudo systemctl restart cadence-parser
sleep 2
systemctl status --no-pager --lines=10 cadence-parser
