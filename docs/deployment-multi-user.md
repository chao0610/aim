# Aim Multi-User 部署指南

本指南适用于 `main-server` 分支，该分支在原始 Aim 基础上增加了多用户认证与数据隔离能力。

---

## 前置要求

```bash
# Python 3.8+
pip install -e .
pip install -r requirements.dev.txt
```

---

## 1. 生成 SECRET KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# 输出类似: a3f8c2d1e4b5a6f7...
```

---

## 2. 设置环境变量

```bash
export AIM_SECRET_KEY="你上面生成的密钥"
export AIM_REPO_PATH="/path/to/your/.aim"   # 可选，默认当前目录
```

> **重要**: 不设置 `AIM_SECRET_KEY`，web server 和 tracking server 均会拒绝启动。

---

## 3. 初始化数据库 & 创建第一个管理员

```bash
# 创建管理员账户（首次使用）
aim users create --username admin --password yourpassword --admin
```

---

## 4. 启动 Web Server

```bash
# 基本启动
aim up

# 自定义配置
aim up -h 0.0.0.0 -p 8080 --workers 4

# 带 base_path（如部署在 /aim 子路径下）
aim up -h 0.0.0.0 -p 8080 --base-path /aim
```

访问 `http://your-server:8080`，跳转到 `/sign-in` 页面。

---

## 5. 启动 Remote Tracking Server（可选）

如果你的训练脚本运行在另一台机器上：

```bash
# 在数据中心/GPU 机器上
export AIM_SECRET_KEY="与 web server 相同的密钥"
aim server --port 53800
```

---

## 6. SDK 连接（训练脚本端）

### 使用 API Token（推荐）

先在 Web UI 的 Settings 页面创建 API Token，然后：

```python
import os
import aim

os.environ["AIM_API_TOKEN"] = "aim_tok_xxxxxxxxxxxxxxxx"

run = aim.Run(
    repo="aim://tracking-server:53800",
    experiment="my-experiment"
)
run["hparams"] = {"lr": 0.001, "batch_size": 32}

for step in range(100):
    run.track(loss, name="loss", step=step)
```

### 使用用户名密码（获取 JWT token）

```bash
# 获取 access token
curl -X POST http://your-server:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'

# 响应
# {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

```python
os.environ["AIM_RT_BEARER_TOKEN"] = "eyJ..."  # access_token
```

---

## 7. 多用户管理

### 创建普通用户

```bash
aim users create --username alice --password alicepass
aim users create --username bob   --password bobpass
```

### 用户可见性规则

| Run/Experiment | 可见范围 |
|----------------|---------|
| `user_id = NULL`（历史遗留数据） | 所有人可见可写 |
| `is_public = True` | 所有人可见，仅 owner 可写 |
| `is_public = False`（默认） | 仅 owner 可见可写 |

设置公开可见（通过 API）：

```bash
curl -X PUT http://your-server:8080/api/runs/{run_id}/visibility \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"is_public": true}'
```

---

## 8. 修改密码

在 Web UI 的 **Settings → Change Password** 中填写当前密码和新密码即可。

或通过 API：

```bash
curl -X POST http://your-server:8080/api/settings/change-password \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"current_password": "old", "new_password": "newpass123"}'
```

---

## 9. 验证部署

```bash
# 检查服务状态
curl http://your-server:8080/api/projects/

# 登录验证
curl -X POST http://your-server:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'

# 用 token 访问 runs（应只返回 admin 的 runs）
curl http://your-server:8080/api/runs/search/run/ \
  -H "Authorization: Bearer eyJ..."
```

---

## 10. 生产配置建议（systemd）

```ini
# /etc/systemd/system/aim.service

[Unit]
Description=Aim ML Tracking Server
After=network.target

[Service]
Type=simple
User=aim
WorkingDirectory=/opt/aim
Environment=AIM_SECRET_KEY=your-secret-key
Environment=AIM_REPO_PATH=/data/aim
ExecStart=aim up -h 0.0.0.0 -p 8080 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable aim
systemctl start aim
systemctl status aim
```

---

## 快速排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 启动报 `RuntimeError: AIM_SECRET_KEY` | 未设置环境变量 | `export AIM_SECRET_KEY=...` |
| 登录报 401 | 密码错误或用户不存在 | `aim users create ...` |
| SDK 写入后 run 归属为空 | tracking server 未配 `AIM_SECRET_KEY` | 两端用同一个 key |
| 其他用户的 run 不可见 | 正常，按设计隔离 | 在 Settings 设置 `is_public=true` 共享 |
| `/sign-in` 跳转丢失前缀 | 已修复，`getBasePath()` 自动处理 | 升级到最新代码 |
