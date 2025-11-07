from sqlalchemy import create_engine, Engine,Text,event
from sqlalchemy.orm import sessionmaker, declarative_base,scoped_session, Session
from sqlalchemy import Column, Integer, String, DateTime
from typing import Optional, List
from contextlib import contextmanager
from .models import Feed, Article
from .config import cfg
from core.models.base import Base  
from core.print import print_warning,print_info,print_error,print_success
# 声明基类
# Base = declarative_base()

class Db:
    connection_str: str=None
    def __init__(self,tag:str="默认",User_In_Thread=True):
        self.Session= None
        self.engine = None
        self.User_In_Thread=User_In_Thread
        self.tag=tag
        print_success(f"[{tag}]连接初始化")
        # 在多进程环境中，延迟连接初始化以避免启动时连接冲突
        import os
        import time
        # 使用进程ID生成延迟，确保每个进程有不同的延迟时间
        # 延迟范围：0-1秒，基于进程ID的哈希值（减少延迟时间）
        process_id = os.getpid()
        delay = (process_id % 10) / 10.0  # 0-1秒的延迟
        if delay > 0:
            time.sleep(delay)
        self.init(cfg.get("db"))
    def get_engine(self) -> Engine:
        """Return the SQLAlchemy engine for this database connection."""
        if self.engine is None:
            raise ValueError("Database connection has not been initialized.")
        return self.engine
    def get_session_factory(self):
        return sessionmaker(bind=self.engine, autoflush=True, expire_on_commit=True, future=True)
    def init(self, con_str: str) -> None:
        """Initialize database connection and create tables"""
        try:
            self.connection_str=con_str
            # 检查SQLite数据库文件是否存在
            if con_str.startswith('sqlite:///'):
                import os
                db_path = con_str[10:]  # 去掉'sqlite:///'前缀
                if not os.path.exists(db_path):
                    try:
                        os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    except Exception as e:
                        pass
                    open(db_path, 'w').close()
            
            # 根据数据库类型配置连接池参数
            # Supabase Free 限制：最大 20 个连接（无 Pooler）
            # 为了安全，我们设置最大连接数为 15（pool_size + max_overflow <= 15）
            is_postgresql = con_str.startswith('postgresql://') or con_str.startswith('postgres://')
            is_supabase = 'supabase.co' in con_str or 'supabase' in con_str.lower()
            
            # 初始化连接参数配置
            connect_args_config = {}
            
            if is_postgresql or is_supabase:
                # Supabase Pooler 有两种模式：
                # 1. Session 模式（端口 5432）：每个应用实例只能使用 pool_size 个连接，不支持 max_overflow
                # 2. Transaction 模式（端口 6543）：支持连接池，可以使用 max_overflow，每个连接只能在一个事务中使用
                # 
                # 代码中已经使用 session_scope 模式，每个事务使用一个连接，符合 Transaction 模式的要求
                # 因此推荐使用 Transaction 模式（端口 6543）以获得更好的连接池支持
                if 'pooler.supabase.com' in con_str:
                    # 检查端口号判断是 Session 模式还是 Transaction 模式
                    if ':6543' in con_str:
                        # Transaction 模式：支持连接池，可以使用 max_overflow
                        pool_size = 5
                        max_overflow = 10  # Transaction 模式支持 overflow
                        print_info(f"[{self.tag}] 检测到 Supabase Pooler Transaction 模式（端口 6543），使用连接池配置: pool_size={pool_size}, max_overflow={max_overflow}")
                    else:
                        # Session 模式（默认端口 5432）：限制严格，不支持 max_overflow
                        pool_size = 3
                        max_overflow = 0  # Session 模式不支持 overflow
                        print_warning(f"[{self.tag}] 检测到 Supabase Pooler Session 模式（端口 5432），连接数限制严格: pool_size={pool_size}, max_overflow={max_overflow}")
                        print_warning(f"[{self.tag}] 建议使用 Transaction 模式（端口 6543）以获得更好的连接池支持")
                else:
                    # 直接连接：使用原始配置
                    pool_size = 5
                    max_overflow = 10
                    print_info(f"[{self.tag}] 检测到 PostgreSQL/Supabase 直接连接，使用连接池配置: pool_size={pool_size}, max_overflow={max_overflow}")
                
                pool_recycle = 300  # PostgreSQL 连接回收时间（5分钟）
                pool_pre_ping = True  # 连接前检查连接是否有效
                # 添加连接参数：设置查询超时和连接超时
                connect_args_config = {
                    "connect_timeout": 30,  # 连接超时30秒
                    "options": "-c statement_timeout=30000"  # 查询超时30秒（PostgreSQL）
                }
            elif con_str.startswith('sqlite:///'):
                # SQLite 配置：不需要连接池
                pool_size = 1
                max_overflow = 0
                pool_recycle = None
                pool_pre_ping = False
                connect_args_config = {"check_same_thread": False}
            else:
                # MySQL 等其他数据库：中等配置
                pool_size = 5
                max_overflow = 10
                pool_recycle = 3600  # 1小时
                pool_pre_ping = True
                connect_args_config = {}
            
            # 准备连接参数
            connect_args = connect_args_config
            
            # 对于PostgreSQL/Supabase，不使用AUTOCOMMIT，使用默认的READ COMMITTED
            # AUTOCOMMIT可能导致事务问题
            isolation_level_config = None if (is_postgresql or is_supabase) else "AUTOCOMMIT"
            
            self.engine = create_engine(con_str,
                                     pool_size=pool_size,          # 最小空闲连接数
                                     max_overflow=max_overflow,      # 允许的最大溢出连接数（总连接数 = pool_size + max_overflow）
                                     pool_timeout=90,      # 获取连接时的超时时间（秒）- 增加到90秒，给多进程启动更多时间
                                     echo=False,
                                     pool_recycle=pool_recycle,  # 连接池回收时间（秒）
                                     pool_pre_ping=pool_pre_ping,  # 连接前检查连接是否有效（防止使用已断开的连接）
                                     isolation_level=isolation_level_config,  # PostgreSQL使用默认隔离级别
                                     connect_args=connect_args
                                     )
            self.session_factory=self.get_session_factory()
        except Exception as e:
            print(f"Error creating database connection: {e}")
            raise
    def create_tables(self):
        """Create all tables defined in models"""
        from core.models.base import Base as B # 导入所有模型
        try:
            B.metadata.create_all(self.engine)
        except Exception as e:
            print_error(f"Error creating tables: {e}")

        print('All Tables Created Successfully!')    
        
    def close(self) -> None:
        """Close the database connection"""
        if self.SESSION:
            self.SESSION.close()
            self.SESSION.remove()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    def delete_article(self,article_data:dict)->bool:
        try:
            art = Article(**article_data)
            if art.id:
               art.id=f"{str(art.mp_id)}-{art.id}".replace("MP_WXS_","")
            session=DB.get_session()
            article = session.query(Article).filter(Article.id == art.id).first()
            if article is not None:
                session.delete(article)
                session.commit()
                return True
        except Exception as e:
            print_error(f"delete article:{str(e)}")
            pass      
        return False
     
    def add_article(self, article_data: dict,check_exist=False) -> bool:
        """添加文章到数据库
        
        Args:
            article_data: 文章数据字典
            check_exist: 是否检查文章是否已存在
            
        Returns:
            bool: 是否成功添加
        """
        try:
            from datetime import datetime
            from core.models.base import DATA_STATUS
            
            # 使用 session_scope 确保连接正确关闭
            with self.session_scope(auto_commit=True) as session:
                art = Article(**article_data)
                if art.id:
                   art.id=f"{str(art.mp_id)}-{art.id}".replace("MP_WXS_","")
                
                if check_exist:
                    # 检查文章是否已存在
                    existing_article = session.query(Article).filter(
                        (Article.url == art.url) | (Article.id == art.id)
                    ).first()
                    if existing_article is not None:
                        print_warning(f"Article already exists: {art.id}")
                        return False
                
                if art.created_at is None:
                    art.created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if art.updated_at is None:
                    art.updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                art.created_at=datetime.strptime(art.created_at ,'%Y-%m-%d %H:%M:%S')
                art.updated_at=datetime.strptime(art.updated_at,'%Y-%m-%d %H:%M:%S')
                art.content=art.content
                art.status=DATA_STATUS.ACTIVE
                session.add(art)
                # commit 会在 session_scope 退出时自动执行
                
        except Exception as e:
            if "UNIQUE" in str(e) or "Duplicate entry" in str(e) or "duplicate key" in str(e).lower():
                print_warning(f"Article already exists: {art.id if 'art' in locals() else 'unknown'}")
            else:
                print_error(f"Failed to add article: {e}")
                import traceback
                print_error(f"Error details: {traceback.format_exc()}")
            return False
        return True    
        
    def get_articles(self, id:str=None, limit:int=30, offset:int=0) -> List[Article]:
        try:
            data = self.get_session().query(Article).limit(limit).offset(offset)
            return data
        except Exception as e:
            print_error(f"Failed to fetch Articles: {e}")
            return []    
             
    def get_all_mps(self) -> List[Feed]:
        """Get all Feed records"""
        try:
            with self.session_scope(auto_commit=False) as session:
                return session.query(Feed).all()
        except Exception as e:
            print_error(f"Failed to fetch all Feeds: {e}")
            import traceback
            print_error(f"Error details: {traceback.format_exc()}")
            return []
            
    def get_mps_list(self, mp_ids:str) -> List[Feed]:
        try:
            if not mp_ids or not mp_ids.strip():
                return []
            ids=mp_ids.split(',')
            # 过滤空字符串
            ids = [id.strip() for id in ids if id.strip()]
            if not ids:
                return []
            with self.session_scope(auto_commit=False) as session:
                data = session.query(Feed).filter(Feed.id.in_(ids)).all()
                return data
        except Exception as e:
            print_error(f"Failed to fetch Feeds by IDs: {e}")
            import traceback
            print_error(f"Error details: {traceback.format_exc()}")
            return []
    def get_mps(self, mp_id:str) -> Optional[Feed]:
        try:
            if not mp_id or not mp_id.strip():
                return None
            with self.session_scope(auto_commit=False) as session:
                data = session.query(Feed).filter_by(id=mp_id).first()
                return data
        except Exception as e:
            print_error(f"Failed to fetch Feed by ID: {e}")
            import traceback
            print_error(f"Error details: {traceback.format_exc()}")
            return None

    def get_faker_id(self, mp_id:str):
        """获取公众号的faker_id"""
        data = self.get_mps(mp_id)
        if data is None:
            print_error(f"未找到ID为 {mp_id} 的公众号")
            return None
        return data.faker_id if hasattr(data, 'faker_id') else None
    def expire_all(self):
        if self.Session:
            self.Session.expire_all()    
    def bind_event(self,session):
        # Session Events
        @event.listens_for(session, 'before_commit')
        def receive_before_commit(session):
            print("Transaction is about to be committed.")

        @event.listens_for(session, 'after_commit')
        def receive_after_commit(session):
            print("Transaction has been committed.")

        # Connection Events
        @event.listens_for(self.engine, 'connect')
        def connect(dbapi_connection, connection_record):
            print("New database connection established.")

        @event.listens_for(self.engine, 'close')
        def close(dbapi_connection, connection_record):
            print("Database connection closed.")
    def get_session(self):
        """获取新的数据库会话
        
        注意：使用 scoped_session 时，需要在请求结束后调用 session.remove() 来清理
        建议在 FastAPI 中使用 session_dependency() 作为依赖注入
        """
        UseInThread=self.User_In_Thread
        def _session():
            if UseInThread:
                self.Session=scoped_session(self.session_factory)
                # self.Session=self.session_factory
            else:
                self.Session=self.session_factory
            # self.bind_event(self.Session)
            return self.Session
        
        
        if self.Session is None:
            _session()
        
        session = self.Session()
        # session.expire_all()
        # session.expire_on_commit = True  # 确保每次提交后对象过期
        # 检查会话是否已经关闭
        if not session.is_active:
            from core.print import print_info
            print_info(f"[{self.tag}] Session is already closed.")
            _session()
            return self.Session()
        # 检查数据库连接是否已断开
        # 注意：由于已经启用了 pool_pre_ping（对于PostgreSQL/Supabase），这个检查可能不再需要
        # 但保留作为备用，只在必要时执行（减少性能开销）
        # 如果 pool_pre_ping 正常工作，这个检查应该很少触发
        # 对于SQLite，pool_pre_ping通常是False，所以需要这个检查
        try:
            # 对于PostgreSQL/Supabase，pool_pre_ping已经处理了连接检查
            # 这里只对SQLite进行额外检查（如果需要的话）
            # 由于pool_pre_ping在init中设置，我们通过检查engine的pool_pre_ping属性来判断
            if hasattr(self.engine, 'pool') and hasattr(self.engine.pool, '_pre_ping'):
                # 如果启用了pre_ping，就不需要额外的检查
                pass
            else:
                # 对于没有pre_ping的情况，执行简单检查
                from core.models import User
                session.query(User.id).limit(1).first()
        except Exception as e:
            # 如果检查失败，可能是连接已断开，尝试重新初始化
            from core.print import print_warning
            print_warning(f"[{self.tag}] Database connection check failed: {e}. This may be normal if pool_pre_ping is enabled.")
            # 不立即重新初始化，让pool_pre_ping处理
        return session
    def auto_refresh(self):
        # 定义一个事件监听器，在对象更新后自动刷新
        def receive_after_update(mapper, connection, target):
            print(f"Refreshing object: {target}")
        from core.models import MessageTask,Article
        event.listen(Article,'after_update', receive_after_update)
        event.listen(MessageTask,'after_update',receive_after_update)
        
    @contextmanager
    def session_scope(self, auto_commit=True):
        """上下文管理器，确保 session 被正确关闭
        
        使用示例:
            # 写入操作（默认自动 commit）
            with DB.session_scope() as session:
                session.add(item)
                # commit 会自动调用
            
            # 只读操作（不需要 commit）
            with DB.session_scope(auto_commit=False) as session:
                items = session.query(Item).all()
        """
        session = self.get_session()
        try:
            yield session
            if auto_commit:
                session.commit()
        except Exception as e:
            if auto_commit:
                session.rollback()
            raise
        finally:
            # 对于 scoped_session，必须调用 remove() 来清理线程本地存储
            if self.User_In_Thread and hasattr(session, 'remove'):
                try:
                    session.remove()
                except Exception as e:
                    print_warning(f"[{self.tag}] Error removing session: {e}")
            elif hasattr(session, 'close'):
                try:
                    session.close()
                except Exception as e:
                    print_warning(f"[{self.tag}] Error closing session: {e}")
    
    def session_dependency(self):
        """FastAPI依赖项，用于请求范围的会话管理
        
        使用示例:
            @router.get("/items")
            async def get_items(db: Session = Depends(DB.session_dependency)):
                # 使用 db 进行数据库操作
                items = db.query(Item).all()
                return items
            # session 会在请求结束后自动清理
        """
        session = self.get_session()
        try:
            yield session
        except Exception as e:
            session.rollback()
            raise
        finally:
            # 对于 scoped_session，必须调用 remove() 来清理线程本地存储
            if self.User_In_Thread and hasattr(session, 'remove'):
                try:
                    session.remove()
                except Exception as e:
                    print_warning(f"[{self.tag}] Error removing session: {e}")
            elif hasattr(session, 'close'):
                try:
                    session.close()
                except Exception as e:
                    print_warning(f"[{self.tag}] Error closing session: {e}")

# 全局数据库实例
DB = Db(User_In_Thread=True)
DB.init(cfg.get("db"))