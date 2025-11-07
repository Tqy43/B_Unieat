# 标准库导入
from decimal import Decimal

# DRF相关导入
from rest_framework import serializers

# 项目内部模型导入
from .models import (
    Banner,
    Canteen, Stall, Dish,
    UserProfile,
    MealExtraRecord,
    ConsumptionRecord, ConsumptionItem,
    Feedback,
    CheckInRecord,
    Avatar, UserAvatar, RecheckInCard, UserRecheckInCard,
    RenameCard, UserRenameCard, PointsTransaction
)

# =======================
# 轮播图
# =======================
class BannerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = ['id', 'image_url', 'order', 'uploaded_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

# =======================
# DishDetail 使用
# =======================
class CanteenSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Canteen
        fields = ['id', 'name', 'image']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class StallSerializer(serializers.ModelSerializer):
    canteen = CanteenSerializer(read_only=True)  # 嵌套 Canteen，但不再嵌套 Dish
    image = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'canteen', 'image','type']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class DishSerializer(serializers.ModelSerializer):
    stall = StallSerializer(read_only=True)  # 嵌套 Stall（里面有 Canteen）
    stall_name = serializers.CharField(source='stall.name', read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ['id', 'name', 'price', 'tags', 'image', 'stall','stall_name', 'type']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


# =======================
# StallDetail 使用
# =======================
# 简化版 DishSerializer（用于 StallDetail 避免循环）
class SimpleDishSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ['id', 'name', 'price', 'image']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class StallDetailSerializer(serializers.ModelSerializer):
    canteen = CanteenSerializer(read_only=True)
    image = serializers.SerializerMethodField()  # Stall 自己的图片
    dishes = SimpleDishSerializer(many=True, read_only=True)
    average_price = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'floor', 'canteen', 'dishes', 'average_price','image','type']

    def get_average_price(self, obj):
        dishes = obj.dishes.all()
        if not dishes:
            return 0
        total = sum([dish.price for dish in dishes])
        return round(total / len(dishes), 2)

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

# =======================
# CanteenDetail 使用
# =======================
class SimpleStallSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'floor', 'image']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CanteenDetailSerializer(serializers.ModelSerializer):
    stalls = SimpleStallSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Canteen
        fields = ['id', 'name', 'image', 'stalls']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

# =======================
# 用户
# =======================

class UserProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserProfile
        fields = ('nickname', 'avatar', 'budget')
        read_only_fields = ()

    def validate_avatar_url(self, value):
        # 允许为空（不授权时）
        if value:
            if not (value.startswith("http://") or value.startswith("https://")):
                raise serializers.ValidationError("avatar_url must be an absolute http/https URL")
        return value



class ConsumptionItemInputSerializer(serializers.Serializer):
    """
    创建时使用的输入明细：
    - 如果是菜品：传 dish_id、quantity（unit_price 可不传，以数据库为准）
    - 如果是自定义项：不传 dish_id，传 name + unit_price + quantity
    """
    dish_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        dish_id = data.get("dish_id")
        name = data.get("name")
        unit_price = data.get("unit_price")

        if dish_id:
            # 菜品项：name/unit_price 可不传
            return data
        else:
            # 自定义项：必须有 name + unit_price
            if not name:
                raise serializers.ValidationError("自定义项必须提供 name")
            if unit_price is None:
                raise serializers.ValidationError("自定义项必须提供 unit_price")
            return data

class ConsumptionItemSerializer(serializers.ModelSerializer):
    dish = serializers.SerializerMethodField()

    class Meta:
        model = ConsumptionItem
        fields = ("id", "dish", "name", "unit_price", "quantity", "amount")

    def get_dish(self, obj):
        if not obj.dish:
            return None
        return {
            "id": obj.dish_id,
            "name": obj.dish.name,
        }

