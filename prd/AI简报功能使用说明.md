# AI简报功能使用说明

## ✅ 功能状态确认

如果你已经：
1. ✅ 设置了环境变量 `AI_BRIEF_ENABLED=True`
2. ✅ 设置了环境变量 `AI_BRIEF_AUTO_GENERATE=True`
3. ✅ 设置了环境变量 `GLM_API_KEY=your-key`
4. ✅ 执行了数据库迁移

那么AI简报功能**已经启用**，应该可以正常工作了！

## 🔍 验证功能是否正常

### 1. 检查日志

部署后查看Railway日志，应该能看到：

```
[AI简报生成] 已添加AI简报生成定时任务: xxx (每60分钟执行一次，每批10篇)
定时任务已启用
```

### 2. 测试API接口

#### 手动生成简报（测试用）

```bash
POST /api/articles/{article_id}/brief/generate
Authorization: Bearer {token}
```

#### 查询简报

```bash
GET /api/articles/{article_id}/brief
Authorization: Bearer {token}
```

#### 获取文章详情（包含简报）

```bash
GET /api/articles/{article_id}?include_brief=true
Authorization: Bearer {token}
```

### 3. 检查定时任务

定时任务会：
- 每60分钟（或你设置的间隔）执行一次
- 每次处理10篇（或你设置的批次大小）没有简报的文章
- 自动为这些文章生成AI简报

## 📋 环境变量检查清单

确保以下环境变量已设置：

```bash
# 必需：启用定时任务
ENABLE_JOB=True

# 必需：启用AI简报功能
AI_BRIEF_ENABLED=True

# 必需：启用自动生成
AI_BRIEF_AUTO_GENERATE=True

# 必需：GLM API密钥
GLM_API_KEY=your-api-key-here

# 可选：自定义配置
AI_BRIEF_GENERATE_INTERVAL=60  # 执行间隔（分钟）
AI_BRIEF_BATCH_SIZE=10         # 每批处理数量
```

## 🚀 功能工作流程

1. **文章抓取**：正常抓取文章并保存到数据库
2. **定时任务触发**：每60分钟（可配置）自动检查未生成简报的文章
3. **批量生成**：每次处理10篇（可配置）文章
4. **AI处理**：调用GLM API生成简报
5. **保存结果**：将简报保存到 `briefs` 表
6. **API查询**：用户可以通过API查询简报

## 🐛 如果功能不工作

### 检查1：环境变量是否正确

在Railway中检查：
- `AI_BRIEF_ENABLED=True` ✅
- `AI_BRIEF_AUTO_GENERATE=True` ✅
- `GLM_API_KEY` 已设置 ✅
- `ENABLE_JOB=True` ✅

### 检查2：数据库表是否存在

执行以下SQL检查：

```sql
SELECT * FROM briefs LIMIT 1;
```

如果表不存在，执行迁移脚本。

### 检查3：查看日志

在Railway日志中查找：
- "AI简报功能未启用" - 说明 `AI_BRIEF_ENABLED` 未设置或为False
- "AI简报自动生成功能未启用" - 说明 `AI_BRIEF_AUTO_GENERATE` 未设置或为False
- "GLM_API_KEY未配置" - 说明API密钥未设置
- "已添加AI简报生成定时任务" - 说明功能已启用 ✅

### 检查4：手动测试

使用API手动生成一篇简报，测试功能是否正常：

```bash
POST /api/articles/{article_id}/brief/generate
```

如果手动生成成功，说明功能正常，只是定时任务可能还没到执行时间。

## 📊 功能说明

### 自动生成

- **触发方式**：定时任务自动执行
- **执行频率**：每60分钟（可配置）
- **处理数量**：每次10篇（可配置）
- **处理对象**：有内容但还没有简报的文章

### 手动生成

- **触发方式**：通过API接口手动触发
- **适用场景**：测试、紧急生成、特定文章

### 查询简报

- **方式1**：`GET /api/articles/{article_id}/brief` - 只获取简报
- **方式2**：`GET /api/articles/{article_id}?include_brief=true` - 获取文章+简报

## 💡 提示

1. **首次运行**：如果有很多历史文章，可能需要一些时间才能全部生成简报
2. **成本控制**：每篇文章需要调用一次AI API，注意控制批次大小和间隔
3. **已生成不重复**：已经生成过简报的文章不会重复生成
4. **空内容跳过**：没有内容的文章不会生成简报

---

**总结**：如果你已经设置了环境变量和执行了数据库迁移，功能应该已经启用。如果遇到问题，按照上面的检查清单排查。

