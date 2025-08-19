#%% md
## FBV（Function-Based View）
```
def welcome(request):
    ...
```
- 本质：普通的 Python 函数，接收一个 request 对象，返回一个 HttpResponse 或 JsonResponse。
- 优点：简单直观，上手快，写小型接口、一次性逻辑非常方便。
- 缺点：如果逻辑复杂（比如 GET、POST、PUT 分别处理不同代码），需要自己写 if request.method == 'GET': ...，会越来越臃肿。

## CBV（Class-Based View）
把视图写成一个类，继承 Django 提供的视图基类，比如：
```python
from django.views import View
from django.http import JsonResponse
from .models import Welcome

class WelcomeView(View):
    def get(self, request):
        res = Welcome.objects.all().order_by('-order').first()
        img = 'http://127.0.0.1:8000/media/' + str(res.img)
        return JsonResponse({'code': 100, 'msg': 'success', 'result': img})
```
在 urls.py 里：

```python
from .views import WelcomeView

urlpatterns = [
    path('welcome/', WelcomeView.as_view()),
]
```
- 本质：用类封装 HTTP 请求处理逻辑，按 HTTP 方法拆成不同方法（get()、post()、put()...）。
- 优点：
    - 结构清晰：不同请求方法分开写，互不干扰；
    - 可扩展性强：方便继承、复用代码，适合大项目；
    - 可用混入类（Mixin） 添加通用功能（比如权限、分页）。

- 缺点：
    - 上手稍微比 FBV 难一点；
    - 初学者调试可能没 FBV 直观。

#%% md
## Django REST Framework（DRF）是什么？

DRF 是 Django 的一个第三方库，专门用来快速开发 Web API（也就是给前端、小程序、移动端等提供数据接口）的工具包。
它封装了很多复杂的接口设计细节，让你用更少代码实现：
- JSON 格式的自动序列化（模型转成 JSON）
- 反序列化（JSON 转模型）
- 认证、权限控制
- 请求解析（支持文件上传、多种格式）
- 分页、过滤等功能

简单说，就是让你写接口更快**更方便**，代码**更简洁**。

## serializers.py 是什么？

在 DRF 里，serializer（序列化器）的作用是定义模型对象和 JSON 数据之间的转换规则。
比如BannerSerializer 就是一个把 Django 模型 Banner 转成 JSON（给前端用）和把上传来的 JSON 数据转成模型对象的“桥梁”。
serializers.py 只是放 serializer 类的常规文件名，和 Django 里的 models.py 类似，你可以理解为 **“存放数据转换类”** 的地方。

## 开始使用
安装 DRF：
```
pip install djangorestframework
```
在你的 Django 项目 settings.py 里的 INSTALLED_APPS 添加：
```python
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'your_app_name',  # 你的 app 名字，比如 myapp 或 unieat_v1
]
```
在你的 app 目录下，新建一个 serializers.py 文件，内容写 BannerSerializer。
目录结构示例：
```
your_project/
├── your_app/            <--- 你的 app，比如 unieat_v1
│   ├── serializers.py   <--- 你新建这个文件
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
```
#%% md
# 前后端流程总结
## 1. 功能规划与设计阶段
- 明确功能需求：比如“获取时间接口”等。
- 划分功能模块：前端需要哪些展示、交互；后端需要哪些数据接口、存储结构。
- 接口设计（API 设计）：定义前后端交互数据格式、请求方式、URL 路径。

## 2. 后端开发流程
### 2.1 设计数据库模型（Model）
- 先设计好业务相关的数据库结构（模型）
- 在 models.py 定义模型类。

### 2.2 迁移数据库
```
python manage.py makemigrations app_name
python manage.py migrate
```
- 确保数据库表创建成功。
- 一定要记得在admin.py里注册！

### 2.3 开发接口（View）
- 编写处理业务逻辑的视图函数或基于 DRF 的 API 视图。
- 实现数据的增删改查逻辑。
- 使用 Serializer（如果用 DRF）定义数据序列化规则。

### 2.4 配置路由（URL）
- 在 app 目录下的 urls.py 定义接口路由。
- 在项目根 urls.py 中包含 app 路由。

### 2.5 配置媒体文件访问
- 设置 MEDIA_ROOT 和 MEDIA_URL
- 在开发时配置路由提供媒体文件访问（django.views.static.serve）
- 生产环境配置专用静态文件服务器或 CDN

## 3. 前端开发流程（微信小程序）
### 3.1 UI 设计与静态布局
- 先写 WXML + WXSS 设计静态页面结构和样式（布局、颜色、动画等）
- 实现页面骨架，保证页面视觉效果

### 3.2 逻辑实现
- 在 JS 里写数据绑定和交互逻辑
- 写请求后端 API 的代码（wx.request / wx.uploadFile 等）
- 实现数据获取、展示和事件响应

### 3.3 调试联调
本机调试时，前端请求地址写 http://127.0.0.1:8000/unieat/...
通过微信开发者工具调试前端请求和接口响应
确保数据能正常交互，接口能返回预期数据

## 4. 前后端联调要点
- 先后端接口上线，确保接口可用并可访问。可以先用 Postman、curl 或浏览器测试接口。
- 前端请求接口时，确认请求地址正确（含项目路由前缀），确保前端和后端 URL 保持一致。
- 开发环境解决跨域问题：
    - 微信小程序开发者工具可关闭域名校验
    - 后端允许跨域（CORS）或调试环境用本机 IP

5. 迭代更新
- 功能开发完成后，写好测试用例测试接口和前端展示
- 根据需求调整数据结构和接口，重复迁移数据库与代码更新
- 前端同步更新页面逻辑和样式
- 多次联调确认无误后发布上线












