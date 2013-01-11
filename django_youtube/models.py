from django.db import models
from django_youtube.api import AccessControl, Api
import django.dispatch
from django.utils.translation import ugettext as _


class Video(models.Model):
    user = models.ForeignKey('auth.User')
    video_id = models.CharField(max_length=255, unique=True, null=True,
                                help_text=_("The Youtube id of the video"))
    title = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    keywords = models.CharField(max_length=200, null=True, blank=True,
                                help_text=_("Comma seperated keywords"))
    youtube_url = models.URLField(max_length=255, null=True, blank=True)
    swf_url = models.URLField(max_length=255, null=True, blank=True)
    access_control = models.SmallIntegerField(max_length=1,
                                              choices=(
                                              (AccessControl.Public,
                                               "Public"),
                                              (AccessControl.Unlisted,
                                               "Unlisted"),
                                              (AccessControl.Private,
                                               "Private"),
                                              ),
                                              default=AccessControl.Public)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        """
        Returns the swf url
        """
        return self.swf_url

    def entry(self):
        """
        Connects to Youtube Api and retrieves the video entry object

        Return:
            gdata.youtube.YouTubeVideoEntry
        """
        api = Api()
        api.authenticate()
        return api.fetch_video(self.video_id)

    def save(self, *args, **kwargs):
        """
        Syncronize the video information on db with the video on Youtube
        The reason that I didn't use signals is to avoid saving the video instance twice.
        """

        # if this is a new instance add details from api
        if not self.id:
            # Connect to api and get the details
            entry = self.entry()

            # Set the details
            self.title = entry.media.title.text
            self.description = entry.media.description.text
            self.keywords = entry.media.keywords.text
            self.youtube_url = entry.media.player.url
            self.swf_url = entry.GetSwfUrl()
            if entry.media.private:
                self.access_control = AccessControl.Private
            else:
                self.access_control = AccessControl.Public

            # Save the instance
            super(Video, self).save(*args, **kwargs)

            # show thumbnails
            for thumbnail in entry.media.thumbnail:
                t = Thumbnail()
                t.url = thumbnail.url
                t.video = self
                t.save()
        else:
            # updating the video instance
            # Connect to API and update video on youtube
            api = Api()

            # update method needs authentication
            api.authenticate()

            # Update the info on youtube, raise error on failure
            api.update_video(self.video_id, self.title, self.description,
                             self.keywords, self.access_control)

        # Save the model
        return super(Video, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Deletes the video from youtube

        Raises:
            OperationError
        """
        api = Api()

        # Authentication is required for deletion
        api.authenticate()

        # Send API request, raises OperationError on unsuccessful deletion
        api.delete_video(self.video_id)

        # Call the super method
        return super(Video, self).delete(*args, **kwargs)

    def default_thumbnail(self):
        """
        Returns the 1st thumbnail in thumbnails
        This method can be updated as adding default attribute the Thumbnail model and return it

        Returns:
            Thumbnail object
        """
        return self.thumbnail_set.all()[0]


class Thumbnail(models.Model):
    video = models.ForeignKey(Video, null=True)
    url = models.URLField(max_length=255)

    def __unicode__(self):
        return self.url

    def get_absolute_url(self):
        return self.url


class UploadedVideo(models.Model):
    """
    temporary video object that is uploaded to use in direct upload
    """

    file_on_server = models.FileField(upload_to='videos', null=True,
                                      help_text=_("Temporary file on server for \
                                              using in `direct upload` from \
                                              your server to youtube"))

    def __unicode__(self):
        """string representation"""
        return self.file_on_server.url
#
# Signal Definitions
#

video_created = django.dispatch.Signal(providing_args=["video"])
