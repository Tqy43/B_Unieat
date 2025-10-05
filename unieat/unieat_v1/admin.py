from django.contrib import admin
from .models import Welcome, Banner, Canteen, Stall, Dish, UserProfile, ConsumptionRecord, ConsumptionItem, Feedback

admin.site.register(Welcome)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'uploaded_at')
    ordering = ('-order', '-uploaded_at')

admin.site.register(Canteen)
admin.site.register(UserProfile)

class ConsumptionItemInline(admin.TabularInline):
    model = ConsumptionItem
    extra = 0

@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "stall", "total_amount", "items_count", "consumed_at", "created_at")
    list_filter = ("stall__canteen", "stall", "consumed_at")
    search_fields = ("user__username", "stall__name")
    inlines = [ConsumptionItemInline]

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    在后台管理界面中显示反馈数据
    """
    list_display = ("id", "description", "contact", "created_at")
    search_fields = ("description", "contact")  # 支持搜索
    list_filter = ("created_at",)  # 按提交时间过滤

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