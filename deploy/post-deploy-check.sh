#!/bin/bash
# 部署后自动检查所有容器健康状态
set -e

echo "⏳ 等待容器启动（45s）..."
sleep 45

echo "📋 容器状态："
docker compose ps

FAILED=0

for svc in api frontend worker redis nginx; do
  health=$(docker compose ps "$svc" --format '{{.Health}}' 2>/dev/null || echo "")
  status=$(docker compose ps "$svc" --format '{{.State}}' 2>/dev/null || echo "")

  if [[ "$status" != "running" ]]; then
    echo "❌ $svc 未运行 (state=$status)"
    docker compose logs "$svc" --tail 20
    FAILED=1
  elif [[ -n "$health" && "$health" != "healthy" && "$health" != "" ]]; then
    echo "❌ $svc 不健康 (health=$health)"
    docker compose logs "$svc" --tail 20
    FAILED=1
  else
    echo "✅ $svc OK"
  fi
done

echo ""
echo "🔍 端点检查："

if curl -sf http://localhost/health > /dev/null 2>&1; then
  echo "✅ /health 响应正常"
else
  echo "❌ /health 不通"
  FAILED=1
fi

if curl -sf http://localhost/ > /dev/null 2>&1; then
  echo "✅ 前端首页响应正常"
else
  echo "❌ 前端首页不通"
  FAILED=1
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
  echo "🎉 所有容器健康，部署成功"
else
  echo "⚠️  部署存在问题，请检查上方日志"
  exit 1
fi
