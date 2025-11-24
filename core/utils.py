import os
import uuid
from django.utils.text import slugify


def generate_unique_slug(instance, field_name, slug_field_name='slug'):
    """
    Generate a unique slug for a model instance.
    """
    slug = slugify(getattr(instance, field_name))
    if not slug:
        slug = str(uuid.uuid4())[:8]
    
    # Check if slug already exists
    model = instance.__class__
    original_slug = slug
    counter = 1
    
    while model.objects.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        slug = f"{original_slug}-{counter}"
        counter += 1
    
    return slug


def get_file_path(instance, filename):
    """
    Generate a unique file path for uploaded files.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', filename)
