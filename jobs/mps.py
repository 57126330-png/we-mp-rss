from datetime import datetime
from core.models.article import Article
from .article import UpdateArticle,Update_Over
import core.db as db
from core.wx import WxGather
from core.log import logger
from core.task import TaskScheduler
from core.models.feed import Feed
from core.config import cfg,DEBUG
from core.print import print_info,print_success,print_error
from driver.wx import WX_API
from driver.success import Success
wx_db=db.Db(tag="任务调度")
def fetch_all_article():
    print("开始更新")
    wx=WxGather().Model()
    try:
        # 获取公众号列表
        mps=db.DB.get_all_mps()
        for item in mps:
            try:
                wx.get_Articles(item.faker_id,CallBack=UpdateArticle,Mps_id=item.id,Mps_title=item.mp_name, MaxPage=1)
            except Exception as e:
                print(e)
        print(wx.articles) 
    except Exception as e:
        print(e)         
    finally:
        logger.info(f"所有公众号更新完成,共更新{wx.all_count()}条数据")


def test(info:str):
    print("任务测试成功",info)

from core.models.message_task import MessageTask
# from core.queue import TaskQueue
from .webhook import web_hook
interval=int(cfg.get("interval",60)) # 每隔多少秒执行一次
def do_job(mp=None,task:MessageTask=None):
        # TaskQueue.add_task(test,info=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        # print("执行任务", task.mps_id)
        print("执行任务")
        all_count=0
        wx=WxGather().Model()
        try:
            wx.get_Articles(mp.faker_id,CallBack=UpdateArticle,Mps_id=mp.id,Mps_title=mp.mp_name, MaxPage=1,Over_CallBack=Update_Over,interval=interval)
        except Exception as e:
            print_error(e)
            # raise
        finally:
            count=wx.all_count()
            all_count+=count
            from jobs.webhook import MessageWebHook 
            tms=MessageWebHook(task=task,feed=mp,articles=wx.articles)
            web_hook(tms)
            print_success(f"任务({task.id})[{mp.mp_name}]执行成功,{count}成功条数")

from core.queue import TaskQueue
def add_job(feeds:list[Feed]=None,task:MessageTask=None,isTest=False):
    if isTest:
        TaskQueue.clear_queue()
    for feed in feeds:
        TaskQueue.add_task(do_job,feed,task)
        if isTest:
            print(f"测试任务，{feed.mp_name}，加入队列成功")
            reload_job()
            break
        print(f"{feed.mp_name}，加入队列成功")
    print_success(TaskQueue.get_queue_info())
    pass
import json
def get_feeds(task:MessageTask=None):
    """
    获取任务关联的公众号列表
    
    Args:
        task: MessageTask对象，包含mps_id字段
        
    Returns:
        List[Feed]: 公众号列表，如果查询失败返回空列表
    """
    try:
        if not task or not task.mps_id:
            print_warning("任务没有设置mps_id，返回所有公众号")
            mps = wx_db.get_all_mps()
            return mps if isinstance(mps, list) else []
        
        mps_data = json.loads(task.mps_id)
        ids = ",".join([item["id"] for item in mps_data if item.get("id")])
        
        if not ids:
            print_warning("任务mps_id中没有有效的ID，返回所有公众号")
            mps = wx_db.get_all_mps()
            return mps if isinstance(mps, list) else []
        
        mps = wx_db.get_mps_list(ids)
        # 确保返回的是列表
        if not isinstance(mps, list):
            print_warning(f"get_mps_list返回了非列表类型: {type(mps)}，返回所有公众号")
            mps = wx_db.get_all_mps()
            return mps if isinstance(mps, list) else []
        
        if len(mps) == 0:
            print_warning("根据ID未找到公众号，返回所有公众号")
            mps = wx_db.get_all_mps()
            return mps if isinstance(mps, list) else []
        
        return mps
    except json.JSONDecodeError as e:
        print_error(f"解析任务mps_id JSON失败: {e}")
        # JSON解析失败，返回所有公众号
        mps = wx_db.get_all_mps()
        return mps if isinstance(mps, list) else []
    except Exception as e:
        print_error(f"获取公众号列表失败: {e}")
        import traceback
        print_error(f"错误详情: {traceback.format_exc()}")
        # 出错时返回空列表，避免后续处理出错
        return []
scheduler=TaskScheduler()
def reload_job():
    print_success("重载任务")
    scheduler.clear_all_jobs()
    TaskQueue.clear_queue()
    start_job()

def run(job_id:str=None,isTest=False):
    from .taskmsg import get_message_task
    tasks=get_message_task(job_id)
    if not tasks:
        print("没有任务")
        return None
    for task in tasks:
            #添加测试任务
            from core.print import print_warning
            print_warning(f"{task.name} 添加到队列运行")
            add_job(get_feeds(task),task,isTest=isTest)
            pass
    return tasks
def start_job(job_id:str=None):
    from .taskmsg import get_message_task
    tasks=get_message_task(job_id)
    if not tasks:
        print("没有任务")
        return
    tag="定时采集"
    for task in tasks:
        cron_exp=task.cron_exp
        if not cron_exp:
            print_error(f"任务[{task.id}]没有设置cron表达式")
            continue
      
        job_id=scheduler.add_cron_job(add_job,cron_expr=cron_exp,args=[get_feeds(task),task],job_id=str(task.id),tag="定时采集")
        print(f"已添加任务: {job_id}")
    scheduler.start()
    print("启动任务")
def start_all_task():
      #开启自动同步未同步 文章任务
    from jobs.fetch_no_article import start_sync_content
    start_sync_content()
    start_job()
if __name__ == '__main__':
    # do_job()
    # start_all_task()
    pass