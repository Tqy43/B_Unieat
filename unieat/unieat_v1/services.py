"""
业务逻辑层 - 将复杂的业务逻辑从 views.py 中分离出来
"""
import os
import requests
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from .models import (
    ConsumptionRecord, ConsumptionItem, Dish, Stall,
    UserProfile, MealExtraRecord
)
from .utils.wechat import jscode2session, WechatAuthError


class WechatAuthService:
    """微信认证服务"""
    
    @staticmethod
    def login_with_wechat_code(code):
        """
        使用微信 code 进行登录
        
        Args:
            code (str): 微信小程序登录 code
            
        Returns:
            dict: 包含用户信息和 token 的字典
        """
        try:
            wx_data = jscode2session(code)
            openid = wx_data["openid"]
            session_key = wx_data["session_key"]
            
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().filter(openid=openid).first()
                is_new = False
                
                if profile is None:
                    # 创建新用户
                    user = User.objects.create_user(username=f"wx_{openid}")
                    user.set_unusable_password()
                    user.save()
                    
                    profile = UserProfile.objects.create(
                        user=user, openid=openid, session_key=session_key
                    )
                    is_new = True
                else:
                    # 更新现有用户的 session_key
                    profile.session_key = session_key
                    profile.save(update_fields=["session_key", "updated_at"])
                    user = profile.user
                
                return {
                    "user": user,
                    "profile": profile,
                    "is_new": is_new
                }
                
        except WechatAuthError as e:
            raise e


class ConsumptionService:
    """消费记录服务"""
    
    @staticmethod
    def create_consumption_record(user, stall_id, consumed_at=None, notes="", items_data=None):
        """
        创建消费记录
        
        Args:
            user: 用户对象
            stall_id (int): 档口ID
            consumed_at (datetime): 消费时间
            notes (str): 备注
            items_data (list): 消费明细数据
            
        Returns:
            ConsumptionRecord: 创建的消费记录
        """
        try:
            stall = Stall.objects.get(id=stall_id)
        except Stall.DoesNotExist:
            raise ValueError(f"档口 {stall_id} 不存在")
        
        with transaction.atomic():
            # 创建消费记录
            record = ConsumptionRecord.objects.create(
                user=user,
                stall=stall,
                consumed_at=consumed_at or timezone.now(),
                notes=notes
            )
            
            # 创建消费明细
            if items_data:
                for item_data in items_data:
                    ConsumptionService._create_consumption_item(record, item_data)
            
            # 重新计算总金额
            record.recompute_totals()
            
            return record
    
    @staticmethod
    def _create_consumption_item(record, item_data):
        """
        创建消费明细项
        
        Args:
            record: 消费记录对象
            item_data (dict): 明细数据
        """
        dish_id = item_data.get("dish_id")
        quantity = item_data.get("quantity", 1)
        
        if dish_id:
            # 关联菜品的明细
            try:
                dish = Dish.objects.select_related("stall").get(id=dish_id)
                # 校验菜品归属
                if dish.stall_id != record.stall_id:
                    raise ValueError(f"菜品 {dish.id} 不属于当前档口 {record.stall_id}")
                
                ConsumptionItem.objects.create(
                    record=record,
                    dish=dish,
                    name=dish.name,
                    unit_price=dish.price,
                    quantity=quantity,
                )
            except Dish.DoesNotExist:
                raise ValueError(f"菜品 {dish_id} 不存在")
        else:
            # 自定义明细项
            name = item_data.get("name")
            unit_price = item_data.get("unit_price")
            
            if not name or unit_price is None:
                raise ValueError("自定义项必须提供 name 和 unit_price")
            
            ConsumptionItem.objects.create(
                record=record,
                dish=None,
                name=name,
                unit_price=unit_price,
                quantity=quantity,
            )
    
    @staticmethod
    def get_user_consumption_summary(user):
        """
        获取用户消费统计
        
        Args:
            user: 用户对象
            
        Returns:
            dict: 消费统计信息
        """
        today = timezone.now().date()
        
        summary = ConsumptionRecord.objects.filter(user=user).aggregate(
            consumption_today=Sum('total_amount', 
                                filter=Q(consumed_at__date=today)),
            consumption_week=Sum('total_amount',
                                filter=Q(consumed_at__week_day__in=range(1, 8))),
            consumption_month=Sum('total_amount',
                                 filter=Q(consumed_at__year=today.year, 
                                         consumed_at__month=today.month)),
            total_consumption=Sum('total_amount')
        )
        
        return {
            'consumption_today': summary['consumption_today'] or 0,
            'consumption_week': summary['consumption_week'] or 0,
            'consumption_month': summary['consumption_month'] or 0,
            'total_consumption': summary['total_consumption'] or 0
        }


class UserProfileService:
    """用户资料服务"""
    
    @staticmethod
    def update_user_avatar(profile, avatar_url):
        """
        更新用户头像
        
        Args:
            profile: 用户资料对象
            avatar_url (str): 头像URL
        """
        if not avatar_url:
            return
        
        try:
            # 下载头像
            response = requests.get(avatar_url, stream=True, timeout=5)
            if response.status_code == 200:
                # 获取文件扩展名
                ext = avatar_url.split(".")[-1].split("?")[0]
                filename = f"user_{profile.user.id}.{ext}"
                save_dir = os.path.join(settings.MEDIA_ROOT, "user_avatars")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, filename)
                
                # 删除旧头像
                if profile.avatar and os.path.exists(profile.avatar.path):
                    os.remove(profile.avatar.path)
                
                # 保存新头像
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                profile.avatar.name = f"user_avatars/{filename}"
                profile.save(update_fields=['avatar'])
                
        except Exception as e:
            print(f"下载头像失败: {e}")


class StatisticsService:
    """统计服务"""
    
    @staticmethod
    def get_top_sales_stalls(limit=10):
        """
        获取销量最高的档口
        
        Args:
            limit (int): 返回数量限制
            
        Returns:
            QuerySet: 档口销量统计
        """
        return ConsumptionRecord.objects.values(
            'stall__name'
        ).annotate(
            value=Sum('total_amount')
        ).order_by('-value')[:limit].annotate(
            name=F('stall__name')
        )
    
    @staticmethod
    def get_consumption_trends(user, time_range='week'):
        """
        获取消费趋势
        
        Args:
            user: 用户对象
            time_range (str): 时间范围 ('week' 或 'month')
            
        Returns:
            QuerySet: 消费趋势数据
        """
        if time_range == 'week':
            start_date = timezone.now() - timedelta(days=7)
        else:
            start_date = timezone.now() - timedelta(days=30)
            
        return ConsumptionRecord.objects.filter(
            user=user,
            consumed_at__gte=start_date
        ).values(
            'stall__name'
        ).annotate(
            value=Count('id')
        ).order_by('-value')[:5]


def q2(value):
    """
    保证两位小数的量化
    
    Args:
        value: 数值
        
    Returns:
        Decimal: 两位小数的Decimal对象
    """
    if value is None:
        return Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
