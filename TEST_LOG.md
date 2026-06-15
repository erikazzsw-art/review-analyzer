# ClueAI 测试记录

> 版本：v1.0
> 创建日期：2026-05-07

---

## 修复记录

| 日期 | 问题描述 | 解决方案 |
|------|---------|---------|
| 2026-05-07 | Streamlit Cloud 启动报错 `ModuleNotFoundError: No module named 'review_analyzer'` | app.py 顶部加入 `sys.path.insert(0, parent_dir)` 将仓库根目录加入路径 |
| 2026-05-07 | 上传 xlsx 文件报错 `parse_file() missing 1 required positional argument: 'file_type'` | upload.py 改为先写临时文件、提取扩展名，再调用 `parse_file(tmp_path, file_type)` |
| 2026-05-07 | 上传 xlsx 后 `review_id` 被误识别为评论内容，真正的 `review_text` 被塞入 raw_data | parser.py 列名匹配改为优先精确匹配，子串匹配时排除 `_id` 结尾的列 |
| 2026-05-07 | 点击分析评论报错 `analyze_batch() missing required argument: 'api_key'` | upload.py 补充 `api_key=get_api_key(user_id)` 参数传入 |
| 2026-05-07 | 分析完成后导出结果情感/分类/优先级等字段全部为空 | upload.py 传给 `analyze_batch` 的 comments 从字符串列表改为 dict 列表 `[{"content": ..., "rating": ...}]` |
| 2026-05-08 | 重复上传同一文件后仪表盘数据累加（未去重） | 仪表盘改为按 `content_hash` 去重统计，新增 `get_product_stats_deduped` 和 `get_comments_deduped` 查询 |
| 2026-05-08 | 修复代码推送到 develop 但 Streamlit Cloud 连接的是 main 分支，导致修复未生效 | 将 develop 合并到 main 并推送，触发 Streamlit Cloud 重新部署 |
| 2026-05-08 | 上传重复数据时提示"没有可分析的数据"，语义不清 | 区分全部重复/部分重复两种情况，提示改为"上传数据重复" |
| 2026-05-08 | 行动建议用 HTML 标签+符号展示，普通运营看不懂 | 分析结果页和仪表盘的行动建议全部改为自然语言输出 |
| 2026-05-08 | 宣传文案页平台按钮点击后颜色闪回，无法确认选中状态 | 选中平台使用 `type="primary"` 按钮，未选中使用 `type="secondary"` |
| 2026-05-08 | 宣传文案页只输出占位文本，未实际生成广告文案 | 接入 DeepSeek API 实际生成广告文案和理想产品描述 |
| 2026-05-08 | 小标题旁有无用的锚点链接按钮 | 全局 CSS 隐藏 `.stMarkdown h1~h6 a` 和 `stHeaderActionElements` |
| 2026-05-09 | 欢迎页只有"免费试用"和"登录"两个按钮，新用户找不到注册入口 | 欢迎页改为三按钮布局：「立即免费试用」「注册账号」「已有账号，登录」；注册按钮跳转登录页并默认选中注册 Tab |
| 2026-05-09 | 负面率计算不准确（25.9% vs 预期 21.93%），有评分的评论未按评分覆写情感 | 有评分：≤3 负面、≥4 正面（覆写 AI 分析结果）；无评分：使用 AI 情感分析 |
| 2026-05-09 | unrecognizable（无效评论）被计入正面率/负面率分母，导致比例失真 | 统计时排除 unrecognizable，页面显示「无效评论 X 条（不参与统计）」；仪表盘同步修改 |
| 2026-05-09 | 重复检测仅用 content 字段 hash，同内容不同评分/日期的评论被误判为重复 | hash 改为 content+rating+date+reviewer 四字段组合；空内容有评分不算重复；完全空行直接跳过 |
| 2026-05-09 | 历史记录作为独立页面，用户需在侧边栏切换，查看分析结果时无法直接访问历史 | 历史记录整合到分析结果页底部 expander，移除侧边栏「历史记录」导航和独立路由 |
| 2026-05-09 | 分析结果页无时间筛选功能，无法按时间段查看子集数据 | 新增时间筛选栏（全部/7天/14天/30天/90天/自定义），所有选项均弹出日期选择器供精确调整，以数据最新日期为基准推算默认值 |
| 2026-05-09 | 时间环比只有占位文字，无实际对比数据 | 实现自动时间环比：根据数据跨度提供周/双周/月环比选项，自动划分当期 vs 上期，展示正面率/负面率变化和 TOP 问题环比 |
| 2026-05-09 | 历史记录中产品多时查找困难，无搜索功能 | 历史记录区域顶部新增产品搜索框，输入 SKU 关键词即时筛选 |
| 2026-05-11 | Streamlit Cloud 部署环境为 Python 3.9，不支持 `X \| Y` 联合类型语法 | 所有模块顶部添加 `from __future__ import annotations` 兼容 Python 3.9 |
| 2026-05-11 | `requirements.txt` 在子目录下，Streamlit Cloud 无法自动识别依赖 | 将 `requirements.txt` 复制到仓库根目录供 Streamlit Cloud 识别 |
| 2026-05-11 | 评分覆写逻辑遇到浮点格式评分（如 `'3.0'`）时 `int()` 报错 | 评分转换改为 `int(float(rating))` 兼容浮点格式 |
| 2026-05-11 | 情感分布饼图未排除 unrecognizable，导致比例失真 | 饼图排除 unrecognizable，使用 `valid_total` 作为计算基数 |
| 2026-05-11 | 重复检测 hash 仅含 content+rating+date+reviewer，缺少 source 和其他字段 | hash 加入 source + raw_data，所有字段完全一致才判定为重复 |
| 2026-05-11 | 历史记录在 expander 中折叠，产品搜索框不可见，交互体验差 | 历史记录去掉 expander 直接展示，产品搜索框直接可见 |
| 2026-05-11 | 时间筛选只查当前 session 数据，选 90 天时无法覆盖历史 session | 时间筛选支持跨 session 合并，自动拉取同产品同版本的历史数据 |
| 2026-05-11 | 环比功能仅支持固定周期，无法选择时间粒度和版本维度 | 环比功能重做：支持时间粒度（周/双周/月）+ 版本筛选（同版本/跨版本）+ 跨 session 数据合并 |
| 2026-05-25 | 评分2星但评论内容正面时，issue_tag 被强制置空导致差评池中该条评论无标签贡献 | SYSTEM_PROMPT 新增矛盾处理规则：sentiment 按评分，highlight_tag/issue_tag 按内容实际提取 |
| 2026-05-25 | 混合评论（既有亮点又有问题）的 issue_tag 和 highlight_tag 互斥，丢失一半信息 | 输出格式改为 issue_tags/highlight_tags 数组，允许同时填写；新增"混合评价"分类 |
| 2026-05-25 | 同一评论多个同义抱怨被重复计入标签统计（如 "包装破损" 出现两次计2次） | extract_tags_from_comments、_get_top_tags、exporter、notifier 均加入单条评论内去重逻辑 |
| 2026-05-25 | 正负率只有评分版，无法反映评论内容的真实口碑 | 新增 content_sentiment 字段（基于文字内容判断），results.py 新增双版本正负率对比展示（仅在同时有评分和文字内容时出现）|
| 2026-05-25 | 修改 Prompt 后历史数据口径失控，无法追踪哪批数据用的哪个版本 | analyzer.py 新增 PROMPT_VERSION 常量（当前 v2.1）；sessions 表新增 prompt_version 列；结果页标题展示版本号；环比时若两批数据 Prompt 版本不一致自动显示警告 |
| 2026-05-25 | SYSTEM_PROMPT 输出格式分隔符不规范（`/` 而非 `|`），字段说明缺失导致 LLM 理解不稳定 | SYSTEM_PROMPT 升级至 v2.1：规范分隔符为 JSON Schema 标准风格（`|`），新增 4 条字段说明，category 选择规则独立段落 |
| 2026-05-11 | 欢迎页注册按钮指向 prototype.html 而非 Streamlit 应用 | 修正欢迎页注册入口，三按钮布局：「免费注册」「先试用」「已有账号，登录」 |
| 2026-05-13 | 全站 UI 风格不统一，紫色主题与各页面配色不协调 | 全站切换为 Ventriloc 风格：白底灰卡、Inter+Montserrat 字体、#ff682c 橙色点缀、扁平无阴影、统一标题层级（L1 编号徽章 + L2 彩色圆点） |
| 2026-05-13 | Landing 页使用渐变背景和大量 emoji，视觉噪音大 | 移除渐变/阴影/emoji，改为纯色扁平 + 序号标记 + ghost 按钮 |
| 2026-05-13 | 推送设置页规则区域排版凌乱，标题层级不清晰 | 规则行改为单行紧凑布局，标题分级为 L1 编号徽章 + L2 彩色圆点分类（问题红/环比蓝/亮点绿/其他灰） |
| 2026-05-13 | 分析结果页 emoji 图标和紫色配色与新风格不匹配 | 指标卡图标改为几何符号，图表配色统一为绿/红/橙，标题改为编号徽章风格 |
| 2026-05-13 | 数据库迁移：SQLite → Supabase PostgreSQL（详见下方专项记录） | 最终方案：psycopg2-binary + packages.txt(libpq-dev) + 同步 review_analyzer/ 目录下的依赖文件 |
| 2026-05-25 | 邮箱验证码找回密码功能始终失败（详见下方专项记录） | 最终方案：Resend SDK + 验证自有域名 clueai-reviewlens.com，修复 login.py 发送失败静默跳转 bug |
| 2026-05-25 | AI 返回的 issue_tag / highlight_tag 存在同义词变体（如"packaging damage"和"包装损坏"被算作两个不同标签），导致 TOP10 统计被稀释 | config.py 新增 TAG_NORMALIZE_MAP（标准词→变体映射表，覆盖 8 个类目中英文同义词），analyzer.py 新增 _normalize_tag / _normalize_tag_field，在 _validate_result 写库前将所有 tag 变体统一映射到标准词；找不到映射的新词原样保留，不丢失新问题信号 |
| 2026-05-25 | 分析结果页点击"开始分析"报错 `TypeError: 'NoneType' object is not subscriptable`，原因是 `created_at` 字段为 None 时对其做 `[:16]` 切片 | results.py 第228行改为 `(s.get("created_at") or "")[:16]`，防御 None 值 |
| 2026-05-25 | 上传一次但结果页显示同样评论源数据 4 条 | 根因：Streamlit 在分析期间 WebSocket 心跳重新执行脚本，Step 3 的 create_session + add_comments_batch 被重复调用；修复：用 `analyzing_session_id` 在 session_state 中保护，只在首次执行时创建 session 和插入评论，脚本重跑时复用同一 session_id |
| 2026-05-25 | Settings 页面已有环比规则配置 UI（负面率环比、问题占比环比、亮点环比），但 notifier.py 的 check_global_rules() 完全未实现这些逻辑，导致用户配置后永远不触发 | 新增 _get_prev_neg_rate() / _get_prev_top_issues() 辅助函数查询历史批次；check_global_rules() 补全三条环比规则：负面率环比突增、问题占比环比突增、亮点环比变化；should_notify() 签名同步增加 user_id / session_id 参数，透传给规则引擎 |
| 2026-06-03 | V2 RAG/付费代码检查发现 Ask your reviews 未接入结果页、`get_user_plan()` 缺失、users 表缺少付费字段、Paddle webhook 字段不一致 | 新增 rag.py 评论问答模块并接入结果页；补齐 get_user_plan/update_user_plan/get_user_product_count；schema 增加 plan/paddle_customer_id/embedding；修复 webhook custom_data 和 paddle_customer_id 字段 |
| 2026-06-03 | Ask your reviews 仅为文本检索版，未真正生成 embedding 或使用 pgvector 余弦检索 | 新增 embedding 生成、评论向量入库、上传后批量向量化、历史评论按需补齐、`embedding <=> query_embedding` Top-K 检索；文本检索保留为 fallback |
| 2026-06-03 | 上传评论时报错 `psycopg2.errors.UndefinedColumn: column "workflow_purpose" of relation "sessions" does not exist` | `create_session()` 增加数据库兼容降级：若 `sessions` 尚未迁移出 `workflow_purpose/product_ref_id/variant_ref_id`，自动回退到旧字段插入，避免本地上传被 schema 阻塞 |
| 2026-06-04 | 评论分析页上传文件后，用户不容易在首屏找到“开始分析”，完成分析后也缺少“这就是刚生成结果”的承接提示 | 上传页在文件解析成功后前置“开始分析并查看结果”按钮；分析完成后写入跳转标记，结果页显示“本次评论已分析完成，结果页已自动打开”提示 |
| 2026-06-04 | 评论工作流重构后存在旧导航残留、上传完成未稳定进入新结果容器、对比页导出结构与页面矩阵不一致 | 统一一级导航与 `评论分析` 子页路由；上传完成固定跳到 `评论分析 > 分析结果`；结果/对比页补齐翻译缓存隔离；对比页 XLSX 导出兼容矩阵结构；问评论补充产品范围与引用来源展示 |
| 2026-06-04 | 本地登录时报错 `could not translate host name ...pooler.supabase.com`，用户无法判断是 DNS、配置还是网络问题 | `database.py` 新增本地 `DATABASE_URL/SUPABASE_DB_URL` 覆盖逻辑，并按“主机名解析失败 / 网络不通 / 连接串缺失”三类输出明确排查提示；文档补充 `.env` 本地覆盖说明 |
| 2026-06-05 | 打开 `http://localhost:8502/` 未登录时仍显示旧欢迎页，看不到新版本地预览效果 | `app.py` 的未登录默认分支改为直接渲染新版欢迎页 `render_landing_page(variant="refresh")`；旧版仍保留在“预览当前欢迎页”入口中 |
| 2026-06-05 | 切换未登录默认新版欢迎页后报错 `TypeError: render_landing_page() got an unexpected keyword argument 'variant'` | 将欢迎页版本切换改为通过 `st.session_state["landing_preview_variant"]` 控制，`render_landing_page()` 恢复为无参函数，避免 Streamlit 热更新残留旧函数签名时崩溃 |
| 2026-06-05 | 同一浏览器会话里访问过旧版预览后，重新打开 `http://localhost:8502/` 仍会被 `force_public_preview` 状态带回旧版 | 调整 `app.py` 路由顺序：未登录访问时优先清除 `force_public_preview` 并固定渲染新版欢迎页，避免旧预览状态覆盖默认首页 |
| 2026-06-05 | 本地 `8502` 端口确认运行的是 `review_analyzer/app.py`，但欢迎页仍可能因内部默认分支回落到旧版 | 收紧 `landing.py` 的版本决策：默认一律渲染新版，只有显式处于 `force_public_preview` 且选择了 `current` 时才展示旧版欢迎页 |
| 2026-06-05 | 新版欢迎页的大段 HTML 被当作普通文本显示，页面出现 `<div class="refresh-hero">` 等源码内容 | `landing.py` 新增统一 HTML 渲染助手，对多行 HTML 先 `dedent().strip()` 再传给 `st.markdown(..., unsafe_allow_html=True)`，避免缩进触发 Markdown 代码块渲染 |
| 2026-06-08 | ECS 基础环境后续部署文档未明确宿主机 `nginx` 与 compose 内置 `nginx` 的 80 端口冲突，容易导致 `docker compose up` 启动失败 | 在 `docs/deployment-nextjs-fastapi-aliyun.md` 中补充：若采用 `deploy/docker-compose.yml` 的内置 `nginx`，需先停用宿主机 `nginx`，避免 80 端口冲突 |
| 2026-06-08 | ECS 上从 GitHub 拉取的仓库缺少 `webhook/` 目录，导致 `backend_api/Dockerfile` / `workers/Dockerfile` 构建时 `COPY webhook` 失败 | 删除两个 Dockerfile 中对 `webhook/` 的无必要复制，保持 API / Worker 构建不依赖未纳入远端仓库的目录 |
| 2026-06-15 | `/analysis/history`、`/analysis/compare`、`/copywriter` 三个页面未登录访问时返回 500 | history 和 compare 页面补充 try/catch + 401 → EmptyAuthState 降级；copywriter 的 500 根因是 router 未挂载导致后端返回 404，在 `main.py` 中 `include_router(copywriter_router)` 修复 |
| 2026-06-15 | 本地 dev server 开 VPN 后所有页面报 "Cannot read properties of undefined (reading 'call')" | webpack chunk 加载被 VPN 干扰，dev 脚本切换为 `next dev --turbopack`；生产构建不受影响 |
| 2026-06-15 | FeedbackWidget hydration mismatch：服务端渲染 "反馈"、客户端渲染 "Feedback" | `layout.tsx` 的 `<html lang>` 从 `"en"` 改为 `"zh"`，与 `getLocale()` 服务端默认值一致 |
| 2026-06-15 | Turbopack 模式启动报 "Cannot find module 'tailwindcss-animate'" | `npm install tailwindcss-animate` 补装缺失依赖 |

