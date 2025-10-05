# 食蛙 Unieat - 校园食堂管理系统

## 项目简介

食蛙 Unieat 是一个基于 Django 的校园食堂管理系统，为大学生提供食堂信息查询、消费记录管理等功能。

## 功能特性

- 🏫 食堂信息管理
- 🍽️ 档口和菜品展示
- 📊 消费记录统计
- 👤 用户个人信息管理
- 📱 微信小程序集成
- 💰 消费数据分析
- 📸 菜品图片上传
- 🎯 个性化推荐

## 技术栈

- **后端**: Django 5.2.5 + Django REST Framework
- **数据库**: MySQL
- **认证**: JWT (Simple JWT)
- **微信集成**: 微信小程序登录
- **图片处理**: Pillow
- **管理界面**: SimpleUI

## 安装和运行

### 环境要求

- Python 3.8+
- MySQL 5.7+
- pip

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd B_Unieat
```

2. 创建虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

5. 数据库迁移
```bash
cd unieat
python manage.py makemigrations
python manage.py migrate
```

6. 创建超级用户
```bash
python manage.py createsuperuser
```

7. 运行开发服务器
```bash
python manage.py runserver
```

## 项目结构

```
B_Unieat/
├── docs/                    # 项目文档
│   └── HowTo_Settings.md   # 设置说明
├── unieat/                 # Django项目根目录
│   ├── media/              # 媒体文件
│   │   ├── banners/        # 轮播图
│   │   ├── canteen_images/ # 食堂图片
│   │   ├── dish_images/    # 菜品图片
│   │   ├── stall_images/   # 档口图片
│   │   ├── user_avatars/   # 用户头像
│   │   └── welcome/        # 欢迎页图片
│   ├── static/             # 静态文件
│   ├── unieat/             # 项目配置
│   │   ├── __init__.py
│   │   ├── settings.py     # 项目设置
│   │   ├── urls.py         # URL配置
│   │   ├── wsgi.py         # WSGI配置
│   │   └── asgi.py         # ASGI配置
│   └── unieat_v1/          # 主应用
│       ├── models.py       # 数据模型
│       ├── views.py        # 视图函数
│       ├── serializers.py  # 序列化器
│       ├── urls.py         # 应用URL配置
│       ├── admin.py        # 管理后台配置
│       ├── utils/          # 工具模块
│       │   └── wechat.py   # 微信相关工具
│       ├── services.py     # 业务逻辑层
│       ├── exceptions.py   # 自定义异常
│       └── migrations/     # 数据库迁移文件
├── requirements.txt        # 依赖包列表
├── .env.example           # 环境变量模板
├── .gitignore            # Git忽略文件
└── README.md             # 项目说明
```

## API 文档

### 主要接口

#### 用户认证
- `POST /api/user/login/` - 微信登录
- `GET /api/user/me/` - 获取用户信息
- `GET/POST /api/user/profile/` - 用户资料管理

#### 食堂信息
- `GET /api/canteens/` - 获取食堂列表
- `GET /api/canteens/{id}/` - 获取食堂详情
- `GET /api/canteens/full_data/` - 获取完整数据

#### 档口信息
- `GET /api/stalls/` - 获取档口列表
- `GET /api/stalls/{id}/` - 获取档口详情

#### 菜品信息
- `GET /api/dishes/` - 获取菜品列表
- `GET /api/dishes/{id}/` - 获取菜品详情

#### 消费记录
- `GET /api/consumptions/` - 获取消费记录
- `POST /api/consumptions/` - 创建消费记录
- `GET /api/consumption/summary/` - 消费统计
- `GET /api/consumption/records/` - 消费记录列表

#### 其他
- `GET /api/welcome/` - 欢迎页图片
- `GET /api/greeting/` - 问候语
- `GET /api/banners/` - 轮播图
- `POST /api/feedback/` - 用户反馈

详细的 API 文档请参考 [docs/HowTo_Settings.md](docs/HowTo_Settings.md)

## 数据库设计

### 主要模型

- **Canteen**: 食堂信息
- **Stall**: 档口信息
- **Dish**: 菜品信息
- **UserProfile**: 用户资料
- **ConsumptionRecord**: 消费记录
- **ConsumptionItem**: 消费明细
- **Feedback**: 用户反馈

## 配置说明

### 环境变量

创建 `.env` 文件并配置以下变量：

```env
# 数据库配置
DB_NAME=unieat
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306

# 微信配置
WECHAT_APPID=your_wechat_appid
WECHAT_SECRET=your_wechat_secret

# Django配置
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

## 开发指南

### 代码规范

- 使用 Python PEP 8 代码规范
- 函数和类需要添加文档字符串
- 变量命名使用下划线命名法
- 常量使用大写字母

### 提交规范

- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具的变动

## 部署说明

### 生产环境配置

1. 设置 `DEBUG=False`
2. 配置 `ALLOWED_HOSTS`
3. 使用环境变量管理敏感信息
4. 配置静态文件服务
5. 设置数据库连接池

### Docker 部署（可选）

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

如有问题，请通过以下方式联系：
- 提交 Issue
- 发送邮件至 [your-email@example.com]

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 基础功能实现
- 微信登录集成
- 消费记录管理
