# DeepSeek API 调用规范

## 客户端配置
```python
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1",
    timeout=30.0
)
