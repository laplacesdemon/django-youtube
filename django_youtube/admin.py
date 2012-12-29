import models
from django.contrib import admin


class ThumbnailInline(admin.StackedInline):
    model = models.Thumbnail
    fk_name = 'video'
    extra = 0


class VideoAdmin(admin.ModelAdmin):
    readonly_fields = ('video_id', 'youtube_url', 'swf_url',)
    inlines = [ThumbnailInline]
    list_filter = ('title', 'user__username',)
    search_fields = ['title', 'user__first_name', 'user__email',
                     'user__username', 'keywords', ]

    list_display = ('title', 'video_id', 'swf',)

    def swf(self, instance):
        return '<a href="%s">Swf link</a>' % (instance.get_absolute_url())
    swf.allow_tags = True


admin.site.register(models.Video, VideoAdmin)
