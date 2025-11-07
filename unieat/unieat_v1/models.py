from django.db import models
from datetime import time
from django.conf import settings
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone

# welcome页表模型
class Welcome(models.Model):
    # upload_to：图片上传后，放到media文件下下的welcome文件下
    #必须安装pillow 使用pip3 install pillow
    img = models.ImageField(upload_to='welcome', default='/welcome/01.png')
    order = models.IntegerField()
    # 这个字段以后不用传，会自动把上传图片的时间存到数据库
    create_time = models.DateTimeField(auto_now=True)
    is_delete = models.BooleanField(default=False)

# 主页轮播图表模型
class Banner(models.Model):
    # 上传到 media/banners/
    image = models.ImageField(upload_to='banners/')
    order = models.PositiveIntegerField(default=0, help_text="排序，数字越大越靠前")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-order', '-uploaded_at']  # order 值大排前，order相同按上传时间排

    def __str__(self):
        return f"Banner {self.id} (order={self.order})"

# 食堂档口与菜品表
class Canteen(models.Model):
    name = models.CharField(max_length=50, verbose_name="食堂名称")
    location = models.CharField(max_length=100, verbose_name="位置")
    opening_hours = models.CharField(max_length=50, verbose_name="营业时间")  # 如 "07:00-20:00"
    stall_count = models.PositiveIntegerField(default=0, verbose_name="档口数量")
    image = models.ImageField(upload_to='canteen_images/', null=True, blank=True, verbose_name="食堂图片")

    def __str__(self):
        return self.name


class Stall(models.Model):
    name = models.CharField(max_length=100)
    cuisine_type = models.CharField(max_length=50)
    # 管理员手动开关（覆盖时间段）
    manual_open = models.BooleanField(default=True, help_text="管理员手动控制营业状态")
    # 营业时间段（一天内的两个区间，早/晚）
    open_time_morning = models.TimeField(null=True, blank=True)
    close_time_morning = models.TimeField(null=True, blank=True)
    open_time_evening = models.TimeField(null=True, blank=True)
    close_time_evening = models.TimeField(null=True, blank=True)

    image = models.ImageField(upload_to='stall_images/', blank=True, null=True)
    canteen = models.ForeignKey('Canteen', related_name='stalls', on_delete=models.CASCADE)
    floor = models.CharField(max_length=10, blank=True, null=True)

    # 档口类型
    type = models.CharField(
        max_length=20,
        choices=[("fixed", "固定价格"), ("custom", "自定义金额")],
        default="fixed",
        help_text="档口价格模式：固定价格 / 自定义金额"
    )

    def is_currently_open(self):
        """结合时间段 & 管理员手动开关判断营业状态"""
        from datetime import datetime
        now = datetime.now().time()

        if not self.manual_open:
            return False

        # 检查早市
        if self.open_time_morning and self.close_time_morning:
            if self.open_time_morning <= now <= self.close_time_morning:
                return True

        # 检查晚市
        if self.open_time_evening and self.close_time_evening:
            if self.open_time_evening <= now <= self.close_time_evening:
                return True

        return False

    def __str__(self):
        return f"{self.name}（{self.canteen.name}）"


class Dish(models.Model):
    TYPE_CHOICES = (
        ("normal", "普通菜品"),
        ("custom", "自选/称重"),
    )
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, related_name='dishes')
    name = models.CharField(max_length=50, verbose_name="菜品名称")
    price = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="价格")
    tags = models.CharField(max_length=100, blank=True, verbose_name="标签")  # 逗号分隔，如 "麻辣,素食"
    image = models.ImageField(upload_to='dish_images/', null=True, blank=True, verbose_name="菜品图片")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="normal")
    def __str__(self):
        return f"{self.stall.name} - {self.name}"