---

## 专项记录：SQLite → Supabase 数据库迁移（2026-05-13）

### 问题背景
每次 git push 部署或 Streamlit Cloud 重启时，本地 SQLite 文件被清空，用户数据全部丢失。需要迁移到云端持久化数据库。

### 方案选择
选择 Supabase（PostgreSQL）：免费 500MB、自动备份、支持多用户并发、有管理面板。

### 迁移过程中遇到的报错

#### 报错 1：`ModuleNotFoundError: No module named 'psycopg2'`
- **现象**：推送代码后 Streamlit Cloud 启动报错
- **原因分析**：`psycopg2-binary` 需要系统级 C 库 `libpq-dev` 才能安装
- **尝试方案 1**：pin 版本号 `psycopg2-binary==2.9.9` 触发重建 → 失败
- **尝试方案 2**：改用 SQLAlchemy + pg8000（纯 Python 驱动）→ 失败（SQLAlchemy 也报 ModuleNotFoundError）
- **尝试方案 3**：添加 `packages.txt`（内容 `libpq-dev`）+ psycopg2-binary → 失败
- **根本原因**：Streamlit Cloud 入口文件为 `review_analyzer/app.py`，它优先读取 `review_analyzer/requirements.txt`，而该文件一直没有 `psycopg2-binary`。根目录的 requirements.txt 被忽略了。
- **最终解决**：同步更新 `review_analyzer/requirements.txt` 添加 `psycopg2-binary>=2.9.9`，并在 `review_analyzer/` 下也放置 `packages.txt`

