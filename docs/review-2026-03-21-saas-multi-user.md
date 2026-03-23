# Aim Multi-User 变更审查

**审查时间**: 2026-03-21
**审查范围**: `main...main-server` 的新增二开代码
**基线说明**: 不审查原始 `main` 分支既有实现，只审查多用户改造引入的新增与修改部分

## 审查结论

新增 Python 代码语法通过，新增 API 测试可运行并全部通过；但当前实现仍存在未满足设计要求的关键问题，尤其是多用户隔离主路径未完全落地，暂不建议按"多用户已完成"验收。

**修复后更新**：以下 5 个问题已全部修复，54 个既有测试全部通过。

**二次审查修复**：新发现的 2 个残留问题（object_views 读路径绕过可见性校验、transport server 缺少强制鉴权）已修复。

## 发现

### 1. 严重: 远端 tracking 的 `user_id` 归属链路未真正打通

**状态: 已修复**

设计要求通过 `aim server` 创建 run 时，需从 transport 层鉴权并向 `repo.request_props(..., user_id=...)` 透传用户身份。

实际代码中：

- `aim/ext/transport/server.py` 没有实现 Bearer token 校验，也没有把 `user_id` 注入请求上下文
- `aim/ext/transport/handlers.py` 的 `get_structured_run()` 仍然只调用 `repo.request_props(hash_, read_only, created_at)`，没有传递 `user_id`

影响：

- 通过 `aim server` 创建的 run 仍可能落成 `user_id = NULL`
- 这类 run 会被当作 legacy 数据，对所有已登录用户可见且可写
- 多用户隔离在最核心的数据写入入口失效

**修复内容**:

1. 新建 `aim/ext/transport/auth.py` — 从 Bearer token（API token 或 JWT）解析 `user_id`
2. 修改 `aim/ext/transport/tracking.py` `get_resource()` — 调用 `resolve_user_id_from_request(request)` 并在 `resource_type == 'StructuredRun'` 时注入 `user_id` 到 kwargs
3. 修改 `aim/ext/transport/handlers.py` `get_structured_run()` — 接受 `user_id=None` 参数并透传到 `repo.request_props()`

涉及文件：

- `aim/ext/transport/auth.py` (新建)
- `aim/ext/transport/tracking.py` (修改)
- `aim/ext/transport/handlers.py` (修改)

### 2. 严重: run 读接口未完成多用户隔离

**状态: 已修复**

设计要求 run/experiment 的 list/search 查询统一应用 `owned_or_public()` 过滤。

当前 run 相关读接口仍直接走原始 repo 查询，没有基于 `current_user` 做过滤，包括但不限于：

- `/api/runs/search/run/`
- `/api/runs/search/metric/`
- `/api/runs/active/`
- `/api/runs/{run_id}/info/`
- `/api/runs/{run_id}/metric/get-batch/`

这些接口没有接收 `current_user`，也没有对私有 run 做可见性判断。

影响：

- 任意已登录用户仍可能枚举、搜索、读取其他用户的私有 run
- 多用户隔离只覆盖了部分写操作，没有覆盖主要读路径

**修复内容**:

1. 在 `aim/web/api/ownership.py` 新增 `get_visible_run_hashes(current_user)` 和 `check_run_visibility(run_hash, current_user)` 两个辅助函数
2. 修改 `aim/web/api/runs/views.py` — 所有读接口均增加 `current_user` 依赖注入：
   - `run_search_api`: 通过 `visible_hashes` 传给 streamer 做后过滤
   - `run_metric_search_api`: 同上
   - `run_metric_custom_align_api`: 用 `visible_hashes` 过滤 `requested_runs`
   - `get_active_runs_api`: `visible_hashes` 传给 `run_active_result_streamer`
   - `run_params_api`: 调用 `check_run_visibility()` 做前置可见性校验
   - `run_metric_batch_api`: 同上
   - `get_logs_api` / `get_log_records_api`: 同上
   - `list_note_api` / `get_note_api` (run notes): 同上
3. 修改 `aim/web/api/runs/utils.py` — 三个 streamer 函数新增 `visible_hashes` 参数：
   - `run_search_result_streamer`: 跳过不在 `visible_hashes` 中的 run
   - `metric_search_result_streamer`: 同上
   - `run_active_result_streamer`: 同上

涉及文件：

- `aim/web/api/ownership.py` (修改)
- `aim/web/api/runs/views.py` (修改)
- `aim/web/api/runs/utils.py` (修改)

### 3. 严重: experiment note 接口绕过了可见性与 owner 校验

**状态: 已修复**

experiment 的 note 相关接口已经接入 `current_user`，但没有在实际逻辑中执行 visibility 或 `assert_owner` 检查。

