# ReviewLens — Figma 搭建指南

基于 prototype.html 原型，按以下步骤在 Figma 中还原完整设计。

---

## 一、项目初始化

### 1. 创建文件
- 新建 Figma 文件，命名 `ReviewLens - 评论分析系统`
- 创建 5 个 Page：`Login`、`Dashboard`、`Upload`、`Results`、`History`

### 2. 设置画框尺寸
- 桌面端：1440 × 900（主设计稿）
- 平板端：1024 × 768（可选适配）

### 3. 建立颜色样式（Color Styles）
在右侧面板 → Local Styles → 添加以下颜色：

| 名称 | 色值 | 用途 |
|------|------|------|
| Primary | `#6C5CE7` | 主色、按钮、导航高亮 |
| Primary Light | `#A29BFE` | 头像背景、渐变辅助 |
| Green | `#00B894` | 正面标签、上升指标 |
| Red | `#FF6B6B` | 负面标签、下降指标 |
| Yellow | `#FDCB6E` | 中性标签、星级 |
| Blue | `#74B9FF` | 辅助图表色 |
| Background | `#F7F8FC` | 页面背景 |
| Card | `#FFFFFF` | 卡片背景 |
| Text | `#2D3436` | 主文字 |
| Text Light | `#636E72` | 辅助文字 |
| Border | `#E8EAF0` | 分割线、边框 |
| Hover BG | `#F0EEFF` | 悬停背景 |

### 4. 建立文字样式（Text Styles）

| 名称 | 字体 | 大小 | 粗细 |
|------|------|------|------|
| H1 / Page Title | PingFang SC | 22px | Bold (700) |
| H2 / Card Title | PingFang SC | 16px | Semibold (600) |
| H3 / Chart Title | PingFang SC | 15px | Semibold (600) |
| Body | PingFang SC | 14px | Regular (400) |
| Small | PingFang SC | 13px | Regular (400) |
| Caption | PingFang SC | 12px | Regular (400) |
| Metric Value | PingFang SC | 28px | Bold (700) |
| Login Title | PingFang SC | 24px | Bold (700) |

---

## 二、创建组件（Components）

### 1. 侧边栏导航项 (Nav Item)
- 尺寸：224 × 44px
- 圆角：10px
- 内边距：12px 20px
- 图标（20px）+ 间距 12px + 文字（15px）
- 创建 2 个 Variant：`Default`（文字 #636E72）、`Active`（背景 #F0EEFF，文字 #6C5CE7，字重 600）

### 2. 指标卡片 (Metric Card)
- 尺寸：自适应宽度 × 120px
- 圆角：12px
- 白底 + 阴影 `0 2px 12px rgba(108,92,231,0.08)`
- 左侧 4px 色条（用矩形，圆角左上左下 4px）
- 内部结构（纵向排列）：图标 28px → 数值 28px Bold → 标签 13px → 变化标签

### 3. 标签 (Tag)
- 圆角：20px
- 内边距：4px 12px
- 创建 4 个 Variant：
  - `Positive`：背景 #E8F8F5，文字 #00B894
  - `Negative`：背景 #FFEAEA，文字 #FF6B6B
  - `Neutral`：背景 #FFF3E0，文字 #E17055
  - `Topic`：背景 #F0EEFF，文字 #6C5CE7

### 4. 按钮 (Button)
- 圆角：10px
- 内边距：10px 24px
- Variant `Primary`：背景 #6C5CE7，文字白色
- Variant `Outline`：边框 2px #6C5CE7，文字 #6C5CE7
- Variant `Small`：内边距 6px 14px，字号 13px

### 5. 输入框 (Input)
- 高度：44px
- 圆角：10px
- 边框：2px #E8EAF0
- 内边距：12px 16px
- Variant `Focus`：边框色改为 #6C5CE7

### 6. 表格行 (Table Row)
- 高度：48px
- 底部 1px 分割线 #E8EAF0
- Variant `Hover`：背景 #FAFBFF

### 7. 主题卡片 (Topic Card)
- 圆角：12px
- 白底 + 阴影
- 左侧 4px 色条
- 内部：主题名 16px Bold → 情感比例条（6px 高，三色拼接）→ 标签行 → 引用评论

### 8. 历史记录卡片 (History Card)
- 圆角：12px
- 白底 + 阴影
- 内部：元信息行（13px 灰色）→ 文件名（16px Bold）→ 统计行

### 9. Tab 切换组
- 容器：白底圆角 10px + 阴影，内边距 4px
- 单个 Tab：圆角 8px，内边距 8px 20px
- Variant `Active`：背景 #6C5CE7，文字白色
- Variant `Default`：无背景，文字 #636E72

---

## 三、逐页搭建

### Page 1：登录页

1. 画框 1440 × 900
2. 背景：线性渐变 135°，`#A29BFE` → `#6C5CE7` → `#74B9FF`
3. 居中放置登录卡片：
   - 400 × auto，圆角 20px，白底
   - 阴影：`0 20px 60px rgba(0,0,0,0.15)`
   - 内边距：48px 40px
4. 卡片内容（居中对齐，纵向排列）：
   - 🔍 图标（48px）
   - "ReviewLens"（24px Bold，#6C5CE7）
   - 副标题（14px，#636E72）
   - 用户名输入框
   - 密码输入框
   - 登录按钮（Primary，全宽）

### Page 2：仪表盘

1. 左侧固定侧边栏 240px 宽，白底
   - Logo 区域 + 4 个导航项 + 底部语言切换 & 用户信息
2. 右侧主内容区（左边距 240px，内边距 28px 32px）：
   - 页面标题行
   - 4 列指标卡片（等宽 grid，间距 16px）
   - 图表行：左 1.2fr 折线图 + 右 0.8fr 柱状图（间距 16px）
   - 最近记录表格卡片

### Page 3：上传分析

1. 侧边栏同上（"上传分析"项高亮）
2. 主内容：
   - 页面标题
   - 上传区域：虚线边框 2px dashed #A29BFE，圆角 12px，内边距 60px 40px
   - 进度条：6px 高，圆角 3px，渐变填充
   - 文件预览表格卡片
   - 操作行：类目下拉框 + 开始分析按钮

### Page 4：分析结果

1. 侧边栏同上（"分析结果"项高亮）
2. 主内容：
   - 标题行 + 右侧导出/推送按钮
   - Tab 切换组
   - 概览 Tab：左侧环形图 + 右侧关键词云 → 下方 3 列情感指标卡
   - 主题 Tab：2 列 grid 主题卡片
   - 原文 Tab：搜索栏 + 筛选下拉 + 评论表格

### Page 5：历史记录

1. 侧边栏同上（"历史记录"项高亮）
2. 主内容：
   - 页面标题
   - 搜索栏 + 时间筛选下拉
   - 历史卡片 grid（auto-fill，最小 320px）

---

## 四、原型交互（Prototype 模式）

1. 登录按钮 → Navigate to `Dashboard`
2. 侧边栏导航项 → Navigate to 对应页面
3. 上传区域点击 → 显示进度条 → 显示预览（用 Smart Animate）
4. 开始分析按钮 → Navigate to `Results`
5. Tab 切换 → 用 Variant 交互或 Navigate to 不同 Frame
6. 历史卡片点击 → Navigate to `Results`
7. 退出按钮 → Navigate to `Login`
8. 语言切换 → 用 Component Variant 切换中/英文版本

---

## 五、导出与交付

1. 选中所有页面 → 右侧 Export → 导出 2x PNG 用于评审
2. 使用 Figma 的 Share 功能生成预览链接
3. 开发交付时使用 Dev Mode 查看间距、颜色、字体参数
