#!/usr/bin/env bash
# Rewrites OWL files in the canonical layout: ROBOT, at the version pinned in tools/robot.version.
# Same content in, same bytes out, whichever tool (app, Protégé, script) wrote the file.
#
#   tools/format-owl.sh <file>...           format in place
#   tools/format-owl.sh --check <file>...   exit 1 if formatting would change any file
#
# Needs Java 11+ on PATH. Downloads the pinned jar to .cache/robot/ on first use.
set -euo pipefail

check=false
if [ "${1:-}" = "--check" ]; then check=true; shift; fi
[ $# -gt 0 ] || { echo "usage: tools/format-owl.sh [--check] <file>..." >&2; exit 2; }

root=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=robot.version
source "$root/tools/robot.version"

java_major=$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\)\.\{0,1\}\([0-9]*\).*/\1 \2/p' | head -1)
read -r major minor <<<"$java_major"
[ "$major" = 1 ] && major=$minor
if [ -z "${major:-}" ] || [ "$major" -lt 11 ]; then
  echo "format-owl: ROBOT needs Java 11 or newer on PATH (found: $(java -version 2>&1 | head -1))" >&2
  exit 2
fi

jar="$root/.cache/robot/robot-$ROBOT_VERSION.jar"
if [ ! -f "$jar" ]; then
  mkdir -p "$(dirname "$jar")"
  curl -fsSL -o "$jar.part" "https://github.com/ontodev/robot/releases/download/v$ROBOT_VERSION/robot.jar"
  echo "$ROBOT_SHA256  $jar.part" | sha256sum -c --quiet
  mv "$jar.part" "$jar"
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
status=0
for f in "$@"; do
  out="$tmp/$(basename "$f")"
  java -jar "$jar" convert --catalog "$root/ontologies/catalog-v001.xml" \
    --input "$f" --format owl --output "$out"
  if $check; then
    if ! cmp -s <(tr -d '\r' <"$f") "$out"; then
      echo "::error file=$f::not in canonical layout; run tools/format-owl.sh $f" >&2
      diff <(tr -d '\r' <"$f") "$out" | head -20 >&2 || true
      status=1
    fi
  else
    mv "$out" "$f"
  fi
done
exit $status
