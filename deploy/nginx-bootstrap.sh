#!/bin/sh
set -eu

DOMAIN="clueai-reviewlens.com"
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
FULLCHAIN_PATH="${CERT_DIR}/fullchain.pem"
PRIVKEY_PATH="${CERT_DIR}/privkey.pem"

if [ -s "${FULLCHAIN_PATH}" ] && [ -s "${PRIVKEY_PATH}" ]; then
  exit 0
fi

mkdir -p "${CERT_DIR}"

openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout "${PRIVKEY_PATH}" \
  -out "${FULLCHAIN_PATH}" \
  -subj "/CN=${DOMAIN}"
