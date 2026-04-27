# 错误处理规范

## 规则
- 外部调用（API、文件读取）用 `try-except` 捕获，给用户友好提示
- 内部逻辑不做防御性编程，信任已校验的数据
- 禁止裸 `except:`，必须指定异常类型
- Streamlit 页面错误用 `st.error()` 展示，不抛异常到前端

## 正确示例
```python
try:
    result = client.chat.completions.create(...)
except openai.APITimeoutError:
    st.warning("AI 分析超时，已跳过该条评论")
except openai.APIError as e:
    st.error(f"API 调用失败：{e.message}")
    