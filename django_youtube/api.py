import gdata.youtube
import gdata.youtube.service
import os
from django.conf import settings

# Service class is a shared resource
yt_service = gdata.youtube.service.YouTubeService()

# Turn on HTTPS/SSL access.
# Note: SSL is not available at this time for uploads.
yt_service.ssl = False

developer_key = settings.YOUTUBE_DEVELOPER_KEY
client_id = settings.YOUTUBE_CLIENT_ID # client id is not required but will be used for other features like analytics

class OperationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class AccessControl:
    """
    Enum-like structure to determine the permission of a video
    """
    Public, Unlisted, Private = range(3)

def _access_control(access_control):
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
        # set video as private
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

def fetch_video(video_id):
    """
    Retrieve a specific video entry and return it
    @see http://gdata-python-client.googlecode.com/hg/pydocs/gdata.youtube.html#YouTubeVideoEntry
    """
    return yt_service.GetYouTubeVideoEntry('http://gdata.youtube.com/feeds/api/users/default/uploads/%s' % video_id)

def fetch_feed_by_username(username):
    """
    Retrieve the video feed by username
    Returns:
    gdata.youtube.YouTubeVideoFeed object
    """
    # Don't use trailing slash
    youtube_url = 'http://gdata.youtube.com/feeds/api'
    uri = os.sep.join([youtube_url, "users", username, "uploads"])
    return yt_service.GetYouTubeVideoFeed(uri)

def authenticate(email = None, password = None, source = None):
    """
    Adds authentication parameters
    All params are optional, if not set, we will use the ones on the settings
    params are email, password and source. Source is the app id
    """
    # Set the developer key, and optional client id
    yt_service.developer_key = developer_key
    if client_id:
        yt_service.client_id = client_id
    
    # Auth parameters
    yt_service.email = email if email else settings.YOUTUBE_AUTH_EMAIL
    yt_service.password = password if password else settings.YOUTUBE_AUTH_PASSWORD
    yt_service.source = source if source else settings.YOUTUBE_CLIENT_ID
    yt_service.ProgrammaticLogin()

def upload_direct():
    """
    not implemented yet
    """
    pass

def upload(title, description="", keywords="", developer_tags = None, access_control = AccessControl.Public):
    """
    Browser based upload
    
    Creates the video entry and meta data to initiate a browser upload
    
    Params:
        title: string
        description: string
        keywords: comma seperated string
        developer_tags: tuple
    
    Return:
        dict contains post_url and youtube_token. i.e { 'post_url': post_url, 'youtube_token': youtube_token }
    """
    # create media group
    my_media_group = gdata.media.Group(
        title = gdata.media.Title(text=title),
        description = gdata.media.Description(description_type='plain',
                                          text=description),
        keywords = gdata.media.Keywords(text=keywords),
        category = [gdata.media.Category(
            text='Autos',
            scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
            label='Autos')],
        #player = None
    )
    
    # Access Control
    extension = _access_control(access_control)

    # create video entry
    video_entry = gdata.youtube.YouTubeVideoEntry(media=my_media_group, extension_elements=extension)
    
    # add developer tags
    if developer_tags:
        video_entry.AddDeveloperTags(developer_tags)
    
    # upload meta data only
    response = yt_service.GetFormUploadToken(video_entry)
    
    # parse response tuple and use the variables to build a form
    post_url = response[0]
    youtube_token = response[1]
    
    return { 'post_url': post_url, 'youtube_token': youtube_token }

def check_upload_status(video_id):
    """
    Checks the video upload status
    Newsly uploaded videos may be in the processing state
    
    Returns:
        True if video is available
        otherwise a dict containes upload_state and detailed message
        i.e. {"upload_state": "processing", "detailed_message": ""}
    """
    entry = fetch_video(video_id)
    upload_status = yt_service.CheckUploadStatus(entry)
    
    if upload_status is not None:
        video_upload_state = upload_status[0]
        detailed_message = upload_status[1]
        return {"upload_state": video_upload_state, "detailed_message": detailed_message}
    else:
        return True
    
def update_video(video_id, title="", description="", keywords="", access_control=AccessControl.Public):
    """
    Updates the video
    
    Params:
        entry: video entry fetch via 'fetch_video()'
        title: string
        description: string
        keywords: string
    
    Returns:
        a video entry on success
        None otherwise
    """
    
    entry = fetch_video(video_id)
    
    # Set Access Control
    extension = _access_control(access_control)
    entry.extension_elements = extension
    
    if title:
        entry.media.title.text = title
    
    if description:
        entry.media.description.text = description
        
    #if keywords:
    #    entry.media.keywords.text = keywords
    
    return yt_service.UpdateVideoEntry(entry)

def delete_video(video_id):
    """
    Deletes the video
    
    Params:
        entry: video entry fetch via 'fetch_video()'
        
    Return:
        True if successful
        False otherwise
    """
    
    entry = fetch_video(video_id)
    response = yt_service.DeleteVideoEntry(entry)
    return True if response else False
    