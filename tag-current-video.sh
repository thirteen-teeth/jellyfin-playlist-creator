#!/bin/bash
set -euo pipefail

# --- Configuration ---
JELLYFIN_URL="${JELLYFIN_URL:-http://localhost:8096}"
API_KEY="${JELLYFIN_API_KEY:-}"
USER_ID="${JELLYFIN_USER_ID:-}"

# --- Validate configuration ---
if [ -z "$API_KEY" ]; then
  echo "Error: JELLYFIN_API_KEY is not set."
  echo "Set it with: export JELLYFIN_API_KEY=your-api-key-here"
  exit 1
fi

if [ -z "$USER_ID" ]; then
  echo "Error: JELLYFIN_USER_ID is not set."
  echo "Set it with: export JELLYFIN_USER_ID=your-user-id-here"
  exit 1
fi

# --- Validate input ---
if [ $# -eq 0 ]; then
  echo "Usage: tag-current-video.sh <tag1> [tag2] [tag3] ..."
  echo "Example: tag-current-video.sh cat dog pickle"
  exit 1
fi

TAGS=("$@")

# --- Get currently playing item ---
echo "Fetching currently playing video..."
SESSIONS=$(curl -sf -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Sessions")

ITEM_ID=$(echo "$SESSIONS" | jq -r --arg uid "$USER_ID" '
  .[] | select(.UserId == $uid and .NowPlayingItem != null) | .NowPlayingItem.Id
' | head -n 1)

if [ -z "$ITEM_ID" ] || [ "$ITEM_ID" = "null" ]; then
  echo "Error: No video is currently playing for your user."
  exit 1
fi

ITEM_NAME=$(echo "$SESSIONS" | jq -r --arg uid "$USER_ID" '
  .[] | select(.UserId == $uid and .NowPlayingItem != null) | .NowPlayingItem.Name
' | head -n 1)

echo "Currently playing: $ITEM_NAME (ID: $ITEM_ID)"

# --- Fetch current item metadata ---
CURRENT=$(curl -sf -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Items/$ITEM_ID")

# --- Build updated Tags array, appending only new tags ---
TAGS_JSON=$(printf '%s\n' "${TAGS[@]}" | jq -R . | jq -s .)
UPDATED=$(echo "$CURRENT" | jq --argjson new_tags "$TAGS_JSON" '
  .Tags //= [] |
  .Tags += ($new_tags - .Tags)
')

# --- Push updated metadata ---
curl -sf -X POST -H "X-Emby-Token: $API_KEY" -H "Content-Type: application/json" \
  -d "$UPDATED" "$JELLYFIN_URL/Items/$ITEM_ID"

# --- Summary ---
APPLIED_TAGS=$(printf "'%s' " "${TAGS[@]}")
echo "✅ Tagged \"$ITEM_NAME\" with: $APPLIED_TAGS"