#### 报错 2：`ModuleNotFoundError: No module named 'sqlalchemy'`
- **现象**：尝试用 SQLAlchemy 替代 psycopg2 时仍然报错
- **原因分析**：同上，`review_analyzer/requirements.txt` 没有 sqlalchemy，虽然 Streamlit 自带 SQLAlchemy 作为依赖，但可能因为 pip 安装整体失败导致环境不完整
- **结论**：放弃 SQLAlchemy 方案，回归 psycopg2-binary + 正确的 requirements 路径

### 关键教训
> Streamlit Cloud 的依赖文件查找规则：以 app 入口文件所在目录为基准，优先读取该目录下的 `requirements.txt` 和 `packages.txt`。如果 app 入口不在仓库根目录，根目录的依赖文件会被忽略。

---

## 专项记录：psycopg2.OperationalError 数据库连接失败（2026-05-14）

### 问题现象
打开 https://clueai-reviewlens.streamlit.app/ 登录时报错：
```
psycopg2.OperationalError
File "database.py", line 13, in get_connection
    conn = psycopg2.connect(db_url)
```

### 排查过程

#### 排查 1：Supabase 项目是否暂停？
- 检查结果：项目正常运行，排除此原因

#### 排查 2：Python 版本兼容性
- 发现错误日志中 Python 版本为 **3.14**（`/home/adminuser/venv/lib/python3.14/`）
- Python 3.14 是 pre-release 版本，psycopg2-binary 可能未完全适配
- 修复：创建 `runtime.txt` 固定 `python-3.11.0`
- 结果：部署成功但仍连接失败

