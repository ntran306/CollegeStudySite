from django.contrib import admin
from .models import Class

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'student_count', 'tutor_count']
    search_fields = ['name']
    list_filter = ['created_at']
    ordering = ['name']
    readonly_fields = ['created_at']
    
    # Add custom columns to show usage
    def student_count(self, obj):
        """Show how many students are taking this class"""
        return obj.student_skills.count()
    student_count.short_description = 'Students Taking'
    
    def tutor_count(self, obj):
        """Show how many tutors are teaching this class"""
        return obj.tutors.count()
    tutor_count.short_description = 'Tutors Teaching'
    
    # Optional: Add actions for bulk management
    actions = ['mark_for_review', 'approve_classes']
    
    def mark_for_review(self, request, queryset):
        """Custom action to flag classes for review"""
        # You could add a 'needs_review' field to the model if needed
        self.message_user(request, f"{queryset.count()} classes marked for review.")
    mark_for_review.short_description = "Mark selected classes for review"
    
    def approve_classes(self, request, queryset):
        """Custom action to approve classes"""
        self.message_user(request, f"{queryset.count()} classes approved.")
    approve_classes.short_description = "Approve selected classes"
    
    # Show sessions using this class
    def get_queryset(self, request):
        """Optimize queries by prefetching related data"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('student_skills', 'tutors')
    
    # Make it easy to see related objects
    fieldsets = (
        ('Class Information', {
            'fields': ('name', 'created_at')
        }),
    )