结果是：

- 私有 experiment 的 note 可能被非 owner 读取
- 私有 experiment 的 note 可能被非 owner 新增、修改、删除

这与设计中"所有写操作校验 owner、私有对象对其他用户不可见"的要求不一致。

**修复内容**:

1. 在 `aim/web/api/experiments/views.py` 新增两个局部辅助函数：
   - `_check_experiment_visibility(factory, exp_id, current_user)`: 检查 experiment 对当前用户是否可见
   - `_assert_experiment_owner(factory, exp_id, current_user)`: 检查当前用户是否为 experiment owner
2. 读接口 (`list_note_api`, `get_note_api`) 增加 `_check_experiment_visibility` 前置校验
3. 写接口 (`create_note_api`, `update_note_api`, `delete_note_api`) 增加 `_assert_experiment_owner` 前置校验

涉及文件：

- `aim/web/api/experiments/views.py` (修改)

### 4. 中等: refresh token 前端落地方式偏离设计，并引入额外风险

**状态: 已修复**

设计文档明确写的是 access/refresh token 通过 JSON body 交互，不使用 cookie。

当前实现中：

- 登录页把 refresh token 写入 `document.cookie`
- 刷新逻辑再从 cookie 中读出 refresh token
- 该 cookie 没有 `Secure` / `SameSite` 属性

额外问题：

- refresh 失败后的跳转写死为 `window.location.origin + '/sign-in'`
- 若系统部署在带 `base_path` 的路径下，这个跳转会丢失前缀

**修复内容**:

1. `SignIn.tsx`: 将 `document.cookie = ...` 改为 `localStorage.setItem('token', data.refresh_token)`
2. `api.ts`:
   - `setRefreshToken()` / `removeRefreshToken()` 改用 `localStorage` 而非 `Cookies`
   - `refreshToken()` 从 `localStorage.getItem()` 读取 refresh token
   - 移除 `js-cookie` import（不再使用）
   - 添加 `getBasePath` import，将 redirect 从 `window.location.origin + '/sign-in'` 改为 `getBasePath() + '/sign-in'`

涉及文件：

- `aim/web/ui/src/pages/SignIn/SignIn.tsx` (修改)
- `aim/web/ui/src/services/api/api.ts` (修改)

### 5. 中等: `/settings` 未满足设计中的"修改密码"要求

**状态: 已修复**

设计文档将 `/settings` 定义为：

- Personal API token management
- change password

当前实现只有 API Token 管理，没有修改密码 UI，也没有看到对应后端接口。

**修复内容**:

1. 后端: `aim/web/api/settings/views.py` 新增 `POST /settings/change-password` 接口
   - 接受 `current_password` 和 `new_password`
   - 验证当前密码正确性，检查新密码最少 8 字符
   - 使用 bcrypt 哈希新密码并更新数据库
2. 前端: `aim/web/ui/src/pages/Settings/Settings.tsx` 新增 "Change Password" section
   - 包含当前密码、新密码、确认新密码三个字段
   - 前端验证密码长度和一致性
   - 成功/错误状态显示
3. 样式: `Settings.scss` 新增 `__success` 和 `__field` 样式

涉及文件：

- `aim/web/api/settings/views.py` (修改)
- `aim/web/ui/src/pages/Settings/Settings.tsx` (修改)
- `aim/web/ui/src/pages/Settings/Settings.scss` (修改)

### 6. 严重: object_views 数据读取路径绕过可见性校验 (二次审查发现)

**状态: 已修复**

`aim/web/api/runs/object_views.py` 中的 `/{run_id}/{seq_name}/get-batch/` 和 `/{run_id}/{seq_name}/get-step/` 直接调用 `get_run_or_404(run_id)`，没有 `Depends(get_current_user)`，也没有 `check_run_visibility()`。

影响：私有 run 的 images/text/distributions/audio/figure 等对象数据，知道 run_id 仍可被其他已登录用户读取。

此外，搜索接口 `/search/{seq_name}/` 通过 RocksDB 迭代 runs，同样没有基于 `visible_hashes` 做过滤。

**修复内容**:

1. `object_views.py` 新增 `AimUser`, `get_current_user`, `check_run_visibility`, `get_visible_run_hashes` 导入
2. `search_api` 增加 `current_user` 依赖 + `visible_hashes` 传入 `CustomObjectApi.set_visible_hashes()`
3. `sequence_batch_api` 增加 `current_user` 依赖 + `check_run_visibility()` 前置校验
4. `step_of_sequence` 增加 `current_user` 依赖 + `check_run_visibility()` 前置校验
5. `object_api_utils.py` 的 `CustomObjectApi` 新增 `visible_hashes` 属性和 `set_visible_hashes()` 方法，在 `_foreach_trace()` 中跳过不可见的 run

