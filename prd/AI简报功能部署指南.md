# AI简报功能部署指南

## 📋 概述

本文档说明如何部署和配置AI简报生成功能。

## 🚀 快速开始

### 1. 环境变量配置

在Railway或本地环境中设置以下环境变量：

```bash
# 必需：GLM API密钥
GLM_API_KEY=your-glm-api-key-here

# 可选：功能开关
AI_BRIEF_ENABLED=True
AI_BRIEF_AUTO_GENERATE=True
AI_BRIEF_GENERATE_INTERVAL=60  # 每60分钟执行一次
AI_BRIEF_BATCH_SIZE=10  # 每批处理10篇文章

# 可选：API配置
GLM_API_URL=https://open.bigmodel.cn/api/paas/v4/chat/completions
GLM_MODEL=GLM-4.5-Flash
AI_TIMEOUT=60
AI_MAX_RETRIES=3
```

### 2. 配置文件更新

在 `config.yaml` 中添加AI配置（或使用环境变量）：

```yaml
ai:
  brief_enabled: True
  brief_auto_generate: True
  brief_generate_interval: 60
  brief_batch_size: 10
  glm_api_key: ${GLM_API_KEY:-}
  glm_api_url: https://open.bigmodel.cn/api/paas/v4/chat/completions
  glm_model: GLM-4.5-Flash
  timeout: 60
  max_retries: 3
```

### 3. 数据库迁移

#### PostgreSQL/Supabase

```sql
CREATE TABLE IF NOT EXISTS briefs (
    id VARCHAR(255) PRIMARY KEY,
    article_key VARCHAR(255) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL DEFAULT 'GLM-4.5-Flash',
    summary TEXT NOT NULL,
    highlights JSONB,
    version VARCHAR(20) DEFAULT '3.0',
    language VARCHAR(10) DEFAULT 'zh-CN',
    tags TEXT[],
    confidence REAL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_briefs_article_key ON briefs(article_key);
```

#### MySQL

```sql
CREATE TABLE IF NOT EXISTS briefs (
    id VARCHAR(255) PRIMARY KEY,
    article_key VARCHAR(255) UNIQUE NOT NULL,
    model VARCHAR(100) NOT NULL DEFAULT 'GLM-4.5-Flash',
    summary TEXT NOT NULL,
    highlights JSON,
    version VARCHAR(20) DEFAULT '3.0',
    language VARCHAR(10) DEFAULT 'zh-CN',
    tags JSON,
    confidence FLOAT,
    generated_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_briefs_article_key ON briefs(article_key);
```

#### SQLite

```sql
CREATE TABLE IF NOT EXISTS briefs (
    id TEXT PRIMARY KEY,
    article_key TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL DEFAULT 'GLM-4.5-Flash',
    summary TEXT NOT NULL,
    highlights TEXT,
    version TEXT DEFAULT '3.0',
    language TEXT DEFAULT 'zh-CN',
    tags TEXT,
    confidence REAL,
    generated_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_briefs_article_key ON briefs(article_key);
```

**注意**：如果使用SQLAlchemy自动创建表，可以跳过手动迁移，表会在首次运行时自动创建。

### 4. 启动服务

#### 本地开发

```bash
# 方式1：使用命令行参数
python main.py -job True

# 方式2：使用环境变量（推荐）
export ENABLE_JOB=True
python main.py

# 方式3：使用配置文件
# 在 config.yaml 中设置 server.enable_job: True
python main.py
```

#### Railway部署

**无需手动设置启动命令！** Railway会自动使用项目中的配置：

- 如果存在 `railway.json`，Railway会使用其中的 `startCommand`
- 如果存在 `Procfile`，Railway会使用其中的命令
- 当前配置：`python3 main.py`

**只需要设置环境变量：**
- `ENABLE_JOB=True` - 启用定时任务
- `GLM_API_KEY=your-key` - AI API密钥
- 其他AI相关配置（见上方环境变量表格）

Railway部署后，服务会自动启动，定时任务也会自动运行。

## 🔧 Railway 部署

### 重要说明

**你不需要手动设置启动命令！** Railway会自动使用 `railway.json` 或 `Procfile` 中的配置。

启动命令已经配置为：`python3 main.py`

定时任务通过环境变量 `ENABLE_JOB=True` 控制，无需在启动命令中添加 `-job True`。

### 环境变量设置

在Railway项目设置中添加以下环境变量：

1. 进入Railway项目设置
2. 选择 "Variables" 标签
3. 添加以下变量：

#### 必需的环境变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ENABLE_JOB` | `True` | **必需** - 启用定时任务（包括AI简报生成） |
| `GLM_API_KEY` | 你的API密钥 | **必需** - GLM API密钥 |
| `DB` | 数据库连接字符串 | **必需** - 数据库连接（如果使用Railway的PostgreSQL会自动设置） |

