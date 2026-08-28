#!/usr/bin/env bash
#
# Close out the records an earlier run left open, once the person has ruled on the
# change. Runs the manager, which routes the task to the retrospective skill.
set -euo pipefail

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-manager.sh" \
    retrospective-sync \
    "close out the records left inprogress in Claude Code Sessions, now that the pull requests they went out on have been merged or closed and the draft rules have been ruled on"
