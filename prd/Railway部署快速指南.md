# Railway 部署快速指南

## 🚀 快速部署步骤

### 1. 连接GitHub仓库到Railway

1. 登录 [Railway](https://railway.app)
2. 点击 "New Project"
3. 选择 "Deploy from GitHub repo"
4. 选择你的仓库

### 2. 配置环境变量

在Railway项目设置中添加以下**必需**的环境变量：

```bash
# 必需：启用定时任务（包括AI简报生成）
ENABLE_JOB=True

# 必需：GLM API密钥
GLM_API_KEY=your-glm-api-key-here

# 必需：数据库连接（如果使用Railway的PostgreSQL会自动设置）
# 如果使用外部数据库，需要手动设置：
# DB=postgresql://user:password@host:port/database
```

### 3. AI简报功能配置（可选）

如果需要启用AI简报功能，添加以下环境变量：

```bash
# 启用AI简报功能
AI_BRIEF_ENABLED=True

# 启用自动生成
AI_BRIEF_AUTO_GENERATE=True

# 执行间隔（分钟）
AI_BRIEF_GENERATE_INTERVAL=60

# 每批处理数量
AI_BRIEF_BATCH_SIZE=10
```

### 4. 数据库设置

#### 使用Railway的PostgreSQL（推荐）

1. 在Railway项目中点击 "New" → "Database" → "Add PostgreSQL"
2. Railway会自动设置 `DATABASE_URL` 环境变量
3. 项目会自动使用这个数据库

#### 使用外部数据库

在环境变量中设置：

```bash
DB=postgresql://user:password@host:port/database
```

### 5. 执行数据库迁移

#### 方式1：通过Railway CLI（推荐）

```bash
# 安装Railway CLI
npm i -g @railway/cli

# 登录
railway login

# 连接到项目
railway link

# 执行SQL迁移
railway run psql < schemas/brief_migration.sql
```

#### 方式2：通过Supabase Dashboard（如果使用Supabase）

1. 进入Supabase Dashboard
2. 打开 SQL Editor
3. 执行 `schemas/brief_migration.sql` 中的PostgreSQL版本SQL

#### 方式3：首次部署时自动创建（如果使用SQLAlchemy）

如果使用SQLAlchemy自动创建表，可以设置：

```bash
INIT_DB=True
```

**注意**：首次部署后记得移除 `INIT_DB` 环境变量，避免重复初始化。

### 6. 部署和验证

1. Railway会自动检测到代码变更并开始部署
2. 部署完成后，查看日志确认：
   - ✅ "定时任务已启用"
   - ✅ "已添加AI简报生成定时任务"
   - ✅ 服务正常启动

### 7. 测试功能

#### 检查服务状态

访问你的Railway域名，应该能看到服务正常运行。

#### 测试API

```bash
# 获取文章列表
curl https://your-domain.railway.app/api/articles

# 获取文章简报（需要先登录获取token）
curl -H "Authorization: Bearer {token}" \
  https://your-domain.railway.app/api/articles/{article_id}/brief
```

## 📋 环境变量完整列表

### 必需变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ENABLE_JOB` | 启用定时任务 | `True` |
| `GLM_API_KEY` | GLM API密钥 | `your-key-here` |
| `DB` | 数据库连接（Railway PostgreSQL会自动设置） | `postgresql://...` |

### AI简报功能变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `AI_BRIEF_ENABLED` | 启用AI简报功能 | `False` |
| `AI_BRIEF_AUTO_GENERATE` | 启用自动生成 | `False` |
| `AI_BRIEF_GENERATE_INTERVAL` | 执行间隔（分钟） | `60` |
| `AI_BRIEF_BATCH_SIZE` | 每批处理数量 | `10` |
| `GLM_API_URL` | GLM API地址 | `https://open.bigmodel.cn/api/paas/v4/chat/completions` |
| `GLM_MODEL` | 使用的模型 | `GLM-4.5-Flash` |
| `AI_TIMEOUT` | API超时时间（秒） | `60` |
| `AI_MAX_RETRIES` | 最大重试次数 | `3` |

### 其他常用变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PORT` | 服务端口 | `8001`（Railway会自动设置） |
| `SECRET_KEY` | JWT密钥 | `we-mp-rss` |
| `SERVER_NAME` | 服务名称 | `we-mp-rss` |
| `INIT_DB` | 初始化数据库 | `False`（首次部署可设为True） |

## ⚠️ 重要提示

### 1. 启动命令

**你不需要手动设置启动命令！**

项目已经配置了：
- `railway.json` - Railway会使用 `python3 main.py`
- `Procfile` - 备用配置 `web: python3 main.py`

定时任务通过环境变量 `ENABLE_JOB=True` 控制，**不需要**在启动命令中添加 `-job True`。

### 2. 数据库迁移

- **首次部署**：可以设置 `INIT_DB=True` 自动创建表
- **后续部署**：记得移除 `INIT_DB`，避免重复初始化
- **手动迁移**：使用 `schemas/brief_migration.sql` 中的SQL

### 3. 功能开关

- `ENABLE_JOB=True` - 必须设置，否则定时任务不会运行
- `AI_BRIEF_ENABLED=True` - 必须设置，否则AI简报功能不会启用
- `AI_BRIEF_AUTO_GENERATE=True` - 必须设置，否则不会自动生成简报

### 4. 成本控制

- 合理设置 `AI_BRIEF_BATCH_SIZE`（建议10-20）
- 合理设置 `AI_BRIEF_GENERATE_INTERVAL`（建议60分钟以上）
- 已生成的简报不会重复生成

## 🐛 常见问题

### Q: 定时任务没有启动？

**A:** 检查：
1. `ENABLE_JOB=True` 是否设置
2. 查看Railway日志，确认看到 "定时任务已启用"
3. 检查 `server.enable_job` 配置（如果使用config.yaml）

### Q: AI简报没有生成？

**A:** 检查：
1. `AI_BRIEF_ENABLED=True` 是否设置
2. `AI_BRIEF_AUTO_GENERATE=True` 是否设置
3. `GLM_API_KEY` 是否正确
4. 查看日志中的错误信息

### Q: 数据库连接失败？

**A:** 检查：
1. 如果使用Railway PostgreSQL，确认已添加数据库服务
2. 如果使用外部数据库，确认 `DB` 环境变量正确
3. 检查数据库是否允许Railway的IP访问

### Q: 如何查看日志？

**A:** 
1. 在Railway Dashboard中点击你的服务
2. 选择 "Deployments" 标签
3. 点击最新的部署
4. 查看 "Logs" 标签

## 📚 相关文档

- [AI简报功能部署指南](./AI简报功能部署指南.md)
- [AI简报功能实现评估报告](./AI简报功能实现评估报告.md)
- [AIRSS AI简报生成服务端实现指南](./AIRSS%20AI简报生成服务端实现指南.md)

---

*最后更新：2025-01-XX*