def q2(value):
    # 保证两位小数的量化
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class ConsumptionRecord(models.Model):
    """
    一笔消费：属于某用户、某档口；包含若干 ConsumptionItem 明细
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consumption_records")
    stall = models.ForeignKey("unieat_v1.Stall", on_delete=models.PROTECT, related_name="consumption_records")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    items_count = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True, default="")
    consumed_at = models.DateTimeField(default=timezone.now)  # 用餐时间（前端可传）

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-consumed_at", "-id")
        indexes = [
            models.Index(fields=["user", "consumed_at"]),
            models.Index(fields=["stall"]),
        ]

    def __str__(self):
        return f"Record#{self.id} user={self.user_id} stall={self.stall_id} total={self.total_amount}"

    def recompute_totals(self):
        agg = self.items.aggregate(
            total=models.Sum("amount"),
            count=models.Sum("quantity"),
        )
        self.total_amount = q2(agg["total"] or Decimal("0.00"))
        # items_count 你可以理解为“行数”或“份数”，此处按份数汇总
        self.items_count = int(agg["count"] or 0)
        self.save(update_fields=["total_amount", "items_count", "updated_at"])

class ConsumptionItem(models.Model):
    """
    消费明细：可以关联具体 dish，也可以是自定义项（无 dish）
    """
    record = models.ForeignKey(ConsumptionRecord, on_delete=models.CASCADE, related_name="items")
    dish = models.ForeignKey("unieat_v1.Dish", on_delete=models.SET_NULL, null=True, blank=True, related_name="consumption_items")

    # 快照字段，记录当时名称 & 单价，保证历史可追溯
    name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"Item#{self.id} record={self.record_id} {self.name} x{self.quantity} = {self.amount}"

    def save(self, *args, **kwargs):
        # 服务端兜底计算
        self.unit_price = q2(self.unit_price)
        self.amount = q2(self.unit_price * Decimal(self.quantity))
        super().save(*args, **kwargs)





# 用户表
# openid 唯一，作为用户在小程序侧的唯一标识

def user_avatar_path(instance, filename):
    # 存储到 user_avatars/user_<id>.jpg
    ext = filename.split('.')[-1]
    return f"user_avatars/user_{instance.user.id}.{ext}"

class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    openid = models.CharField(max_length=64, unique=True, db_index=True)
    session_key = models.CharField(max_length=128, blank=True, default="")
    nickname = models.CharField(max_length=64, blank=True, default="")
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    points = models.PositiveIntegerField(default=0, verbose_name="积分")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.id}] {self.openid}"

# 用于统计


class MealExtraRecord(models.Model):
    meal = models.ForeignKey(ConsumptionRecord, on_delete=models.CASCADE, related_name="extras")
    desc = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.desc} (+{self.amount}元)"

# ... existing code ...



# 用于反馈

class Feedback(models.Model):
    """
    用户反馈模型（匿名提交）
    """
    description = models.TextField(verbose_name="问题描述")  # 必填，用户反馈的内容
    contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="联系方式"
    )  # 选填，邮箱/微信号/手机号等
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")

    class Meta:
        verbose_name = "用户反馈"
        verbose_name_plural = "用户反馈"

    def __str__(self):
        return f"反馈[{self.id}] - {self.description[:20]}..."


# 签到记录模型
class CheckInRecord(models.Model):
    """用户签到记录"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="checkin_records",
        verbose_name="用户"
    )
    checkin_date = models.DateField(default=timezone.now, verbose_name="签到日期")
    checkin_time = models.DateTimeField(default=timezone.now, verbose_name="签到时间")
    consecutive_days = models.PositiveIntegerField(default=1, verbose_name="连续签到天数")
    points_earned = models.PositiveIntegerField(default=0, verbose_name="本次获得积分")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        unique_together = ['user', 'checkin_date']  # 确保每天只能签到一次
        ordering = ['-checkin_date', '-checkin_time']
        verbose_name = "签到记录"
        verbose_name_plural = "签到记录"
        indexes = [
            models.Index(fields=['user', 'checkin_date']),
        ]
    
    def __str__(self):
        return f"签到[{self.id}] 用户={self.user_id} 日期={self.checkin_date} 连续={self.consecutive_days}天"


# =======================
# 积分商城相关模型
# =======================

def avatar_upload_path(instance, filename):
    """头像图片上传路径"""
    ext = filename.split('.')[-1]
    return f"avatars/avatar_{instance.id}.{ext}"


class Avatar(models.Model):
    """头像商品"""
    name = models.CharField(max_length=50, verbose_name="头像名称")
    image = models.ImageField(upload_to=avatar_upload_path, verbose_name="头像图片")
    price = models.PositiveIntegerField(verbose_name="价格（积分）")
    is_default = models.BooleanField(default=False, verbose_name="是否默认头像（免费）")
    description = models.CharField(max_length=200, blank=True, verbose_name="描述")
    stock = models.IntegerField(null=True, blank=True, verbose_name="库存数量", help_text="留空表示无限库存")
    is_available = models.BooleanField(default=True, verbose_name="是否上架")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "头像商品"
        verbose_name_plural = "头像商品"
        ordering = ['price', 'id']
    
    def __str__(self):
        return f"{self.name} ({self.price}积分)"
    
    def has_stock(self):
        """检查是否有库存"""
        if self.stock is None:
            return True  # 无限库存
        return self.stock > 0
    
    def decrease_stock(self):
        """减少库存"""
        if self.stock is not None and self.stock > 0:
            self.stock -= 1
            self.save(update_fields=['stock'])


