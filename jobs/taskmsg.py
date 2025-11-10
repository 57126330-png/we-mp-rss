from typing import Union
from core.db import Db
from core.config import cfg
from core.models import MessageTask
DB = Db()
DB.init(cfg.get("db"))
def get_message_task(job_id:Union[str, list]=None) -> list[MessageTask]:

    """
    获取消息任务详情
    
    参数:
        job_id: 单个消息任务ID或ID列表
        
    返回:
        包含消息任务详情的列表，或空列表如果任务不存在
    """
    try:
        # 使用 session_scope 确保连接正确关闭
        with DB.session_scope(auto_commit=False) as session:
            query=session.query(MessageTask).filter(MessageTask.status==1)
            if job_id:
                if isinstance(job_id, list):
                    query=query.filter(MessageTask.id.in_(job_id))
                else:
                    query=query.filter(MessageTask.id==job_id)
            message_task = query.all()
            if not message_task:
                return None
            
            # 在session关闭前，确保所有需要的属性都被加载
            # 将对象从session中分离，使其可以在session关闭后继续使用
            result = []
            for task in message_task:
                # 访问所有可能被使用的属性，确保它们被加载
                _ = task.id
                _ = task.name
                _ = task.cron_exp
                _ = task.mps_id
                _ = task.tag_ids
                _ = task.status
                _ = task.message_template
                _ = task.web_hook_url
                _ = task.message_type
                # 将对象从session中分离
                session.expunge(task)
                result.append(task)
            
            return result
    except Exception as e:
        from core.print import print_error
        print_error(f"获取消息任务失败: {e}")
    return None