#### 排查 3：连接字符串配置错误（根本原因）
- Streamlit Cloud Secrets 中配置的是**直连地址**（端口 5432）：
  ```
  postgresql://postgres:Zhangxi%405764047@db.xxx.supabase.co:5432/postgres
  ```
- Supabase 直连地址对外部 IP 有限制，Streamlit Cloud 的 IP 不在允许范围内
- 需要改用 **Connection Pooling 地址**（端口 6543）：
  ```
  postgresql://postgres.inpgrbjwtpxgwungghnz:Zhangxi%405764047@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres
  ```

### 最终解决方案

1. **Streamlit Cloud Secrets 改为 Pooler 连接字符串**：
   ```toml
   [database]
   url = "postgresql://postgres.inpgrbjwtpxgwungghnz:Zhangxi%405764047@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
   ```
2. **添加 `runtime.txt`**：固定 Python 3.11，避免 3.14 兼容性问题
3. **`database.py` 改进**：添加 `connect_timeout=10`、`sslmode="require"`、具体错误信息显示

### 关键知识点

| 项目 | 直连（Direct） | 连接池（Pooler） |
|------|---------------|-----------------|
| 端口 | 5432 | 6543 |
| 用户名 | `postgres` | `postgres.[project-ref]` |
| 主机 | `db.[ref].supabase.co` | `aws-[region].pooler.supabase.com` |
| 外部访问 | 受 IP 限制 | 无限制，推荐用于云部署 |
| 密码中有 `@` | 必须编码为 `%40` | 必须编码为 `%40` |

