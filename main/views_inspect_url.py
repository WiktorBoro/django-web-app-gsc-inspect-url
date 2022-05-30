from django.shortcuts import render
from .models import CredentialsModel
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from oauth2client.client import flow_from_clientsecrets
from oauth2client.contrib.django_util.views import settings
from oauth2client.contrib.django_util.storage import DjangoORMStorage
from oauth2client.contrib import xsrfutil
from secrets import token_urlsafe
from .gsc_inspect_url.inspect_url import  start_inspect
from json import loads

FLOW = flow_from_clientsecrets(
    settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON,
    scope=settings.GOOGLE_OAUTH2_SCOPE,
    redirect_uri=settings.GOOGLE_OAUTH2_REDIRECT_URL)


def inspect_gsc(response):
    FLOW.params['state'] = xsrfutil.generate_token(settings.SECRET_KEY,
                                                   response.user)
    authorize_url = FLOW.step1_get_authorize_url()
    return render(response, f'main/auth.html', {'authorize_url': authorize_url})


def inspect_gsc_auth(response):
    token = token_urlsafe(nbytes=32)
    if not xsrfutil.validate_token(settings.SECRET_KEY,
                                   response.POST.get('state', response.GET.get('state')).encode('UTF-8'),
                                   response.user):
        return HttpResponseBadRequest()
    credential = FLOW.step2_exchange(response.GET)
    storage = DjangoORMStorage(CredentialsModel, 'token', token, 'credential')
    storage.put(credential)

    return HttpResponseRedirect(f'inspect-gsc/auth/{token}')


def inspect_gsc_auth_start(response):
    return render(response, f'main/auth.html', {})


def start_gsc_auth_start(response,):
    is_ajax = "robie-seo" in response.headers.get('host')
    data = loads(response.body)
    token = data['token']
    sheets_url = data['sheets_url']
    if is_ajax and response.method == "POST":
        start_inspect.delay(token=token, sheets_url=sheets_url)
