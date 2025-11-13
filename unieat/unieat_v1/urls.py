from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    greeting,
    BannerUploadView, BannerListView,
    CanteenViewSet, StallViewSet, DishViewSet,
    DishDetailAPIView, StallDetailAPIView, CanteenDetailAPIView,
    WechatLoginView, MeView,
    UserProfileView,
    ConsumptionRecordViewSet,
    ConsumptionSummaryView,
    TopSalesView,
    ConsumptionTrendView, ConsumptionTrendCompositionView,
    ConsumptionRecordsView,
    ConsumptionRecordsDeleteView,
    FeedbackView,
    SearchView,
    CheckInView,
    CheckInStatusView,
    AvatarListView, UserAvatarListView, BuyAvatarView, SetCurrentAvatarView,
    RecheckInCardView, UserRecheckInCardView, BuyRecheckInCardView,
    RenameCardView, UserRenameCardView, BuyRenameCardView,
    UseRecheckInCardView, PointsTransactionListView,
    ShareGiftActivityView
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

    # 搜索 - 放在 router 之前，确保优先级
    path("search/", SearchView.as_view(), name="search"),

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

    # 统计
    path('consumption/summary/', ConsumptionSummaryView.as_view(), name='consumption-summary'),
    path('shops/top_sales/', TopSalesView.as_view(), name='top-sales'),
    path('consumption/trend/', ConsumptionTrendView.as_view(), name='consumption-trend'),
    path('consumption/trend/composition/', ConsumptionTrendCompositionView.as_view(), name='consumption-trend-composition'),
    path('consumption/records/', ConsumptionRecordsView.as_view(), name='consumption-records'),
    path('consumption/delete/', ConsumptionRecordsDeleteView.as_view(), name='consumption-records-delete'),

    # 反馈
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    
    # 签到
    path("checkin/", CheckInView.as_view(), name="checkin"),
    path("checkin/status/", CheckInStatusView.as_view(), name="checkin-status"),
    path("checkin/use-recheckin-card/", UseRecheckInCardView.as_view(), name="use-recheckin-card"),
    
    # 积分商城
    path("shop/avatars/", AvatarListView.as_view(), name="shop-avatars"),
    path("shop/buy-avatar/", BuyAvatarView.as_view(), name="buy-avatar"),
    path("shop/recheckin-cards/", RecheckInCardView.as_view(), name="recheckin-cards"),
    path("shop/buy-recheckin-card/", BuyRecheckInCardView.as_view(), name="buy-recheckin-card"),
    path("shop/rename-cards/", RenameCardView.as_view(), name="rename-cards"),
    path("shop/buy-rename-card/", BuyRenameCardView.as_view(), name="buy-rename-card"),
    
    # 用户相关（头像、续签卡、改名卡、积分记录）
    path("user/avatars/", UserAvatarListView.as_view(), name="user-avatars"),
    path("user/avatar/set-current/", SetCurrentAvatarView.as_view(), name="set-current-avatar"),
    path("user/recheckin-cards/", UserRecheckInCardView.as_view(), name="user-recheckin-cards"),
    path("user/rename-cards/", UserRenameCardView.as_view(), name="user-rename-cards"),
    path("user/points/transactions/", PointsTransactionListView.as_view(), name="points-transactions"),

    # 活动
    path("activity/share-gift/", ShareGiftActivityView.as_view(), name="share-gift-activity"),
]