### 关键教训
> 1. Supabase 直连地址（5432）对外部 IP 有网络限制，云平台部署（Streamlit Cloud、Vercel 等）必须使用 Pooler 连接字符串（6543）
> 2. 数据库密码中的特殊字符（`@`、`#`、`%` 等）必须进行 URL 编码
> 3. `runtime.txt` 可以固定 Streamlit Cloud 的 Python 版本，避免自动升级到不稳定版本

---

## 专项记录：邮箱验证码找回密码功能修复（2026-05-25）

### 问题背景
找回密码功能上线后，用户始终无法收到验证码。输入邮箱点击"发送验证码"后页面跳转到验证码输入界面，但验证码从未实际送达，导致重置密码永远失败。

### 排查过程

#### 排查 1：发现 login.py 静默吞错 bug（代码层面）
- **现象**：发送验证码无论成功失败，页面都跳转到验证码输入界面，用户无任何错误提示
- **根本原因**：`login.py` 第 43-47 行完全忽略了 `request_password_reset()` 的 `ok` 返回值，直接无条件设置 `reset_step = "input_code"` 并 `st.rerun()`
- **修复**：改为先判断 `ok`，只有发送成功才跳转；失败时用 `st.error(msg)` 显示具体错误

#### 排查 2：Gmail SMTP 被云平台 IP 封锁（根本原因）
- **现象**：修复静默 bug 后，错误信息暴露为 `source IP address not allowed`
- **原因**：上一版本（commit `8fe55d2`）将发件方式从 Resend 改成了 Gmail SMTP，但 Gmail 对云服务器 IP 段有封锁，Streamlit Cloud 的出站 IP 不被允许
- **排查 Resend 当初为何放弃**：git 历史显示当时用的是 `onboarding@resend.dev`（Resend 测试地址），该地址只能向已在 Resend 后台验证的邮箱发送，所以普通用户收不到
- **结论**：Resend 本身没问题，问题是发件域名未验证

