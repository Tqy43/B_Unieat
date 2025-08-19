from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),  # 管理后台
    path('api/', include('unieat_v1.urls')),  # 所有 app 的接口入口
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),  # 媒体文件
]

# 开发模式下，Django 直接服务媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
