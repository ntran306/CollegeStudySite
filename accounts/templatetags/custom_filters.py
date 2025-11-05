from django import template

register = template.Library()

@register.filter
def has_studentprofile(user):
    """Check if a user has an associated StudentProfile"""
    return hasattr(user, 'studentprofile')

@register.filter
def has_tutorprofile(user):
    """Check if a user has an associated TutorProfile"""
    return hasattr(user, 'tutorprofile')
