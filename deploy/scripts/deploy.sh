#!/bin/bash
# 部署脚本
# 使用方法: ./deploy.sh

set -e  # 遇到错误立即退出

echo "🚀 开始部署 UniEat 应用..."

# 1. 进入项目目录
cd /path/to/your/unieat/project

# 2. 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 3. 激活虚拟环境
echo "🐍 激活虚拟环境..."
source venv/bin/activate

# 4. 安装依赖
echo "📦 安装依赖包..."
pip install -r requirements.txt

# 5. 数据库迁移
echo "🗄️ 执行数据库迁移..."
python manage.py migrate

# 6. 收集静态文件
echo "📁 收集静态文件..."
python manage.py collectstatic --noinput

# 7. 检查环境配置
echo "🔍 检查环境配置..."
python deploy/scripts/check_env.py

# 8. 重启服务
echo "🔄 重启服务..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 9. 检查服务状态
echo "✅ 检查服务状态..."
sudo systemctl status gunicorn --no-pager -l
sudo systemctl status nginx --no-pager -l

echo "🎉 部署完成！"
echo "🌐 访问地址: https://unieat.top"
