from django.conf.urls.defaults import *

urlpatterns = patterns('django_youtube.views',
    # list of the videos
    url(r'^videos/?$', 'video_list', name="youtube_video_list"),

    # video  display page, convenient to use in an iframe
    url(r'^video/(?P<video_id>[\w.@+-]+)/$', 'video', name="youtube_video"),

    # upload page with a form
    url(r'^upload/?$', 'upload', name="youtube_upload"),

    # page that youtube redirects after upload
    url(r'^upload/return/?$', 'upload_return', name="youtube_upload_return"),

    # upload page with a form
    url(r'^direct-upload/?$', 'direct_upload', name="youtube_direct_upload"),

    # remove video, redirects to upload page when it's done
    url(r'^video/remove/(?P<video_id>[\w.@+-]+)/$', 'remove', name="youtube_video_remove"),
)
