from core.models import Article,Feed,DATA_STATUS
from core.db import DB
import json
class ArticleInfo():
    #没有内容的文章数量
    no_content_count:int=0
    #有内容的文章数量
    has_content_count:int=0
    #所有文章数量
    all_count:int=0
    #不正常的文章数量
    wrong_count:int=0
    #公众号总数
    mp_all_count:int=0

def laxArticle():
    """
    获取文章统计信息
    
    注意：此函数会执行数据库查询，应该在需要时调用，而不是在模块导入时调用
    """
    info=ArticleInfo()
    try:
        # 使用 session_scope 确保连接正确关闭
        with DB.session_scope(auto_commit=False) as session:
            #获取没有内容的文章数量
            info.no_content_count=session.query(Article).filter(Article.content == None).count()
            #所有文章数量
            info.all_count=session.query(Article).count()
            #有内容的文章数量
            info.has_content_count=info.all_count-info.no_content_count

            #获取删除的文章
            info.wrong_count=session.query(Article).filter(Article.status !=DATA_STATUS.ACTIVE ).count()

            #公众号总数
            info.mp_all_count=session.query(Feed).distinct(Feed.id).count()
    except Exception as e:
        from core.print import print_error
        print_error(f"获取文章统计信息失败: {e}")
        import traceback
        print_error(f"错误详情: {traceback.format_exc()}")
        # 返回默认值
        pass
    
    return info.__dict__

# 移除模块级别的数据库查询，改为在需要时动态获取
# ARTICLE_INFO 将在 API 调用时动态获取，避免在模块导入时连接数据库