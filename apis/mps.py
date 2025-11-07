from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from typing import Optional, List
from core.auth import get_current_user
from core.db import DB
from core.wx import search_Biz
from .base import success_response, error_response
from datetime import datetime
from core.config import cfg
from core.res import save_avatar_locally
import io
import os
from jobs.article import UpdateArticle
router = APIRouter(prefix=f"/mps", tags=["公众号管理"])
# import core.db as db
# UPDB=db.Db("数据抓取")
# def UpdateArticle(art:dict):
#             return UPDB.add_article(art)


@router.get("/search/{kw}", summary="搜索公众号")
async def search_mp(
    kw: str = "",
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        result = search_Biz(kw,limit=limit,offset=offset)
        data={
            'list':result.get('list') if result is not None else [],
            'page':{
                'limit':limit,
                'offset':offset
            },
            'total':result.get('total') if result is not None else 0
        }
        return success_response(data)
    except Exception as e:
        print(f"搜索公众号错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message=f"搜索公众号失败,请重新扫码授权！",
            )
        )

@router.get("", summary="获取公众号列表")
async def get_mps(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw: str = Query(""),
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.feed import Feed
        query = session.query(Feed)
        if kw:
            query = query.filter(Feed.mp_name.ilike(f"%{kw}%"))
        total = query.count()
        mps = query.order_by(Feed.created_at.desc()).limit(limit).offset(offset).all()
        return success_response({
            "list": [{
                "id": mp.id,
                "mp_name": mp.mp_name,
                "mp_cover": mp.mp_cover,
                "mp_intro": mp.mp_intro,
                "status": mp.status,
                "created_at": mp.created_at.isoformat()
            } for mp in mps],
            "page": {
                "limit": limit,
                "offset": offset,
                "total": total
            },
            "total": total
        })
    except Exception as e:
        print(f"获取公众号列表错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="获取公众号列表失败"
            )
        )

@router.get("/update/{mp_id}", summary="更新公众号文章")
async def update_mps(
     mp_id: str,
     start_page: int = 0,
     end_page: int = 1,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.feed import Feed
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
           return error_response(
                    code=40401,
                    message="请选择一个公众号"
                )
        import time
        sync_interval=cfg.get("sync_interval",60)
        if mp.update_time is None:
            mp.update_time=int(time.time())-sync_interval
        time_span=int(time.time())-int(mp.update_time)
        if time_span<sync_interval:
           return error_response(
                    code=40402,
                    message="请不要频繁更新操作",
                    data={"time_span":time_span}
                )
        result=[]    
        def UpArt(mp):
            from core.wx import WxGather
            wx=WxGather().Model()
            wx.get_Articles(mp.faker_id,Mps_id=mp.id,Mps_title=mp.mp_name,CallBack=UpdateArticle,start_page=start_page,MaxPage=end_page)
            result=wx.articles
        import threading
        threading.Thread(target=UpArt,args=(mp,)).start()
        return success_response({
            "time_span":time_span,
            "list":result,
            "total":len(result),
            "mps":mp
        })
    except Exception as e:
        print(f"更新公众号文章: {str(e)}",e)
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message=f"更新公众号文章{str(e)}"
            )
        )

@router.get("/{mp_id}", summary="获取公众号详情")
async def get_mp(
    mp_id: str,
    # current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.feed import Feed
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail=error_response(
                    code=40401,
                    message="公众号不存在"
                )
            )
        return success_response(mp)
    except Exception as e:
        print(f"获取公众号详情错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="获取公众号详情失败"
            )
        )
@router.post("/by_article", summary="通过文章链接获取公众号详情")
async def get_mp_by_article(
    url: str=Query(..., min_length=1),
    current_user: dict = Depends(get_current_user)
):
    try:
        from driver.wxarticle import Web
        info=Web.get_article_content(url)
        if not info:
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail=error_response(
                    code=40401,
                    message="公众号不存在"
                )
            )
        return success_response(info)
    except Exception as e:
        print(f"获取公众号详情错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="通过文章链接获取公众号详情"
            )
        )

