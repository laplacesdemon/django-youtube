from django.shortcuts import render_to_response
from django.views.decorators.http import require_http_methods
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django_youtube.api import Api, AccessControl, ApiError
from django_youtube.models import video_created, Video
from django_youtube.forms import YoutubeUploadForm, YoutubeDirectUploadForm
from django.views.decorators.csrf import csrf_exempt
import logging
import json

logger = logging.getLogger(__name__)


def _video_params(request, video_id):

    width = request.GET.get("width", "70%")
    height = request.GET.get("height", "350")
    origin = request.get_host()

    return {"video_id": video_id, "origin": origin, "width": width, "height": height}


def check_video_availability(request, video_id):
    """
    Controls the availability of the video. Newly uploaded videos are in processing stage.
    And others might be rejected.

    Returns:
        json response
    """
    # Check video availability
    # Available states are: processing
    api = Api()
    api.authenticate()
    availability = api.check_upload_status(video_id)

    if availability is not True:
        data = {'success': False}
    else:
        data = {'success': True}

    return HttpResponse(json.dumps(data), content_type="application/json")


def video(request, video_id):
    """
    Displays a video in an embed player
    """

    # Check video availability
    # Available states are: processing
    api = Api()
    api.authenticate()
    availability = api.check_upload_status(video_id)

    if availability is not True:
        # Video is not available
        video = Video.objects.filter(video_id=video_id).get()

        state = availability["upload_state"]

        # Add additional states here. I'm not sure what states are available
        if state == "failed" or state == "rejected":
            return render_to_response(
                "django_youtube/video_failed.html",
                {"video": video, "video_id": video_id, "message":
                    _("Invalid video."), "availability": availability},
                context_instance=RequestContext(request)
            )
        else:
            return render_to_response(
                "django_youtube/video_unavailable.html",
                {"video": video, "video_id": video_id,
                 "message": _("This video is currently being processed"), "availability": availability},
                context_instance=RequestContext(request)
            )

    video_params = _video_params(request, video_id)

    return render_to_response(
        "django_youtube/video.html",
        video_params,
        context_instance=RequestContext(request)
    )


def video_list(request, username=None):
    """
    list of videos of a user
    if username does not set, shows the currently logged in user
    """

    # If user is not authenticated and username is None, raise an error
    if username is None and not request.user.is_authenticated():
        from django.http import Http404
        raise Http404

    from django.contrib.auth.models import User
    user = User.objects.get(username=username) if username else request.user

    # loop through the videos of the user
    videos = Video.objects.filter(user=user).all()
    video_params = []
    for video in videos:
        video_params.append(_video_params(request, video.video_id))

    return render_to_response(
        "django_youtube/videos.html",
        {"video_params": video_params},
        context_instance=RequestContext(request)
    )


@csrf_exempt
@login_required
def direct_upload(request):
    """
    direct upload method
    starts with uploading video to our server
    then sends the video file to youtube

    param:
        (optional) `only_data`: if set, a json response is returns i.e. {'video_id':'124weg'}

    return:
        if `only_data` set, a json object.
        otherwise redirects to the video display page
    """
    if request.method == "POST":
        try:
            form = YoutubeDirectUploadForm(request.POST, request.FILES)
            # upload the file to our server
            if form.is_valid():
                uploaded_video = form.save()

                # send this file to youtube
                api = Api()
                api.authenticate()
                video_entry = api.upload_direct(uploaded_video.file_on_server.path, "Uploaded video from zuqqa")

                # get data from video entry
                swf_url = video_entry.GetSwfUrl()
                youtube_url = video_entry.id.text

                # getting video_id is tricky, I can only reach the url which
                # contains the video_id.
                # so the only option is to parse the id element
                # https://groups.google.com/forum/?fromgroups=#!topic/youtube-api-gdata/RRl_h4zuKDQ
                url_parts = youtube_url.split("/")
                url_parts.reverse()
                video_id = url_parts[0]

                # save video_id to video instance
                video = Video()
                video.user = request.user
                video.video_id = video_id
                video.title = 'tmp video'
                video.youtube_url = youtube_url
                video.swf_url = swf_url
                video.save()

                # send a signal
                video_created.send(sender=video, video=video)

                # delete the uploaded video instance
                uploaded_video.delete()

                # return the response
                return_only_data = request.GET.get('only_data')
                if return_only_data:
                    return HttpResponse(json.dumps({"video_id": video_id}), content_type="application/json")
                else:
                    # Redirect to the video page or the specified page
                    try:
                        next_url = settings.YOUTUBE_UPLOAD_REDIRECT_URL
                    except AttributeError:
                        next_url = reverse(
                            "django_youtube.views.video", kwargs={"video_id": video_id})

                    return HttpResponseRedirect(next_url)
        except:
            import sys
            logger.error("Unexpected error: %s - %s" % (sys.exc_info()[
                0], sys.exc_info()[1]))
            # @todo: proper error management
            return HttpResponse("error happened")

    form = YoutubeDirectUploadForm()

    if return_only_data:
        return HttpResponse(json.dumps({"error": 500}), content_type="application/json")
    else:
        return render_to_response(
            "django_youtube/direct-upload.html",
            {"form": form},
            context_instance=RequestContext(request)
        )


