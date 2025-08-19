from django.contrib import admin
from .models import Welcome
from .models import Banner
from .models import Canteen, Stall, Dish

admin.site.register(Welcome)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'uploaded_at')
    ordering = ('-order', '-uploaded_at')

admin.site.register(Canteen)
admin.site.register(Stall)
admin.site.register(Dish)
