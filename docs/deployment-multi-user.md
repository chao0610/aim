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

## 11. 数据库架构说明

Aim 使用**两个独立的 SQLite 数据库**，调试时需要明确区分：

### 11.1 两个数据库

| 数据库文件 | 用途 | 迁移路径 |
|-----------|------|---------|
| `.aim/run_metadata.sqlite` | 结构化 SDK DB：run、experiment、tag、note、**aim_user、api_token** | `aim/storage/migrations/` |
| `.aim/aim_db` | Web App DB：dashboards、explore_states、reports | `aim/web/migrations/` |

> **关键点**：用户账户（`aim_user`）和 API Token（`api_token`）存储在 `run_metadata.sqlite`，而非 `aim_db`。两者通过不同的 alembic 迁移链独立管理。

### 11.2 迁移链

**结构化 SDK DB（`run_metadata.sqlite`）**

```
1ecf8222220d → fbfe5c4702fb → 9ba30ab3b2b4 → 3c4f22db7a46
→ b07e7b07c8ce → 46b89d830ad8 → 661514b12ee1 → e1f2a3b4c5d6
```

最后的 `e1f2a3b4c5d6` 新增了 `aim_user`、`api_token` 表，以及 `run.user_id`、`run.is_public`、`experiment.user_id`、`experiment.is_public` 列。

**Web App DB（`aim_db`）**

```
... → 3d5fd76e8485 → a1b2c3d4e5f6（no-op）
```

`a1b2c3d4e5f6` 是一个空迁移（no-op），仅用于维持版本链完整性。

### 11.3 用 sqlite3 检查数据库状态

```bash
# 查看 run_metadata.sqlite 的表和 alembic 版本
python3 -c "
import sqlite3
conn = sqlite3.connect('/path/to/.aim/run_metadata.sqlite')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('tables:', sorted([t[0] for t in tables]))
version = conn.execute('SELECT version_num FROM alembic_version').fetchone()
print('alembic version:', version)
users = conn.execute('SELECT id, username, is_admin FROM aim_user').fetchall()
print('users:', users)
conn.close()
"

# 查看 run 表的列（确认 user_id/is_public 已存在）
python3 -c "
import sqlite3
conn = sqlite3.connect('/path/to/.aim/run_metadata.sqlite')
cols = conn.execute('PRAGMA table_info(run)').fetchall()
print('run columns:', [c[1] for c in cols])
conn.close()
"
```

---

## 12. 环境重置（清空所有数据重新开始）

### 12.1 完全重置

```bash
# 停止所有 aim 进程
pkill -f "aim up" || true
pkill -f "aim server" || true

# 删除整个 .aim 目录（包含所有 run 数据、数据库、索引）
rm -rf /path/to/.aim

# 重新初始化
cd /path/to/project
aim init

# 重新创建管理员
export AIM_SECRET_KEY="your-secret-key"
aim users create --username admin --password yourpassword --admin
```

### 12.2 仅重置用户数据（保留 run 数据）

```bash
# 删除结构化 DB（会保留 RocksDB run 数据，仅清除用户/实验/标签等元数据）
rm /path/to/.aim/run_metadata.sqlite

# 重新运行迁移并创建管理员
export AIM_SECRET_KEY="your-secret-key"
aim users create --username admin --password yourpassword --admin
# aim users create 会自动触发 run_upgrades()，重建所有表
```

### 12.3 仅删除用户账户（保留所有 run/experiment 数据）

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/path/to/.aim/run_metadata.sqlite')
conn.execute('DELETE FROM api_token')
conn.execute('DELETE FROM aim_user')
conn.commit()
conn.close()
print('All users and tokens deleted.')
"

# 重新创建管理员
export AIM_SECRET_KEY="your-secret-key"
aim users create --username admin --password yourpassword --admin
```

> **注意**：删除用户后，原来归属于这些用户的 run/experiment 的 `user_id` 列仍然保留旧值（外键不级联删除）。这些 run 会因为找不到 owner 而按 legacy 数据处理（所有人可见可写）。如需清理，需手动执行 `UPDATE run SET user_id = NULL`。

### 12.4 强制重跑迁移（迁移版本错乱时）

```bash
# 检查当前版本
python3 -c "
import sqlite3
for db in ['run_metadata.sqlite', 'aim_db']:
    conn = sqlite3.connect(f'/path/to/.aim/{db}')
    v = conn.execute('SELECT version_num FROM alembic_version').fetchone()
    print(f'{db}: {v}')
    conn.close()
"

# 手动将 run_metadata.sqlite 回退到指定版本并重跑
AIM_RUN_META_DATA_DB_URL=sqlite:////path/to/.aim/run_metadata.sqlite \
  python -m alembic -c aim/storage/migrations/alembic.ini upgrade head

# 手动将 aim_db 回退到最新版本
python -m alembic -c aim/web/migrations/alembic.ini upgrade head
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
| `no such table: aim_user` | 迁移未跑或跑到了错误的 DB | 见第 12.4 节强制重跑迁移 |
| `NoSuchTableError: run`（迁移时） | 迁移脚本错误地操作了 aim_db | 确保代码为最新，`a1b2c3d4e5f6` 应为 no-op |
| 用户存在但登录仍 401 | 用户创建在 aim_db 而非 run_metadata.sqlite（旧 bug） | 重置用户数据（12.3 节），重新创建 |
