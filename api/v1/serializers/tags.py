"""
Serializers for Tags API endpoints.
"""
from rest_framework import serializers
from taggit.models import Tag


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tags."""

    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug', 'usage_count')
        read_only_fields = ('id', 'slug')

    def get_usage_count(self, obj):
        """Get total usage count across all tagged items."""
        # This returns the total count of times this tag is used
        return obj.taggit_taggeditem_items.count()
