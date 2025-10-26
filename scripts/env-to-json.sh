#!/bin/bash
# Convert .env file to JSON format for Lightsail deployment
# Usage: ./env-to-json.sh .env

set -e

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: $ENV_FILE not found" >&2
    exit 1
fi

# Start JSON object
echo "{"

# Parse .env and convert to JSON
first=true
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Extract key=value, removing 'export ' prefix
    line="${line#export }"

    # Skip if not a valid env var
    [[ ! "$line" =~ ^[A-Z_][A-Z0-9_]*= ]] && continue

    # Split on first =
    key="${line%%=*}"
    value="${line#*=}"

    # Remove quotes from value
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"

    # Add comma if not first
    if [ "$first" = false ]; then
        echo ","
    fi
    first=false

    # Output JSON key-value (escape quotes in value)
    value_escaped="${value//\\/\\\\}"
    value_escaped="${value_escaped//\"/\\\"}"
    printf "  \"%s\": \"%s\"" "$key" "$value_escaped"
done < "$ENV_FILE"

# Close JSON object
echo ""
echo "}"
