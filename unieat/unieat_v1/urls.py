from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    greeting,
    BannerUploadView, BannerListView,
    CanteenViewSet, StallViewSet, DishViewSet,
    DishDetailAPIView, StallDetailAPIView, CanteenDetailAPIView,
    WechatLoginView, MeView,
    UserProfileView,UserMealRecordView,
    ConsumptionRecordViewSet
)

# 用 DRF 的路由器注册 ViewSet
router = DefaultRouter()
router.register(r'canteens', CanteenViewSet)
router.register(r'stalls', StallViewSet)
router.register(r'dishes', DishViewSet)
router.register(r"consumptions", ConsumptionRecordViewSet, basename="consumption")


urlpatterns = [
    path('welcome/', views.welcome, name="welcome"),

    # API 接口
    path('greeting/', greeting, name="greeting"),
    path('banners/upload/', BannerUploadView.as_view(), name='banner-upload'),
    path('banners/', BannerListView.as_view(), name='banner-list'),

    # 通过 router 自动生成的接口
    path('', include(router.urls)),

    # 单个对象详情
    path('dish/<int:pk>/', DishDetailAPIView.as_view(), name='dish-detail'),
    path('stall/<int:pk>/', StallDetailAPIView.as_view(), name='stall-detail'),
    path('canteen/<int:id>/', CanteenDetailAPIView.as_view(), name='canteen-detail'),

    # 用户相关
    path('user/login/', WechatLoginView.as_view(), name='user-login'),
    path('user/me/', MeView.as_view(), name='user-me'),
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),

    # 订餐（fake）
    path("user/meal_records/", UserMealRecordView.as_view(), name="user-meal-records"),
    path("", include(router.urls)),

]
