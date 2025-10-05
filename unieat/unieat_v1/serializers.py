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
    Feedback
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
    name = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
 
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










