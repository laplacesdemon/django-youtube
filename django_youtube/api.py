import os

import gdata.youtube.service
from django.conf import settings
from django.utils.translation import ugettext as _


class OperationError(BaseException):
    """
    Raise when an error happens on Api class
    """
    pass


class ApiError(BaseException):
    """
    Raise when a Youtube API related error occurs
    i.e. redirect Youtube errors with this error
    """
    pass


class AccessControl:
    """
    Enum-like structure to determine the permission of a video
    """
    Public, Unlisted, Private = range(3)


class Api:
    """
    Wrapper for Youtube API
    See: https://developers.google.com/youtube/1.0/developers_guide_python
    """

    # Service class is a shared resource
    yt_service = gdata.youtube.service.YouTubeService()

    def __init__(self):
        try:
            self.developer_key = settings.YOUTUBE_DEVELOPER_KEY
        except AttributeError:
            raise OperationError(
                "Youtube Developer Key is missing on settings.")

        try:
            # client id is not required but will be used for other features like analytics
            self.client_id = settings.YOUTUBE_CLIENT_ID
        except AttributeError:
            self.client_id = None

        # Turn on HTTPS/SSL access.
        # Note: SSL is not available at this time for uploads.
        Api.yt_service.ssl = False

        # Set the developer key, and optional client id
        Api.yt_service.developer_key = self.developer_key
        if self.client_id:
            Api.yt_service.client_id = self.client_id

        self.authenticated = False

    def _access_control(self, access_control, my_media_group=None):
        """
        Prepares the extension element for access control
        Extension element is the optional parameter for the YouTubeVideoEntry
        We use extension element to modify access control settings

        Returns:
            tuple of extension elements
        """
        # Access control
        extension = None
        if access_control is AccessControl.Private:
            # WARNING: this part of code is not tested
            # set video as private
            if my_media_group:
                my_media_group.private = gdata.media.Private()
        elif access_control is AccessControl.Unlisted:
            # set video as unlisted
            from gdata.media import YOUTUBE_NAMESPACE
            from atom import ExtensionElement
            kwargs = {
                "namespace": YOUTUBE_NAMESPACE,
                "attributes": {'action': 'list', 'permission': 'denied'},
            }
            extension = ([ExtensionElement('accessControl', **kwargs)])
        return extension

    def fetch_video(self, video_id):
        """
        Retrieve a specific video entry and return it
        @see http://gdata-python-client.googlecode.com/hg/pydocs/gdata.youtube.html#YouTubeVideoEntry
        """
        return Api.yt_service.GetYouTubeVideoEntry('http://gdata.youtube.com/feeds/api/users/default/uploads/%s' % video_id)

    def fetch_feed_by_username(self, username):
        """
        Retrieve the video feed by username
        Returns:
        gdata.youtube.YouTubeVideoFeed object
        """
        # Don't use trailing slash
        youtube_url = 'http://gdata.youtube.com/feeds/api'
        uri = os.sep.join([youtube_url, "users", username, "uploads"])
        return Api.yt_service.GetYouTubeVideoFeed(uri)

    def authenticate(self, email=None, password=None, source=None):
        """
        Authenticates the user and sets the GData Auth token.
        All params are optional, if not set, we will use the ones on the settings, if no settings found, raises AttributeError
        params are email, password and source. Source is the app id

        Raises:
            gdata.service.exceptions.BadAuthentication
        """
        from gdata.service import BadAuthentication

        # Auth parameters
        Api.yt_service.email = email if email else settings.YOUTUBE_AUTH_EMAIL
        Api.yt_service.password = password if password else settings.YOUTUBE_AUTH_PASSWORD
        Api.yt_service.source = source if source else settings.YOUTUBE_CLIENT_ID
        try:
            Api.yt_service.ProgrammaticLogin()
            self.authenticated = True
        except BadAuthentication:
            raise ApiError(_("Incorrect username or password"))

    def upload_direct(self, video_path, title, description="", keywords="", developer_tags=None, access_control=AccessControl.Public):
        """
        Direct upload method:
            Uploads the video directly from your server to Youtube and creates a video

        Returns:
            gdata.youtube.YouTubeVideoEntry

        See: https://developers.google.com/youtube/1.0/developers_guide_python#UploadingVideos
        """
        # prepare a media group object to hold our video's meta-data
        my_media_group = gdata.media.Group(
            title=gdata.media.Title(text=title),
            description=gdata.media.Description(description_type='plain',
                                                text=description),
            keywords=gdata.media.Keywords(text=keywords),
            category=[gdata.media.Category(
                text='Autos',
                scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
                label='Autos')],
            #player = None
        )

        # Access Control
        extension = self._access_control(access_control, my_media_group)

        # create the gdata.youtube.YouTubeVideoEntry to be uploaded
        video_entry = gdata.youtube.YouTubeVideoEntry(media=my_media_group, extension_elements=extension)

        # add developer tags
        if developer_tags:
            video_entry.AddDeveloperTags(developer_tags)

        # upload the video and create a new entry
        new_entry = Api.yt_service.InsertVideoEntry(video_entry, video_path)

        return new_entry

    def upload(self, title, description="", keywords="", developer_tags=None, access_control=AccessControl.Public):
        """
        Browser based upload
        Creates the video entry and meta data to initiate a browser upload

        Authentication is needed

        Params:
            title: string
            description: string
            keywords: comma seperated string
            developer_tags: tuple

        Return:
            dict contains post_url and youtube_token. i.e { 'post_url': post_url, 'youtube_token': youtube_token }

        Raises:
            ApiError: on no authentication
        """
        # Raise ApiError if not authenticated
        if not self.authenticated:
            raise ApiError(_("Authentication is required"))

        # create media group
        my_media_group = gdata.media.Group(
            title=gdata.media.Title(text=title),
            description=gdata.media.Description(description_type='plain',
                                                text=description),
            keywords=gdata.media.Keywords(text=keywords),
            category=[gdata.media.Category(
                text='Autos',
                scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
                label='Autos')],
            #player = None
        )

        # Access Control
        extension = self._access_control(access_control, my_media_group)

        # create video entry
        video_entry = gdata.youtube.YouTubeVideoEntry(
            media=my_media_group, extension_elements=extension)

        # add developer tags
        if developer_tags:
            video_entry.AddDeveloperTags(developer_tags)

        # upload meta data only
        response = Api.yt_service.GetFormUploadToken(video_entry)

        # parse response tuple and use the variables to build a form
        post_url = response[0]
        youtube_token = response[1]

        return {'post_url': post_url, 'youtube_token': youtube_token}

    def check_upload_status(self, video_id):
        """
        Checks the video upload status
        Newly uploaded videos may be in the processing state

        Authentication is required

        Returns:
            True if video is available
            otherwise a dict containes upload_state and detailed message
            i.e. {"upload_state": "processing", "detailed_message": ""}
        """
        # Raise ApiError if not authenticated
        if not self.authenticated:
            raise ApiError(_("Authentication is required"))

        entry = self.fetch_video(video_id)
        upload_status = Api.yt_service.CheckUploadStatus(entry)

        if upload_status is not None:
            video_upload_state = upload_status[0]
            detailed_message = upload_status[1]
            return {"upload_state": video_upload_state, "detailed_message": detailed_message}
        else:
            return True

    def update_video(self, video_id, title="", description="", keywords="", access_control=AccessControl.Unlisted):
        """
        Updates the video

        Authentication is required

        Params:
            entry: video entry fetch via 'fetch_video()'
            title: string
            description: string
            keywords: string

        Returns:
            a video entry on success
            None otherwise
        """

        # Raise ApiError if not authenticated
        if not self.authenticated:
            raise ApiError(_("Authentication is required"))

        entry = self.fetch_video(video_id)

        # Set Access Control
        extension = self._access_control(access_control)
        if extension:
            entry.extension_elements = extension

        if title:
            entry.media.title.text = title

        if description:
            entry.media.description.text = description

        #if keywords:
        #    entry.media.keywords.text = keywords

        success = Api.yt_service.UpdateVideoEntry(entry)
        return success
        #if success is None:
        #    raise OperationError(_("Cannot update video on Youtube"))

    def delete_video(self, video_id):
        """
        Deletes the video

        Authentication is required

        Params:
            entry: video entry fetch via 'fetch_video()'

        Return:
            True if successful

        Raise:
            OperationError: on unsuccessful deletion
        """
        # Raise ApiError if not authenticated
        if not self.authenticated:
            raise ApiError(_("Authentication is required"))

        entry = self.fetch_video(video_id)
        response = Api.yt_service.DeleteVideoEntry(entry)

        if not response:
            raise OperationError(_("Cannot be deleted from Youtube"))

        return True
