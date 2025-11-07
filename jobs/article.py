
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
        if DB.add_article(art,check_exist=check_exist):
            mps_count=mps_count+1
            print_info(f"成功添加文章: {art.get('title', '未知标题')} (ID: {art.get('id', 'unknown')})")
            return True
        else:
            print_info(f"文章添加失败或已存在: {art.get('title', '未知标题')} (ID: {art.get('id', 'unknown')})")
            return False
    except Exception as e:
        print_error(f"UpdateArticle 执行失败: {str(e)}")
        import traceback
        print_error(f"错误详情: {traceback.format_exc()}")
        return False
def Update_Over(data=None):
    print("更新完成")
    pass