#### AI简报相关环境变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `AI_BRIEF_ENABLED` | `True` | 启用AI简报功能 |
| `AI_BRIEF_AUTO_GENERATE` | `True` | 启用自动生成 |
| `AI_BRIEF_GENERATE_INTERVAL` | `60` | 执行间隔（分钟） |
| `AI_BRIEF_BATCH_SIZE` | `10` | 每批处理数量 |

#### 其他可选环境变量

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `PORT` | `8001` | 服务端口（Railway会自动设置） |
| `INIT_DB` | `True` | 首次部署时初始化数据库（可选） |
| `SERVER_NAME` | `we-mp-rss` | 服务名称 |
| `SECRET_KEY` | 你的密钥 | 用于JWT等加密 |

### 数据库迁移

如果使用Supabase：

1. 进入Supabase Dashboard
2. 打开SQL Editor
3. 执行PostgreSQL版本的迁移SQL（见上方）

如果使用Railway提供的PostgreSQL：

1. 连接到数据库
2. 执行PostgreSQL版本的迁移SQL

### 验证部署

1. **检查日志**：查看Railway日志，确认定时任务已启动
2. **测试API**：调用 `/api/articles/{article_id}/brief` 查看是否有简报
3. **手动触发**：调用 `/api/articles/{article_id}/brief/generate` 手动生成简报

## 📊 API接口说明

### 1. 获取文章简报

```http
GET /api/articles/{article_id}/brief
Authorization: Bearer {token}
```

**响应示例**：
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "article_key": "article-id",
    "summary": "文章摘要...",
    "highlights": [
      {
        "title": "核心要点1",
        "detail": "详细说明..."
      }
    ],
    "version": "3.0",
    "language": "zh-CN",
    "tags": ["标签1", "标签2"],
    "confidence": 0.9
  }
}
```

### 2. 手动生成简报

```http
POST /api/articles/{article_id}/brief/generate
Authorization: Bearer {token}
```

### 3. 获取文章详情（包含简报）

```http
GET /api/articles/{article_id}?include_brief=true
Authorization: Bearer {token}
```

## ⚙️ 配置说明

### 功能开关

- `ai.brief_enabled`: 总开关，控制是否启用AI简报功能
- `ai.brief_auto_generate`: 是否自动生成简报（定时任务）

### 性能调优

- `ai.brief_generate_interval`: 定时任务执行间隔（分钟）
- `ai.brief_batch_size`: 每批处理的文章数量
- `ai.timeout`: API请求超时时间（秒）
- `ai.max_retries`: 失败重试次数

### 成本控制

1. **批次大小**：减小 `brief_batch_size` 可以降低API调用频率
2. **执行间隔**：增大 `brief_generate_interval` 可以降低API调用频率
3. **缓存机制**：已存在的简报不会重复生成

## 🐛 故障排查

### 问题1：简报未生成

**检查项**：
1. 确认 `GLM_API_KEY` 已正确设置
2. 检查 `ai.brief_enabled` 是否为 `True`
3. 检查文章是否有内容（空内容不会生成简报）
4. 查看日志中的错误信息

### 问题2：定时任务未启动

**检查项**：
1. 确认 `server.enable_job` 为 `True`
2. 确认 `ai.brief_auto_generate` 为 `True`
3. 查看启动日志，确认任务已添加

### 问题3：API调用失败

**检查项**：
1. 验证 `GLM_API_KEY` 是否有效
2. 检查网络连接
3. 查看API响应错误信息
4. 检查速率限制（429错误）

### 问题4：数据库错误

**检查项**：
1. 确认已执行数据库迁移
2. 检查数据库连接配置
3. 查看数据库日志

## 📝 日志示例

### 成功生成简报

```
[AI简报生成] 正在生成简报 (尝试 1/3): 文章标题...
[AI简报生成] 简报生成成功: 文章标题...
[AI简报生成] 简报生成并保存成功: 文章标题...
```

### 失败重试

```
[AI简报生成] 正在生成简报 (尝试 1/3): 文章标题...
[AI简报生成] 速率限制，等待 2 秒后重试...
[AI简报生成] 正在生成简报 (尝试 2/3): 文章标题...
[AI简报生成] 简报生成成功: 文章标题...
```

## 🔒 安全建议

1. **API密钥安全**：
   - 使用环境变量存储 `GLM_API_KEY`
   - 不要在代码中硬编码密钥
   - 定期轮换API密钥

2. **访问控制**：
   - 简报生成接口需要认证
   - 限制API调用频率

3. **数据隐私**：
   - 简报数据存储在数据库中
   - 遵循数据保护法规

## 📚 相关文档

- [AI简报功能实现评估报告](./AI简报功能实现评估报告.md)
- [AIRSS AI简报生成服务端实现指南](./AIRSS%20AI简报生成服务端实现指南.md)

---

*最后更新：2025-01-XX*