@login_required
def upload(request):
    """
    Displays an upload form
    Creates upload url and token from youtube api and uses them on the form
    """
    # Get the optional parameters
    title = request.GET.get("title", "%s's video on %s" % (
        request.user.username, request.get_host()))
    description = request.GET.get("description", "")
    keywords = request.GET.get("keywords", "")

    # Try to create post_url and token to create an upload form
    try:
        api = Api()

        # upload method needs authentication
        api.authenticate()

        # Customize following line to your needs, you can add description, keywords or developer_keys
        # I prefer to update video information after upload finishes
        data = api.upload(title, description=description, keywords=keywords,
                          access_control=AccessControl.Unlisted)
    except ApiError as e:
        # An api error happened, redirect to homepage
        messages.add_message(request, messages.ERROR, e.message)
        return HttpResponseRedirect("/")
    except:
        # An error happened, redirect to homepage
        messages.add_message(request, messages.ERROR, _(
            'An error occurred during the upload, Please try again.'))
        return HttpResponseRedirect("/")

    # Create the form instance
    form = YoutubeUploadForm(initial={"token": data["youtube_token"]})

    protocol = 'https' if request.is_secure() else 'http'
    next_url = '%s://%s%s/' % (protocol, request.get_host(), reverse("django_youtube.views.upload_return"))
    return render_to_response(
        "django_youtube/upload.html",
        {"form": form, "post_url": data["post_url"], "next_url": next_url},
        context_instance=RequestContext(request)
    )


@login_required
def upload_return(request):
    """
    The upload result page
    Youtube will redirect to this page after upload is finished
    Saves the video data and redirects to the next page

    Params:
        status: status of the upload (200 for success)
        id: id number of the video
    """
    status = request.GET.get("status")
    video_id = request.GET.get("id")

    if status == "200" and video_id:
        # upload is successful

        # save the video entry
        video = Video()
        video.user = request.user
        video.video_id = video_id
        video.save()

        # send a signal
        video_created.send(sender=video, video=video)

        # Redirect to the video page or the specified page
        try:
            next_url = settings.YOUTUBE_UPLOAD_REDIRECT_URL
        except AttributeError:
            next_url = reverse(
                "django_youtube.views.video", kwargs={"video_id": video_id})

        return HttpResponseRedirect(next_url)
    else:
        # upload failed, redirect to upload page
        from django.contrib import messages
        messages.add_message(
            request, messages.ERROR, _('Upload failed, Please try again.'))
        return HttpResponseRedirect(reverse("django_youtube.views.upload"))


@login_required
@require_http_methods(["POST"])
def remove(request, video_id):
    """
    Removes the video from youtube and from db
    Requires POST
    """

    # prepare redirection url
    try:
        next_url = settings.YOUTUBE_DELETE_REDIRECT_URL
    except AttributeError:
        next_url = reverse("django_youtube.views.upload")

    # Remove from db
    try:
        Video.objects.get(video_id=video_id).delete()
    except:
        from django.contrib import messages
        messages.add_message(
            request, messages.ERROR, _('Video could not be deleted.'))

    # Return to upload page or specified page
    return HttpResponseRedirect(next_url)
