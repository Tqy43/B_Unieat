from rest_framework import serializers
from .models import Banner
from .models import Canteen, Stall, Dish

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
            return f"http://127.0.0.1:8000{obj.image.url}"
        return None


class StallSerializer(serializers.ModelSerializer):
    canteen = CanteenSerializer(read_only=True)  # 嵌套 Canteen，但不再嵌套 Dish
    image = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'canteen', 'image']

    def get_image(self, obj):
        if obj.image:
            return f"http://127.0.0.1:8000{obj.image.url}"
        return None


class DishSerializer(serializers.ModelSerializer):
    stall = StallSerializer(read_only=True)  # 嵌套 Stall（里面有 Canteen）
    image = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ['id', 'name', 'price', 'tags', 'image', 'stall']

    def get_image(self, obj):
        if obj.image:
            return f"http://127.0.0.1:8000{obj.image.url}"
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
            return f"http://127.0.0.1:8000{obj.image.url}"
        return None


class StallDetailSerializer(serializers.ModelSerializer):
    canteen = CanteenSerializer(read_only=True)
    image = serializers.SerializerMethodField()  # Stall 自己的图片
    dishes = SimpleDishSerializer(many=True, read_only=True)
    average_price = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'floor', 'canteen', 'dishes', 'average_price','image']

    def get_average_price(self, obj):
        dishes = obj.dishes.all()
        if not dishes:
            return 0
        total = sum([dish.price for dish in dishes])
        return round(total / len(dishes), 2)

    def get_image(self, obj):
        if obj.image:
            return f"http://127.0.0.1:8000{obj.image.url}"
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
            return f"http://127.0.0.1:8000{obj.image.url}"
        return None


class CanteenDetailSerializer(serializers.ModelSerializer):
    stalls = SimpleStallSerializer(many=True, read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Canteen
        fields = ['id', 'name', 'image', 'stalls']

    def get_image(self, obj):
        if obj.image:
            return f"http://127.0.0.1:8000{obj.image.url}"
        return None

