# Supabase 连接配置指南

## 连接模式说明

Supabase Pooler 提供两种连接模式：

### 1. Session 模式（端口 5432）
- **特点**：每个应用实例只能使用 `pool_size` 个连接
- **限制**：不支持 `max_overflow`
- **适用场景**：需要保持会话状态的应用
- **连接字符串格式**：
  ```
  postgresql://postgres.zyzcbybrdytfxnlhprpd:[PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
  ```

### 2. Transaction 模式（端口 6543）⭐ 推荐
- **特点**：支持连接池，可以使用 `max_overflow`
- **优势**：支持更多并发连接（pool_size + max_overflow）
- **适用场景**：每个事务使用一个连接，事务结束后连接返回池中
- **连接字符串格式**：
  ```
  postgresql://postgres.zyzcbybrdytfxnlhprpd:[PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres
  ```

## 获取连接字符串

1. 登录 Supabase Dashboard
2. 进入 Project Settings → Database
3. 找到 "Connection string" 或 "Connection pooling"
4. 选择 "Transaction" 模式
5. 复制连接字符串
6. 替换 `[YOUR-PASSWORD]` 为实际数据库密码

## 密码认证失败问题

如果遇到 `password authentication failed` 错误：

### 快速诊断步骤

1. **先测试 Session 模式（端口 5432）**
   如果 Session 模式可以连接，说明密码是正确的，问题可能在 Transaction 模式的配置上。
   
   使用 Session 模式连接字符串：
   ```
   postgresql://postgres.zyzcbybrdytfxnlhprpd:[PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
   ```

2. **从 Supabase 控制台获取正确的连接字符串**
   - 登录 Supabase Dashboard
   - 进入 Project Settings → Database
   - 找到 "Connection string" 或 "Connection pooling"
   - **直接复制完整的连接字符串**（不要手动拼接）
   - 选择 "Transaction" 模式，复制完整的连接字符串

3. **检查密码是否正确**
   - 确认连接字符串中的密码与 Supabase 控制台中的密码一致
   - 注意密码中可能包含特殊字符，需要进行 URL 编码

4. **检查用户名格式**
   - Session/Transaction 模式：`postgres.zyzcbybrdytfxnlhprpd`（包含项目标识）
   - 直接连接：`postgres`
   - **重要**：Pooler 模式的用户名格式与直接连接不同

5. **URL 编码特殊字符**
   如果密码包含特殊字符（如 `@`, `#`, `%`, `&` 等），需要进行 URL 编码：
   - `@` → `%40`
   - `#` → `%23`
   - `%` → `%25`
   - `&` → `%26`
   - `/` → `%2F`
   - `:` → `%3A`
   - `?` → `%3F`
   - `=` → `%3D`

6. **使用环境变量**
   建议使用环境变量存储密码，避免在代码中硬编码：
   ```bash
   export DB="postgresql://postgres.zyzcbybrdytfxnlhprpd:[PASSWORD]@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"
   ```

### 常见问题

**Q: Session 模式可以连接，但 Transaction 模式不行？**
A: 这通常说明密码是正确的，但 Transaction 模式可能需要不同的配置。检查：
- 确认端口号是 6543
- 确认用户名格式正确（包含项目标识）
- 尝试从 Supabase 控制台直接复制 Transaction 模式的连接字符串

**Q: 如何确认密码是否正确？**
A: 最简单的方法是：
1. 在 Supabase 控制台找到连接字符串
2. 直接复制完整的连接字符串（不要手动修改）
3. 如果还是不行，先测试 Session 模式（端口 5432）

## 代码自动检测

代码会自动检测连接模式：
- 如果检测到端口 `6543`，使用 Transaction 模式配置（`pool_size=5, max_overflow=10`）
- 如果检测到端口 `5432` 或没有端口，使用 Session 模式配置（`pool_size=3, max_overflow=0`）

## 推荐配置

**推荐使用 Transaction 模式（端口 6543）**，因为：
- 支持更大的连接池（最多 15 个连接）
- 代码已经使用 `session_scope`，符合 Transaction 模式的要求
- 性能更好，减少连接等待时间

