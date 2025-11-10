from fastapi import status
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

class BaseResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None

def success_response(data=None, message="success"):
    return {
        "code": 0,
        "message": message,
        "data": data
    }

def error_response(code: int, message: str, data=None):
    return {
        "code": code,
        "message": message,
        "data": data
    }
from sqlalchemy import and_,or_
from core.models import Article
def format_search_kw(keyword: str, model=Article):
    words = keyword.replace("-"," ").replace("|"," ").split(" ")
    column = getattr(model, "title", Article.title)
    rule = or_(*[column.like(f"%{w}%") for w in words])
    return rule