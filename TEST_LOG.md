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