class UserAvatar(models.Model):
    """用户拥有的头像"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_avatars",
        verbose_name="用户"
    )
    avatar = models.ForeignKey(
        Avatar,
        on_delete=models.CASCADE,
        related_name="user_avatars",
        verbose_name="头像"
    )
    is_current = models.BooleanField(default=False, verbose_name="是否当前使用")
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name="购买时间")
    
    class Meta:
        unique_together = ['user', 'avatar']  # 用户不能重复购买同一头像
        verbose_name = "用户头像"
        verbose_name_plural = "用户头像"
        indexes = [
            models.Index(fields=['user', 'is_current']),
        ]
    
    def __str__(self):
        return f"用户{self.user_id} - {self.avatar.name}"


class RecheckInCard(models.Model):
    """续签卡商品"""
    name = models.CharField(max_length=50, default="续签卡", verbose_name="名称")
    price = models.PositiveIntegerField(default=5, verbose_name="价格（积分）")
    description = models.CharField(max_length=200, default="可以补签前一天未签到的记录", verbose_name="描述")
    stock = models.IntegerField(null=True, blank=True, verbose_name="库存数量", help_text="留空表示无限库存")
    is_available = models.BooleanField(default=True, verbose_name="是否上架")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "续签卡商品"
        verbose_name_plural = "续签卡商品"
    
    def __str__(self):
        return f"{self.name} ({self.price}积分)"
    
    def has_stock(self):
        """检查是否有库存"""
        if self.stock is None:
            return True  # 无限库存
        return self.stock > 0
    
    def decrease_stock(self, quantity=1):
        """减少库存"""
        if self.stock is not None and self.stock >= quantity:
            self.stock -= quantity
            self.save(update_fields=['stock'])


class RenameCard(models.Model):
    """改名卡商品"""
    name = models.CharField(max_length=50, default="改名卡", verbose_name="名称")
    price = models.PositiveIntegerField(default=1, verbose_name="价格（积分）")
    description = models.CharField(max_length=200, default="可以修改一次用户昵称", verbose_name="描述")
    stock = models.IntegerField(null=True, blank=True, verbose_name="库存数量", help_text="留空表示无限库存")
    is_available = models.BooleanField(default=True, verbose_name="是否上架")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "改名卡商品"
        verbose_name_plural = "改名卡商品"
    
    def __str__(self):
        return f"{self.name} ({self.price}积分)"
    
    def has_stock(self):
        """检查是否有库存"""
        if self.stock is None:
            return True  # 无限库存
        return self.stock > 0
    
    def decrease_stock(self, quantity=1):
        """减少库存"""
        if self.stock is not None and self.stock >= quantity:
            self.stock -= quantity
            self.save(update_fields=['stock'])


class UserRecheckInCard(models.Model):
    """用户拥有的续签卡"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recheckin_card",
        verbose_name="用户"
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name="数量")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "用户续签卡"
        verbose_name_plural = "用户续签卡"
    
    def __str__(self):
        return f"用户{self.user_id} - {self.quantity}张续签卡"


class UserRenameCard(models.Model):
    """用户拥有的改名卡"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rename_card",
        verbose_name="用户"
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name="数量")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "用户改名卡"
        verbose_name_plural = "用户改名卡"
    
    def __str__(self):
        return f"用户{self.user_id} - {self.quantity}张改名卡"


class PointsTransaction(models.Model):
    """积分交易记录"""
    TRANSACTION_TYPES = [
        ('earn', '获得'),
        ('spend', '消费'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="points_transactions",
        verbose_name="用户"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        verbose_name="交易类型"
    )
    points = models.IntegerField(verbose_name="积分数量")  # 正数表示获得，负数表示消费
    description = models.CharField(max_length=200, verbose_name="描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "积分交易记录"
        verbose_name_plural = "积分交易记录"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.get_transaction_type_display()} {abs(self.points)}积分 - {self.description}"


