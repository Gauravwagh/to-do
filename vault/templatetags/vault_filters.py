"""
Custom template filters for vault app.
"""
from django import template
from django.utils.safestring import mark_safe
import markdown as md

register = template.Library()


@register.filter(name='markdown')
def markdown_format(text):
    """
    Convert markdown text to HTML.

    Usage:
        {{ note.decrypted_content|markdown }}
    """
    if not text:
        return ''

    # Configure markdown extensions
    extensions = [
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
    ]

    # Convert markdown to HTML
    html = md.markdown(text, extensions=extensions)

    # Mark as safe to prevent HTML escaping
    return mark_safe(html)