#### 排查 3：Resend 域名验证失败（DNS 配置问题）
- **现象**：Resend 后台域名 `clueai-reviewlens.com` 状态为 Failed
- **错误**：`Invalid DKIM: The record value is incorrect`
- **原因**：阿里云 DNS 中已有 `resend._domainkey` 的 TXT 记录，但填写的值不正确
- **修复**：在阿里云 DNS 控制台更新该 TXT 记录为 Resend 提供的正确值；SPF 和 MX 记录此前已验证通过
- **结果**：DKIM 验证通过，域名状态变为 Active

### 最终解决方案

1. **mailer.py 切回 Resend SDK**，发件人改为 `noreply@clueai-reviewlens.com`
2. **login.py 修复静默 bug**：发送失败时展示 `st.error(msg)`，不跳转
3. **Resend 后台验证域名**：修正阿里云 DNS 中 DKIM TXT 记录值，点击 Restart 重新验证
4. **Streamlit Cloud Secrets** 已有 `[resend]` api_key，无需修改

### 关键知识点

| 发件方案 | 限制 |
|---------|------|
| Gmail SMTP | 云服务器 IP 被封，无法在 Streamlit Cloud 使用 |
| Resend（测试地址 onboarding@resend.dev） | 只能发给已在 Resend 后台验证的邮箱 |
| Resend（验证自有域名） | 无限制，可发任意收件人，推荐方案 |

