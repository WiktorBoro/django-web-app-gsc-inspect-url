from django.shortcuts import render
from .models import CredentialsModel
from django.http import HttpResponseRedirect, JsonResponse
import google_auth_oauthlib.flow
from secrets import token_urlsafe
from .gsc_inspect_url.inspect_url import start_inspect
from json import dumps
from datetime import datetime, timedelta
from django.urls import resolve
from django.utils import timezone


icea_flow = google_auth_oauthlib.flow.Flow.from_client_config(cred_icea,
            scopes='https://www.googleapis.com/auth/webmasters.readonly')
icea_redirect_uri = "https://robie-seo.herokuapp.com/inspect-gsc-icea/auth"

normal_flow = google_auth_oauthlib.flow.Flow.from_client_config(cred,
            scopes='https://www.googleapis.com/auth/webmasters.readonly')
normal_redirect_uri = "https://robie-seo.herokuapp.com/inspect-gsc/auth"

def del_old_cred():
    # free heroku server only works when someone is using it, so only then i can delete old files
    for cred in CredentialsModel.objects.all():
        if cred.start_date + timedelta(days=1) < timezone.now():
            cred.delete()


@shared_task(bind=True)
def save_credentials_to_db(self, current_url, authorization_response, token):

    if 'inspect-gsc-icea-auth' == current_url:
        flow = icea_flow
        flow.redirect_uri = icea_redirect_uri
    else:
        flow = normal_flow
        flow.redirect_uri = normal_redirect_uri

    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    credentials_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'id_token': credentials.id_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes,
        'expiry': datetime.strftime(credentials.expiry, '%Y-%m-%d %H:%M:%S')
    }

    CredentialsModel(token=token,
                     credential=dumps(credentials_dict),
                     start_date=datetime.now()).save()
    # free heroku server only works when someone is using it, so only then i can delete old files
    del_old_cred()


def inspect_gsc(response):

    current_url = resolve(response.path_info).url_name

    if 'inspect-gsc-icea' == current_url:
        flow = icea_flow
        flow.redirect_uri = icea_redirect_uri
    else:
        flow = normal_flow
        flow.redirect_uri = normal_redirect_uri

    # get auth url
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scope='true',
        prompt='consent')
    return render(response, f'main/auth.html', {'authorize_url': authorization_url})


def inspect_gsc_auth(response):
    token = token_urlsafe(nbytes=32)

    # Saving credentials on free heroku version it's slow and user's get 500 so I needed to add async function
    current_url = resolve(response.path_info).url_name
    authorization_response = response.build_absolute_uri()
    save_credentials_to_db.delay(current_url=current_url,
                                 authorization_response=authorization_response,
                                 token=token)

    return HttpResponseRedirect(f'/inspect-gsc/auth/{token}')


def inspect_gsc_auth_start(response, token):
    # render page after success auth
    return render(response, f'main/inspect_gsc_auth.html', {'token': token})


def auth_start_inspect(response):
    is_ajax = "robie-seo" in response.headers.get('host')
    if is_ajax and response.method == "POST":
        token = response.POST['token']
        sheets_url = response.POST['sheets_url']

        # start inspect
        start_inspect.delay(token=token, sheets_url=sheets_url)
        return JsonResponse({"Success": "success", "token": token, "sheets_url": sheets_url})
    return JsonResponse({"Error": "error"})
