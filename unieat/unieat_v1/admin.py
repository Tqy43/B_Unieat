from django.contrib import admin
from .models import Welcome
from .models import Banner
from .models import Canteen, Stall, Dish
from .models import UserProfile
from .models import ConsumptionRecord, ConsumptionItem

admin.site.register(Welcome)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'uploaded_at')
    ordering = ('-order', '-uploaded_at')

admin.site.register(Canteen)
admin.site.register(Stall)
admin.site.register(Dish)
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