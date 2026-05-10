#!/bin/bash
# Oracle solver: copies the pre-renamed reference site that lives alongside
# this script (in /solution/site/) into /app/site/.
#
# The oracle answer is shipped inside the Harbor task's solution/ directory
# and is only copied into /solution/ in the container during Oracle runs,
# never during regular agent runs. The oracle therefore reads only what
# Harbor mounts at /solution/, with no other shared state to worry about.

set -euo pipefail

ORACLE_SITE_DIR="/solution/site"
SITE_DIR="/app/site"

if [ ! -d "${ORACLE_SITE_DIR}" ]; then
  echo "Missing oracle site at ${ORACLE_SITE_DIR}" >&2
  exit 1
fi

mkdir -p "${SITE_DIR}"
rm -rf "${SITE_DIR:?}"/*
cp -R "${ORACLE_SITE_DIR}"/. "${SITE_DIR}"/

echo "Oracle copied $(find "${SITE_DIR}" -maxdepth 1 -name '*.html' | wc -l) HTML page(s) to ${SITE_DIR}"
