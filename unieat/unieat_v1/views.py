# 标准库导入
import os
import requests
from datetime import datetime , timedelta
from random import sample

# Django核心模块导入
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.db.models import Sum, Count, F
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.core.paginator import Paginator

# DRF相关模块导入
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer, CharField
from rest_framework_simplejwt.tokens import RefreshToken

# 项目内部模型导入
from .models import (
    Welcome, Banner, Canteen, Stall, Dish,
    UserProfile, ConsumptionRecord, ConsumptionItem,
    MealExtraRecord
)

# 项目内部序列化器导入
from .serializers import (
    BannerSerializer,
    CanteenSerializer, StallSerializer, DishSerializer,
    StallDetailSerializer, CanteenDetailSerializer,
    UserProfileSerializer,
    ConsumptionRecordSerializer,
    ConsumptionRecordCreateSerializer,
    TopSalesSerializer, ConsumptionSummarySerializer,
    FeedbackSerializer
)

# 项目内部工具导入
from .utils.wechat import jscode2session, WechatAuthError
from decimal import Decimal, ROUND_HALF_UP


# 开屏广告页
def welcome(request):
    # 查出order最大的一张图片，返回给前端
    res=Welcome.objects.all().order_by('-order').first()
    if res and res.img:
        img = request.build_absolute_uri(res.img.url)
    else:
        img = None
    #此处使用的是手动写 JSON 返回
    return JsonResponse({'code':100,'msg':'success','result':img})

# 主页问候语获取
def greeting(request):
    hour = datetime.now().hour
    if 5 <= hour < 11:
        message = "早上好！新的一天开始了~🥰"
    elif 11 <= hour < 12:
        message = "想好中午要吃什么吗？😋"
    elif 12 <= hour < 14:
        message = "中午好！今天想吃些什么？🫦"
    elif 14 <= hour < 17:
        message = "下午好！想要下午茶吗？🥤"
    elif 17 <= hour < 19:
        message = "想好晚餐吃什么了吗？🍴"
    else:
        message = "晚上好！夜宵已经准备好啦！🍲"
    #cd
    return JsonResponse({"message": message})

