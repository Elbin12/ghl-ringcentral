from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


import requests, base64
from datetime import datetime, timedelta, timezone
from django.utils.timezone  import now
from django.utils import timezone as dj_timezone

import pytz 

from .models import GHLAuthCredentials, RCToken, GHLContactCache, CeleryIntegrationToggle
from .utils import *
from urllib.parse import quote

import json


# Create your views here.

GHL_CONV_PROVIDER_ID = settings.GHL_CONV_PROVIDER_ID
GHL_CLIENT_ID = settings.GHL_CLIENT_ID
GHL_REDIRECTED_URI = settings.GHL_REDIRECTED_URI
BASE_URI = settings.BASE_URI
GHL_CLIENT_SECRET = settings.GHL_CLIENT_SECRET
TOKEN_URL = "https://services.leadconnectorhq.com/oauth/token"

RINGCENTRAL_CLIENT_ID = settings.RINGCENTRAL_CLIENT_ID
RINGCENTRAL_CLIENT_SECRET = settings.RINGCENTRAL_CLIENT_SECRET
RINGCENTRAL_JWT = settings.RINGCENTRAL_JWT
RINGCENTRAL_PHONE = settings.RINGCENTRAL_PHONE

denver_tz = pytz.timezone("America/Denver")

def auth_connect(request):
    scopes = "conversations.readonly conversations.write conversations/message.readonly conversations/message.write contacts.readonly contacts.write"
    encoded_scopes = quote(scopes)
    auth_url = ("https://marketplace.leadconnectorhq.com/oauth/chooselocation?response_type=code&"
                f"redirect_uri={GHL_REDIRECTED_URI}&"
                f"client_id={GHL_CLIENT_ID}&"
                f"scope={scopes}"
                )
    return redirect(auth_url)

def callback(request):
    code = request.GET.get('code')

    if not code:
        return JsonResponse({"error": "Authorization code not received from OAuth"}, status=400)

    return redirect(f'{BASE_URI}/auth/tokens?code={code}')

def tokens(request):
    authorization_code = request.GET.get("code")
    if not authorization_code:
        return JsonResponse({"error": "Authorization code not found"}, status=400)
    
    data = {
        "grant_type": "authorization_code",
        "client_id": GHL_CLIENT_ID,
        "client_secret": GHL_CLIENT_SECRET,
        "redirect_uri": GHL_REDIRECTED_URI,
        "code": authorization_code,
    }

    response = requests.post(TOKEN_URL, data=data)
    try:
        response_data = response.json()
        print(response.json(), 'from tokensss')
        if not response_data.get('access_token'):
            return JsonResponse({"message": "Invalid JSON response from API"})
        
        obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= response_data.get("locationId"),
            defaults={
                "access_token": response_data.get("access_token"),
                "refresh_token": response_data.get("refresh_token"),
                "expires_in": response_data.get("expires_in"),
                "scope": response_data.get("scope"),
                "user_type": response_data.get("userType"),
                "company_id": response_data.get("companyId"),
                "user_id":response_data.get("userId"),
            }
        )

        print(response_data, 'response_data')

        return JsonResponse({'success':'Authentication Successfull.'})

    except requests.exceptions.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON response'})
    

def get_auth_from_jwt(request):
    url = "https://platform.ringcentral.com/restapi/oauth/token"

    client_credentials = f"{RINGCENTRAL_CLIENT_ID}:{RINGCENTRAL_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(client_credentials.encode("utf-8")).decode("utf-8")

    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": RINGCENTRAL_JWT
    }
    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
        'Accept': "application/json",
        'Authorization': f"Basic {encoded_credentials}"
    }

    response = requests.post(url, data=payload, headers=headers)
    if response.status_code != 200:
        return None
    response_data = response.json()
    print(response_data)
    response_data['ghl_location_id'] = GHLAuthCredentials.objects.first().location_id
    response_data['rc_phone_no'] = RINGCENTRAL_PHONE
    response_data['jwt_code'] = RINGCENTRAL_JWT
    response_data['client_id'] = RINGCENTRAL_CLIENT_ID
    response_data['client_secret'] = RINGCENTRAL_CLIENT_SECRET
    token_obj = create_token(response_data)

    return JsonResponse({
        "message": "Token created successfully",
        "token_id": token_obj.id,
        "access_token": token_obj.access_token
    })

def refresh_ringcentral_token(token):
    url = "https://platform.ringcentral.com/restapi/oauth/token"

    RC_CLIENT_ID = token.client_id
    RC_CLIENT_SECRET = token.client_secret

    client_credentials = f"{RC_CLIENT_ID}:{RC_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(client_credentials.encode("utf-8")).decode("utf-8")

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": token.refresh_token
    }
    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
        'Accept': "application/json",
        'Authorization': f"Basic {encoded_credentials}"
    }
    ghl_location_id = token.ghl_location_id
    rc_phone_no = token.rc_phone_no
    jwt_code = token.jwt_code
    response = requests.post(url, data=payload, headers=headers)
    response_data = response.json()
    print(response_data)
    response_data['ghl_location_id'] = ghl_location_id
    response_data['rc_phone_no'] = rc_phone_no
    response_data['jwt_code'] = jwt_code
    response_data['client_id'] = RC_CLIENT_ID
    response_data['client_secret'] = RC_CLIENT_SECRET
    return create_token(response_data)

