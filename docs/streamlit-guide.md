# Streamlit 开发规范

- 页面状态统一用 `st.session_state` 管理，不用全局变量
- 所有用户输入组件必须设置唯一 `key` 参数
- 耗时操作（AI 分析、文件解析）使用 `st.spinner()` 或 `st.progress()`
- 侧边栏导航用 `st.sidebar.radio()`，页面路由用 `if-elif` 分发
- 中英双语：所有用户可见文本通过字典映射，不硬编码
