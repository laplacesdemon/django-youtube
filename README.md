Django Youtube
==============

Django Youtube is a wrapper app around youtube api. It helps you to implement frequent api operations easily.

The main functionality is to use Youtube API to upload videos and show them in your website.
In order use this app, you need a developer account on Youtube and use them to authenticate, and upload videos into this account.

Django Youtube designed to work with built in `contrib.auth` app, although you can modify the views.py to work without authentication.

Please feel free to fork and contribute! There are lots of things that I am not happy with, if you're interested, send a message.

Features
--------

1. Retrieve specific videos
3. Browser based upload
4. Programmatic Authentication
5. Admin panel ready
6. Supports i18n
7. Direct upload

Features are not yet implemented
--------------------------------

1. Retrieve feeds (most visited etc)
2. oAuth authentication

Dependencies
------------

gdata python library (http://code.google.com/p/gdata-python-client/downloads/list)

Installation
------------

Run `pip install django-youtube` or add `django_youtube` folder at your python path.

Add `django_youtube` to your installed apps

Add following lines to your settings.py and edit them accordingly

    YOUTUBE_AUTH_EMAIL = 'yourmail@gmail.com'
    YOUTUBE_AUTH_PASSWORD = 'yourpassword'
    YOUTUBE_DEVELOPER_KEY = 'developer key, get one from http://code.google.com/apis/youtube/dashboard/'
    YOUTUBE_CLIENT_ID = 'client-id'
    
Optionally you can add following lines to your settings. If you don't set them, default settings will be used.
    
    # url to redirect after upload finishes, default is respected `video` page
    YOUTUBE_UPLOAD_REDIRECT_URL = '/youtube/videos/'

    # url to redirect after deletion video, default is `upload page`
    YOUTUBE_DELETE_REDIRECT_URL = '/myurl/'

Add Following lines to your urls.py file

    (r'^youtube/', include('django_youtube.urls')),
    
Don't forget to run `manage.py syncdb`

Usage
-----

Go to `/youtube/upload/` to upload video files directly to youtube. When you upload a file, the video entry is created on youtube, `Video` model that includes video details (`video_id`, `title`, etc.) created on your db and a signal sent that you can add your logic to it.
After successful upload, it redirects to the specified page at `YOUTUBE_UPLOAD_REDIRECT_URL`, if no page is specified, it redirects to the corresponding video page.

Youtube API is integrated to the `Video` model. In order to change information of the video on Youtube, just save the model instance as you normally do, `django_youtube` will do the necessary changes using Youtube API.

Api methods can be used separately. Please see `api.py` to get info about methods. Please note that some operations requires authentication. Api methods will not do more than one operation, i.e. will not call authenticate method. So you will need to authenticate manually. Otherwise api methods will raise `OperationError`.  Please see `views.py` for a sample implementation.

You can use views for uploading, displaying, deleting the videos.

You can also override templates to customise the html. `Iframe API` used for displaying the videos for convenience. Please see Youtube API Docs (https://developers.google.com/youtube/) to implement other player API's on your template files. Other options are `Javascript API` and `Flash API`.

Signals
-------

The `video_created` sent after video upload finished and video created successfully. You can also choose to register `post_save` event of `Video` model
Following is an example of how you process the signal

    from django_youtube.models import video_created
    from django.dispatch import receiver
    
    @receiver(video_created)
    def video_created_callback(sender, **kwargs):
        """
        Youtube Video is created.
        Not it's time to do something about it
    """
    pass
