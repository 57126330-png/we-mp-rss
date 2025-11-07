from core.db import DB
from sqlalchemy.orm import Session
from typing import Generator

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入函数，用于获取数据库会话
    
    使用示例:
        @router.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
        # session 会在请求结束后自动清理
    """
    yield from DB.session_dependency()