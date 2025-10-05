#!/bin/bash
# 日志系统设置脚本
# 使用方法: sudo ./setup_logging.sh

set -e

echo "🔧 设置日志系统..."

# 1. 创建日志目录
echo "📁 创建日志目录..."
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/log/nginx
sudo mkdir -p /var/run/gunicorn

# 2. 设置目录权限
echo "🔐 设置目录权限..."
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/log/nginx
sudo chown -R www-data:www-data /var/run/gunicorn

# 3. 复制logrotate配置
echo "📋 配置日志轮转..."
sudo cp deploy/logrotate/unieat /etc/logrotate.d/unieat

# 4. 测试logrotate配置
echo "🧪 测试logrotate配置..."
sudo logrotate -d /etc/logrotate.d/unieat

# 5. 创建日志监控脚本
echo "📊 创建日志监控脚本..."
sudo tee /usr/local/bin/unieat-logs > /dev/null << 'EOF'
#!/bin/bash
# UniEat日志查看工具

case "$1" in
    "app")
        tail -f /path/to/your/unieat/project/logs/django.log
        ;;
    "error")
        tail -f /path/to/your/unieat/project/logs/error.log
        ;;
    "nginx")
        tail -f /var/log/nginx/unieat_access.log
        ;;
    "gunicorn")
        tail -f /var/log/gunicorn/unieat_access.log
        ;;
    "all")
        tail -f /path/to/your/unieat/project/logs/django.log \
               /path/to/your/unieat/project/logs/error.log \
               /var/log/nginx/unieat_access.log \
               /var/log/gunicorn/unieat_access.log
        ;;
    *)
        echo "使用方法: unieat-logs {app|error|nginx|gunicorn|all}"
        echo "  app      - 应用日志"
        echo "  error    - 错误日志"
        echo "  nginx    - Nginx访问日志"
        echo "  gunicorn - Gunicorn日志"
        echo "  all      - 所有日志"
        ;;
esac
EOF

sudo chmod +x /usr/local/bin/unieat-logs

# 6. 设置定时任务检查日志
echo "⏰ 设置定时任务..."
sudo tee /etc/cron.d/unieat-log-cleanup > /dev/null << 'EOF'
# UniEat日志清理任务
# 每天凌晨2点清理30天前的日志
0 2 * * * root find /path/to/your/unieat/project/logs -name "*.log.*" -mtime +30 -delete
EOF

echo "✅ 日志系统设置完成！"
echo ""
echo "📋 可用命令："
echo "  unieat-logs app      - 查看应用日志"
echo "  unieat-logs error    - 查看错误日志"
echo "  unieat-logs nginx    - 查看Nginx日志"
echo "  unieat-logs gunicorn - 查看Gunicorn日志"
echo "  unieat-logs all      - 查看所有日志"
echo ""
echo "📊 日志文件位置："
echo "  应用日志: /path/to/your/unieat/project/logs/"
echo "  Nginx日志: /var/log/nginx/unieat_*.log"
echo "  Gunicorn日志: /var/log/gunicorn/*.log"
