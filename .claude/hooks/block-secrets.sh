#!/usr/bin/env bash
# PreToolUse (Edit|Write): block obvious secrets and sensitive filenames.
set -euo pipefail

INPUT="$(cat)"

if command -v jq >/dev/null 2>&1; then
  FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')"
  CONTENT="$(printf '%s' "$INPUT" | jq -r '.tool_input.content // .tool_input.new_string // empty')"
else
  FILE_PATH="$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  CONTENT=""
fi

VIOLATIONS=()

case "$FILE_PATH" in
  *.pem|*.key|*/id_rsa|*/id_ed25519|*credentials*.json|*service-account*.json)
    VIOLATIONS+=("sensitive filename: $FILE_PATH")
    ;;
esac

case "$FILE_PATH" in
  *.env.example|*.env.sample) ;;
  *.env|*.env.*|*/.env|*/.env.*)
    VIOLATIONS+=("env file write blocked: $FILE_PATH")
    ;;
esac

check() {
  local pattern="$1" label="$2"
  [ -z "$CONTENT" ] && return 0
  if printf '%s' "$CONTENT" | grep -Eq -- "$pattern"; then
    VIOLATIONS+=("$label")
  fi
}

check 'AKIA[0-9A-Z]{16}' 'AWS access key'
check '-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----' 'private key block'
check 'xox[baprs]-[A-Za-z0-9-]{10,}' 'Slack token'
check 'ghp_[A-Za-z0-9]{36}' 'GitHub PAT'
check 'sk-(ant-)?[A-Za-z0-9_-]{20,}' 'API key (Anthropic/OpenAI style)'
check 'AIza[0-9A-Za-z_-]{35}' 'Google API key'
check 'lsv2_[a-z]+_[A-Za-z0-9]+' 'LangSmith API key'

if [ "${#VIOLATIONS[@]}" -gt 0 ]; then
  REASON="block-secrets: refusing write. Found: $(IFS=', '; echo "${VIOLATIONS[*]}"). Use placeholders or keep secrets in gitignored env files."
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg reason "$REASON" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
  else
    printf '%s\n' "$REASON" >&2
    exit 2
  fi
  exit 0
fi

exit 0
