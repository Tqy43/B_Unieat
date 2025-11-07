#!/bin/bash

echo "===================================="
echo "  UniEat Docker开发环境启动脚本"
echo "===================================="
echo ""

echo "[1/3] 检查Docker是否运行..."
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi
echo "✅ Docker正在运行"

echo ""
echo "[2/3] 启动开发环境..."
docker-compose -f docker-compose.dev.yml up -d

if [ $? -ne 0 ]; then
    echo "❌ 启动失败"
    exit 1
fi

echo ""
echo "[3/3] 等待服务启动..."
sleep 5

echo ""
echo "===================================="
echo "  ✅ 开发环境启动成功！"
echo "===================================="
echo ""
echo "📍 访问地址:"
echo "   - API: http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin"
echo ""
echo "📝 查看日志: docker-compose -f docker-compose.dev.yml logs -f web"
echo "🛑 停止服务: docker-compose -f docker-compose.dev.yml stop"
echo ""

