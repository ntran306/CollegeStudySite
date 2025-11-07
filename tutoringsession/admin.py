from django.contrib import admin
from .models import TutoringSession, SessionRequest


class SessionRequestInline(admin.TabularInline):
    model = SessionRequest
    extra = 0
    readonly_fields = ('student', 'created_at', 'note')
    fields = ('student', 'status', 'note', 'created_at')
    can_delete = False


@admin.register(TutoringSession)
class TutoringSessionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'tutor', 'date', 'start_time', 'end_time', 'location', 'seats_taken', 'capacity', 'is_full')
    list_filter = ('date', 'is_remote', 'subject', 'tutor')
    search_fields = ('subject', 'tutor__username', 'location', 'description')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tutor', 'subject', 'description')
        }),
        ('Schedule', {
            'fields': ('date', 'start_time', 'end_time')
        }),
        ('Location', {
            'fields': ('is_remote', 'location', 'latitude', 'longitude')
        }),
        ('Capacity', {
            'fields': ('capacity',)
        }),
    )
    
    inlines = [SessionRequestInline]
    
    def seats_taken(self, obj):
        return obj.seats_taken()
    seats_taken.short_description = 'Seats Taken'


@admin.register(SessionRequest)
class SessionRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'session', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__username', 'session__subject', 'note')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Request Information', {
            'fields': ('session', 'student', 'note')
        }),
        ('Status', {
            'fields': ('status', 'created_at')
        }),
    )