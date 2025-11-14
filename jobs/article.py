
import core.wx as wx 
import core.db as db
from core.config import DEBUG,cfg
from core.models.article import Article

DB=db.Db(tag="文章采集API")

def UpdateArticle(art:dict,check_exist=False):
    """更新文章到数据库
    
    Args:
        art: 文章数据字典
        check_exist: 是否检查文章是否已存在
        
    Returns:
        bool: 是否成功添加
    """
    from core.print import print_info, print_error
    try:
        mps_count=0
        if DEBUG:
            # DB.delete_article(art)
            pass
        # 计算最终的文章ID（与DB.add_article中的逻辑保持一致）
        article_id = art.get('id', 'unknown')
        if article_id and art.get('mp_id'):
            article_id = f"{str(art.get('mp_id'))}-{article_id}".replace("MP_WXS_","")
        
        if DB.add_article(art,check_exist=check_exist):
            mps_count=mps_count+1
            print_info(f"成功添加文章: {art.get('title', '未知标题')} (ID: {article_id})")
            
            # 如果文章有内容且AI简报功能启用，立即触发简报生成
            _trigger_brief_generation_if_needed(art, article_id)
            
            return True
        else:
            print_info(f"文章添加失败或已存在: {art.get('title', '未知标题')} (ID: {art.get('id', 'unknown')})")
            return False
    except Exception as e:
        print_error(f"UpdateArticle 执行失败: {str(e)}")
        import traceback
        print_error(f"错误详情: {traceback.format_exc()}")
        return False

def _trigger_brief_generation_if_needed(art: dict, article_id: str):
    """如果文章有内容且AI简报功能启用，立即触发简报生成"""
    try:
        from core.config import cfg
        from core.queue import TaskQueue
        from jobs.brief import generate_brief_for_article
        
        # 检查功能是否启用
        if not cfg.get('ai.brief_enabled', False):
            return
        
        # 检查是否启用立即生成（新增配置项，默认True）
        if not cfg.get('ai.brief_auto_generate_on_fetch', True):
            return
        
        # 检查文章是否有内容
        content = art.get('content', '')
        if not content or content.strip() == '':
            return
        
        # 异步触发简报生成（使用队列，避免阻塞文章抓取流程）
        def generate_brief_sync():
            """同步版本的简报生成，用于队列"""
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(generate_brief_for_article(article_id))
        
        # 添加到任务队列（异步执行，不阻塞）
        TaskQueue.add_task(generate_brief_sync)
        from core.print import print_info
        print_info(f"已触发文章 {article_id} 的AI简报生成任务")
        
    except Exception as e:
        # 简报生成失败不影响文章添加流程
        from core.print import print_error
        print_error(f"触发AI简报生成失败: {str(e)}")
def Update_Over(data=None):
    print("更新完成")
    pass