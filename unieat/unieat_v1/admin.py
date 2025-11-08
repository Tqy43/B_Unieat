from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django import forms
from .models import (
    Welcome, Banner, Canteen, Stall, Dish, UserProfile, 
    ConsumptionRecord, ConsumptionItem, Feedback, CheckInRecord,
    Avatar, UserAvatar, RecheckInCard, UserRecheckInCard,
    RenameCard, UserRenameCard, PointsTransaction
)

admin.site.register(Welcome)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'uploaded_at')
    ordering = ('-order', '-uploaded_at')

admin.site.register(Canteen)


class UserAvatarInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        selected = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            if form.cleaned_data.get('is_current'):
                selected += 1
        if selected > 1:
            raise forms.ValidationError("只能设置一个“当前”头像。")


class UserAvatarInline(admin.TabularInline):
    model = UserAvatar
    formset = UserAvatarInlineFormSet
    fk_name = 'user'
    extra = 0
    fields = ('avatar', 'is_current', 'purchased_at')
    readonly_fields = ('purchased_at',)
    autocomplete_fields = ('avatar',)


class UserRecheckInCardInline(admin.StackedInline):
    model = UserRecheckInCard
    fk_name = 'user'
    can_delete = False
    extra = 0
    fields = ('quantity',)
    max_num = 1

    def get_extra(self, request, obj=None, **kwargs):
        if obj and hasattr(obj, 'recheckin_card'):
            return 0
        return 1


class UserRenameCardInline(admin.StackedInline):
    model = UserRenameCard
    fk_name = 'user'
    can_delete = False
    extra = 0
    fields = ('quantity',)
    max_num = 1

    def get_extra(self, request, obj=None, **kwargs):
        if obj and hasattr(obj, 'rename_card'):
            return 0
        return 1


class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserAvatarInline, UserRecheckInCardInline, UserRenameCardInline]

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if formset.model == UserAvatar and form.instance:
            selected_ids = []
            for inline_form in formset.forms:
                if not hasattr(inline_form, "cleaned_data"):
                    continue
                if inline_form.cleaned_data.get('DELETE'):
                    continue
                if inline_form.cleaned_data.get('is_current'):
                    instance = inline_form.instance
                    if instance.pk:
                        selected_ids.append(instance.pk)
            if selected_ids:
                UserAvatar.objects.filter(user=form.instance).exclude(pk__in=selected_ids).update(is_current=False)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)


@admin.register(UserAvatar)
class UserAvatarAdmin(admin.ModelAdmin):
    """用户头像拥有记录"""
    list_display = ('id', 'user', 'avatar', 'is_current', 'purchased_at')
    list_filter = ('is_current', 'avatar__is_default', 'purchased_at')
    search_fields = ('user__username', 'user__profile__nickname', 'avatar__name')
    ordering = ('user', '-is_current', '-purchased_at')
    readonly_fields = ('purchased_at',)
    autocomplete_fields = ('user', 'avatar')
    list_editable = ('is_current',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'avatar', 'user__profile')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.is_current:
            UserAvatar.objects.filter(user=obj.user).exclude(pk=obj.pk).update(is_current=False)


@admin.register(UserRecheckInCard)
class UserRecheckInCardAdmin(admin.ModelAdmin):
    """用户续签卡拥有记录"""
    list_display = ('id', 'user', 'quantity', 'updated_at')
    search_fields = ('user__username', 'user__profile__nickname')
    ordering = ('user', '-updated_at')
    readonly_fields = ('updated_at',)
    autocomplete_fields = ('user',)
    list_editable = ('quantity',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'user__profile')