### 关键教训
> 1. 云平台部署的邮件发送必须使用事务性邮件服务（Resend、SendGrid 等），不能用 Gmail SMTP——云服务器 IP 会被 Google 封锁
> 2. Resend 免费版需验证发件域名（自有域名），才能向任意收件人发送；使用测试地址 `onboarding@resend.dev` 只能发给已验证邮箱
> 3. 邮件发送结果必须检查返回值，发送失败应明确告知用户，不能静默跳转

---

## 数据库基建审查（2026-06-09）

> 在规划 V4-T2 套餐配额（quota.py）实现前，对数据库环境与 schema 进行了一次完整审查，发现 7 项 SaaS 上线前必须修复的问题。整改方案已写入 [PROGRESS_V2.md](PROGRESS_V2.md) Step 2 子任务 2.0-2.7。

### 已踩坑记录

| 编号 | 问题描述 | 风险等级 | 解决方案（Step 2 对应） |
|------|---------|---------|---------|
| DB-1 | 本地开发 / 阿里云生产 / Streamlit Cloud 三处共用同一个 Supabase 项目（`inpgrbjwtpxgwungghnz`），本地代码可直接污染生产数据 | 🔴 高 | 新建 `clueai-dev` 独立开发项目；本地 `.env` 切换到 dev 库（Step 2.1） |
| DB-2 | 数据库密码为弱密码（人名+生日格式 `Zhangxi@5764047`），且明文存于 [.env](.env)、[deploy/.env](deploy/.env)、[.streamlit/secrets.toml](.streamlit/secrets.toml) 三个文件 | 🔴 高 | 立即重置密码为 24 位随机串；检查 git 历史是否泄露过；同步更新三处文件（Step 2.0） |
| DB-3 | 业务表（comments / sessions / products / actions / trackers）共 ~56 条 SQL 查询的 `user_id` 过滤情况未审计，可能存在跨用户数据泄露 | 🔴 高 | 静态扫描 + 修复漏过滤 SQL；Supabase 启用 RLS Policy 双重隔离（Step 2.3） |
| DB-4 | 业务表缺 `updated_at` / `deleted_at` 字段，无法追踪修改时间和支持软删除（GDPR 数据恢复） | 🟡 中 | 业务表统一加时间戳三件套 + 自动更新触发器（Step 2.4） |
| DB-5 | schema SQL 没有版本号编号，`supabase_schema.sql` 单文件累积所有 ALTER 语句，无法回滚 | 🟡 中 | 建立 `migrations/001_xxx.sql` 编号化 schema 管理（Step 2.2） |
| DB-6 | 缺关键字段 CHECK 约束（如 `plan` 枚举值、`rating` 范围、`sentiment` 枚举），数据合法性仅靠应用层校验 | 🟡 中 | 关键字段加 CHECK 约束 + 外键级联策略明确（Step 2.4） |
| DB-7 | 仅依赖 Supabase 默认 7 天快照，无异地周备份（OSS），单点风险高 | 🟡 中 | 写 `scripts/backup_to_oss.sh` 周备份脚本，配置 cron 每周一 09:00 自动跑（Step 2.5） |

