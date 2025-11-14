-- AI简报表创建脚本
-- 支持PostgreSQL/Supabase, MySQL, SQLite

-- PostgreSQL/Supabase版本
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

-- MySQL版本（如果使用MySQL，请使用以下SQL）
/*
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
*/

-- SQLite版本（如果使用SQLite，请使用以下SQL）
/*
CREATE TABLE IF NOT EXISTS briefs (
    id TEXT PRIMARY KEY,
    article_key TEXT UNIQUE NOT NULL,
    model TEXT NOT NULL DEFAULT 'GLM-4.5-Flash',
    summary TEXT NOT NULL,
    highlights TEXT,  -- JSON格式存储为TEXT
    version TEXT DEFAULT '3.0',
    language TEXT DEFAULT 'zh-CN',
    tags TEXT,  -- JSON格式存储为TEXT
    confidence REAL,
    generated_at TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_briefs_article_key ON briefs(article_key);
*/