@router.post("", summary="添加公众号")
async def add_mp(
    mp_name: str = Body(..., min_length=1, max_length=255),
    mp_cover: str = Body(None, max_length=255),
    mp_id: str = Body(None, max_length=255),
    avatar: str = Body(None, max_length=500),
    mp_intro: str = Body(None, max_length=255),
    tag_ids: Optional[List[str]] = Body(None),  # 新增：标签ID列表（可选）
    current_user: dict = Depends(get_current_user)
):
    # 使用 session_scope 确保连接正确关闭
    try:
        from core.models.feed import Feed
        from core.models.tags import Tags as TagsModel
        import time
        import json
        now = datetime.now()
        
        import base64
        mpx_id = base64.b64decode(mp_id).decode("utf-8")
        local_avatar_path = f"{save_avatar_locally(avatar)}"
        
        # 初始化变量
        existing_feed = None
        feed_id = None
        feed_mp_name = None
        feed_mp_cover = None
        feed_mp_intro = None
        feed_status = None
        feed_created_at = None
        is_new_feed = False
        
        with DB.session_scope(auto_commit=True) as session:
            # 检查公众号是否已存在
            existing_feed = session.query(Feed).filter(Feed.faker_id == mp_id).first()
            
            if existing_feed:
                # 更新现有记录
                existing_feed.mp_name = mp_name
                existing_feed.mp_cover = local_avatar_path
                existing_feed.mp_intro = mp_intro
                existing_feed.updated_at = now
                # 在session关闭前保存所有需要的属性值
                feed_id = existing_feed.id
                feed_mp_name = existing_feed.mp_name
                feed_mp_cover = existing_feed.mp_cover
                feed_mp_intro = existing_feed.mp_intro
                feed_status = existing_feed.status
                feed_created_at = existing_feed.created_at
                is_new_feed = False
            else:
                # 创建新的Feed记录
                new_feed = Feed(
                    id=f"MP_WXS_{mpx_id}",
                    mp_name=mp_name,
                    mp_cover= local_avatar_path,
                    mp_intro=mp_intro,
                    status=1,  # 默认启用状态
                    created_at=now,
                    updated_at=now,
                    faker_id=mp_id,
                    update_time=0,
                    sync_time=0,
                )
                session.add(new_feed)
                # 在session关闭前保存所有需要的属性值
                feed_id = new_feed.id
                feed_mp_name = new_feed.mp_name
                feed_mp_cover = new_feed.mp_cover
                feed_mp_intro = new_feed.mp_intro
                feed_status = new_feed.status
                feed_created_at = new_feed.created_at
                is_new_feed = True
        
        # 确保feed已创建
        if not feed_id:
            raise ValueError("创建或获取Feed失败")
        
        # 如果提供了标签ID列表，更新相关标签的mps_id（在单独的session中处理）
        if tag_ids and isinstance(tag_ids, list) and len(tag_ids) > 0:
            try:
                with DB.session_scope(auto_commit=True) as tag_session:
                    # 准备要添加的公众号信息（使用已保存的值）
                    mp_info = {
                        "id": feed_id,
                        "mp_name": feed_mp_name,
                        "mp_cover": feed_mp_cover
                    }
                    
                    # 遍历所有选中的标签
                    for tag_id in tag_ids:
                        tag = tag_session.query(TagsModel).filter(TagsModel.id == tag_id).first()
                        if tag:
                            # 解析现有的mps_id
                            try:
                                mps_list = json.loads(tag.mps_id) if tag.mps_id else []
                            except:
                                mps_list = []
                            
                            # 检查是否已存在该公众号
                            mp_exists = any(mp.get("id") == feed_id for mp in mps_list)
                            
                            if not mp_exists:
                                # 添加新公众号到标签
                                mps_list.append(mp_info)
                                tag.mps_id = json.dumps(mps_list, ensure_ascii=False)
                                tag.updated_at = now
            except Exception as tag_error:
                # 标签更新失败不影响订阅号创建，只记录错误
                from core.print import print_error
                print_error(f"更新标签关联失败: {tag_error}")
        
        # 在这里实现第一次添加获取公众号文章（只有新创建的才需要）
        if is_new_feed:
            from core.queue import TaskQueue
            from core.wx import WxGather
            from driver.token import wx_cfg
            from core.print import print_info, print_warning
            
            # 检查微信登录状态
            cookie = wx_cfg.get('cookie', '')
            token = wx_cfg.get('token', '')
            
            if not cookie or not token:
                print_warning(f"添加公众号 [{mp_name}] 成功，但微信未登录，无法立即抓取内容。请先登录微信公众平台。")
            else:
                Max_page=int(cfg.get("max_page","2"))
                print_info(f"添加公众号 [{mp_name}] 成功，已加入抓取队列，将抓取 {Max_page} 页内容")
                TaskQueue.add_task( WxGather().Model().get_Articles,faker_id=mp_id,Mps_id=feed_id,CallBack=UpdateArticle,MaxPage=Max_page,Mps_title=mp_name)
            
        return success_response({
            "id": feed_id,
            "mp_name": feed_mp_name,
            "mp_cover": feed_mp_cover,
            "mp_intro": feed_mp_intro,
            "status": feed_status,
            "faker_id":mp_id,
            "created_at": feed_created_at.isoformat() if feed_created_at else now.isoformat()
        })
    except Exception as e:
        from core.print import print_error
        print_error(f"添加公众号错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                code=50001,
                message=f"添加公众号失败: {str(e)}"
            )
        )


@router.delete("/{mp_id}", summary="删除订阅号")
async def delete_mp(
    mp_id: str,
    current_user: dict = Depends(get_current_user)
):
    session = DB.get_session()
    try:
        from core.models.feed import Feed
        mp = session.query(Feed).filter(Feed.id == mp_id).first()
        if not mp:
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail=error_response(
                    code=40401,
                    message="订阅号不存在"
                )
            )
        
        session.delete(mp)
        session.commit()
        return success_response({
            "message": "订阅号删除成功",
            "id": mp_id
        })
    except Exception as e:
        session.rollback()
        print(f"删除订阅号错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail=error_response(
                code=50001,
                message="删除订阅号失败"
            )
        )
