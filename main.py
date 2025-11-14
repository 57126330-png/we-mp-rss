import uvicorn
import os
from core.config import cfg
from core.print import print_warning, print_info
import threading
if __name__ == '__main__':
    # 支持环境变量控制初始化（向后兼容，不影响原有逻辑）
    should_init = cfg.args.init == "True" or os.getenv("INIT_DB", "").lower() == "true"
    if should_init:
        import init_sys as init
        init.init()
    
    # 保持原有逻辑：命令行参数 AND 配置文件（向后兼容）
    # 同时支持环境变量作为额外选项（新增功能）
    # 原有逻辑：cfg.args.job == "True" and cfg.get("server.enable_job", False)
    # 新增：如果设置了环境变量ENABLE_JOB，也可以启用（不影响原有逻辑）
    enable_job_by_env = os.getenv("ENABLE_JOB", "").lower() == "true"
    enable_job_original = cfg.args.job == "True" and cfg.get("server.enable_job", False)
    
    # 如果环境变量设置了，或者原有逻辑满足，则启用定时任务
    if enable_job_by_env or enable_job_original:
        from jobs import start_all_task
        print_info("定时任务已启用")
        threading.Thread(target=start_all_task, daemon=False).start()
    else:
        print_warning("未开启定时任务")
    
    print("启动服务器")
    AutoReload=cfg.get("server.auto_reload",False)
    thread=cfg.get("server.threads",1)
    uvicorn.run("web:app", host="0.0.0.0", port=int(cfg.get("port",8001)),
            reload=AutoReload,
            reload_dirs=['core','web_ui'],
            reload_excludes=['static','web_ui','data'], 
            workers=thread,
            )
    pass