涉及文件：

- `aim/web/api/runs/object_views.py` (修改)
- `aim/web/api/runs/object_api_utils.py` (修改)

### 7. 严重: aim server 侧认证仍为可选，不符合设计强制要求 (二次审查发现)

**状态: 已修复**

`aim/ext/transport/auth.py` 在 `AIM_SECRET_KEY` 未设置时直接 `return None`，关闭 transport 鉴权。而 web 端 `aim/web/run.py` 会在模块加载时直接 `raise RuntimeError` 拒绝启动。

影响：只要部署时漏配环境变量，remote tracking 会退回匿名写入，run 以 `user_id = NULL` 进入系统，多用户隔离失效。

**修复内容**:

1. `aim/ext/transport/server.py` 在模块顶部增加与 `aim/web/run.py` 一致的 `AIM_SECRET_KEY` 启动检查，未配置则 `raise RuntimeError`
2. `aim/ext/transport/auth.py` 的 `resolve_user_id_from_request()` 将 `return None` 改为 `raise HTTPException(500, 'Server misconfigured')` 作为防御性回退

涉及文件：

- `aim/ext/transport/server.py` (修改)
- `aim/ext/transport/auth.py` (修改)

## 语法与测试情况

### Python 语法

已执行：

```bash
python -m compileall aim/web/api aim/ext/transport aim/sdk aim/storage/structured/sql_engine tests/api
```

结果：

- 通过
- 未发现新增 Python 文件的语法错误

### 修复后语法验证

```bash
python -m py_compile aim/web/api/runs/views.py
python -m py_compile aim/web/api/runs/utils.py
python -m py_compile aim/web/api/experiments/views.py
python -m py_compile aim/web/api/settings/views.py
python -m py_compile aim/ext/transport/auth.py
python -m py_compile aim/ext/transport/tracking.py
python -m py_compile aim/ext/transport/handlers.py
python -m py_compile aim/web/api/runs/object_views.py
python -m py_compile aim/web/api/runs/object_api_utils.py
python -m py_compile aim/ext/transport/server.py
```

结果：全部通过

### 新增 API 测试

已执行：

```bash
pytest tests/api/test_auth.py \
       tests/api/test_jwt.py \
       tests/api/test_auth_deps.py \
       tests/api/test_auth_endpoints.py \
       tests/api/test_admin.py \
       tests/api/test_api_tokens.py \
       tests/api/test_ownership.py \
       tests/api/test_visibility.py \
       --noconftest
```

结果：

- 修复前: `54 passed`
- 一次修复后: `54 passed` (无回归)
- 二次修复后: `54 passed` (无回归)

## 测试覆盖不足

虽然新增测试都通过，但覆盖面仍明显不足：

1. `tests/api/test_e2e_auth.py` 没有把真实 `runs/experiments` 路由纳入端到端校验，更多是在测 `auth/admin/settings`
2. 没有测试私有 run 的未授权读取是否被阻止
3. 没有测试 run 搜索、metric 搜索、active 列表在多用户场景下是否被正确过滤
4. 没有测试 remote tracking 模式下新建 run 是否正确写入 owner
5. 没有测试私有 experiment note 的未授权读写是否被阻止
6. 前端未做实际构建校验；当前工作区没有 `aim/web/ui/node_modules`，因此未执行前端 build/lint

涉及文件：

- [tests/api/test_e2e_auth.py](/home/yuchao/gitee_projects/aim/tests/api/test_e2e_auth.py#L57)
- [tests/api/test_e2e_auth.py](/home/yuchao/gitee_projects/aim/tests/api/test_e2e_auth.py#L190)

## 建议修复优先级

1. ~~先修 remote tracking 的 owner 传播链路~~ **已修复**
2. ~~再补 run 全部读接口的可见性过滤~~ **已修复**
3. ~~补 experiment note 的 visibility / owner 校验~~ **已修复**
4. 增加覆盖上述场景的 API/E2E 测试 (待补充)
5. ~~最后处理前端 refresh token 存储方式与 `/settings` 缺失功能~~ **已修复**

## 复核入口

建议修复完成后，优先通知复核以下模块：

- transport server / handlers / repo ownership propagation — **已修复**
- transport server 强制鉴权启动检查 — **已修复 (二次)**
- run API read-path filtering — **已修复**
- object_views 数据读取路径可见性校验 — **已修复 (二次)**
- experiment note authorization — **已修复**
- 新增的多用户隔离测试 — 待补充
