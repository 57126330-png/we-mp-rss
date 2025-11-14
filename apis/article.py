from fastapi import APIRouter, Depends, HTTPException, status as fast_status, Query
from core.auth import get_current_user
from core.db import DB
from core.models.base import DATA_STATUS
from core.models.article import Article,ArticleBase
from sqlalchemy import and_, or_, desc
from .base import success_response, error_response
from core.config import cfg
from apis.base import format_search_kw
from core.print import print_warning, print_info, print_error, print_success
router = APIRouter(prefix=f"/articles", tags=["文章管理"])


    
@router.delete("/clean", summary="清理无效文章(MP_ID不存在于Feeds表中的文章)")
async def clean_orphan_articles(
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.feed import Feed
        from core.models.article import Article
        
        # 找出Articles表中mp_id不在Feeds表中的记录
        subquery = session.query(Feed.id).subquery()
        deleted_count = session.query(Article)\
            .filter(~Article.mp_id.in_(subquery))\
            .delete(synchronize_session=False)
        
        session.commit()
        
        return success_response({
            "message": "清理无效文章成功",
            "deleted_count": deleted_count
        })
    except Exception as e:
        session.rollback()
        print(f"清理无效文章错误: {str(e)}")
        raise HTTPException(
            status_code=fast_status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="清理无效文章失败"
            )
        )
    
@router.delete("/clean_duplicate_articles", summary="清理重复文章")
async def clean_duplicate(
    current_user: dict = Depends(get_current_user)
):
    try:
        from tools.clean import clean_duplicate_articles
        (msg, deleted_count) =clean_duplicate_articles()
        return success_response({
            "message": msg,
            "deleted_count": deleted_count
        })
    except Exception as e:
        print(f"清理重复文章: {str(e)}")
        raise HTTPException(
            status_code=fast_status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="清理重复文章"
            )
        )


@router.api_route("", summary="获取文章列表",methods= ["GET", "POST"], operation_id="get_articles_list")
async def get_articles(
    offset: int = Query(0, ge=0),
    limit: int = Query(5, ge=1, le=100),
    status: str = Query(None),
    search: str = Query(None),
    mp_id: str = Query(None),
    has_content:bool=Query(False),
    current_user: dict = Depends(get_current_user)
):
    with DB.session_scope(auto_commit=False) as session:
        try:
            model = Article if has_content else ArticleBase

            # 构建查询条件
            query = session.query(model)

            if status:
                query = query.filter(model.status == status)
            else:
                query = query.filter(model.status != DATA_STATUS.DELETED)

            if mp_id:
                query = query.filter(model.mp_id == mp_id)

            if search:
                query = query.filter(format_search_kw(search, model=model))

            # 获取总数
            total = query.count()

            query = (
                query.order_by(model.created_at.desc())
                .offset(offset)
                .limit(limit)
            )

            # 分页查询（按发布时间降序）
            articles = query.all()

            # 打印生成的 SQL 语句（包含分页参数）
            print_warning(
                query.statement.compile(compile_kwargs={"literal_binds": True})
            )

            # 查询公众号名称
            from core.models.feed import Feed

            mp_names = {}
            for article in articles:
                if article.mp_id and article.mp_id not in mp_names:
                    feed = (
                        session.query(Feed)
                        .filter(Feed.id == article.mp_id)
                        .first()
                    )
                    mp_names[article.mp_id] = feed.mp_name if feed else "未知公众号"

            # 查询哪些文章已有简报（批量查询，提高性能）
            from core.models.brief import Brief
            article_ids = [article.id for article in articles]
            brief_article_keys = set()
            if article_ids:  # 避免空列表查询
                briefs = session.query(Brief.article_key).filter(
                    Brief.article_key.in_(article_ids)
                ).all()
                brief_article_keys = {brief[0] for brief in briefs}
                # 调试日志：打印查询到的简报数量
                from core.print import print_info, print_warning
                print_info(f"文章列表查询：共{len(article_ids)}篇文章，其中{len(brief_article_keys)}篇有简报")
                # 打印所有brief的article_key（用于调试）
                if brief_article_keys:
                    print_info(f"数据库中的brief.article_key列表: {list(brief_article_keys)[:5]}...")  # 只打印前5个
                # 打印所有article.id（用于调试）
                print_info(f"查询的文章ID列表: {article_ids[:5]}...")  # 只打印前5个
            
            # 合并公众号名称和简报状态到文章列表
            article_list = []
            for article in articles:
                article_dict = dict(article.__dict__)
                article_dict.pop("_sa_instance_state", None)
                article_dict["mp_name"] = mp_names.get(article.mp_id, "未知公众号")
                has_brief = article.id in brief_article_keys
                article_dict["has_brief"] = has_brief  # 添加是否有简报的标识
                # 调试日志：打印匹配情况
                from core.print import print_info, print_warning
                if has_brief:
                    print_info(f"✓ 文章 {article.id[:50]} 有简报 (article.id={article.id})")
                else:
                    # 检查是否有类似的article_key（可能是格式问题）
                    matching_keys = [key for key in brief_article_keys if article.id in key or key in article.id]
                    if matching_keys:
                        print_warning(f"⚠ 文章 {article.id[:50]} 没有匹配的简报，但发现相似的article_key: {matching_keys}")
                article_list.append(article_dict)

            from .base import success_response

            return success_response({"list": article_list, "total": total})
        except HTTPException as e:
            session.rollback()
            raise e
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=50001, message=f"获取文章列表失败: {str(e)}"
                ),
            )

