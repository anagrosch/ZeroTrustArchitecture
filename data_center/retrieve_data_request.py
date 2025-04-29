'''
This file will have the functions related to collecting trust signals, processing them and storing them in json files.
This file also handles data requests from other nodes.
'''

import os
import json
import yaml
from filelock import FileLock, Timeout

data_directory = os.path.abspath(os.path.join(os.getcwd(), 'policy_data'))

'''
HANDLING PROCESSING OF AUTH_DATA
'''

def calculate_sign_in_risk(auth_data):
    user_dict = {}
    sign_in_risk = {}
    user_chain = {}

    # Initialize user_chain for each user_id
    for entry in auth_data:
        user_id = entry['user_id']
        user_chain[user_id] = [0]  # Assuming starting sign-in risk

    # Iterate through auth_data to compute sign-in risk for each user_id
    for entry in auth_data:
        user_id = entry['user_id']
        auth_status = entry['auth_status']

        if user_id not in user_dict:
            user_dict[user_id] = {'success_count': 0, 'failure_count': 0}

        # Update success or failure count for each user
        if auth_status == 1:
            user_dict[user_id]['success_count'] += 1
        else:
            user_dict[user_id]['failure_count'] += 1

        # Calculate the sign-in risk based on the success and failure counts
        success_count = user_dict[user_id]['success_count']
        failure_count = user_dict[user_id]['failure_count']
        total_count = success_count + failure_count

        if total_count > 0:
            sign_in_risk[user_id] = success_count / total_count

        # Update Markov Chain for each user
        user_chain[user_id].append(sign_in_risk[user_id])

    return user_chain


def predict_sign_in_risk(user_chain, current_sign_in_risk):
    # Predict the next sign-in risk based on the transition probabilities
    predicted_sign_in_risk = {}

    for user_id, chain in user_chain.items():
        if len(chain) > 1:
            transition_prob = chain[-1] - chain[-2]  # Difference between last two values
            if user_id in current_sign_in_risk:
                predicted_sign_in_risk[user_id] = current_sign_in_risk[user_id] + transition_prob
            else:
                predicted_sign_in_risk[user_id] = transition_prob  # Assign transition_prob if user_id not found

    return predicted_sign_in_risk


def process_events(events_data):
    cleaned_data = []

    for event in events_data:
        if event['user_id'] is not None:  # Skip entries with null user_id
            cleaned_event = {
                'time': event.get('time', None),
                'type': event.get('type', None),
                'user_id': event.get('user_id', None),
                'ip_address': event.get('ip_address', None),
                'auth_type': event.get('auth_type', None),
                'auth_status': 1 if event.get('type') == 'LOGIN' else 0
            }

            # Skip records not matching criteria
            if cleaned_event['auth_status'] == 0 and event.get('type') != 'LOGIN_ERROR':
                continue

            cleaned_data.append(cleaned_event)

    # Update auth_data with calculated sign-in risk
    auth_data = cleaned_data[:]
    user_chain = calculate_sign_in_risk(auth_data)

    for entry in auth_data:
        user_id = entry['user_id']
        entry['sign_in_risk'] = user_chain[user_id][-1]

    # Predict the next sign-in risk
    current_sign_in_risk = {entry['user_id']: entry['sign_in_risk'] for entry in auth_data if entry['user_id'] is not None}
    predicted_sign_in_risk = predict_sign_in_risk(user_chain, current_sign_in_risk)

    # Blend the predicted and current sign-in risk
    for entry in auth_data:
        user_id = entry['user_id']
        if user_id in predicted_sign_in_risk:
            entry['sign_in_risk'] = (entry['sign_in_risk'] + predicted_sign_in_risk[user_id]) / 2

    # File handling to store events in a JSON file
    try:
        # Load data with file lock precaution
        existing_data, __ = load_data_with_lock('auth_data.json')

        new_id = 1
        if existing_data:
            last_entry = existing_data[-1]
            new_id = last_entry.get('ID', 0) + 1  # Check if 'ID' exists, otherwise set new_id to 1

        # Filter out events that already exist in the JSON file
        auth_data_to_add = [event for event in auth_data if not any(event['user_id'] == entry.get('user_id') for entry in existing_data)]

        for i, event in enumerate(auth_data_to_add, start=new_id):
            event['ID'] = i
            existing_data.append(event)

        # Write the updated data to the JSON file
        dump_file_with_lock('auth_data.json', existing_data)

    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error occurred while handling the JSON file: {e}")


'''
HANDLING JSON FILE DATA
'''

# Safely load data from JSON file with lock
def load_data_with_lock(filename):
    file_path = os.path.join(data_directory, filename)

    # Set up lock for json file
    lock_path = file_path + '.lock'
    lock = FileLock(lock_path, timeout=5)

    data = []
    try:
        # Try to acquire lock within 5 seconds
        with lock.acquire(timeout=5):
            with open(file_path, 'r') as file:
                data = json.load(file)

    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error occurred while handling the JSON file: {e}")

    except IOError as e:
        print(f"Error occurred while loading the json data {e}")

    except Timeout:
        print("Failed to acquire lock within the timeout period.")

    finally:
        lock.release()

    return data, file_path


