# 🚀 AIRSS AI简报生成服务端实现指南

## 📋 概述

本文档详细说明如何在 `rss.aistockdaily.com` 服务端实现与 iOS 客户端完全一致的 AI 简报生成功能。

## 🗄️ 数据库结构

### Supabase 简报表
```sql
CREATE TABLE briefs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_key TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL,
    summary TEXT NOT NULL,
    highlights JSONB,
    version TEXT DEFAULT '3.0',
    language TEXT DEFAULT 'zh-CN',
    tags TEXT[],
    confidence REAL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🤖 AI API 配置

**端点**: `https://open.bigmodel.cn/api/paas/v4/chat/completions`  
**默认模型**: `GLM-4.5-Flash`  
**API Key**: 环境变量 `GLM_API_KEY`

## 📝 Prompt 模板 (完整版)

### 系统提示
```
你是一位专业的内容分析师，擅长以结构化方式总结中文文章，帮助读者快速理解价值。
生成内容需严格遵循指定 JSON Schema，不得输出额外解释或 Markdown。
```

### 用户提示 (完整详细版)
```
请为以下文章生成结构化简报（AI Brief），输出 JSON，符合 Schema v3.0：

{
  "meta": {
    "version": "3.0",
    "language": "zh-CN",
    "generated_at": <ISO8601 时间戳，可选>,
    "tags": <可选的字符串数组>,
    "confidence": <可选，0-1 之间数值或 high/medium/low>
  },
  "summary": "对全文的简介总结，长度不限，直接陈述文章主要观点",
  "highlights": [
    {
      "title": "核心重点标题，简洁聚焦",
      "description": "对该重点的说明，解释具体内容、原因或影响"
    }
  ]
}

生成要求：
1. "summary" 段落需覆盖文章核心观点，不做字数限制。
2. "highlights" 至少 1 条，最多 6 条，每条描述需解释重点
3. 不得输出除上述 JSON 结构以外的内容，字段顺序和名称必须一致。
4. 保持客观、中立，不插入主观评价；若正文缺失或信息不足，请明确说明，不得虚构细节。
5. 仅根据提供的正文内容回答，不引用外部知识，不猜测或编造事实。

文章标题：{article.title}
文章作者：{article.author ?? "未知"}
发布时间：{ISO8601(publishDate)}
正文完整度：{contentStatus}
文章内容：
{contentSnippet}{truncateNotice}
```

**内容处理逻辑**:
- 正文超过 24000 字符时自动截断
- 空内容时显示"正文缺失：无可用文字"
- 发布时间格式化为 ISO8601 格式

## 🔧 核心代码实现

### 1. API请求构造
```javascript
const GLMRequest = {
  model: "GLM-4.5-Flash",
  messages: [
    {
      role: "system",
      content: systemPrompt
    },
    {
      role: "user", 
      content: userPrompt
    }
  ],
  temperature: 0.3,
  max_tokens: 4000,
  response_format: { type: "json_object" }
};
```

### 2. 响应解析器
```javascript
function parseGLMResponse(response, articleKey, model) {
  // 清理JSON响应
  let content = response.choices[0].message.content;
  content = content.replace(/```json|```/g, '').trim();
  
  const data = JSON.parse(content);
  const meta = data.meta || {};
  
  return {
    articleKey: articleKey,
    model: model,
    summary: data.summary,
    highlights: data.highlights.map(h => ({
      title: h.title,
      detail: h.description || h.detail
    })),
    version: meta.version || '3.0',
    language: meta.language || 'zh-CN',
    tags: meta.tags || [],
    confidence: parseConfidence(meta.confidence),
    generatedAt: parseDate(meta.generated_at) || new Date(),
    createdAt: new Date(),
    updatedAt: new Date()
  };
}
```

### 3. 错误处理
```javascript
// 置信度解析
function parseConfidence(value) {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    switch (value.toLowerCase()) {
      case '高': case 'high': return 0.9;
      case '中': case 'medium': return 0.7;
      case '低': case 'low': return 0.5;
      default: return parseFloat(value);
    }
  }
  return null;
}

// 日期解析  
function parseDate(value) {
  if (typeof value === 'number') {
    return new Date(value * 1000); // Unix时间戳
  }
  if (typeof value === 'string') {
    return new Date(value); // ISO8601
  }
  return null;
}
```

## 🚦 错误分类处理

| 错误类型 | 处理策略 | 重试策略 |
|---------|---------|---------|
| HTTP 400 | 跳过该文章 | 不重试 |
| HTTP 429 | 速率限制 | 指数退避重试 |
| JSON解析失败 | 记录日志 | 可配置重试 |
| 网络超时 | 自动重试 | 3次重试 |

## 📊 数据模型映射

### iOS客户端 → 服务端
| 客户端字段 | 服务端字段 | 类型 |
|-----------|-----------|------|
| `articleKey` | `article_key` | TEXT |
| `model` | `model` | TEXT |
| `summary` | `summary` | TEXT |
| `highlights` | `highlights` | JSONB |
| `version` | `version` | TEXT |
| `language` | `language` | TEXT |
| `tags` | `tags` | TEXT[] |
| `confidence` | `confidence` | REAL |
| `generatedAt` | `generated_at` | TIMESTAMPTZ |

## ✅ 迁移优势

1. **避免重复计算** - 相同文章只生成一次简报
2. **成本优化** - 减少AI API调用次数  
3. **一致性** - 所有客户端获取相同内容
4. **性能提升** - 客户端无需等待生成

## 🚀 实施步骤

1. **阶段一**: 在Supabase创建`briefs`表
2. **阶段二**: 实现GLM API调用服务
3. **阶段三**: 添加文章处理队列和重试机制
4. **阶段四**: 实现客户端同步查询接口
5. **阶段五**: 逐步迁移现有文章简报生成
6. **阶段六**: 关闭客户端AI生成功能

---
*基于iOS客户端 v3.0 实现 - 文档生成时间: 2025-11-14*