### 关键教训

> 1. **环境隔离是 SaaS 红线**：本地 / 测试 / 生产必须使用不同数据库实例。即使没用户也要分——一次本地 `DROP TABLE` 误操作就能搞垮生产。Supabase 免费档每账号可建 2 个项目，零成本即可分离
> 2. **凭证安全要在代码上线第一天就做对**：弱密码 + 明文 `.env` + 不查 git 历史 = 上线即被脱库。任何密钥的存储与轮换流程必须在第一次 commit 之前定好，而不是上线前补救
> 3. **多租户隔离不能只靠应用层**：代码层 `WHERE user_id = %s` 总会有人漏写。必须用 Supabase RLS Policy 在数据库层兜底，做到「即使代码漏了也不会泄露」。RLS 是 SaaS 数据合规的必备，不是 nice-to-have
> 4. **schema 变更必须可回滚**：每个 schema 改动写编号 migration 文件（含 UP/DOWN），单文件累积 ALTER 不是 schema 管理，是 schema 灾难。严禁在 Supabase 后台 SQL Editor 直接改生产 schema
> 5. **CHECK 约束在数据库层而非应用层**：`plan IN ('free','pro_early','pro','team')` 这种规则必须 DB 兜底——多语言 / 多服务接入同一个库时，应用层校验会绕过
> 6. **备份策略不是有就行，要演练能恢复**：每周一次 `pg_dump` 到阿里云 OSS（标准存储 ¥0.12/GB/月几乎免费），关键是定期演练"从备份恢复出可用数据库"——没演练过的备份不算备份
> 7. **Phase 1 初创阶段恰恰是建立基建的最佳窗口期**：用户少、数据量小、改动成本低。等用户多了再补基建是 10 倍工作量 + 业务中断风险

### 整改优先级

> 整改顺序按风险等级和耗时综合排序，详见 [PROGRESS_V2.md](PROGRESS_V2.md) V4-T2 Step 2 完整执行计划：
> - **立即（30 分钟）**：DB-2 凭证安全（Step 2.0）
> - **当天（1 小时 + 1 天）**：DB-1 环境隔离（Step 2.1）+ DB-3 多租户审计（Step 2.3）
> - **本周内（1 天）**：DB-4/5/6 schema 标准化 + DB-7 备份脚本（Step 2.2/2.4/2.5）
> - **回灌生产（30 分钟）**：所有 dev 库验证通过后再操作生产库（Step 2.6）