class ConsumptionRecordSerializer(serializers.ModelSerializer):
    stall = serializers.SerializerMethodField()
    items = ConsumptionItemSerializer(many=True, read_only=True)
    stallsName = serializers.CharField(source='stall.name', read_only=True)
    canteenInfo = serializers.CharField(source='stall.canteen.name', read_only=True)
    remark = serializers.CharField(source='notes', read_only=True)

    class Meta:
        model = ConsumptionRecord
        # fields = ("id", "stallsName", "canteenInfo", "total_amount", "items_count", "notes", "consumed_at", "items", "created_at", "remark")
        #fields = '__all__'
        fields = ("id", "stall", "stallsName", "canteenInfo", "total_amount", "items_count", "notes", "consumed_at", "items", "created_at", "remark")


    def get_stall(self, obj):
        return {
            "id": obj.stall_id,
            "name": obj.stall.name,
            "image": obj.stall.image.url if obj.stall.image else None,
            "canteen": {
                "id": obj.stall.canteen_id,
                "name": obj.stall.canteen.name,
            },
        }

class ConsumptionRecordCreateSerializer(serializers.Serializer):
    stall_id = serializers.IntegerField()
    consumed_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)
    items = ConsumptionItemInputSerializer(many=True)

    def validate_stall_id(self, value):
        if not Stall.objects.filter(id=value).exists():
            raise serializers.ValidationError("无效的档口 ID")
        return value

    def validate(self, data):
        items = data.get("items") or []
        if not items:
            raise serializers.ValidationError("至少需要一条明细 items")
        return data

    def create(self, validated_data):
        from django.utils import timezone
        
        user = self.context["request"].user
        stall = Stall.objects.get(id=validated_data["stall_id"])
        consumed_at = validated_data.get("consumed_at") or timezone.now()
        notes = validated_data.get("notes", "")

        record = ConsumptionRecord.objects.create(
            user=user,
            stall=stall,
            consumed_at=consumed_at,
            notes=notes,
        )

        # 逐条创建明细（服务端计算单价/金额）
        for it in validated_data["items"]:
            dish_id = it.get("dish_id")
            quantity = it.get("quantity", 1)

            if dish_id:
                dish = Dish.objects.select_related("stall").get(id=dish_id)
                # 校验菜品归属
                if dish.stall_id != stall.id:
                    raise serializers.ValidationError(f"菜品 {dish.id} 不属于当前档口 {stall.id}")
                name = dish.name
                unit_price = dish.price  # 以数据库为准
                ConsumptionItem.objects.create(
                    record=record,
                    dish=dish,
                    name=name,
                    unit_price=unit_price,
                    quantity=quantity,
                )
            else:
                # 自定义项
                name = it["name"]
                unit_price = it["unit_price"]
                ConsumptionItem.objects.create(
                    record=record,
                    dish=None,
                    name=name,
                    unit_price=unit_price,
                    quantity=quantity,
                )

        # 汇总计算总价与总份数
        record.recompute_totals()
        return record

# =======================
# 统计
# =======================
class MealStatisticsSerializer(serializers.Serializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    by_canteen = serializers.ListField()
    by_stall = serializers.ListField()
    by_dish = serializers.ListField()
    extra_expenses = serializers.ListField()

class TopSalesSerializer(serializers.Serializer):
    name = serializers.CharField(source='stall__name')
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    image = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    
    def get_image(self, obj):
        """获取店铺图片URL"""
        image_path = obj.get('stall__image')
        if image_path:
            request = self.context.get('request')
            if request:
                # 如果路径不是完整URL，构建完整URL
                if image_path.startswith('http'):
                    return image_path
                # 构建媒体文件的完整URL
                return request.build_absolute_uri('/media/' + image_path)
            return image_path
        return None
    
    def get_user_name(self, obj):
        """获取在该档口消费最多的用户名字"""
        user_nickname = obj.get('top_user__profile__nickname')
        username = obj.get('top_user__username', '')
        
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"序列化用户名称 - 昵称: '{user_nickname}', 用户名: '{username}'")
        
        # 检查昵称是否存在且不为空字符串
        if user_nickname and str(user_nickname).strip():
            result = str(user_nickname).strip()
            logger.debug(f"使用昵称: '{result}'")
            return result
        
        # 如果没有昵称，返回用户名
        if username:
            if username.startswith('wx_'):
                result = '用户' + username[-4:]  # 显示后4位
            else:
                result = username[:10] if len(username) > 10 else username
            logger.debug(f"使用用户名生成: '{result}'")
            return result
        
        logger.warning(f"用户名称获取失败，返回'未知用户'")
        return '未知用户'
    
    def get_user_avatar(self, obj):
        """获取在该档口消费最多的用户头像"""
        request = self.context.get('request')
        if not request:
            return None
        
        # 获取用户当前使用的头像
        user_id = obj.get('top_user__id')
        if not user_id:
            return None
        
        from .models import UserAvatar
        try:
            user_avatar = UserAvatar.objects.filter(
                user_id=user_id,
                is_current=True
            ).select_related('avatar').first()
            
            if user_avatar and user_avatar.avatar and user_avatar.avatar.image:
                return request.build_absolute_uri(user_avatar.avatar.image.url)
        except:
            pass
        
        # 如果没有头像，尝试使用用户资料中的头像
        try:
            from .models import UserProfile
            profile = UserProfile.objects.filter(user_id=user_id).first()
            if profile and profile.avatar:
                return request.build_absolute_uri(profile.avatar.url)
        except:
            pass
        
        return None
 
