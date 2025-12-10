from django import template
register = template.Library()

@register.filter
def get_request_for(requests, user):
    return requests.filter(student=user).first()