def get_company_call_records():
    url = "https://platform.ringcentral.com/restapi/v1.0/account/~/call-log"

    ghl_credential = GHLAuthCredentials.objects.first()
    token = RCToken.objects.first()

    # Current time in Denver
    now_denver = datetime.now(denver_tz)

    # 5 minutes before now
    date_from = (now_denver - timedelta(minutes=5)).astimezone(pytz.UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    print(date_from, 'date_from')

    page = 1
    base_url = url
    params = {
        "dateFrom": date_from,
        "page": page,
        "perPage": 100
    }
    while True:
        print(page, 'pageeeee')

        headers = {
            'Authorization': f"Bearer {token.access_token}"
        }

        try:

            if url == base_url:
                response = requests.get(url, headers=headers, params=params)
            else:
                response = requests.get(url, headers=headers)

            if response.status_code == 401:
                print('token failed d')
                token = refresh_ringcentral_token(token)
                headers = {
                    'Authorization': f"Bearer {token.access_token}"
                }
                response = requests.get(url, headers=headers, params=params)
                print('new_response', 'new token ', response.json())

            response.raise_for_status()
            response_data = response.json()
            print(response_data, response.status_code, 'response_data')

        except requests.exceptions.HTTPError as e:
            print(f"[HTTP ERROR] {e.response.status_code} - {e.response.text}")
            return
        except requests.exceptions.RequestException as e:
            print(f"[REQUEST ERROR] {e}")
            return
        except ValueError as e:
            print(f"[JSON ERROR] Failed to parse JSON: {e}")
            return

        records = response_data.get('records')
        if not records:
            navigation = response_data.get('navigation', {})
            print(f"Records empty, checking for nextPage: {navigation}")
            next_page = navigation.get('nextPage', {}).get('uri')
            if not next_page:
                break
            url = next_page
            params = None
            continue
            # return JsonResponse({"message": "No records found"})

        for record in records:
            direction = record.get('direction')
            if direction == 'Outbound':
                ph_no = record.get('to', {}).get('phoneNumber')
                name = record.get('to', {}).get('name')
            else:
                ph_no = record.get('from', {}).get('phoneNumber')
                name = record.get('from', {}).get('name')
            print(ph_no, 'phone number from record')
            cache = GHLContactCache.objects.filter(phone_number=ph_no).first()
            if cache:
                contact_id = cache.contact_id
                conv_id = cache.conversation_id
            else:
                #Search contact in GHL
                contacts = search_ghl_contact(ghl_credential.access_token, ph_no, ghl_credential.location_id)
                print(contacts, 'contacts search kkd')

                if not contacts:
                    # Create contact if not found
                    contact_id = create_ghl_contact(ghl_credential.access_token, ghl_credential.location_id, ph_no, name)
                else:
                    print("Contact found")
                    contact_id = contacts[0].get("id")

                # Search conversation
                conv_data = search_conversations(ghl_credential.access_token, contact_id, ghl_credential.location_id)
                print(conv_data, 'conv_data')
                if not conv_data or not conv_data.get('conversations'):
                    # Create conversation if not found
                    conv_id = create_conversation(ghl_credential.access_token, ghl_credential.location_id, contact_id)
                else:
                    conv_id=conv_data.get('conversations')[0].get('id')

                GHLContactCache.objects.update_or_create(
                    phone_number=ph_no,
                    contact_id=contact_id,
                    conversation_id=conv_id
                )

            if direction == 'Outbound':
                add_external_call(access_token=ghl_credential.access_token, conversationId=conv_id, ph_no=ph_no, conv_provider_id=GHL_CONV_PROVIDER_ID, rc_phone=RINGCENTRAL_PHONE)
            else:
                add_inbound_call(access_token=ghl_credential.access_token, conversationId=conv_id, ph_no=ph_no, conv_provider_id=GHL_CONV_PROVIDER_ID, rc_phone=RINGCENTRAL_PHONE)

        navigation = response_data.get('navigation', {})
        next_page = navigation.get('nextPage', {}).get('uri')
        if not next_page:
            break
        url = next_page
        params = None

    print('everything worked..')
    return JsonResponse({"message": "Processed call records successfully"})

@login_required(login_url='login')
def celery_toggle_view(request):
    # Ensure exactly one toggle row exists
    print("Authenticated:", request.user.is_authenticated)
    toggle, _ = CeleryIntegrationToggle.objects.get_or_create(id=1, defaults={"enabled": True})

    if request.method == "POST":
        toggle.enabled = "enabled" in request.POST   # checkbox present → True
        toggle.save()   
        messages.success(
            request,
            f"Celery integration {'enabled' if toggle.enabled else 'disabled'}."
        )
        return redirect("celery_toggle")             # named route (see below)

    return render(request, "toggle.html", {"toggle": toggle})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('celery_toggle')
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        print(username, password, 'dod')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect("celery_toggle")  # Replace with your desired redirect URL
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    return redirect('login')