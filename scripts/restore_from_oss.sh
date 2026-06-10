#!/usr/bin/env bash
# scripts/restore_from_oss.sh — 从 OSS 备份恢复到指定数据库（通常是 dev）
#
# 用法：
#   ./scripts/restore_from_oss.sh                    # 恢复最新备份到 DEV_DATABASE_URL
#   ./scripts/restore_from_oss.sh 20260610           # 恢复指定日期的备份
#   TARGET_DB_URL=<url> ./scripts/restore_from_oss.sh  # 恢复到自定义目标库
#
# 安全措施：默认只允许恢复到 dev 库，恢复到 prod 需要显式确认

set -euo pipefail

BUCKET="oss://clueai-backup"
OSSUTIL="ossutil64"
BACKUP_DATE="${1:-latest}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/../deploy/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/../deploy/.env"
    set +a
fi
if [ -f "${SCRIPT_DIR}/../.env" ]; then
    set -a
    source "${SCRIPT_DIR}/../.env"
    set +a
fi

TARGET_URL="${TARGET_DB_URL:-${DEV_DATABASE_URL:-}}"
if [ -z "$TARGET_URL" ]; then
    echo "ERROR: TARGET_DB_URL or DEV_DATABASE_URL not set"
    exit 1
fi

# Safety check: warn if restoring to prod
if echo "$TARGET_URL" | grep -q "inpgrbjwtpxgwungghnz"; then
    echo "⚠️  WARNING: Target looks like PRODUCTION database!"
    read -p "Type 'yes-restore-prod' to continue: " confirm
    if [ "$confirm" != "yes-restore-prod" ]; then
        echo "Aborted."
        exit 1
    fi
fi

if ! command -v ${OSSUTIL} &> /dev/null; then
    OSSUTIL="ossutil"
    if ! command -v ${OSSUTIL} &> /dev/null; then
        echo "ERROR: ossutil not found."
        exit 1
    fi
fi

# Find backup file
if [ "$BACKUP_DATE" = "latest" ]; then
    echo "Finding latest backup..."
    FILENAME=$(${OSSUTIL} ls "${BUCKET}/weekly/" | grep "clueai_prod_" | awk '{print $NF}' | sort | tail -1)
else
    FILENAME="${BUCKET}/weekly/clueai_prod_${BACKUP_DATE}.sql.gz"
fi

if [ -z "$FILENAME" ]; then
    echo "ERROR: No backup found."
    exit 1
fi

echo "Restoring from: ${FILENAME}"
echo "Target DB: (host hidden for security)"

TMPFILE=$(mktemp /tmp/clueai_restore_XXXXXX.sql.gz)
trap "rm -f $TMPFILE" EXIT

# Download
${OSSUTIL} cp "${FILENAME}" "${TMPFILE}"

# Restore
echo "Applying to database..."
gunzip -c "${TMPFILE}" | psql "${TARGET_URL}" --single-transaction -q

echo "✅ Restore complete."
echo "Verify: psql \$DEV_DATABASE_URL -c 'SELECT COUNT(*) FROM users;'"
