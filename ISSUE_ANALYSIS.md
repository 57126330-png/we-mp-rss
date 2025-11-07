# 数据库卡死问题分析报告

## 问题描述

**现象**：`https://rss.aistockdaily.com/` 网站卡死，无法正常访问

**触发场景**：在本地开发订阅 APP 时，通过获取该网站的 API 进行了大量重复测试

## 根本原因分析

### 1. **Session 泄漏问题（主要原因）**

**问题代码位置**：
- `apis/rss.py` - `get_rss_feeds()` 函数（第70行）
- `apis/rss.py` - `get_mp_articles_source()` 函数（第196行）
- `apis/article.py` - `get_article_detail()` 函数（第145行）

**问题代码**：
```python
session = DB.get_session()  # ❌ 获取 session
try:
    # ... 数据库操作 ...
    return Response(...)
except Exception as e:
    # ... 错误处理 ...
# ❌ 没有 finally 块清理 session！
```

**影响**：
- 这些 RSS API 端点**没有认证保护**（注释掉了 `current_user`）
- 可以被外部大量调用
- 每个请求创建一个 session，但**从未被清理**
- Session 持有数据库连接，连接不会被释放回连接池

### 2. **连接池配置问题**

**原配置**：
```python
pool_size=2, max_overflow=20  # 最大 22 个连接
```

**Supabase Free 限制**：
- 最大连接数：**20 个**
- 无连接池（Pooler）

**问题**：
- 配置的最大连接数（22）超过了 Supabase 的限制（20）
- 在大量请求下，连接数快速达到上限
- 新请求无法获取连接，导致卡死

### 3. **大量并发请求的放大效应**

**场景重现**：
1. 本地开发订阅 APP
2. 重复测试调用 RSS API（如 `/rss/{feed_id}`）
3. 每个请求：
   - 创建一个 session（占用一个连接）
   - 执行数据库查询
   - **Session 没有被清理**（连接不释放）
4. 短时间内大量请求 → 连接数快速累积
5. 达到 Supabase 的 20 个连接上限
6. 新请求无法获取连接 → **数据库卡死**

## 解决方案

### ✅ 已实施的修复

#### 1. 修复 Session 泄漏（关键修复）

**修复后的代码**：
```python
# 使用上下文管理器确保 session 被正确清理
with DB.session_scope() as session:
    try:
        # ... 数据库操作 ...
        return Response(...)
    except Exception as e:
        # ... 错误处理 ...
    # ✅ session 会在退出 with 块时自动清理
```

**修复的端点**：
- ✅ `apis/rss.py::get_rss_feeds()` 
- ✅ `apis/rss.py::get_mp_articles_source()`
- ✅ `apis/article.py::get_article_detail()`

#### 2. 优化连接池配置

**新配置**（自动检测 Supabase）：
```python
# Supabase/PostgreSQL 自动应用：
pool_size=5, max_overflow=10  # 最大 15 个连接 ✅
pool_pre_ping=True  # 连接前检查有效性
pool_recycle=300  # 5分钟回收连接
```

**优势**：
- 最大连接数（15）低于 Supabase 限制（20），留有余量
- 自动检测 Supabase 连接并应用优化配置
- 连接健康检查防止使用已断开的连接

### 📋 待完成的工作

#### 1. 部署修复到生产环境

**步骤**：
1. 提交代码到 GitHub
2. Railway 自动部署（如果已配置）
3. 或手动部署到生产环境

#### 2. 监控验证

**检查项**：
- [ ] Supabase 控制台查看当前连接数
- [ ] 观察连接数是否稳定在 15 以下
- [ ] 测试 RSS API 是否正常响应
- [ ] 检查应用日志是否有连接相关错误

#### 3. 逐步迁移其他端点（可选）

虽然已修复最关键的 RSS 端点，但其他 API 端点也存在类似问题。建议逐步迁移：

**需要迁移的端点**：
- `apis/user.py` - 多个端点
- `apis/mps.py` - 多个端点
- `apis/message_task.py` - 多个端点
- `apis/export.py` - 多个端点
- `apis/config_management.py` - 多个端点

**迁移方式**：
1. 使用 `Depends(get_db)` 依赖注入（推荐）
2. 或使用 `DB.session_scope()` 上下文管理器

## 预防措施

### 1. 开发环境测试建议

**避免**：
- ❌ 直接对生产环境进行大量测试
- ❌ 无限制的并发请求测试

**推荐**：
- ✅ 使用本地开发环境进行测试
- ✅ 使用测试数据库（非生产 Supabase）
- ✅ 限制并发请求数量
- ✅ 使用请求限流/节流

### 2. 监控和告警

**建议添加**：
- 连接数监控（Supabase 控制台）
- 应用性能监控（APM）
- 错误日志告警

### 3. 代码审查检查清单

**每次代码审查时检查**：
- [ ] 所有 `DB.get_session()` 调用是否有对应的清理逻辑
- [ ] 是否使用了 `session_scope()` 或 `Depends(get_db)`
- [ ] 是否有 try/finally 确保 session 清理
- [ ] 外部可访问的 API 是否有适当的限流保护

## 总结

**问题根源**：
1. Session 泄漏导致连接不释放
2. 连接池配置超过 Supabase 限制
3. 大量并发请求放大问题

**解决方案**：
1. ✅ 修复 RSS API 端点的 session 泄漏
2. ✅ 优化连接池配置（自动检测 Supabase）
3. ⏳ 部署到生产环境
4. ⏳ 监控验证效果

**预期效果**：
- 连接数稳定在 15 以下
- 不再出现数据库卡死
- RSS API 正常响应
- 系统稳定性提升

