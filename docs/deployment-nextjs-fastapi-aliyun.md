# ClueAI 阿里云部署说明

> 适用范围：`clueai-reviewlens.com` 主站、`app.clueai-reviewlens.com` 应用站、`api.clueai-reviewlens.com` API
> 部署方式：ECS + Docker Compose + Nginx
> 架构：Next.js 15 + FastAPI + RQ Worker + Redis + Supabase PostgreSQL

## 1. 域名分工

- `clueai-reviewlens.com`：营销主站，承接 SEO、定价、功能介绍和转化 CTA
- `app.clueai-reviewlens.com`：登录后的应用站，承接工作台、上传、分析、问评论、行动中心、复盘、文案、设置
- `api.clueai-reviewlens.com`：FastAPI 接口与 webhook 入口

## 2. 服务器准备

1. 购买一台阿里云 ECS
2. 安装 Docker 与 Docker Compose
3. 绑定 DNS 解析到 ECS 公网 IP
4. 准备以下环境变量：
   - `DATABASE_URL`
   - `AES_SECRET_KEY`
   - `API_SESSION_SECRET`
   - `DEEPSEEK_API_KEY`
   - `LETSENCRYPT_EMAIL`

其余变量按功能启用情况再补：

- `FEISHU_WEBHOOK`
- `PADDLE_CLIENT_TOKEN`
- `PADDLE_PRICE_ID`
- `PADDLE_WEBHOOK_SECRET`
- `PADDLE_ENVIRONMENT`

### 2.1 环境变量优先级

首发上线时，至少要准备这些值：

- `DATABASE_URL`：Supabase PostgreSQL 连接串，API、Worker、Webhook 都要用
- `AES_SECRET_KEY`：API Key 加密密钥，建议新生成，不要复用旧环境里不确定来源的值
- `API_SESSION_SECRET`：API 会话签名密钥，可与 `AES_SECRET_KEY` 不同
- `DEEPSEEK_API_KEY`：评论分析和文案生成必需
- `LETSENCRYPT_EMAIL`：Let's Encrypt 注册邮箱，证书首次签发和续期提醒都要用

可以先留空或后补的项：

- `FEISHU_WEBHOOK`：飞书推送通知
- `PADDLE_CLIENT_TOKEN`：Paddle 前端收银台
- `PADDLE_PRICE_ID`：Paddle 价格 ID
- `PADDLE_WEBHOOK_SECRET`：Paddle 回调签名校验
- `PADDLE_ENVIRONMENT`：默认 `production`，如果测试环境可改 `sandbox`
- `OPENAI_API_KEY` / `EMBEDDING_API_KEY`：评论问答 RAG 的 embedding key，只有启用向量检索时才需要
- `EMBEDDING_API_BASE_URL` / `EMBEDDING_MODEL`：embedding 服务地址和模型名，默认可直接使用 OpenAI 兼容接口
- `SHULEX_API_KEY`：仅用于抓取/测试 Shulex 数据脚本，不影响主站启动

## 3. 启动方式

在仓库根目录执行：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

注意：`deploy/docker-compose.yml` 里已经包含 `nginx` 容器，并同时占用宿主机 `80` 和 `443` 端口。
如果你前面已经在 ECS 上安装并启动了系统级 `nginx`，请先停用它，避免端口冲突：

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

compose 会自动读取 `deploy/.env`，所以部署时请把环境变量文件放在 `deploy/.env`，然后再执行上面的启动命令。

如果是第一次上线 HTTPS，需要先让 Nginx 用 80 端口接住 ACME 校验，再签发证书：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml --profile certbot run --rm certbot
docker compose -f deploy/docker-compose.yml exec nginx nginx -s reload
```

说明：

- `up -d --build` 只负责起容器
- `certbot` 只负责签发和更新证书，证书会落在 `/etc/letsencrypt`
- Nginx 通过 `/var/www/certbot` 提供 `/.well-known/acme-challenge/`

启动后会得到：

- `frontend`：Next.js 站点
- `api`：FastAPI 服务
- `worker`：RQ 后台任务
- `redis`：任务队列
- `nginx`：统一反向代理

## 4. Nginx 路由逻辑

- `http://clueai-reviewlens.com`、`http://app.clueai-reviewlens.com`、`http://api.clueai-reviewlens.com` 统一跳转到 HTTPS
- `https://clueai-reviewlens.com`、`https://www.clueai-reviewlens.com`、`https://app.clueai-reviewlens.com` 代理到前端容器
- `https://api.clueai-reviewlens.com` 代理到 API 容器
- API 容器内部默认监听 `8000`，前端容器默认监听 `3000`
- API 与前端通过 `NEXT_PUBLIC_API_BASE_URL=https://api.clueai-reviewlens.com` 通信
- 证书默认挂载到 `/etc/letsencrypt`，ACME 校验目录挂载到 `/var/www/certbot`

## 5. 验证清单

部署后先确认：

1. `http://clueai-reviewlens.com/` 会跳转到 `https://clueai-reviewlens.com/`
2. `https://clueai-reviewlens.com/` 可打开首页
3. `https://app.clueai-reviewlens.com/login` 可打开登录页
4. `https://api.clueai-reviewlens.com/health` 返回健康状态
5. 浏览器证书链显示为 Let's Encrypt 签发，且没有混合内容报错
6. 登录后 `/workspace`、`/products`、`/upload`、`/qa`、`/actions`、`/reviews`、`/copywriter`、`/settings` 可访问
7. 上传任务会进入 Redis/RQ 队列
8. Paddle webhook 回调能成功回写 `users.plan`

## 6. 日常部署（代码推送后）

职责分离：Claude Code 负责写代码 + push 到 develop；**部署由 Erika 在 ECS 上手动执行**。

### 标准流程

```bash
cd /opt/clueai/deploy
git pull origin develop
docker compose up -d --build <服务名>
docker compose exec nginx nginx -s reload
```

### 服务名对照表

| 改动范围 | `--build` 参数 |
|---------|---------------|
| 仅前端 (`frontend/`) | `frontend` |
| 仅后端 API (`backend_api/`) | `api` |
| 仅 Worker (`workers/`、`review_analyzer/`) | `worker` |
| 前端 + 后端 | `frontend api` |
| 全部 | `frontend api worker` |

### 注意事项

- `nginx -s reload` **每次都要执行**——rebuild 容器后 IP 变化，不 reload 会 502（6/23 事故教训）
- 改了 `deploy/.env` 后必须 `docker compose up -d --force-recreate <服务名>`（`restart` 不重读 .env）
- 改了 `deploy/nginx.conf` 后需 `docker compose up -d --build nginx`
- 部署后验证：`curl https://api.clueai-reviewlens.com/health` 返回 200 即可

## 7. 回退方案

如果部署后出现严重问题：

1. `docker compose logs <服务名> --tail=50` 查看错误
2. `git log --oneline -5` 确认问题 commit
3. `git revert <commit>` 或 `git checkout <上一个好的commit> -- <文件>`
4. 重新 `docker compose up -d --build <服务名>`
5. 不回滚已经验证通过的产品代码
