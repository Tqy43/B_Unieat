# 标准库导入
import os
import logging
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
from django.db.models import Sum, Count, F, Case, When, Value, IntegerField
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.core.paginator import Paginator

# DRF相关模块导入
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import ValidationError
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
    MealExtraRecord, CheckInRecord,
    Avatar, UserAvatar, RecheckInCard, UserRecheckInCard,
    RenameCard, UserRenameCard, PointsTransaction
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
    FeedbackSerializer,
    CheckInRecordSerializer, CheckInStatusSerializer,
    AvatarSerializer, UserAvatarSerializer, RecheckInCardSerializer,
    UserRecheckInCardSerializer, RenameCardSerializer, UserRenameCardSerializer,
    PointsTransactionSerializer
)

# 项目内部工具导入
from .utils.wechat import (
    jscode2session,
    WechatAuthError,
    msg_sec_check,
    WechatServiceError,
)
from decimal import Decimal, ROUND_HALF_UP


logger = logging.getLogger(__name__)

DEFAULT_FREE_AVATAR_ID = getattr(settings, "DEFAULT_FREE_AVATAR_ID", 9)


def get_default_avatar():
    avatar = Avatar.objects.filter(id=DEFAULT_FREE_AVATAR_ID).first()
    if avatar:
        return avatar
    return Avatar.objects.filter(is_default=True).order_by('id').first()


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
    try:
        # 使用时区感知的时间，转换为中国时区
        from django.utils import timezone
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        if settings.USE_TZ:
            # 使用时区感知的时间，转换为中国时区
            tz = ZoneInfo(settings.TIME_ZONE)
            now = timezone.now().astimezone(tz)
        else:
            # 不使用时区，直接使用本地时间
            now = datetime.now()
        
        hour = now.hour
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
        return JsonResponse({"message": message})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"greeting error: {str(e)}", exc_info=True)
        # 如果时区转换失败，使用简单的本地时间作为后备
        try:
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
            return JsonResponse({"message": message})
        except:
            return JsonResponse({"error": "获取问候语失败"}, status=500)

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
        try:
            banners = Banner.objects.all()[:3]
            serializer = BannerSerializer(banners, many=True, context={'request': request})
            return Response(serializer.data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"BannerListView error: {str(e)}", exc_info=True)
            return Response({"error": "获取轮播图失败"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        try:
            canteen_id = request.query_params.get('id')
            only_open = request.query_params.get('only_open', 'false').lower() == 'true'
            random_dishes_count = request.query_params.get('random_dishes')

            # 食堂筛选
            queryset = Canteen.objects.all()
            # 验证canteen_id是否为有效整数，防止SQL注入
            if canteen_id:
                try:
                    canteen_id = int(canteen_id)
                    queryset = queryset.filter(id=canteen_id)
                except (ValueError, TypeError):
                    return Response({"error": "无效的canteen_id参数"}, status=status.HTTP_400_BAD_REQUEST)

            # 如果只要随机菜品
            if random_dishes_count:
                try:
                    random_dishes_count = int(random_dishes_count)
                    if random_dishes_count < 0:
                        return Response({"error": "random_dishes参数必须大于0"}, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, TypeError):
                    return Response({"error": "无效的random_dishes参数"}, status=status.HTTP_400_BAD_REQUEST)
                
                # 按档口分组收集菜品，确保每个档口最多选一个菜品
                stall_dishes_map = {}
                for canteen in queryset:
                    stalls = canteen.stalls.all()
                    # 暂时注释掉档口时间限制，允许显示所有档口
                    # if only_open:
                    #     stalls = [stall for stall in stalls if stall.is_currently_open()]
                    for stall in stalls:
                        # 过滤掉0元菜品
                        dishes = list(stall.dishes.filter(price__gt=0))
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
            serializer = CanteenSerializer(queryset, many=True, context={'request': request})
            return Response({
                "status": "success",
                "count": queryset.count(),
                "data": serializer.data
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"CanteenViewSet.full_data error: {str(e)}", exc_info=True)
            return Response({"error": "获取食堂数据失败", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StallViewSet(viewsets.ModelViewSet):
    queryset = Stall.objects.all()
    serializer_class = StallSerializer
    pagination_class = None  # 禁用分页，返回直接数组

    def list(self, request, *args, **kwargs):
        try:
            canteen_id = request.query_params.get("canteen_id")
            floor = request.query_params.get("floor")

            qs = self.queryset
            # 验证canteen_id是否为有效整数，防止SQL注入
            if canteen_id:
                try:
                    canteen_id = int(canteen_id)
                    qs = qs.filter(canteen_id=canteen_id)
                except (ValueError, TypeError):
                    return Response({"error": "无效的canteen_id参数"}, status=status.HTTP_400_BAD_REQUEST)
            # 验证floor是否为有效整数或字符串
            if floor:
                try:
                    floor = int(floor)
                    qs = qs.filter(floor=floor)
                except (ValueError, TypeError):
                    # floor也可能是字符串类型，直接过滤（但需要验证长度以防止过长字符串）
                    if len(str(floor)) > 50:
                        return Response({"error": "无效的floor参数"}, status=status.HTTP_400_BAD_REQUEST)
                    qs = qs.filter(floor=floor)

            data = []
            for stall in qs:
                # 过滤掉0元菜品
                dishes = stall.dishes.filter(price__gt=0)
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
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"StallViewSet.list error: {str(e)}", exc_info=True)
            return Response({"error": "获取档口列表失败", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    pagination_class = None  # 禁用分页，返回直接数组

    def get_queryset(self):
        queryset = super().get_queryset()
        # ✅ 过滤掉0元菜品
        queryset = queryset.filter(price__gt=0)
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
                
                # 给新用户添加默认头像
                default_avatar = Avatar.objects.filter(is_default=True).first()
                if default_avatar:
                    UserAvatar.objects.create(
                        user=user,
                        avatar=default_avatar,
                        is_current=True  # 默认头像设为当前使用
                    )
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

        raw_nickname = request.data.get("nickname")
        nickname = raw_nickname if raw_nickname is not None else profile.nickname
        avatar_url = request.data.get("avatar_url")
        budget = request.data.get("budget", profile.budget)

        nickname_changed = False
        if nickname and nickname != profile.nickname:
            nickname = nickname.strip()
            if nickname == profile.nickname:
                nickname_changed = False
            else:
                if not nickname:
                    return Response({"detail": "昵称不能为空"}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    security_resp = msg_sec_check(openid=profile.openid, content=nickname)
                except WechatServiceError as exc:
                    logger.warning("微信昵称内容安全检测失败: %s", exc)
                    return Response({"detail": "昵称校验失败，请稍后再试"}, status=status.HTTP_400_BAD_REQUEST)

                suggest = security_resp.get("result", {}).get("suggest", "pass")
                if suggest != "pass":
                    return Response({"detail": "昵称包含违规内容，请修改后再试"}, status=status.HTTP_400_BAD_REQUEST)

                nickname_changed = True

                # 用户要修改昵称
                # 检查是否是首次改名（nickname为空或等于默认值）
                is_first_rename = not profile.nickname or profile.nickname.strip() == ''

                if not is_first_rename:
                    # 不是首次改名，需要消耗改名卡
                    user_rename_card, created = UserRenameCard.objects.get_or_create(user=request.user)
                    if user_rename_card.quantity < 1:
                        return Response(
                            {"detail": "改名卡数量不足，请先购买改名卡"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # 消耗一张改名卡
                    user_rename_card.quantity -= 1
                    user_rename_card.save()
                    # 记录积分交易
                    PointsTransaction.objects.create(
                        user=request.user,
                        transaction_type='spend',
                        points=0,  # 改名卡已消耗，不扣积分
                        description=f'使用改名卡修改昵称: {profile.nickname} -> {nickname}'
                    )

        if nickname_changed:
            profile.nickname = nickname
        elif raw_nickname is not None and raw_nickname == "":
            profile.nickname = ""
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
        # 验证canteen_id和stall_id，防止SQL注入
        if canteen_id:
            try:
                canteen_id = int(canteen_id)
                qs = qs.filter(stall__canteen_id=canteen_id)
            except (ValueError, TypeError):
                pass  # 忽略无效的canteen_id
        if stall_id:
            try:
                stall_id = int(stall_id)
                qs = qs.filter(stall_id=stall_id)
            except (ValueError, TypeError):
                pass  # 忽略无效的stall_id

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
        # 使用 timezone.now() 获取当前时间（已转换为中国时区）
        # 如果 USE_TZ=True，timezone.now() 会返回 UTC 时间，需要转换为本地时区
        from django.utils import timezone
        from django.conf import settings
        from zoneinfo import ZoneInfo
        
        if settings.USE_TZ:
            # 使用时区感知的时间，转换为中国时区
            tz = ZoneInfo(settings.TIME_ZONE)
            now = timezone.now().astimezone(tz)
        else:
            # 不使用时区，直接使用本地时间
            now = timezone.now()
        
        today = now.date()
        
        # 计算本周的开始日期（周一）
        # weekday() 返回 0=Monday, 1=Tuesday, ..., 6=Sunday
        # 如果今天是周日（weekday=6），应该算作本周的最后一天，本周开始是前6天的周一
        # 如果今天是周一（weekday=0），本周开始就是今天
        days_since_monday = today.weekday()  # 0-6
        week_start = today - timedelta(days=days_since_monday)
        
        # 计算本月的开始日期
        month_start = today.replace(day=1)
        
        # 调试日志 - 先初始化logger
        import logging
        logger = logging.getLogger(__name__)
        
        # 使用__date查询，避免时区转换问题
        # Django的__date查询会自动处理时区，提取日期部分进行比较
        
        # 今日消费 - 使用日期查询
        consumption_today = ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # 本周消费（从本周一到今天）
        consumption_week = ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__date__gte=week_start,
            consumed_at__date__lte=today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # 本月消费（从本月1号到今天）
        consumption_month = ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__date__gte=month_start,
            consumed_at__date__lte=today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # 总消费（所有时间）
        total_consumption = ConsumptionRecord.objects.filter(
            user=user
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # 调试日志
        logger.info(f"消费统计 - 用户: {user.id}, 用户名: {user.username}")
        logger.info(f"当前时间: {now}, 当前日期: {today}")
        logger.info(f"日期范围 - 今日: {today}, 本周开始: {week_start}, 本月开始: {month_start}")
        logger.info(f"消费金额 - 今日: {consumption_today}, 本周: {consumption_week}, 本月: {consumption_month}, 总计: {total_consumption}")
        
        # 验证：检查本周记录数量和详情
        week_records = ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__date__gte=week_start,
            consumed_at__date__lte=today
        ).values('id', 'consumed_at', 'total_amount').order_by('consumed_at')
        
        total_count = ConsumptionRecord.objects.filter(user=user).count()
        week_count = len(week_records)
        
        logger.info(f"记录数量 - 本周: {week_count}, 总计: {total_count}")
        
        # 打印本周每条记录的日期和金额
        for record in week_records:
            consumed_date = record['consumed_at'].date() if hasattr(record['consumed_at'], 'date') else record['consumed_at']
            logger.info(f"  - 记录ID {record['id']}: 日期={consumed_date}, 金额={record['total_amount']}")
        
        # 打印所有记录的日期范围
        all_records = ConsumptionRecord.objects.filter(user=user).values('consumed_at').order_by('consumed_at')
        if all_records:
            first_date = all_records[0]['consumed_at'].date() if hasattr(all_records[0]['consumed_at'], 'date') else all_records[0]['consumed_at']
            last_date = all_records[len(all_records)-1]['consumed_at'].date() if hasattr(all_records[len(all_records)-1]['consumed_at'], 'date') else all_records[len(all_records)-1]['consumed_at']
            logger.info(f"所有记录日期范围: {first_date} 到 {last_date}")
        
        # 如果本周消费等于总消费，但记录数量不同，记录警告
        if consumption_week == total_consumption and week_count < total_count:
            logger.warning(f"警告：周消费等于总消费，但记录数量不同（本周: {week_count}, 总计: {total_count}）")
            logger.warning(f"本周开始日期: {week_start}, 今日: {today}")
            logger.warning(f"这可能表示数据库中的consumed_at日期超出预期范围")
        
        serializer = ConsumptionSummarySerializer(data={
            'consumptionToday': float(consumption_today),
            'consumptionWeek': float(consumption_week),
            'consumptionMonth': float(consumption_month),
            'totalConsumption': float(total_consumption)
        })
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)

class TopSalesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 获取所有用户下单最多的档口（不限制当前用户）
        from django.db.models import Sum
        
        # 首先获取每个档口的总销量
        stall_sales = ConsumptionRecord.objects.values(
            'stall__id'
        ).annotate(
            total_sales=Sum('total_amount')
        ).order_by('-total_sales')[:10]
        
        # 对于每个档口，找到在该档口消费最多的用户
        result = []
        for stall_sale in stall_sales:
            stall_id = stall_sale['stall__id']
            
            # 获取该档口消费最多的用户
            top_user = ConsumptionRecord.objects.filter(
                stall_id=stall_id
            ).values(
                'user__id'
            ).annotate(
                user_total=Sum('total_amount')
            ).order_by('-user_total').first()
            
            # 获取档口信息
            from .models import Stall
            try:
                stall = Stall.objects.select_related('canteen').get(id=stall_id)
            except Stall.DoesNotExist:
                continue
            
            # 构建结果数据
            result_item = {
                'stall__id': stall.id,
                'stall__name': stall.name,
                'stall__image': stall.image.name if stall.image else None,
                'value': stall_sale['total_sales'],
                'top_user__id': top_user['user__id'] if top_user else None,
                'top_user__username': None,
                'top_user__profile__nickname': None,
            }
            
            # 获取用户信息
            import logging
            logger = logging.getLogger(__name__)
            
            if top_user and top_user.get('user__id'):
                from django.contrib.auth.models import User
                from .models import UserProfile
                try:
                    user_id = top_user['user__id']
                    # 强制从数据库重新获取最新数据，不使用缓存
                    user = User.objects.select_related('profile').get(id=user_id)
                    # 强制从数据库重新获取profile数据，不使用任何缓存
                    try:
                        # 直接从数据库查询，不使用select_related缓存
                        profile = UserProfile.objects.filter(user_id=user_id).first()
                        if profile:
                            # 强制刷新，清除Django的实例缓存，确保获取最新数据
                            profile.refresh_from_db()
                            nickname = profile.nickname
                            logger.info(f"档口 {stall.name} - 用户 {user.id} 从数据库获取昵称: '{nickname}' (类型: {type(nickname)}, 长度: {len(nickname) if nickname else 0})")
                        else:
                            nickname = None
                            logger.warning(f"档口 {stall.name} - 用户 {user.id} profile查询返回None")
                    except UserProfile.DoesNotExist:
                        nickname = None
                        logger.warning(f"档口 {stall.name} - 用户 {user.id} 没有profile")
                    except Exception as e:
                        nickname = None
                        logger.error(f"档口 {stall.name} - 获取用户profile失败: {e}", exc_info=True)
                    
                    result_item['top_user__id'] = user_id
                    result_item['top_user__username'] = user.username
                    
                    # 如果昵称为空或只有空格，使用默认名称
                    if nickname and nickname.strip():
                        result_item['top_user__profile__nickname'] = nickname.strip()
                        logger.info(f"档口 {stall.name} - 最终使用昵称: '{nickname.strip()}'")
                    else:
                        # 如果没有昵称，使用用户名的后4位
                        username = user.username
                        if username.startswith('wx_'):
                            result_item['top_user__profile__nickname'] = '用户' + username[-4:]
                        else:
                            result_item['top_user__profile__nickname'] = username[:10] if len(username) > 10 else username
                        logger.info(f"档口 {stall.name} - 使用默认名称: {result_item['top_user__profile__nickname']}")
                    
                except User.DoesNotExist:
                    logger.error(f"档口 {stall.name} - 用户 {top_user.get('user__id')} 不存在")
                    result_item['top_user__profile__nickname'] = '未知用户'
                except Exception as e:
                    logger.error(f"档口 {stall.name} - 获取用户信息失败: {e}", exc_info=True)
                    result_item['top_user__profile__nickname'] = '未知用户'
            else:
                logger.warning(f"档口 {stall.name} - 没有top_user或user__id为空")
                result_item['top_user__profile__nickname'] = '未知用户'
            
            result.append(result_item)
        
        # 调试：打印原始数据
        logger.info(f"排行榜原始数据（前3条）:")
        for i, item in enumerate(result[:3]):
            logger.info(f"  第{i+1}名: 档口={item.get('stall__name')}, 用户ID={item.get('top_user__id')}, 昵称={item.get('top_user__profile__nickname')}")
        
        # 序列化数据
        serializer = TopSalesSerializer(result, many=True, context={'request': request})
        serialized_data = serializer.data
        
        # 调试：打印序列化后的数据
        logger.info(f"排行榜序列化后数据（前3条）:")
        for i, item in enumerate(serialized_data[:3]):
            logger.info(f"  第{i+1}名: 档口={item.get('name')}, 用户昵称={item.get('user_name')}, 用户头像={item.get('user_avatar')}")
        
        return Response(serialized_data)
 
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
        queryset = ConsumptionRecord.objects.filter(user=user).select_related(
            'stall', 'stall__canteen'
        ).prefetch_related('items', 'extras').annotate(
            stallsName=F('stall__name'),
            canteenInfo=F('stall__canteen__name')
        )
        
        # 处理日期筛选参数
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        # 导入必要的模块
        from datetime import datetime, time as dt_time
        from django.conf import settings
        from zoneinfo import ZoneInfo
        import logging
        logger = logging.getLogger(__name__)
        
        if date_from:
            try:
                # 解析日期字符串 (YYYY-MM-DD)
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                # 使用时区感知的 datetime 进行过滤
                if settings.USE_TZ:
                    tz = ZoneInfo(settings.TIME_ZONE)
                    date_from_datetime = datetime.combine(date_from_obj, dt_time.min).replace(tzinfo=tz)
                else:
                    date_from_datetime = datetime.combine(date_from_obj, dt_time.min)
                
                queryset = queryset.filter(consumed_at__gte=date_from_datetime)
                logger.info(f"消费记录筛选 - date_from: {date_from} -> {date_from_datetime}")
            except (ValueError, TypeError) as e:
                logger.warning(f"无效的 date_from 参数: {date_from}, 错误: {e}")
        
        if date_to:
            try:
                # 解析日期字符串 (YYYY-MM-DD)
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                # 使用时区感知的 datetime 进行过滤
                if settings.USE_TZ:
                    tz = ZoneInfo(settings.TIME_ZONE)
                    date_to_datetime = datetime.combine(date_to_obj, dt_time.max).replace(tzinfo=tz)
                else:
                    date_to_datetime = datetime.combine(date_to_obj, dt_time.max)
                
                queryset = queryset.filter(consumed_at__lte=date_to_datetime)
                logger.info(f"消费记录筛选 - date_to: {date_to} -> {date_to_datetime}")
            except (ValueError, TypeError) as e:
                logger.warning(f"无效的 date_to 参数: {date_to}, 错误: {e}")
        
        return queryset.order_by('-consumed_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # 记录筛选后的数量
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            page_start = int(request.query_params.get('pageStart', 0))
            page_size = int(request.query_params.get('pageSize', 10))
            # 限制page_size的最大值，防止过大的查询
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 10
            if page_start < 0:
                page_start = 0
        except (ValueError, TypeError):
            page_start = 0
            page_size = 10
        
        # 获取筛选后的总数
        total_count = queryset.count()
        logger.info(f"消费记录筛选后总数: {total_count}, pageStart: {page_start}, pageSize: {page_size}")
        logger.info(f"筛选参数: date_from={request.query_params.get('date_from')}, date_to={request.query_params.get('date_to')}")
        
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
            'total': total_count,
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
        try:
            order_id = int(request.query_params.get('order_id'))
            return self.handle_delete(request, order_id)
        except (ValueError, TypeError):
            return Response({"error": "无效的order_id参数"}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            order_id = int(request.query_params.get('order_id'))
            return self.handle_delete(request, order_id)
        except (ValueError, TypeError):
            return Response({"error": "无效的order_id参数"}, status=status.HTTP_400_BAD_REQUEST)

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


class SearchView(APIView):
    """
    搜索 API
    支持搜索菜品、档口、食堂
    参数：
    - q: 搜索关键词
    - type: 搜索类型（dish/stall/canteen/all），默认为 all
    """
    permission_classes = [permissions.AllowAny]  # 允许匿名访问
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'all').lower()
        
        if not query:
            return Response({
                'dishes': [],
                'stalls': [],
                'canteens': [],
                'total': 0
            })
        
        results = {
            'dishes': [],
            'stalls': [],
            'canteens': [],
            'total': 0
        }
        
        # 搜索菜品
        if search_type in ['dish', 'all']:
            dishes = Dish.objects.filter(
                Q(name__icontains=query) | Q(tags__icontains=query),
                price__gt=0
            ).select_related('stall', 'stall__canteen')[:20]
            
            for dish in dishes:
                dish_image = ""
                if dish.image:
                    dish_image = request.build_absolute_uri(dish.image.url)
                
                results['dishes'].append({
                    'id': dish.id,
                    'name': dish.name,
                    'price': str(dish.price),
                    'tags': dish.tags,
                    'image': dish_image,
                    'stall': {
                        'id': dish.stall.id,
                        'name': dish.stall.name,
                        'canteen': dish.stall.canteen.name
                    }
                })
        
        # 搜索档口
        if search_type in ['stall', 'all']:
            stalls = Stall.objects.filter(
                Q(name__icontains=query) | Q(cuisine_type__icontains=query)
            ).select_related('canteen')[:20]
            
            for stall in stalls:
                stall_image = ""
                if stall.image:
                    stall_image = request.build_absolute_uri(stall.image.url)
                
                canteen_image = ""
                if stall.canteen.image:
                    canteen_image = request.build_absolute_uri(stall.canteen.image.url)
                
                # 计算平均价格
                dishes = stall.dishes.filter(price__gt=0)
                avg_price = sum([float(d.price) for d in dishes]) / len(dishes) if dishes else 0.0
                
                results['stalls'].append({
                    'id': stall.id,
                    'name': stall.name,
                    'floor': stall.floor,
                    'cuisine_type': stall.cuisine_type,
                    'image': stall_image,
                    'avg_price': "%.2f" % avg_price,
                    'type': stall.type,
                    'canteen': {
                        'id': stall.canteen.id,
                        'name': stall.canteen.name,
                        'image': canteen_image
                    }
                })
        
        # 搜索食堂
        if search_type in ['canteen', 'all']:
            canteens = Canteen.objects.filter(
                Q(name__icontains=query) | Q(location__icontains=query)
            )[:20]
            
            for canteen in canteens:
                canteen_image = ""
                if canteen.image:
                    canteen_image = request.build_absolute_uri(canteen.image.url)
                
                results['canteens'].append({
                    'id': canteen.id,
                    'name': canteen.name,
                    'location': canteen.location,
                    'image': canteen_image,
                    'stall_count': canteen.stall_count
                })
        
        results['total'] = len(results['dishes']) + len(results['stalls']) + len(results['canteens'])
        
        return Response(results, status=status.HTTP_200_OK)


# =======================
# 签到功能
# =======================
class CheckInView(APIView):
    """
    签到接口
    POST /api/checkin/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def calculate_points(self, consecutive_days):
        """
        根据连续签到天数计算积分
        规则：
        - 签到一次：1积分
        - 连续签到7天及以上：以后每次获得3积分
        - 连续签到20天及以上：以后每次获得5积分
        """
        if consecutive_days >= 20:
            return 5
        elif consecutive_days >= 7:
            return 3
        else:
            return 1
    
    def post(self, request):
        user = request.user
        today = timezone.now().date()
        
        # 检查今天是否已签到
        today_checkin = CheckInRecord.objects.filter(
            user=user,
            checkin_date=today
        ).first()
        
        if today_checkin:
            return Response(
                {"detail": "今天已经签到过了", "already_signed": True},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取昨天的签到记录
        yesterday = today - timedelta(days=1)
        yesterday_checkin = CheckInRecord.objects.filter(
            user=user,
            checkin_date=yesterday
        ).first()
        
        # 计算连续签到天数
        if yesterday_checkin:
            consecutive_days = yesterday_checkin.consecutive_days + 1
        else:
            consecutive_days = 1
        
        # 计算本次获得的积分
        points_earned = self.calculate_points(consecutive_days)
        
        # 创建签到记录
        checkin_record = CheckInRecord.objects.create(
            user=user,
            checkin_date=today,
            consecutive_days=consecutive_days,
            points_earned=points_earned
        )
        
        # 更新用户积分
        profile = getattr(user, "profile", None)
        if profile:
            profile.points = (profile.points or 0) + points_earned
            profile.save(update_fields=["points", "updated_at"])
        
        # 记录积分获得
        PointsTransaction.objects.create(
            user=user,
            transaction_type='earn',
            points=points_earned,
            description=f"每日签到（连续{consecutive_days}天）"
        )
        
        # 序列化返回
        serializer = CheckInRecordSerializer(checkin_record)
        return Response({
            "message": "签到成功",
            "checkin": serializer.data,
            "total_points": profile.points if profile else 0,
            "points_earned": points_earned,
            "consecutive_days": consecutive_days
        }, status=status.HTTP_201_CREATED)


class CheckInStatusView(APIView):
    """
    查询签到状态
    GET /api/checkin/status/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # 检查今天是否已签到
        today_checkin = CheckInRecord.objects.filter(
            user=user,
            checkin_date=today
        ).first()
        
        # 获取用户积分
        profile = getattr(user, "profile", None)
        total_points = profile.points if profile else 0
        
        # 获取最近的签到记录（用于计算连续天数）
        last_checkin = CheckInRecord.objects.filter(
            user=user
        ).order_by('-checkin_date').first()
        
        if today_checkin:
            # 今天已签到
            consecutive_days = today_checkin.consecutive_days
            today_points = today_checkin.points_earned
            last_checkin_date = today_checkin.checkin_date
        elif last_checkin:
            # 今天未签到，但有历史记录
            # 检查昨天是否签到，如果昨天签到，连续天数应该是昨天的+1，否则重置为0
            yesterday = today - timedelta(days=1)
            if last_checkin.checkin_date == yesterday:
                consecutive_days = last_checkin.consecutive_days  # 今天未签到，连续天数保持昨天的值
            else:
                consecutive_days = 0  # 中断了，连续天数为0
            today_points = 0
            last_checkin_date = last_checkin.checkin_date
        else:
            # 从未签到
            consecutive_days = 0
            today_points = 0
            last_checkin_date = None
        
        data = {
            "today_signed": today_checkin is not None,
            "consecutive_days": consecutive_days,
            "total_points": total_points,
            "today_points": today_points if today_checkin else 0,
            "last_checkin_date": last_checkin_date.isoformat() if last_checkin_date else None
        }
        
        serializer = CheckInStatusSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


# =======================
# 积分商城功能
# =======================

class AvatarListView(APIView):
    """
    获取所有可购买的头像
    GET /api/shop/avatars/
    Header: Authorization: Bearer <access> (可选，登录后显示是否已拥有)
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        avatars = (
            Avatar.objects
            .annotate(
                is_free=Case(
                    When(price=0, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
            .order_by('-is_free', '-is_default', 'price', 'id')
        )
        serializer = AvatarSerializer(avatars, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserAvatarListView(APIView):
    """
    获取用户拥有的头像
    GET /api/user/avatars/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        with transaction.atomic():
            default_avatar = get_default_avatar()
            user_avatars_qs = UserAvatar.objects.filter(user=user)
            has_current = user_avatars_qs.filter(is_current=True).exists()

            if default_avatar and not user_avatars_qs.filter(avatar=default_avatar).exists():
                UserAvatar.objects.create(
                    user=user,
                    avatar=default_avatar,
                    is_current=not has_current,
                )
                user_avatars_qs = UserAvatar.objects.filter(user=user)
                has_current = user_avatars_qs.filter(is_current=True).exists()

            if not has_current:
                target_avatar = (
                    user_avatars_qs.filter(avatar=default_avatar).first()
                    if default_avatar else user_avatars_qs.first()
                )
                if target_avatar and not target_avatar.is_current:
                    target_avatar.is_current = True
                    target_avatar.save(update_fields=["is_current"])

        user_avatars = UserAvatar.objects.filter(user=user).select_related('avatar')
        serializer = UserAvatarSerializer(user_avatars, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuyAvatarView(APIView):
    """
    购买头像
    POST /api/shop/buy-avatar/
    Header: Authorization: Bearer <access>
    Body: { "avatar_id": 1 }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        avatar_id = request.data.get('avatar_id')
        if not avatar_id:
            return Response({"detail": "请提供头像ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Response({"detail": "用户资料不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        with transaction.atomic():
            try:
                avatar = Avatar.objects.select_for_update().get(id=avatar_id)
            except Avatar.DoesNotExist:
                return Response({"detail": "头像不存在"}, status=status.HTTP_404_NOT_FOUND)

            profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
            user_avatar = UserAvatar.objects.select_for_update().filter(user=user, avatar=avatar).first()

            # 默认头像走免费逻辑，同时允许用户重新设置为当前头像
            if avatar.id == DEFAULT_FREE_AVATAR_ID or avatar.is_default:
                if not user_avatar:
                    user_avatar = UserAvatar.objects.create(user=user, avatar=avatar, is_current=False)

                if not user_avatar.is_current:
                    UserAvatar.objects.filter(user=user, is_current=True).exclude(id=user_avatar.id).update(is_current=False)
                    user_avatar.is_current = True
                    user_avatar.save(update_fields=["is_current"])

                serializer = UserAvatarSerializer(user_avatar, context={'request': request})
                return Response({
                    "message": "已切换为默认头像",
                    "user_avatar": serializer.data
                }, status=status.HTTP_200_OK)

            if user_avatar:
                return Response({"detail": "您已经拥有此头像"}, status=status.HTTP_400_BAD_REQUEST)

            if not avatar.has_stock():
                return Response({"detail": "该头像已售罄"}, status=status.HTTP_400_BAD_REQUEST)

            if profile.points < avatar.price:
                return Response({"detail": f"积分不足，需要{avatar.price}积分，当前拥有{profile.points}积分"},
                                status=status.HTTP_400_BAD_REQUEST)

            profile.points -= avatar.price
            profile.save(update_fields=["points", "updated_at"])

            user_avatar = UserAvatar.objects.create(user=user, avatar=avatar, is_current=False)
            try:
                avatar.decrease_stock()
            except ValueError:
                raise ValidationError({"detail": "该头像已售罄"})

            PointsTransaction.objects.create(
                user=user,
                transaction_type='spend',
                points=-avatar.price,
                description=f"购买头像：{avatar.name}"
            )

        serializer = UserAvatarSerializer(user_avatar, context={'request': request})
        return Response({
            "message": "购买成功",
            "user_avatar": serializer.data,
            "remaining_points": profile.points
        }, status=status.HTTP_201_CREATED)


class SetCurrentAvatarView(APIView):
    """
    设置当前使用的头像
    POST /api/user/avatar/set-current/
    Header: Authorization: Bearer <access>
    Body: { "avatar_id": 1 }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        avatar_id = request.data.get('avatar_id')
        if not avatar_id:
            return Response({"detail": "请提供头像ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        with transaction.atomic():
            try:
                user_avatar = UserAvatar.objects.select_for_update().get(user=user, avatar_id=avatar_id)
            except UserAvatar.DoesNotExist:
                default_avatar = Avatar.objects.filter(id=avatar_id).first()
                if not default_avatar or (default_avatar.id != DEFAULT_FREE_AVATAR_ID and not default_avatar.is_default):
                    return Response({"detail": "您尚未拥有此头像"}, status=status.HTTP_400_BAD_REQUEST)
                user_avatar = UserAvatar.objects.create(user=user, avatar=default_avatar, is_current=False)

            UserAvatar.objects.filter(user=user, is_current=True).exclude(id=user_avatar.id).update(is_current=False)
            if not user_avatar.is_current:
                user_avatar.is_current = True
                user_avatar.save(update_fields=["is_current"])
        
        serializer = UserAvatarSerializer(user_avatar, context={'request': request})
        return Response({
            "message": "头像设置成功",
            "user_avatar": serializer.data
        }, status=status.HTTP_200_OK)


class RecheckInCardView(APIView):
    """
    获取续签卡信息
    GET /api/shop/recheckin-cards/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        card = RecheckInCard.objects.first()
        if not card:
            # 如果没有，创建一个默认的
            card = RecheckInCard.objects.create()
        serializer = RecheckInCardSerializer(card)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRecheckInCardView(APIView):
    """
    获取用户拥有的续签卡数量
    GET /api/user/recheckin-cards/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user_card, created = UserRecheckInCard.objects.get_or_create(user=user)
        serializer = UserRecheckInCardSerializer(user_card)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuyRecheckInCardView(APIView):
    """
    购买续签卡
    POST /api/shop/buy-recheckin-card/
    Header: Authorization: Bearer <access>
    Body: { "quantity": 1 } (可选，默认1张)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        quantity = request.data.get('quantity', 1)
        if quantity < 1:
            return Response({"detail": "购买数量必须大于0"}, status=status.HTTP_400_BAD_REQUEST)
        
        card = RecheckInCard.objects.first()
        if not card:
            card = RecheckInCard.objects.create()
        
        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Response({"detail": "用户资料不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        total_price = card.price * quantity
        
        # 检查积分是否足够
        if profile.points < total_price:
            return Response({"detail": f"积分不足，需要{total_price}积分，当前拥有{profile.points}积分"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # 扣除积分
        profile.points -= total_price
        profile.save(update_fields=["points", "updated_at"])
        
        # 增加续签卡数量
        user_card, created = UserRecheckInCard.objects.get_or_create(user=user)
        user_card.quantity += quantity
        user_card.save(update_fields=["quantity", "updated_at"])
        
        # 记录积分交易
        PointsTransaction.objects.create(
            user=user,
            transaction_type='spend',
            points=-total_price,
            description=f"购买续签卡 x{quantity}"
        )
        
        return Response({
            "message": "购买成功",
            "quantity": user_card.quantity,
            "remaining_points": profile.points
        }, status=status.HTTP_201_CREATED)


class UseRecheckInCardView(APIView):
    """
    使用续签卡补签
    POST /api/checkin/use-recheckin-card/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # 检查昨天是否已签到
        yesterday_checkin = CheckInRecord.objects.filter(
            user=user,
            checkin_date=yesterday
        ).first()
        
        if yesterday_checkin:
            return Response({"detail": "昨天已经签到过了，无需使用续签卡"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户是否有续签卡
        user_card, created = UserRecheckInCard.objects.get_or_create(user=user)
        if user_card.quantity < 1:
            return Response({"detail": "续签卡数量不足"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取前天的签到记录（用于计算连续天数）
        day_before_yesterday = yesterday - timedelta(days=1)
        day_before_checkin = CheckInRecord.objects.filter(
            user=user,
            checkin_date=day_before_yesterday
        ).first()
        
        # 计算连续签到天数
        if day_before_checkin:
            consecutive_days = day_before_checkin.consecutive_days + 1
        else:
            consecutive_days = 1
        
        # 计算积分（使用连续天数计算）
        checkin_view = CheckInView()
        points_earned = checkin_view.calculate_points(consecutive_days)
        
        # 创建昨天的签到记录
        checkin_record = CheckInRecord.objects.create(
            user=user,
            checkin_date=yesterday,
            consecutive_days=consecutive_days,
            points_earned=points_earned
        )
        
        # 更新用户积分
        profile = getattr(user, "profile", None)
        if profile:
            profile.points = (profile.points or 0) + points_earned
            profile.save(update_fields=["points", "updated_at"])
        
        # 扣除一张续签卡
        user_card.quantity -= 1
        user_card.save(update_fields=["quantity", "updated_at"])
        
        # 记录积分获得
        PointsTransaction.objects.create(
            user=user,
            transaction_type='earn',
            points=points_earned,
            description=f"使用续签卡补签（{yesterday}）"
        )
        
        serializer = CheckInRecordSerializer(checkin_record)
        return Response({
            "message": "补签成功",
            "checkin": serializer.data,
            "total_points": profile.points if profile else 0,
            "points_earned": points_earned,
            "consecutive_days": consecutive_days,
            "remaining_cards": user_card.quantity
        }, status=status.HTTP_201_CREATED)


class RenameCardView(APIView):
    """
    获取改名卡商品信息
    GET /api/shop/rename-cards/
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        card = RenameCard.objects.first()
        if not card:
            # 如果没有，创建一个默认的
            card = RenameCard.objects.create()
        serializer = RenameCardSerializer(card)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRenameCardView(APIView):
    """
    获取用户拥有的改名卡数量
    GET /api/user/rename-cards/
    Header: Authorization: Bearer <access>
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user_card, created = UserRenameCard.objects.get_or_create(user=user)
        serializer = UserRenameCardSerializer(user_card)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuyRenameCardView(APIView):
    """
    购买改名卡
    POST /api/shop/buy-rename-card/
    Header: Authorization: Bearer <access>
    Body: { "quantity": 1 } (可选，默认1张)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        quantity = request.data.get('quantity', 1)
        if quantity < 1:
            return Response({"detail": "购买数量必须大于0"}, status=status.HTTP_400_BAD_REQUEST)
        
        card = RenameCard.objects.first()
        if not card:
            card = RenameCard.objects.create()
        
        if not card.is_available:
            return Response({"detail": "改名卡已下架"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not card.has_stock():
            return Response({"detail": "改名卡库存不足"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        profile = getattr(user, "profile", None)
        if not profile:
            return Response({"detail": "用户资料不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        total_cost = card.price * quantity
        if (profile.points or 0) < total_cost:
            return Response({"detail": f"积分不足，需要{total_cost}积分"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 扣除积分
        profile.points = (profile.points or 0) - total_cost
        profile.save(update_fields=["points", "updated_at"])
        
        # 增加改名卡
        user_card, created = UserRenameCard.objects.get_or_create(user=user)
        user_card.quantity += quantity
        user_card.save(update_fields=["quantity", "updated_at"])
        
        # 减少库存
        card.decrease_stock(quantity)
        
        # 记录积分交易
        PointsTransaction.objects.create(
            user=user,
            transaction_type='spend',
            points=total_cost,
            description=f'购买{quantity}张改名卡'
        )
        
        return Response({
            "message": "购买成功",
            "quantity": quantity,
            "remaining_points": profile.points,
            "total_cards": user_card.quantity
        }, status=status.HTTP_201_CREATED)


class PointsTransactionListView(APIView):
    """
    获取积分交易记录
    GET /api/user/points/transactions/
    Header: Authorization: Bearer <access>
    Query: ?page=1&page_size=20
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        transactions = PointsTransaction.objects.filter(user=user)
        
        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        paginator = Paginator(transactions, page_size)
        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)
        
        serializer = PointsTransactionSerializer(page_obj, many=True)
        return Response({
            "total": paginator.count,
            "page": page,
            "page_size": page_size,
            "results": serializer.data
        }, status=status.HTTP_200_OK)