# Safely write to JSON file with lock
def dump_file_with_lock(filename, data):
    file_path = os.path.join(data_directory, filename)

    # Set up lock for json file
    lock_path = file_path + '.lock'
    lock = FileLock(lock_path, timeout=5)

    try:
        # Try to acquire lock within 5 seconds
        with lock.acquire(timeout=5):
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)

    except IOError as e:
        print(f"Error occurred while writing JSON data: {e}")

    except Timeout:
        print("Failed to acquire lock within the timeout period.")

    finally:
        lock.release()


'''
HANDLING DATA CENTER REQUESTS
'''

# Function to get the next ID in access request JSON file
def get_next_access_req_id():
    # Load data with file lock precaution
    existing_data, __ = load_data_with_lock('access_requests.json')

    new_id = 1
    if existing_data:
        last_entry = existing_data[-1]
        new_id = last_entry['ID'] + 1

    return new_id, existing_data


# Function to get the latest access decision data from the JSON file
def get_next_access_dec_id():
    # Load data with file lock precaution
    access_decisions, file_path = load_data_with_lock('access_decision.json')

    new_id = 1
    if access_decisions:
        last_entry = access_decisions[-1]
        new_id = last_entry['ID'] + 1

    return new_id, access_decisions, file_path


# Function to create or update policyConfiguration.yml file
def update_policy_configurations(data):
    file_path = os.path.join(data_directory, 'policyConfiguration.yml')

    try:
        with open(file_path, 'r') as file:
            existing_data = yaml.safe_load(file)
    except FileNotFoundError:
        existing_data = {}
        return 'fail'

    existing_data.update(data)

    with open(file_path, 'w') as file:
        yaml.dump(existing_data, file)
    return 'success'


# Function to retrieve policy configurations
def load_policy_location_configs():
    file_path = os.path.join(data_directory, 'policyConfiguration.yml')

    # Load policyConfiguration.yml file
    with open(file_path, 'r') as file:
        policy_configurations = yaml.safe_load(file)

    # Extract country lists for each risk category
    high_risk_countries = policy_configurations.get('highRiskLocations', [])
    medium_risk_countries = policy_configurations.get('mediumRiskLocations', [])
    low_risk_countries = policy_configurations.get('lowRiskLocations', [])

    # Extract night start and night end times and convert to datetime objects
    period_start = policy_configurations.get('periodStartInput', '00:00:00')
    period_end = policy_configurations.get('periodEndInput', '06:00:00')

    return high_risk_countries, medium_risk_countries, low_risk_countries, period_start, period_end


def load_policy_threshold_configs():
    file_path = os.path.join(data_directory, 'policyConfiguration.yml')

    # Load policyConfiguration.yml file
    with open(file_path, 'r') as file:
        policy_configurations = yaml.safe_load(file)

    # Access specific values from the policy configuration
    admin_threshold = float(policy_configurations['adminThreshold'])
    approver_threshold = float(policy_configurations['approverThreshold'])
    security_viewer_threshold = float(policy_configurations['securityViewerThreshold'])
    sign_in_risk_threshold = float(policy_configurations['signInRiskThreshold'])

    return admin_threshold, approver_threshold, security_viewer_threshold, sign_in_risk_threshold


'''
HANDLING PROCESSING AND STORAGE OF EVENTS DATA
'''

def store_keycloak_events(cleaned_data):
    file_path = os.path.join(data_directory, 'events.json')

    try:
        existing_data = []
        new_id = 1

        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                existing_data = json.load(file)
                if existing_data:
                    last_entry = existing_data[-1]
                    new_id = last_entry['ID'] + 1

        for i, event in enumerate(cleaned_data, start=new_id):
            event_exists = False
            for existing_event in existing_data:
                if event['time'] == existing_event['time'] and event['user_id'] == existing_event['user_id']:
                    event_exists = True
                    break

            if not event_exists:
                event['ID'] = i
                existing_data.append(event)

        dump_file_with_lock('events.json', existing_data)

    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error occurred while handling the JSON file: {e}")

    except IOError as e:
        print(f"Error occurred while writing JSON data: {e}")


# Get the latest access request data for a particular user_id
def get_latest_access_request(user_id):
    # Load data with file lock precaution
    data, __ = load_data_with_lock('access_requests.json')

    latest_request = None
    for request in data:
        if request['user_id'] == user_id:
            if latest_request is None or request['access_request_time'] > latest_request['access_request_time']:
                latest_request = request

    return latest_request

#get the latest auth data for the particular user_id
def get_latest_auth_data(user_id):
    # Load data with file lock precaution
    data, __ = load_data_with_lock('auth_data.json')

    latest_data = None
    for entry in data:
        if entry['user_id'] == user_id:
            if latest_data is None or entry['time'] > latest_data['time']:
                latest_data = entry

    return latest_data

# Get user identity information
def get_user_identity_data_by_id(user_id):
    # Load data with file lock precaution
    user_data, __ = load_data_with_lock('user_data.json')

    for user in user_data:
        if user['user_id'] == user_id:
            return user

    return None  # Return None if user_id not found