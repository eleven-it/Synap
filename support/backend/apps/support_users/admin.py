from django.contrib import admin
from .models import SupportUser, ChannelIdentity


class ChannelIdentityInline(admin.TabularInline):
    model = ChannelIdentity
    extra = 0


@admin.register(SupportUser)
class SupportUserAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_authorized", "language")
    list_filter = ("company", "is_authorized")
    inlines = [ChannelIdentityInline]


@admin.register(ChannelIdentity)
class ChannelIdentityAdmin(admin.ModelAdmin):
    list_display = ("channel_type", "external_id", "support_user")
