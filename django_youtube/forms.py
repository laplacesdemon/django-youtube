from django import forms

class YoutubeUploadForm(forms.Form):
    token = forms.CharField()
    file = forms.FileField()