@admin.register(UserRenameCard)
class UserRenameCardAdmin(admin.ModelAdmin):
    """用户改名卡拥有记录"""
    list_display = ('id', 'user', 'quantity', 'updated_at')
    search_fields = ('user__username', 'user__profile__nickname')
    ordering = ('user', '-updated_at')
    readonly_fields = ('updated_at',)
    autocomplete_fields = ('user',)
    list_editable = ('quantity',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'user__profile')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """用户资料管理 - 集成头像、续签卡、改名卡"""
    list_display = ('id', 'user', 'nickname_display', 'openid_short', 'budget', 'points', 
                    'avatar_preview', 'recheckin_cards_count', 'rename_cards_count', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'nickname', 'openid')
    ordering = ('-created_at',)
    
    # 字段分组
    fieldsets = (
        ('用户信息', {
            'fields': ('user', 'openid', 'nickname')
        }),
        ('财务信息', {
            'fields': ('budget', 'points')
        }),
        ('头像信息', {
            'fields': ('avatar', 'avatar_preview_large'),
            'classes': ('collapse',)
        }),
        ('拥有的商品', {
            'fields': ('user_avatars_display', 'recheckin_cards_display', 'rename_cards_display'),
            'description': '显示用户拥有的头像、续签卡和改名卡'
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'avatar_preview', 'avatar_preview_large',
                       'user_avatars_display', 'recheckin_cards_display', 'rename_cards_display')
    
    def save_model(self, request, obj, form, change):
        """保存时确保数据正确写入数据库"""
        super().save_model(request, obj, form, change)
        obj.refresh_from_db()
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Admin保存UserProfile - 用户ID: {obj.user_id}, 昵称: '{obj.nickname}'")
    
    def nickname_display(self, obj):
        """显示昵称，如果为空则显示提示"""
        if obj.nickname and obj.nickname.strip():
            return f'<span style="color: #2e7d32; font-weight: bold;">{obj.nickname}</span>'
        return '<span style="color: #d32f2f; font-style: italic;">未设置</span>'
    nickname_display.short_description = '昵称'
    nickname_display.allow_tags = True
    
    def openid_short(self, obj):
        """显示openid的前10位"""
        if obj.openid:
            return f"{obj.openid[:10]}..." if len(obj.openid) > 10 else obj.openid
        return "-"
    openid_short.short_description = 'OpenID'
    
    def avatar_preview(self, obj):
        """列表页小图预览"""
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="40" height="40" style="border-radius: 50%; object-fit: cover;" />'
        return "无头像"
    avatar_preview.short_description = '头像'
    avatar_preview.allow_tags = True
    
    def avatar_preview_large(self, obj):
        """编辑页大图预览"""
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="150" height="150" style="border-radius: 50%; object-fit: cover; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />'
        return "未上传头像"
    avatar_preview_large.short_description = '当前头像'
    avatar_preview_large.allow_tags = True
    
    def recheckin_cards_count(self, obj):
        """显示续签卡数量"""
        try:
            card = obj.user.recheckin_card
            return f'<span style="color: #20B2AA; font-weight: bold;">{card.quantity}张</span>'
        except:
            return '<span style="color: #999;">0张</span>'
    recheckin_cards_count.short_description = '续签卡'
    recheckin_cards_count.allow_tags = True
    
    def rename_cards_count(self, obj):
        """显示改名卡数量"""
        try:
            card = obj.user.rename_card
            return f'<span style="color: #20B2AA; font-weight: bold;">{card.quantity}张</span>'
        except:
            return '<span style="color: #999;">0张</span>'
    rename_cards_count.short_description = '改名卡'
    rename_cards_count.allow_tags = True
    
    def user_avatars_display(self, obj):
        """显示用户拥有的头像列表"""
        avatars = UserAvatar.objects.filter(user=obj.user).select_related('avatar')
        if not avatars.exists():
            return '<span style="color: #999;">暂无头像</span>'
        
        html = '<div style="display: flex; flex-wrap: wrap; gap: 10px;">'
        for ua in avatars:
            current_badge = ' <span style="background: #20B2AA; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">当前</span>' if ua.is_current else ''
            html += f'''
            <div style="border: 1px solid #ddd; padding: 8px; border-radius: 8px; text-align: center; min-width: 100px;">
                <img src="{ua.avatar.image.url if ua.avatar.image else ''}" width="60" height="60" style="border-radius: 50%; object-fit: cover; margin-bottom: 5px;" />
                <div style="font-size: 12px; color: #333;">{ua.avatar.name}{current_badge}</div>
            </div>
            '''
        html += '</div>'
        return html
    user_avatars_display.short_description = '拥有的头像'
    user_avatars_display.allow_tags = True
    
    def recheckin_cards_display(self, obj):
        """显示续签卡信息"""
        try:
            card = obj.user.recheckin_card
            return f'<div style="padding: 10px; background: #e8f5e9; border-radius: 8px;"><strong>数量：</strong><span style="color: #20B2AA; font-size: 18px; font-weight: bold;">{card.quantity}张</span><br><small style="color: #666;">最后更新：{card.updated_at.strftime("%Y-%m-%d %H:%M")}</small></div>'
        except:
            return '<div style="padding: 10px; background: #f5f5f5; border-radius: 8px; color: #999;">0张</div>'
    recheckin_cards_display.short_description = '续签卡'
    recheckin_cards_display.allow_tags = True
    
    def rename_cards_display(self, obj):
        """显示改名卡信息"""
        try:
            card = obj.user.rename_card
            return f'<div style="padding: 10px; background: #fff3cd; border-radius: 8px;"><strong>数量：</strong><span style="color: #20B2AA; font-size: 18px; font-weight: bold;">{card.quantity}张</span><br><small style="color: #666;">最后更新：{card.updated_at.strftime("%Y-%m-%d %H:%M")}</small></div>'
        except:
            return '<div style="padding: 10px; background: #f5f5f5; border-radius: 8px; color: #999;">0张</div>'
    rename_cards_display.short_description = '改名卡'
    rename_cards_display.allow_tags = True

class ConsumptionItemInline(admin.TabularInline):
    model = ConsumptionItem
    extra = 0
    fields = ('dish', 'name', 'unit_price', 'quantity', 'amount')
    readonly_fields = ('amount',)  # amount 是自动计算的，设为只读

@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "stall", "total_amount", "items_count", "consumed_at", "created_at")
    list_filter = ("stall__canteen", "stall", "consumed_at", "created_at")
    search_fields = ("user__username", "stall__name", "notes")
    inlines = [ConsumptionItemInline]
    readonly_fields = ('created_at', 'updated_at')  # 创建和更新时间自动生成，设为只读
    
    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'stall', 'consumed_at')
        }),
        ('消费信息', {
            'fields': ('total_amount', 'items_count', 'notes')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # 可折叠
        }),
    )
    
    # 保存时重新计算总额
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # 保存后重新计算总额
        if obj.pk:
            obj.recompute_totals()
    
    # 保存内联对象后重新计算总额
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # 保存内联后重新计算总额（特别是修改了 items 后）
        if form.instance.pk:
            form.instance.recompute_totals()
    
    # 响应保存操作
    def response_add(self, request, obj, post_url_continue=None):
        """添加后重新计算总额"""
        response = super().response_add(request, obj, post_url_continue)
        if obj.pk:
            obj.recompute_totals()
        return response
    
    def response_change(self, request, obj):
        """修改后重新计算总额"""
        response = super().response_change(request, obj)
        if obj.pk:
            obj.recompute_totals()
        return response

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    在后台管理界面中显示反馈数据
    """
    list_display = ("id", "description", "contact", "created_at")
    search_fields = ("description", "contact")  # 支持搜索
    list_filter = ("created_at",)  # 按提交时间过滤

@admin.register(CheckInRecord)
class CheckInRecordAdmin(admin.ModelAdmin):
    """
    签到记录管理
    """
    list_display = ("id", "user", "checkin_date", "checkin_time", "consecutive_days", "points_earned", "created_at")
    list_filter = ("checkin_date", "consecutive_days")
    search_fields = ("user__username", "user__profile__openid")
    ordering = ("-checkin_date", "-checkin_time")

@admin.register(Stall)
class StallAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'canteen', 'floor', 'type', 'manual_open')
    list_filter = ('canteen', 'floor', 'type')


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    # 列表页显示的字段
    list_display = ['name', 'stall', 'price', 'get_type_display', 'tags']

    # 可搜索的字段
    search_fields = ['name', 'stall__name']

    # 过滤器
    list_filter = ['type', 'stall']

    # 编辑页面的字段排列
    fields = ['stall', 'name', 'type', 'price', 'tags', 'image']


# =======================
# 积分商城管理
# =======================
@admin.register(Avatar)
class AvatarAdmin(admin.ModelAdmin):
    """头像商品管理"""
    list_display = ('id', 'name', 'price', 'stock_display', 'is_available', 'is_default', 'image_preview', 'description', 'created_at')
    list_filter = ('is_default', 'is_available', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('price', 'id')
    
    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'price', 'is_default')
        }),
        ('库存与上架', {
            'fields': ('stock', 'is_available'),
            'description': '库存留空表示无限库存；未上架的商品不会在商城显示'
        }),
        ('头像图片', {
            'fields': ('image', 'image_preview_large'),
            'description': '上传头像图片（建议尺寸：200x200像素）'
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'image_preview', 'image_preview_large')
    
    def stock_display(self, obj):
        """库存显示"""
        if obj.stock is None:
            return '<span style="color: green; font-weight: bold;">无限</span>'
        elif obj.stock > 10:
            return f'<span style="color: green;">{obj.stock}</span>'
        elif obj.stock > 0:
            return f'<span style="color: orange; font-weight: bold;">{obj.stock}</span>'
        else:
            return '<span style="color: red; font-weight: bold;">售罄</span>'
    stock_display.short_description = '库存'
    stock_display.allow_tags = True
    
    def image_preview(self, obj):
        """列表页小图预览"""
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />'
        return "无图片"
    image_preview.short_description = '预览'
    image_preview.allow_tags = True
    
    def image_preview_large(self, obj):
        """编辑页大图预览"""
        if obj.image:
            return f'<img src="{obj.image.url}" width="200" height="200" style="border-radius: 10px; object-fit: cover; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />'
        return "未上传图片"
    image_preview_large.short_description = '当前图片'
    image_preview_large.allow_tags = True


@admin.register(RecheckInCard)
class RecheckInCardAdmin(admin.ModelAdmin):
    """续签卡商品管理"""
    list_display = ('id', 'name', 'price', 'stock_display', 'is_available', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('price', 'id')
    list_filter = ('is_available', 'created_at')
    
    # 字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'price'),
            'description': '续签卡允许用户补签前一天的签到记录'
        }),
        ('库存与上架', {
            'fields': ('stock', 'is_available'),
            'description': '库存留空表示无限库存；未上架的商品不会在商城显示'
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)
    
    def stock_display(self, obj):
        """库存显示"""
        if obj.stock is None:
            return '<span style="color: green; font-weight: bold;">无限</span>'
        elif obj.stock > 20:
            return f'<span style="color: green;">{obj.stock}</span>'
        elif obj.stock > 0:
            return f'<span style="color: orange; font-weight: bold;">{obj.stock}</span>'
        else:
            return '<span style="color: red; font-weight: bold;">售罄</span>'
    stock_display.short_description = '库存'
    stock_display.allow_tags = True


@admin.register(RenameCard)
class RenameCardAdmin(admin.ModelAdmin):
    """改名卡商品管理"""
    list_display = ('id', 'name', 'price', 'stock_display', 'is_available', 'description', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('price', 'id')
    list_filter = ('is_available', 'created_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'description', 'price'),
            'description': '改名卡允许用户修改一次昵称'
        }),
        ('库存与上架', {
            'fields': ('stock', 'is_available'),
            'description': '库存留空表示无限库存；未上架的商品不会在商城显示'
        }),
        ('时间信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at',)
    
    def stock_display(self, obj):
        """库存显示"""
        if obj.stock is None:
            return '<span style="color: green; font-weight: bold;">无限</span>'
        elif obj.stock > 20:
            return f'<span style="color: green;">{obj.stock}</span>'
        elif obj.stock > 0:
            return f'<span style="color: orange; font-weight: bold;">{obj.stock}</span>'
        else:
            return '<span style="color: red; font-weight: bold;">售罄</span>'
    stock_display.short_description = '库存'
    stock_display.allow_tags = True


@admin.register(PointsTransaction)
class PointsTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'transaction_type', 'points', 'description', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__username', 'description')
    ordering = ('-created_at',)