# 主页轮播图
class BannerUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        image = request.FILES.get('image')
        order = request.data.get('order', 0)
        if not image:
            return Response({"error": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        banner = Banner.objects.create(image=image, order=order)
        serializer = BannerSerializer(banner, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class BannerListView(APIView):
    def get(self, request, format=None):
        banners = Banner.objects.all()[:3]
        serializer = BannerSerializer(banners, many=True, context={'request': request})
        return Response(serializer.data)


# 菜品档口食堂
class CanteenViewSet(viewsets.ModelViewSet):
    queryset = Canteen.objects.all()
    serializer_class = CanteenSerializer
    pagination_class = None  # 禁用分页，返回直接数组

    @action(detail=False, methods=['get'])
    def full_data(self, request):
        """
        获取食堂-档口-菜品完整数据
        参数：
        - id: 指定某个食堂（如 ?id=1）
        - only_open: true 只返回当前营业的档口
        - random_dishes: 随机返回指定数量菜品（如 ?random_dishes=5）
        """
        canteen_id = request.query_params.get('id')
        only_open = request.query_params.get('only_open', 'false').lower() == 'true'
        random_dishes_count = request.query_params.get('random_dishes')

        # 食堂筛选
        queryset = Canteen.objects.all()
        if canteen_id:
            queryset = queryset.filter(id=canteen_id)

        # 如果只要随机菜品
        if random_dishes_count:
            random_dishes_count = int(random_dishes_count)
            
            # 按档口分组收集菜品，确保每个档口最多选一个菜品
            stall_dishes_map = {}
            for canteen in queryset:
                stalls = canteen.stalls.all()
                # 暂时注释掉档口时间限制，允许显示所有档口
                # if only_open:
                #     stalls = [stall for stall in stalls if stall.is_currently_open()]
                for stall in stalls:
                    dishes = list(stall.dishes.all())
                    if dishes:  # 只添加有菜品的档口
                        stall_dishes_map[stall.id] = {
                            'stall_name': stall.name,
                            'canteen_name': stall.canteen.name,
                            'dishes': dishes
                        }

            # 随机选择档口，每个档口最多选一个菜品
            stall_ids = list(stall_dishes_map.keys())
            selected_stalls = sample(stall_ids, min(random_dishes_count, len(stall_ids)))
            
            dishes_sample = []
            for stall_id in selected_stalls:
                stall_info = stall_dishes_map[stall_id]
                # 从该档口中随机选择一个菜品
                selected_dish = sample(stall_info['dishes'], 1)[0]
                dishes_sample.append({
                    'dish': selected_dish,
                    'stall_name': stall_info['stall_name'],
                    'canteen_name': stall_info['canteen_name']
                })

            dishes_data = [
                {
                    "id": dish['dish'].id,
                    "name": dish['dish'].name,
                    "price": str(dish['dish'].price),
                    "tags": dish['dish'].tags,
                    "image": request.build_absolute_uri(dish['dish'].image.url) if dish['dish'].image else None,
                    "stall": dish['stall_name'],
                    "canteen": dish['canteen_name']
                }
                for dish in dishes_sample
            ]
            return Response({
                "status": "success",
                "count": len(dishes_data),
                "data": dishes_data
            })

        # 否则返回完整层级数据
        serializer = CanteenSerializer(queryset, many=True)
        return Response({
            "status": "success",
            "count": queryset.count(),
            "data": serializer.data
        })


class StallViewSet(viewsets.ModelViewSet):
    queryset = Stall.objects.all()
    serializer_class = StallSerializer
    pagination_class = None  # 禁用分页，返回直接数组

    def list(self, request, *args, **kwargs):
        canteen_id = request.query_params.get("canteen_id")
        floor = request.query_params.get("floor")

        qs = self.queryset
        if canteen_id:
            qs = qs.filter(canteen_id=canteen_id)
        if floor:
            qs = qs.filter(floor=floor)

        data = []
        for stall in qs:
            dishes = stall.dishes.all()
            avg_price = (
                sum([float(d.price) for d in dishes]) / len(dishes)
                if dishes else 0.0
            )
            
            # 使用 request.build_absolute_uri() 生成完整的图片URL
            stall_image = ""
            if stall.image:
                stall_image = request.build_absolute_uri(stall.image.url)
            
            canteen_image = ""
            if stall.canteen.image:
                canteen_image = request.build_absolute_uri(stall.canteen.image.url)
            
            data.append({
                "id": stall.id,
                "name": stall.name,
                "floor": stall.floor,
                "image": stall_image,
                "avg_price": "%.2f" % avg_price,
                "type": stall.type,  # 添加档口类型
                "dishes": list(dishes.values('id', 'name', 'price', 'tags', 'type')),  # 添加菜品列表
                "canteen": {
                    "id": stall.canteen.id,
                    "name": stall.canteen.name,
                    "image": canteen_image
                }
            })

        return Response(data)


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    pagination_class = None  # 禁用分页，返回直接数组

    def get_queryset(self):
        queryset = super().get_queryset()
        # ✅ 在 stallDetail 页面时，不返回 custom 菜品
        if self.action == "list" and self.request.query_params.get("context") == "stall":
            queryset = queryset.filter(type="normal")
        return queryset


class DishDetailAPIView(RetrieveAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer

class StallDetailAPIView(RetrieveAPIView):
    queryset = Stall.objects.all()
    serializer_class = StallDetailSerializer

class CanteenDetailAPIView(RetrieveAPIView):
    queryset = Canteen.objects.all()
    serializer_class = CanteenDetailSerializer
    lookup_field = 'id'



# 用户登录
class LoginRequestSerializer(Serializer):
    code = CharField(required=True, allow_blank=False)

class WechatLoginView(APIView):
    """
    POST /api/user/login/
    body: { "code": "<wx.login返回的code>" }
    resp: { access, refresh, is_new, user: { id, openid } }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = LoginRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        code = ser.validated_data["code"]

        try:
            wx = jscode2session(code)
        except WechatAuthError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        openid = wx["openid"]
        session_key = wx["session_key"]

        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().filter(openid=openid).first()
            is_new = False

            if profile is None:
                # 创建对应的 Django User（用户名用 openid，设置不可用密码）
                user = User.objects.create_user(username=f"wx_{openid}")
                user.set_unusable_password()
                user.save()

                profile = UserProfile.objects.create(
                    user=user, openid=openid, session_key=session_key
                )
                is_new = True
            else:
                # 老用户，更新 session_key
                profile.session_key = session_key
                profile.save(update_fields=["session_key", "updated_at"])
                user = profile.user

        # 颁发 JWT
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        data = {
            "access": str(access),
            "refresh": str(refresh),
            "is_new": is_new,
            "user": {
                "id": user.id,
                "openid": profile.openid,
            },
        }
        return Response(data, status=status.HTTP_200_OK)


# 鉴权自测：拿access调这个接口验证token是否生效
class MeView(APIView):
    """
    GET /api/user/me/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        profile = getattr(u, "profile", None)
        return Response({
            "id": u.id,
            "username": u.username,
            "openid": getattr(profile, "openid", ""),
        })

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return Response({"detail": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return Response({"detail": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

        nickname = request.data.get("nickname", profile.nickname)
        avatar_url = request.data.get("avatar_url")
        budget = request.data.get("budget", profile.budget)

        profile.nickname = nickname
        profile.budget = budget

        # ✅ 如果传了微信头像 URL，下载并保存到 MEDIA_ROOT
        if avatar_url:
            try:
                r = requests.get(avatar_url, stream=True, timeout=5)
                if r.status_code == 200:
                    ext = avatar_url.split(".")[-1].split("?")[0]
                    filename = f"user_{profile.user.id}.{ext}"
                    save_dir = os.path.join(settings.MEDIA_ROOT, "user_avatars")
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, filename)

                    # 删除旧头像
                    if profile.avatar and os.path.exists(profile.avatar.path):
                        os.remove(profile.avatar.path)

                    with open(save_path, "wb") as f:
                        for chunk in r.iter_content(1024):
                            f.write(chunk)

                    profile.avatar.name = f"user_avatars/{filename}"
            except Exception as e:
                print("下载头像失败:", e)

        profile.save()
        serializer = UserProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        return self.post(request)






class IsOwnerOnly(permissions.BasePermission):
    """仅允许访问自己的消费记录"""
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id

class ConsumptionRecordViewSet(viewsets.ModelViewSet):
    """
    /api/consumptions/
    """
    queryset = ConsumptionRecord.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]

    def get_queryset(self):
        user = self.request.user
        qs = ConsumptionRecord.objects.filter(user=user).select_related("stall", "stall__canteen").prefetch_related("items", "items__dish")

        # 过滤：date_from, date_to, canteen_id, stall_id
        df = self.request.query_params.get("date_from")
        dt = self.request.query_params.get("date_to")
        canteen_id = self.request.query_params.get("canteen_id")
        stall_id = self.request.query_params.get("stall_id")

        if df:
            qs = qs.filter(consumed_at__date__gte=parse_date(df))
        if dt:
            qs = qs.filter(consumed_at__date__lte=parse_date(dt))
        if canteen_id:
            qs = qs.filter(stall__canteen_id=canteen_id)
        if stall_id:
            qs = qs.filter(stall_id=stall_id)

        return qs

    def get_serializer_class(self):
        if self.action in ["create"]:
            return ConsumptionRecordCreateSerializer
        return ConsumptionRecordSerializer

    def perform_create(self, serializer):
        # create() 里已经使用 request.user 并完成了合计；这里留空
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        # 仍然会走 IsOwnerOnly 限制
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def ping(self, request):
        return Response({"ok": True})

# 统计
def q2(value):
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ConsumptionSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        summary = ConsumptionRecord.objects\
            .filter(user=user)\
            .aggregate(
                consumptionToday=Sum('total_amount', 
                                    filter=Q(consumed_at__date=today)),
                consumptionWeek=Sum('total_amount',
                                    filter=Q(consumed_at__week_day__in=range(1, 8))),
                consumptionMonth=Sum('total_amount',
                                     filter=Q(consumed_at__year=today.year, 
                                             consumed_at__month=today.month)),
                totalConsumption=Sum('total_amount')
            )
        
        serializer = ConsumptionSummarySerializer(data={
            'consumptionToday': summary['consumptionToday'] or 0,
            'consumptionWeek': summary['consumptionWeek'] or 0,
            'consumptionMonth': summary['consumptionMonth'] or 0,
            'totalConsumption': summary['totalConsumption'] or 0
        })
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)

class TopSalesView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopSalesSerializer
    pagination_class = None
    
    def get_queryset(self):
        return ConsumptionRecord.objects.values(
            'stall__name'
        ).annotate(
            value=Sum('total_amount')
        ).order_by('-value')[:10].annotate(
            name=F('stall__name')
        )
 
class ConsumptionTrendView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        time_range = request.query_params.get('time_range', 'week')
        
        if time_range == 'week':
            start_date = timezone.now() - timedelta(days=7)
        else:
            start_date = timezone.now() - timedelta(days=30)
            
        trends = ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__gte=start_date
        ).values(
            'stall__name'
        ).annotate(
            value=Count('id')
        ).order_by('-value')[:5]
        
        return Response(trends)
 
# ... existing code ...
class ConsumptionRecordsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsumptionRecordSerializer
    
    def get_queryset(self):
        user = self.request.user
        return ConsumptionRecord.objects.filter(user=user).select_related(
            'stall', 'stall__canteen'
        ).prefetch_related('items', 'extras').annotate(
            stallsName=F('stall__name'),
            canteenInfo=F('stall__canteen__name')
        ).order_by('-consumed_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page_start = int(request.query_params.get('pageStart', 0))
        page_size = int(request.query_params.get('pageSize', 10))
        
        paginator = Paginator(queryset, page_size)
        page = paginator.page(page_start // page_size + 1)
        
        serializer = self.get_serializer(page, many=True)
        
        # 为每个消费记录添加items信息和extras信息
        records_data = serializer.data
        for record_data in records_data:
            record_id = record_data['id']
            # 获取该记录的所有消费明细
            items = ConsumptionItem.objects.filter(record_id=record_id)
            items_data = []
            for item in items:
                item_data = {
                    'id': item.id,
                    'dish_id': item.dish.id if item.dish else None,
                    'name': item.name,
                    'unit_price': item.unit_price,
                    'quantity': item.quantity,
                    'amount': item.amount
                }
                # 如果有关联的菜品，添加菜品信息
                if item.dish:
                    item_data['dish'] = {
                        'id': item.dish.id,
                        'name': item.dish.name,
                        'price': item.dish.price,
                        'image': item.dish.image.url if item.dish.image else None
                    }
                items_data.append(item_data)
            record_data['items'] = items_data
            
            # 获取该记录的所有额外支出
            extras = MealExtraRecord.objects.filter(meal_id=record_id)
            extras_data = []
            for extra in extras:
                extras_data.append({
                    'id': extra.id,
                    'desc': extra.desc,
                    'amount': extra.amount
                })
            record_data['extras'] = extras_data
            
        return Response({
            'total': len(queryset),
            'records': records_data
        })
# ... existing code ...


class ConsumptionRecordsDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    
    def perform_delete(self, order_id, user):
        try:
            # 获取对应的记录
            consumption_record = ConsumptionRecord.objects.get(
                id=order_id
            )
        except ConsumptionRecord.DoesNotExist:
            consumption_record = None
            
        return consumption_record
    
    def delete_objects(self, consumption_record):
        # 执行删除操作
        if consumption_record:
            consumption_record.delete()
            
        return Response(
            {'message': '订单删除成功'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    def handle_delete(self, request, order_id):
        # 执行删除逻辑
        consumption_record = self.perform_delete(order_id, request.user)
        
        if not consumption_record:
            return Response(
                {'error': '订单不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return self.delete_objects(consumption_record)
    
    def get(self, request):
        order_id=int(request.query_params.get('order_id'))
        return self.handle_delete(request, order_id)
    
    def post(self, request):
        order_id=int(request.query_params.get('order_id'))
        return self.handle_delete(request, order_id)

class FeedbackView(APIView):
    """
    用户提交反馈的 API（匿名提交）
    """
    permission_classes = [permissions.AllowAny]  # ✅ 允许匿名访问
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # 保存到数据库
            return Response(
                {"message": "反馈提交成功", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "提交失败", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )










