# UniEat 部署指南

## 概述
本文档详细说明如何将UniEat小程序后端部署到阿里云ECS服务器。

## 服务器环境
- **操作系统**: Alibaba Cloud Linux 3.2104 LTS 64位
- **域名**: unieat.top
- **公网IP**: 8.153.160.186
- **已安装**: Nginx 1.20.1

## 第一阶段：代码准备 ✅

### 1. 环境变量配置
- [x] 创建 `env.example` 环境变量模板
- [x] 创建 `env.production` 生产环境配置
- [x] 配置数据库连接、SECRET_KEY、微信配置等

### 2. 静态文件处理
- [x] 配置 Django 的 `STATIC_ROOT` 和 `STATICFILES_DIRS`
- [x] 处理媒体文件的存储路径
- [x] 添加阿里云OSS配置支持

### 3. 数据库配置
- [x] 生产环境数据库配置
- [x] 创建数据迁移脚本

### 4. 其他配置
- [x] 更新 requirements.txt 添加生产环境依赖
- [x] 创建部署脚本和环境检查脚本
- [x] 修复代码中的硬编码URL
- [x] 配置日志轮转系统

## 第二阶段：服务器部署

### 1. 环境搭建

#### 1.1 更新系统包
```bash
sudo yum update -y
```

#### 1.2 安装Python 3.9+
```bash
sudo yum install -y python39 python39-pip python39-devel
```

#### 1.3 安装MySQL
```bash
sudo yum install -y mysql-server mysql-devel
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

#### 1.4 创建数据库
```bash
mysql -u root -p
CREATE DATABASE unieat_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'unieat_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON unieat_production.* TO 'unieat_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2. 项目部署

#### 2.1 克隆代码
```bash
cd /opt
sudo git clone https://github.com/your-username/unieat.git
sudo chown -R www-data:www-data unieat
```

#### 2.2 创建虚拟环境
```bash
cd /opt/unieat
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.3 配置环境变量
```bash
cp env.production .env
# 编辑 .env 文件，填入实际的配置值
nano .env
```

#### 2.4 数据库迁移
```bash
python manage.py migrate
python deploy/scripts/migrate_data.py check
```

### 3. Web服务器配置

#### 3.1 配置Nginx
```bash
sudo cp deploy/nginx/unieat.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/unieat.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3.2 配置Gunicorn
```bash
sudo cp deploy/gunicorn/gunicorn.conf.py /etc/gunicorn/
sudo cp deploy/systemd/unieat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable unieat
sudo systemctl start unieat
```

### 4. SSL证书配置

#### 4.1 安装Certbot
```bash
sudo yum install -y certbot python3-certbot-nginx
```

#### 4.2 获取SSL证书
```bash
sudo certbot --nginx -d unieat.top -d www.unieat.top
```

#### 4.3 自动续期
```bash
sudo crontab -e
# 添加以下行
0 12 * * * /usr/bin/certbot renew --quiet
```

## 第三阶段：域名和HTTPS

### 1. 域名解析
确保域名已正确解析到服务器IP：
- A记录: unieat.top → 8.153.160.186
- A记录: www.unieat.top → 8.153.160.186

### 2. 微信小程序配置

#### 2.1 服务器域名白名单
在微信公众平台配置以下域名：
- request合法域名: `https://unieat.top`
- uploadFile合法域名: `https://unieat.top`
- downloadFile合法域名: `https://unieat.top`

#### 2.2 微信登录配置
- 配置AppID和AppSecret
- 设置授权回调域名

## 部署后检查

### 1. 服务状态检查
```bash
sudo systemctl status nginx
sudo systemctl status unieat
sudo systemctl status mysqld
```

### 2. 环境检查
```bash
cd /opt/unieat
source venv/bin/activate
python deploy/scripts/check_env.py
```

### 3. API测试
```bash
curl -I https://unieat.top/api/canteens/
curl -I https://unieat.top/api/stalls/
```

### 4. 日志检查
```bash
unieat-logs app
unieat-logs error
unieat-logs nginx
```

## 维护命令

### 部署更新
```bash
cd /opt/unieat
sudo ./deploy/scripts/deploy.sh
```

### 数据备份
```bash
cd /opt/unieat
source venv/bin/activate
python deploy/scripts/backup_data.py backup
```

### 数据恢复
```bash
cd /opt/unieat
source venv/bin/activate
python deploy/scripts/backup_data.py restore fixtures/backup_20240101_120000.json
```

### 日志管理
```bash
unieat-logs all          # 查看所有日志
unieat-logs app          # 查看应用日志
sudo journalctl -u unieat -f  # 查看系统日志
```

## 故障排除

### 1. 服务无法启动
```bash
sudo systemctl status unieat
sudo journalctl -u unieat -f
```

### 2. 数据库连接失败
```bash
mysql -u root -p
SHOW DATABASES;
```

### 3. 静态文件404
```bash
sudo nginx -t
ls -la /opt/unieat/staticfiles/
```

### 4. SSL证书问题
```bash
sudo certbot certificates
sudo certbot renew --dry-run
```

## 安全建议

1. **防火墙配置**
   ```bash
   sudo firewall-cmd --permanent --add-service=http
   sudo firewall-cmd --permanent --add-service=https
   sudo firewall-cmd --permanent --add-service=ssh
   sudo firewall-cmd --reload
   ```

2. **定期备份**
   - 设置自动备份脚本
   - 备份数据库和媒体文件

3. **监控告警**
   - 配置服务监控
   - 设置磁盘空间告警

## 联系信息

如有问题，请联系：
- 项目维护者: [你的姓名]
- 邮箱: [你的邮箱]
- 文档更新时间: 2024年1月
