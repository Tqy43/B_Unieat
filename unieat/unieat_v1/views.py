from django.http import JsonResponse
from .models import Welcome
from datetime import datetime
from random import sample

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from .models import Banner
from .models import Canteen, Stall, Dish
from .serializers import BannerSerializer
from .serializers import CanteenSerializer, StallSerializer, DishSerializer
from .serializers import StallDetailSerializer,CanteenDetailSerializer

from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer, CharField
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile
from .utils.wechat import jscode2session, WechatAuthError

# 开屏广告页
def welcome(request):
    # 查出order最大的一张图片，返回给前端
    res=Welcome.objects.all().order_by('-order').first()
    img='http://127.0.0.1:8000/media/'+str(res.img)
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
            all_dishes = []
            for canteen in queryset:
                stalls = canteen.stalls.all()
                if only_open:
                    stalls = [stall for stall in stalls if stall.is_currently_open()]
                for stall in stalls:
                    all_dishes.extend(stall.dishes.all())

            dishes_sample = sample(list(all_dishes), min(random_dishes_count, len(all_dishes)))
            dishes_data = [
                {
                    "id": dish.id,
                    "name": dish.name,
                    "price": str(dish.price),
                    "tags": dish.tags,
                    "image": f"http://127.0.0.1:8000{dish.image.url}" if dish.image else None,
                    "stall": dish.stall.name,
                    "canteen": dish.stall.canteen.name
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


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer

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