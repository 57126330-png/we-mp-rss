from .base import Base, Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy import Float
from datetime import datetime
from core.config import cfg

# 根据数据库类型选择JSON类型
def get_json_type():
    """根据数据库类型返回合适的JSON类型"""
    db_str = cfg.get("db", "")
    if "postgresql" in db_str or "postgres" in db_str or "supabase" in db_str:
        # PostgreSQL/Supabase 使用 JSONB
        return JSONB
    else:
        # MySQL/SQLite 使用 JSON
        return JSON

def get_array_type():
    """根据数据库类型返回合适的数组类型"""
    db_str = cfg.get("db", "")
    if "postgresql" in db_str or "postgres" in db_str or "supabase" in db_str:
        # PostgreSQL/Supabase 支持原生数组
        return ARRAY(String)
    else:
        # MySQL/SQLite 不支持数组，使用JSON存储
        return JSON

JSONType = get_json_type()
ArrayType = get_array_type()

class Brief(Base):
    """AI简报数据模型"""
    from_attributes = True
    __tablename__ = 'briefs'
    
    # 主键
    id = Column(String(255), primary_key=True)
    
    # 文章唯一标识（对应Article.id）
    article_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # 使用的AI模型
    model = Column(String(100), nullable=False, default='GLM-4.5-Flash')
    
    # 简报摘要
    summary = Column(Text, nullable=False)
    
    # 核心要点（JSON格式存储）
    highlights = Column(JSONType, nullable=True)
    
    # 版本号
    version = Column(String(20), default='3.0')
    
    # 语言
    language = Column(String(10), default='zh-CN')
    
    # 标签（数组或JSON）
    tags = Column(ArrayType, nullable=True)
    
    # 置信度（0-1之间的浮点数）
    confidence = Column(Float, nullable=True)
    
    # 生成时间
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'article_key': self.article_key,
            'model': self.model,
            'summary': self.summary,
            'highlights': self.highlights if isinstance(self.highlights, (list, dict)) else (self.highlights if self.highlights else []),
            'version': self.version,
            'language': self.language,
            'tags': self.tags if isinstance(self.tags, list) else (self.tags if self.tags else []),
            'confidence': self.confidence,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

