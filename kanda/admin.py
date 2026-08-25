from django.contrib import admin
from .models import Mshiriki, Ibada, Uthibitisho, SMSConfig, Mahudhurio, SMSLog

@admin.register(Mshiriki)
class MshirikiAdmin(admin.ModelAdmin):
    list_display = ('jina', 'simu', 'familia', 'jukumu', 'cheo', 'is_active', 'created_at')
    list_filter = ('jukumu', 'is_active')
    search_fields = ('jina', 'simu', 'familia')
    ordering = ('jina',)

@admin.register(Ibada)
class IbadaAdmin(admin.ModelAdmin):
    list_display = ('mwenyeji', 'tarehe_muda', 'is_completed', 'created_at')
    list_filter = ('is_completed',)
    search_fields = ('mwenyeji', 'masomo', 'maelekezo')
    ordering = ('-tarehe_muda',)

@admin.register(Uthibitisho)
class UthibitishoAdmin(admin.ModelAdmin):
    list_display = ('mshiriki', 'ibada', 'status', 'updated_at')
    list_filter = ('status', 'ibada')
    search_fields = ('mshiriki__jina', 'ibada__mwenyeji', 'maoni')

@admin.register(SMSConfig)
class SMSConfigAdmin(admin.ModelAdmin):
    list_display = ('sender_id', 'is_active')

@admin.register(Mahudhurio)
class MahudhurioAdmin(admin.ModelAdmin):
    list_display = ('mshiriki', 'ibada', 'is_present', 'created_at')
    list_filter = ('is_present', 'ibada')
    search_fields = ('mshiriki__jina', 'ibada__mwenyeji')

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('phone', 'type', 'status', 'ibada', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('phone', 'message', 'mshiriki__jina', 'ibada__mwenyeji')
    ordering = ('-created_at',)
    readonly_fields = ('mshiriki', 'ibada', 'type', 'status', 'phone', 'message', 'error', 'created_at')
