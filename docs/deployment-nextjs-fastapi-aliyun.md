# ClueAI 阿里云部署说明

> 适用范围：`clueai.com` 主站、`app.clueai.com` 应用站、`api.clueai.com` API
> 部署方式：ECS + Docker Compose + Nginx
> 目标：在保留 Streamlit 回退口的前提下，稳定上线 Next.js + FastAPI + Redis/RQ 三层架构

## 1. 域名分工

- `clueai.com`：营销主站，承接 SEO、定价、功能介绍和转化 CTA
- `app.clueai.com`：登录后的应用站，承接工作台、上传、分析、问评论、行动中心、复盘、文案、设置
- `api.clueai.com`：FastAPI 接口与 webhook 入口

## 2. 服务器准备

1. 购买一台阿里云 ECS
2. 安装 Docker 与 Docker Compose
3. 申请 SSL 证书
4. 绑定 DNS 解析到 ECS 公网 IP
5. 准备以下环境变量：
   - `DATABASE_URL`
   - `AES_SECRET_KEY`
   - `API_SESSION_SECRET`
   - `DEEPSEEK_API_KEY`
   - `FEISHU_WEBHOOK`
   - `PADDLE_CLIENT_TOKEN`
   - `PADDLE_PRICE_ID`
   - `PADDLE_WEBHOOK_SECRET`
   - `PADDLE_ENVIRONMENT`

## 3. 启动方式

在仓库根目录执行：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
```

启动后会得到：

- `frontend`：Next.js 站点
- `api`：FastAPI 服务
- `worker`：RQ 后台任务
- `redis`：任务队列
- `nginx`：统一反向代理

## 4. Nginx 路由逻辑

- `clueai.com` 和 `app.clueai.com` 代理到前端容器
- `api.clueai.com` 代理到 API 容器
- API 与前端通过 `NEXT_PUBLIC_API_BASE_URL=https://api.clueai.com` 通信

## 5. 验证清单

部署后先确认：

1. `https://clueai.com/` 可打开首页
2. `https://app.clueai.com/login` 可打开登录页
3. `https://api.clueai.com/health` 返回健康状态
4. 登录后 `/workspace`、`/products`、`/upload`、`/qa`、`/actions`、`/reviews`、`/copywriter`、`/settings` 可访问
5. 上传任务会进入 Redis/RQ 队列
6. Paddle webhook 回调能成功回写 `users.plan`

## 6. Streamlit 下线前置条件

只在以下条件同时满足时才考虑下线 Streamlit：

- Next.js 覆盖全部主路径
- 登录、上传、分析、结果、问评论、行动、复盘、计费全部跑通
- 关键阻塞问题连续 2 周未出现
- 业务方已接受新应用站作为默认工作入口

## 7. 回退方案

如果部署后出现严重问题：

1. 暂停 `nginx` 对外流量
2. 保留 `streamlit` 旧入口作为临时回退
3. 回滚 `deploy/` 配置
4. 不回滚已经验证通过的产品代码

