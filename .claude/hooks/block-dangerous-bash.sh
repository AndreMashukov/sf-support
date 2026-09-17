#!/usr/bin/env bash
# PreToolUse (Bash): deny force-push, hosting deploy, destructive rm -rf.
set -euo pipefail

INPUT="$(cat)"
if command -v jq >/dev/null 2>&1; then
  COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')"
else
  COMMAND="$(printf '%s' "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi

[ -z "$COMMAND" ] && exit 0

deny() {
  local reason="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg reason "$reason" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
  else
    printf '%s\n' "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":$(printf '%s' "$reason" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}}"
  fi
  exit 0
}

if printf '%s' "$COMMAND" | grep -Eq 'firebase[[:space:]]+deploy([^[:alnum:]]|$).*--only[[:space:]]*hosting|firebase[[:space:]]+deploy[[:space:]]+--only[[:space:]]+hosting'; then
  deny "This repo is not StudyForge web hosting. Do not firebase deploy hosting from sf-support."
fi

if printf '%s' "$COMMAND" | grep -Eq 'git[[:space:]]+push[[:space:]].*(--force|-f)([[:space:]]|$)|git[[:space:]]+push[[:space:]]+-f'; then
  deny "Force push blocked by project hook."
fi

if printf '%s' "$COMMAND" | grep -Eq '(^|[[:space:];|&])rm[[:space:]]+(-[a-zA-Z]*f[a-zA-Z]*|--force).*[[:space:]]+/($|[[:space:]])|(^|[[:space:];|&])rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*)[[:space:]]+(\.\.|~|/|\$HOME)'; then
  deny "Destructive rm -rf of home/root/parent paths blocked by project hook."
fi

exit 0
