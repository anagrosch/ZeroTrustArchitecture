'''
This file will have the functions related to collecting trust signals, processing them and storing them in json files
'''

'''
HANDLING PROCESSING AND STORAGE OF EVENTS DATA
'''

def get_keycloak_events(keycloak_admin):
    query_params = {
        "dateFrom": "2023-01-01",
        "dateTo": "2025-12-31",
        "max": 10000,
    }

    events_data = keycloak_admin.get_events(query=query_params)
    cleaned_data = []

    for event in events_data:
        cleaned_event = {
            'time': event.get('time', None),
            'type': event.get('type', None),
            'user_id': event.get('userId', None),
            'ip_address': event.get('ipAddress', None)
        }

        if 'details' in event:
            details = event['details']
            cleaned_event['auth_type'] = details.get('auth_type', None)
            cleaned_event['token_id'] = details.get('token_id', None)

        cleaned_event['session_id'] = event.get('sessionId', None)

        cleaned_data.append(cleaned_event)

    return cleaned_data