@router.get("/{article_id}", summary="获取文章详情")
async def get_article_detail(
    article_id: str,
    content: bool = False,
    include_brief: bool = Query(False, description="是否包含AI简报"),
    # current_user: dict = Depends(get_current_user)
):
    # 使用上下文管理器确保 session 被正确清理（只读操作，不需要 commit）
    with DB.session_scope(auto_commit=False) as session:
        try:
            article = session.query(Article).filter(Article.id==article_id).filter(Article.status != DATA_STATUS.DELETED).first()
            if not article:
                from .base import error_response
                raise HTTPException(
                    status_code=fast_status.HTTP_404_NOT_FOUND,
                    detail=error_response(
                        code=40401,
                        message="文章不存在"
                    )
                )
            
            result = dict(article.__dict__)
            result.pop("_sa_instance_state", None)
            
            # 如果需要包含简报
            if include_brief:
                from core.models.brief import Brief
                brief = session.query(Brief).filter(Brief.article_key == article_id).first()
                if brief:
                    result['brief'] = brief.to_dict()
                else:
                    result['brief'] = None
            
            return success_response(result)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=50001,
                    message=f"获取文章详情失败: {str(e)}"
                )
            )   

@router.delete("/{article_id}", summary="删除文章")
async def delete_article(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.article import Article
        
        # 检查文章是否存在
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=40401,
                    message="文章不存在"
                )
            )
        # 逻辑删除文章（更新状态为deleted）
        article.status = DATA_STATUS.DELETED
        if cfg.get("article.true_delete", False):
            session.delete(article)
        session.commit()
        
        return success_response(None, message="文章已标记为删除")
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
            detail=error_response(
                code=50001,
                message=f"删除文章失败: {str(e)}"
            )
        )

@router.get("/{article_id}/next", summary="获取下一篇文章")
async def get_next_article(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        # 获取当前文章的发布时间
        current_article = session.query(Article).filter(Article.id == article_id).first()
        if not current_article:
            raise HTTPException(
                status_code=fast_status.HTTP_404_NOT_FOUND,
                detail=error_response(
                    code=40401,
                    message="当前文章不存在"
                )
            )
        
        # 查询发布时间更晚的第一篇文章
        next_article = session.query(Article)\
            .filter(Article.publish_time > current_article.publish_time)\
            .filter(Article.status != DATA_STATUS.DELETED)\
            .filter(Article.mp_id == current_article.mp_id)\
            .order_by(Article.publish_time.asc())\
            .first()
        
        if not next_article:
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=40402,
                    message="没有下一篇文章"
                )
            )
        
        return success_response(next_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
            detail=error_response(
                code=50001,
                message=f"获取下一篇文章失败: {str(e)}"
            )
        )

@router.get("/{article_id}/prev", summary="获取上一篇文章")
async def get_prev_article(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        # 获取当前文章的发布时间
        current_article = session.query(Article).filter(Article.id == article_id).first()
        if not current_article:
            raise HTTPException(
                status_code=fast_status.HTTP_404_NOT_FOUND,
                detail=error_response(
                    code=40401,
                    message="当前文章不存在"
                )
            )
        
        # 查询发布时间更早的第一篇文章
        prev_article = session.query(Article)\
            .filter(Article.publish_time < current_article.publish_time)\
            .filter(Article.status != DATA_STATUS.DELETED)\
            .filter(Article.mp_id == current_article.mp_id)\
            .order_by(Article.publish_time.desc())\
            .first()
        
        if not prev_article:
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=40403,
                    message="没有上一篇文章"
                )
            )
        
        return success_response(prev_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
            detail=error_response(
                code=50001,
                message=f"获取上一篇文章失败: {str(e)}"
            )
        )

@router.get("/{article_id}/brief", summary="获取文章AI简报")
async def get_article_brief(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取指定文章的AI简报"""
    with DB.session_scope(auto_commit=False) as session:
        try:
            from core.models.brief import Brief
            
            brief = session.query(Brief).filter(Brief.article_key == article_id).first()
            
            if not brief:
                raise HTTPException(
                    status_code=fast_status.HTTP_404_NOT_FOUND,
                    detail=error_response(
                        code=40402,
                        message="该文章尚未生成AI简报"
                    )
                )
            
            return success_response(brief.to_dict())
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
                detail=error_response(
                    code=50001,
                    message=f"获取AI简报失败: {str(e)}"
                )
            )

@router.post("/{article_id}/brief/generate", summary="手动生成文章AI简报")
async def generate_article_brief(
    article_id: str,
    current_user: dict = Depends(get_current_user)
):
    """手动触发为指定文章生成AI简报"""
    try:
        from jobs.brief import generate_brief_for_article
        import asyncio
        
        # 获取或创建事件循环
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        brief = await generate_brief_for_article(article_id)
        
        if not brief:
            raise HTTPException(
                status_code=fast_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_response(
                    code=50002,
                    message="AI简报生成失败，请检查文章内容和配置"
                )
            )
        
        return success_response(brief.to_dict(), message="AI简报生成成功")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=fast_status.HTTP_406_NOT_ACCEPTABLE,
            detail=error_response(
                code=50001,
                message=f"生成AI简报失败: {str(e)}"
            )
        )