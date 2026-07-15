#!/usr/bin/env bash
#
# Build a Chrome Web Store upload package for the ClueAI ReviewLens extension.
#
# Produces dist/clueai-reviewlens-<version>.zip containing ONLY the files the
# extension needs at runtime — test fixtures, specs, and reports are excluded
# so the review package stays minimal (smaller = faster review, fewer flags).
#
# Usage:
#   bash scripts/build_extension_zip.sh
#
# The version is read from chrome-extension/manifest.json so the zip name always
# matches the manifest — bump manifest "version" before running for a new upload.

set -euo pipefail

# Resolve repo root relative to this script (works regardless of CWD).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXT_DIR="${REPO_ROOT}/chrome-extension"
DIST_DIR="${REPO_ROOT}/dist"

if [[ ! -f "${EXT_DIR}/manifest.json" ]]; then
  echo "❌ manifest.json not found at ${EXT_DIR}/manifest.json" >&2
  exit 1
fi

# Extract "version": "x.y.z" from manifest.json (no jq dependency).
VERSION="$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]+"' "${EXT_DIR}/manifest.json" \
  | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
if [[ -z "${VERSION}" ]]; then
  echo "❌ Could not parse version from manifest.json" >&2
  exit 1
fi

ZIP_NAME="clueai-reviewlens-${VERSION}.zip"
ZIP_PATH="${DIST_DIR}/${ZIP_NAME}"

mkdir -p "${DIST_DIR}"
rm -f "${ZIP_PATH}"

# Runtime files to ship. Keep this list explicit (allowlist, not denylist) so a
# stray dev file never leaks into a public upload.
FILES=(
  manifest.json
  background.js
  content.js
  inject.js
  i18n.js
  popup.html
  popup.css
  popup.js
)

# Verify every listed file exists before zipping.
for f in "${FILES[@]}"; do
  if [[ ! -f "${EXT_DIR}/${f}" ]]; then
    echo "❌ Required file missing: chrome-extension/${f}" >&2
    exit 1
  fi
done

# Icons dir is required by the manifest.
if [[ ! -d "${EXT_DIR}/icons" ]]; then
  echo "❌ icons/ directory missing" >&2
  exit 1
fi

echo "📦 Building ${ZIP_NAME} (manifest version ${VERSION})…"

# Zip from inside the extension dir so paths are relative to the extension root
# (Chrome requires manifest.json at the zip root, not nested in a folder).
(
  cd "${EXT_DIR}"
  zip -q -r "${ZIP_PATH}" "${FILES[@]}" icons/ \
    -x "icons/*.DS_Store"
)

SIZE="$(du -h "${ZIP_PATH}" | cut -f1)"
echo "✅ Built ${ZIP_PATH} (${SIZE})"
echo ""
echo "Contents:"
unzip -l "${ZIP_PATH}" | awk 'NR>3 && $4 != "" {print "  " $4}' | grep -v '^  $' || true
echo ""
echo "Next: upload ${ZIP_NAME} at https://chrome.google.com/webstore/devconsole"
