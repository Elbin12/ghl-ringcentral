from django.utils import timezone
import requests

from .models import RCToken


def create_token(data):
    if not data.get('access_token'):
        raise ValueError("Access token is required")
    token, _ = RCToken.objects.update_or_create(
        owner_id = data.get('owner_id'),
        defaults={
            'access_token': data.get('access_token'),
            'token_type': data.get('token_type'),
            'expires_in': data.get('expires_in'),
            'refresh_token': data.get('refresh_token'),
            'refresh_token_expires_in': data.get('refresh_token_expires_in'),
            'scope': data.get('scope'),
            'ghl_location_id': data.get('ghl_location_id'),
            'rc_phone_no': data.get('rc_phone_no'),
            'jwt_code': data.get('jwt_code'),
            'client_id': data.get('client_id'),
            'client_secret': data.get('client_secret'),
            'created_at': timezone.now(),
        })
    
    return token

def search_conversations(access_token, contact_id, locationId):
    url = 'https://services.leadconnectorhq.com/conversations/search'
    response = requests.get(
        url,
        headers={
            'Accept': 'application/json',
            'Authorization': f"Bearer {access_token}",
            'Version': '2021-07-28'
        },
        params={"contactId": contact_id, "locationId": locationId}
    )
    print("Raw response: search convvvv", response.status_code, response.text, response.json())

    if response.status_code == 200:
        return response.json()
    return None

def add_inbound_call(access_token, conversationId, ph_no, conv_provider_id, rc_phone):
    url = "https://services.leadconnectorhq.com/conversations/messages/inbound"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }

    payload = {
        "type":"Call",
        "conversationId": conversationId,
        "conversationProviderId": conv_provider_id,
        "direction":"inbound",
        "call":{
            'to':rc_phone,
            "from":ph_no,
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print("Raw response: from inbound call", response.status_code, response.json())

    if response.status_code in [200, 201]:
        print("Internal call added to conversation.")
        return response.json()
    else:
        print("Failed to add Internal call:", response.status_code)
        return None

def add_external_call(access_token, conversationId, ph_no, conv_provider_id, rc_phone):
    url = "https://services.leadconnectorhq.com/conversations/messages/outbound"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Version": "2021-07-28",
        "Content-Type": "application/json"
    }

    payload = {
        "type":"Call",
        "conversationId": conversationId,
        "conversationProviderId": conv_provider_id,
        "call":{
            "to":ph_no,
            'from':rc_phone,
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        print("External call added to conversation.")
        return response.json()
    else:
        print("Failed to add external call:")
        return None

def search_ghl_contact(access_token, phone_number, locationId):
    url = 'https://services.leadconnectorhq.com/contacts/'
    response = requests.get(
        url,
        headers={
            'Accept': 'application/json',
            'Authorization': f"Bearer {access_token}",
            'Version': '2021-07-28'
        },
        params={"query": phone_number, "locationId": locationId}
    )
    print("Raw response:", response.status_code, response.text, response.json())
    return response.json().get("contacts", [])


def create_ghl_contact(access_token, locationId, phone, name):
    url = 'https://services.leadconnectorhq.com/contacts/'
    if name:
        first, *last = name.split(' ')
        first_name = first
        last_name = " ".join(last) if last else ""
    else:
        first_name = "Unknown"
        last_name = ""

    payload = {
        'phone': phone,
        'firstName': first_name,
        'lastName': last_name,
        "locationId": locationId
    }

    response = requests.post(
        url,
        headers={
            'Accept': 'application/json',
            'Authorization': f"Bearer {access_token}",
            'Version': '2021-07-28'
        },
        json=payload
    )

    if response.status_code == 200:
        return response.json().get("contact", {}).get("id")
    else:
        print("Failed to create contact:", response.json())
        return None


def create_conversation(access_token, locationId, contactId):
    url = 'https://services.leadconnectorhq.com/conversations/'

    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {access_token}",
        'Version': '2021-07-28',
        'Content-Type': 'application/json'
    }

    payload = {
        "contactId": contactId,
        "locationId": locationId
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        print("Conversation created")
        return response.json().get('conversation').get('id')
    else:
        print("Error creating conversation:", response.json())
        return None