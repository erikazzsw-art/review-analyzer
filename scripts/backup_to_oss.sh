#!/usr/bin/env bash
# scripts/backup_to_oss.sh — 周备份 Supabase PostgreSQL 到阿里云 OSS
#
# 前置条件（首次使用前需手动完成）：
#   1. 阿里云 OSS 创建 bucket: clueai-backup（标准存储，区域同 ECS）
#   2. ECS 安装 ossutil:
#      curl -o /usr/local/bin/ossutil64 https://gosspublic.alicdn.com/ossutil/1.7.18/ossutil-v1.7.18-linux-amd64/ossutil64
#      chmod +x /usr/local/bin/ossutil64
#      ossutil64 config  # 填入 AccessKey ID/Secret + endpoint
#   3. ECS 上设置环境变量 PROD_DATABASE_URL（或从 deploy/.env 加载）
#   4. 确保 pg_dump 已安装（apt install postgresql-client-15）
#
# 用法：
#   ./scripts/backup_to_oss.sh           # 手动执行
#   crontab: 0 9 * * 1 /path/to/scripts/backup_to_oss.sh  # 每周一 09:00
#
# 保留策略：近 4 周全量保留，更早的按月保留 1 份（每月 1 号那份）

set -euo pipefail

BUCKET="oss://clueai-backup"
DATE=$(date +%Y%m%d)
MONTH_DAY=$(date +%d)
FILENAME="clueai_prod_${DATE}.sql.gz"
OSS_PATH="${BUCKET}/weekly/${FILENAME}"
OSSUTIL="ossutil64"
LOG_PREFIX="[backup $(date '+%Y-%m-%d %H:%M:%S')]"

# 加载环境变量
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "${SCRIPT_DIR}/../deploy/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/../deploy/.env"
    set +a
fi

DB_URL="${PROD_DATABASE_URL:-${DATABASE_URL:-}}"
if [ -z "$DB_URL" ]; then
    echo "${LOG_PREFIX} ERROR: PROD_DATABASE_URL or DATABASE_URL not set"
    exit 1
fi

# 检查工具
if ! command -v pg_dump &> /dev/null; then
    echo "${LOG_PREFIX} ERROR: pg_dump not found. Install: apt install postgresql-client-15"
    exit 1
fi

if ! command -v ${OSSUTIL} &> /dev/null; then
    # fallback to ossutil without 64 suffix
    OSSUTIL="ossutil"
    if ! command -v ${OSSUTIL} &> /dev/null; then
        echo "${LOG_PREFIX} ERROR: ossutil not found. See script header for install instructions."
        exit 1
    fi
fi

echo "${LOG_PREFIX} Starting backup → ${OSS_PATH}"

# 执行备份
pg_dump "${DB_URL}" --no-owner --no-privileges | gzip | ${OSSUTIL} cp - "${OSS_PATH}"

echo "${LOG_PREFIX} Upload complete: ${OSS_PATH}"

# 保留策略：删除超过 28 天的 weekly 备份（保留每月 1 号的）
echo "${LOG_PREFIX} Applying retention policy..."
CUTOFF_DATE=$(date -d "-28 days" +%Y%m%d 2>/dev/null || date -v-28d +%Y%m%d)

${OSSUTIL} ls "${BUCKET}/weekly/" | grep "clueai_prod_" | awk '{print $NF}' | while read -r obj; do
    obj_date=$(echo "$obj" | grep -oP '\d{8}' || true)
    if [ -z "$obj_date" ]; then
        continue
    fi
    if [ "$obj_date" -lt "$CUTOFF_DATE" ]; then
        obj_day=${obj_date:6:2}
        if [ "$obj_day" = "01" ]; then
            # 每月 1 号的备份移到 monthly/ 目录保留
            monthly_path="${BUCKET}/monthly/$(basename "$obj")"
            ${OSSUTIL} cp "$obj" "${monthly_path}" --force 2>/dev/null || true
        fi
        ${OSSUTIL} rm "$obj" --force 2>/dev/null || true
        echo "${LOG_PREFIX} Removed old backup: $(basename "$obj")"
    fi
done

echo "${LOG_PREFIX} Backup complete. File: ${FILENAME}"
