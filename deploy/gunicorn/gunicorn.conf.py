# Gunicorn配置文件
# 使用方法: gunicorn --config deploy/gunicorn/gunicorn.conf.py unieat.wsgi:application

# 服务器socket
bind = "127.0.0.1:8000"

# 工作进程数量 (CPU核心数 * 2 + 1)
workers = 3

# 工作进程类型
worker_class = "sync"

# 工作进程超时时间 (秒)
timeout = 30

# 保持连接时间 (秒)
keepalive = 2

# 最大请求数 (防止内存泄漏)
max_requests = 1000
max_requests_jitter = 50

# 预加载应用 (节省内存)
preload_app = True

# 进程名称
proc_name = "unieat"

# 用户和组 (生产环境建议)
# user = "www-data"
# group = "www-data"

# 日志配置
accesslog = "/var/log/gunicorn/unieat_access.log"
errorlog = "/var/log/gunicorn/unieat_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程ID文件
pidfile = "/var/run/gunicorn/unieat.pid"

# 守护进程模式 (生产环境)
daemon = False

# 重载配置
reload = False

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
