"""
AI简报生成任务
异步处理文章简报生成
"""
import uuid
from datetime import datetime
from typing import List, Optional
import core.db as db
from core.models.article import Article
from core.models.brief import Brief
from core.models.feed import Feed
from core.ai.brief_generator import BriefGenerator
from core.config import cfg
from core.print import print_info, print_error, print_success, print_warning

DB = db.Db(tag="AI简报生成")

class BriefService:
    """简报服务类"""
    
    def __init__(self):
        self.generator = BriefGenerator()
        self.batch_size = cfg.get('ai.brief_batch_size', 10)
        # 配置默认值应该与config.example.yaml保持一致（False）
        self.enabled = cfg.get('ai.brief_enabled', False)
    
    def _get_article_data(self, article: Article, mp_name: str = None) -> dict:
        """获取文章数据字典"""
        return {
            'id': article.id,
            'title': article.title or '',
            'content': article.content or '',
            'author': mp_name or '未知',
            'mp_name': mp_name or '未知',
            'publish_time': article.publish_time,
            'created_at': article.created_at.isoformat() if article.created_at else None,
            'url': article.url or '',
        }
    
    async def generate_brief_for_article(self, article_key: str) -> Optional[Brief]:
        """
        为单篇文章生成简报
        
        Args:
            article_key: 文章唯一标识（对应Article.id）
            
        Returns:
            Brief对象或None
        """
        if not self.enabled:
            print_warning("AI简报功能已禁用")
            return None
        
        # 第一步：查询文章信息（在session内完成所有数据获取）
        with DB.session_scope(auto_commit=False) as session:
            # 检查简报是否已存在
            existing_brief = session.query(Brief).filter(
                Brief.article_key == article_key
            ).first()
            
            if existing_brief:
                print_info(f"文章 {article_key} 的简报已存在，跳过生成")
                return existing_brief
            
            # 查询文章（article_key就是Article.id）
            article = session.query(Article).filter(Article.id == article_key).first()
            if not article:
                print_error(f"文章不存在: {article_key}")
                return None
            
            # 检查文章是否有内容
            if not article.content or article.content.strip() == '':
                print_warning(f"文章 {article_key} 内容为空，跳过简报生成")
                return None
            
            # 获取公众号名称
            mp_name = '未知'
            if article.mp_id:
                feed = session.query(Feed).filter(Feed.id == article.mp_id).first()
                if feed:
                    mp_name = feed.mp_name or '未知'
            
            # 准备文章数据（在session内获取，避免分离问题）
            article_data = self._get_article_data(article, mp_name)
            # 提前保存文章标题，避免session分离后无法访问
            article_title = article.title[:50] if article.title else '未知'
        
        # 第二步：生成简报（在session外执行，避免长时间占用连接）
        try:
            print_info(f"开始为文章生成简报: {article_title}")
            brief_data = await self.generator.generate(article_data, article_key)
        except Exception as e:
            print_error(f"生成简报失败 (文章: {article_key}): {str(e)}")
            import traceback
            print_error(f"错误详情: {traceback.format_exc()}")
            return None
        
        # 第三步：保存简报（重新获取session用于保存）
        with DB.session_scope(auto_commit=False) as session:
            try:
                # 再次检查简报是否已存在（防止并发创建）
                existing_brief = session.query(Brief).filter(
                    Brief.article_key == article_key
                ).first()
                
                if existing_brief:
                    print_info(f"文章 {article_key} 的简报已存在（并发创建），跳过保存")
                    return existing_brief
                
                # 创建并保存简报
                brief = Brief(
                    id=str(uuid.uuid4()),
                    article_key=article_key,  # article_key就是Article.id
                    model=brief_data['model'],
                    summary=brief_data['summary'],
                    highlights=brief_data['highlights'],
                    version=brief_data['version'],
                    language=brief_data['language'],
                    tags=brief_data['tags'],
                    confidence=brief_data['confidence'],
                    generated_at=brief_data['generated_at'],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(brief)
                session.commit()
                
                print_success(f"简报生成并保存成功: {article_title}")
                return brief
                
            except Exception as e:
                session.rollback()
                print_error(f"保存简报失败 (文章: {article_key}): {str(e)}")
                import traceback
                print_error(f"错误详情: {traceback.format_exc()}")
                return None
    
    async def generate_briefs_for_articles(self, article_keys: List[str], limit: Optional[int] = None) -> dict:
        """
        批量生成简报（支持可控并发）
        
        Args:
            article_keys: 文章唯一标识列表
            limit: 限制处理数量
            
        Returns:
            处理结果统计
        """
        if not self.enabled:
            print_warning("AI简报功能已禁用")
            return {'success': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        
        if limit:
            article_keys = article_keys[:limit]
        
        total = len(article_keys)
        success = 0
        failed = 0
        skipped = 0
        
        # 获取并发控制配置（默认2个并发，避免触发API速率限制）
        max_concurrent = int(cfg.get('ai.brief_max_concurrent', 2))
        print_info(f"开始批量生成简报，共 {total} 篇文章，最大并发数: {max_concurrent}")
        
        # 使用信号量控制并发数量
        import asyncio
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_article(article_key: str, index: int) -> tuple:
            """处理单篇文章（带并发控制）"""
            async with semaphore:  # 获取信号量，控制并发
                try:
                    print_info(f"处理进度: {index}/{total} - 文章ID: {article_key[:50] if article_key else 'unknown'}")
                    brief = await self.generate_brief_for_article(article_key)
                    if brief:
                        return ('success', article_key)
                    else:
                        return ('skipped', article_key)
                except Exception as e:
                    print_error(f"处理文章 {article_key} 时出错: {str(e)}")
                    import traceback
                    print_error(f"错误详情: {traceback.format_exc()}")
                    return ('failed', article_key)
        
        # 并发执行所有任务
        tasks = [
            process_single_article(article_key, i + 1)
            for i, article_key in enumerate(article_keys)
        ]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif isinstance(result, tuple):
                status, _ = result
                if status == 'success':
                    success += 1
                elif status == 'skipped':
                    skipped += 1
                else:
                    failed += 1
        
        result = {
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'total': total
        }
        
        print_info(f"批量生成完成: 成功 {success}, 失败 {failed}, 跳过 {skipped}, 总计 {total}")
        return result
    
    def get_articles_without_brief(self, limit: int = 10) -> List[str]:
        """
        获取没有简报的文章ID列表
        
        Args:
            limit: 限制返回数量
            
        Returns:
            文章ID列表（Article.id列表）
        """
        # 使用session_scope确保连接正确关闭
        with DB.session_scope(auto_commit=False) as session:
            try:
                # 查询有内容但没有简报的文章
                # Article.id == Brief.article_key 是正确的映射关系
                articles = session.query(Article.id).filter(
                    Article.content.isnot(None),
                    Article.content != '',
                    Article.status == 1  # 只处理活跃文章（DATA_STATUS.ACTIVE）
                ).outerjoin(
                    Brief, Article.id == Brief.article_key
                ).filter(
                    Brief.id.is_(None)
                ).limit(limit).all()
                
                article_keys = [article[0] for article in articles]
                return article_keys
                
            except Exception as e:
                print_error(f"查询未生成简报的文章失败: {str(e)}")
                import traceback
                print_error(f"错误详情: {traceback.format_exc()}")
                return []

# 全局服务实例
brief_service = BriefService()

async def generate_brief_for_article(article_key: str) -> Optional[Brief]:
    """为单篇文章生成简报（便捷函数）"""
    return await brief_service.generate_brief_for_article(article_key)

async def generate_briefs_batch(limit: int = 10):
    """批量生成简报（定时任务使用）"""
    article_keys = brief_service.get_articles_without_brief(limit=limit)
    if not article_keys:
        print_info("没有需要生成简报的文章")
        return
    
    result = await brief_service.generate_briefs_for_articles(article_keys)
    return result

def generate_briefs_batch_sync(limit: int = 10):
    """批量生成简报（同步版本，用于定时任务）"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(generate_briefs_batch(limit=limit))

# 定时任务集成
from core.task import TaskScheduler
from core.queue import TaskQueue
from core.config import cfg

# 使用全局调度器（与fetch_no_article.py保持一致的模式）
# 注意：这里不创建新的scheduler，而是使用jobs/mps.py中的全局scheduler
# 或者创建一个独立的scheduler实例，但需要确保不与主调度器冲突

def start_brief_generation_task():
    """启动简报生成定时任务"""
    # 配置默认值应该与config.example.yaml保持一致
    if not cfg.get('ai.brief_enabled', False):
        print_warning("AI简报功能未启用，跳过定时任务")
        return
    
    if not cfg.get('ai.brief_auto_generate', False):
        print_warning("AI简报自动生成功能未启用")
        return
    
    interval = int(cfg.get('ai.brief_generate_interval', 60))  # 默认60分钟
    batch_size = int(cfg.get('ai.brief_batch_size', 10))  # 默认每批10篇
    
    # 生成cron表达式，处理分钟和小时的转换
    if interval < 60:
        # 小于60分钟：每N分钟执行一次
        cron_expr = f"*/{interval} * * * *"
    elif interval == 60:
        # 等于60分钟：每小时的第0分钟执行
        cron_expr = "0 * * * *"
    else:
        # 大于60分钟：转换为小时
        hours = interval // 60
        cron_expr = f"0 */{hours} * * *"
    
    def do_generate():
        """执行简报生成任务"""
        # 使用全局TaskQueue
        TaskQueue.add_task(generate_briefs_batch_sync, limit=batch_size)
    
    # 使用jobs/mps.py中的全局scheduler，避免冲突
    from jobs.mps import scheduler
    
    job_id = scheduler.add_cron_job(
        do_generate,
        cron_expr=cron_expr,
        tag="AI简报生成"
    )
    
    print_success(f"已添加AI简报生成定时任务: {job_id} (每{interval}分钟执行一次，每批{batch_size}篇)")
    # 注意：scheduler.start()已经在start_job()中调用，这里不需要重复启动