class ConsumptionSummarySerializer(serializers.Serializer):
    consumptionToday = serializers.DecimalField(max_digits=10, decimal_places=2)
    consumptionWeek = serializers.DecimalField(max_digits=10, decimal_places=2)
    consumptionMonth = serializers.DecimalField(max_digits=10, decimal_places=2)
    totalConsumption = serializers.DecimalField(max_digits=10, decimal_places=2)
 

# =======================
# 反馈
# =======================

class FeedbackSerializer(serializers.ModelSerializer):
    """
    用于验证和序列化反馈数据
    """
    class Meta:
        model = Feedback
        fields = ["id", "description", "contact", "created_at"]
        read_only_fields = ["id", "created_at"]


# =======================
# 签到
# =======================
class CheckInRecordSerializer(serializers.ModelSerializer):
    """签到记录序列化器"""
    class Meta:
        model = CheckInRecord
        fields = ['id', 'checkin_date', 'checkin_time', 'consecutive_days', 'points_earned', 'created_at']
        read_only_fields = ['id', 'checkin_date', 'checkin_time', 'consecutive_days', 'points_earned', 'created_at']


class CheckInStatusSerializer(serializers.Serializer):
    """签到状态序列化器"""
    today_signed = serializers.BooleanField()
    consecutive_days = serializers.IntegerField()
    total_points = serializers.IntegerField()
    today_points = serializers.IntegerField(required=False)
    last_checkin_date = serializers.DateField(required=False, allow_null=True)


# =======================
# 积分商城
# =======================
class AvatarSerializer(serializers.ModelSerializer):
    """头像商品序列化器"""
    image_url = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    
    class Meta:
        model = Avatar
        fields = ['id', 'name', 'image_url', 'price', 'is_default', 'description', 'stock', 'is_available', 'is_owned']
        read_only_fields = ['id', 'image_url', 'is_owned']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None
    
    def get_is_owned(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserAvatar.objects.filter(user=request.user, avatar=obj).exists()
        return False


class UserAvatarSerializer(serializers.ModelSerializer):
    """用户拥有的头像序列化器"""
    avatar = AvatarSerializer(read_only=True)
    avatar_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = UserAvatar
        fields = ['id', 'avatar', 'avatar_id', 'is_current', 'purchased_at']
        read_only_fields = ['id', 'purchased_at']


class RecheckInCardSerializer(serializers.ModelSerializer):
    """续签卡商品序列化器"""
    class Meta:
        model = RecheckInCard
        fields = ['id', 'name', 'price', 'description', 'stock', 'is_available']
        read_only_fields = ['id']


class UserRecheckInCardSerializer(serializers.ModelSerializer):
    """用户拥有的续签卡序列化器"""
    class Meta:
        model = UserRecheckInCard
        fields = ['quantity', 'updated_at']
        read_only_fields = ['quantity', 'updated_at']


class RenameCardSerializer(serializers.ModelSerializer):
    """改名卡商品序列化器"""
    class Meta:
        model = RenameCard
        fields = ['id', 'name', 'price', 'description', 'stock', 'is_available']
        read_only_fields = ['id']


class UserRenameCardSerializer(serializers.ModelSerializer):
    """用户拥有的改名卡序列化器"""
    class Meta:
        model = UserRenameCard
        fields = ['quantity', 'updated_at']
        read_only_fields = ['quantity', 'updated_at']


class PointsTransactionSerializer(serializers.ModelSerializer):
    """积分交易记录序列化器"""
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = PointsTransaction
        fields = ['id', 'transaction_type', 'transaction_type_display', 'points', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']










