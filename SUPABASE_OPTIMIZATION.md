# Supabase 连接池优化说明

## 问题描述

使用 Free Supabase（无 Pooler）时，SQLAlchemy 连接池配置不当会导致：
- 连接数超过 Supabase 的 20 个连接限制
- 数据库卡死或连接被拒绝
- 应用性能下降

## 已实施的优化

### 1. 连接池配置优化

**优化前：**
```python
pool_size=2, max_overflow=20  # 最大 22 个连接 ❌
```

**优化后：**
```python
# Supabase/PostgreSQL 自动检测并应用：
pool_size=5, max_overflow=10  # 最大 15 个连接 ✅
pool_pre_ping=True  # 连接前检查连接有效性
pool_recycle=300  # 5分钟回收连接
```

### 2. Session 管理改进

新增了两种安全的 session 使用方式：

#### 方式一：FastAPI 依赖注入（推荐）

```python
from fastapi import Depends
from core.database import get_db
from sqlalchemy.orm import Session

@router.get("/articles")
async def get_articles(db: Session = Depends(get_db)):
    # 使用 db 进行数据库操作
    articles = db.query(Article).all()
    return success_response(articles)
    # session 会在请求结束后自动清理 ✅
```

#### 方式二：上下文管理器

```python
from core.db import DB

@router.delete("/clean")
async def clean_articles():
    with DB.session_scope() as session:
        # 使用 session 进行数据库操作
        deleted_count = session.query(Article).delete()
        # session.commit() 会自动调用
    # session 会在退出 with 块时自动清理 ✅
```

### 3. 现有代码迁移建议

**旧代码（有连接泄漏风险）：**
```python
@router.delete("/clean")
async def clean_articles():
    session = DB.get_session()  # ❌ 没有清理
    try:
        deleted_count = session.query(Article).delete()
        session.commit()
        return success_response({"deleted_count": deleted_count})
    except Exception as e:
        session.rollback()
        raise
    # ❌ 缺少 finally 块来清理 session
```

**新代码（推荐方式一）：**
```python
@router.delete("/clean")
async def clean_articles(db: Session = Depends(get_db)):
    try:
        deleted_count = db.query(Article).delete()
        db.commit()
        return success_response({"deleted_count": deleted_count})
    except Exception as e:
        db.rollback()
        raise
    # ✅ session 自动清理
```

**新代码（推荐方式二）：**
```python
@router.delete("/clean")
async def clean_articles():
    with DB.session_scope() as session:
        deleted_count = session.query(Article).delete()
        # commit 会自动调用
        return success_response({"deleted_count": deleted_count})
    # ✅ session 自动清理
```

## 连接池配置说明

### Supabase Free 限制
- **最大连接数：20**
- **无连接池（Pooler）**

### 优化后的配置
- **pool_size = 5**：基础连接池大小
- **max_overflow = 10**：允许的溢出连接数
- **最大总连接数 = 15**：留 5 个连接余量，避免达到上限

### 其他数据库配置
- **SQLite**：`pool_size=1, max_overflow=0`（不需要连接池）
- **MySQL**：`pool_size=5, max_overflow=10`（中等配置）

## 监控建议

1. **检查连接数**：在 Supabase 控制台查看当前连接数
2. **查看日志**：注意是否有连接超时或拒绝的错误
3. **性能监控**：观察应用响应时间是否改善

## 迁移步骤

1. ✅ **已完成**：连接池配置优化（自动检测 Supabase）
2. ⏳ **进行中**：逐步迁移 API 端点使用新的 session 管理方式
3. ⏳ **待完成**：测试验证连接数是否稳定

## 注意事项

1. **不要同时使用多种方式**：在一个端点中，要么使用依赖注入，要么使用上下文管理器，不要混用
2. **异步函数**：FastAPI 的依赖注入在异步函数中工作正常
3. **后台任务**：对于后台任务（jobs），建议使用 `DB.session_scope()` 上下文管理器

## 验证优化效果

部署后，可以通过以下方式验证：

1. 查看 Supabase 控制台的连接数监控
2. 检查应用日志，确认没有连接相关的错误
3. 观察应用性能，确认响应时间正常

