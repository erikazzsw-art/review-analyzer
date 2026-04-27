# 安全规范

## 核心规则
- `.env` 文件必须加入 `.gitignore`，禁止提交到版本库
- 密码存储：`bcrypt.hashpw()` 哈希，禁止明文或 MD5/SHA
- API Key 存储：`cryptography.fernet` AES 加密后存入数据库，读取时解密
- 用户输入一律不信任：文件上传内容、表单输入均需校验后再处理
- SQL 注入防护：全部使用参数化查询
- 禁止在日志、错误信息、推送通知中暴露 API Key 或密码
