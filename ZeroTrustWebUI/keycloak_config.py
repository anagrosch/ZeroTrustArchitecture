#THis file contains the constants for the keycloak configurations

# keycloak_config.py

HOST_IP_ADDR = "localhost" #redacted
KEYCLOAK_SERVER_URL = f"http://{HOST_IP_ADDR}:8080/"
KEYCLOAK_REALM = "myrealm"
KEYCLOAK_CLIENT_ID = "ZeroTrustPlatform"
KEYCLOAK_CLIENT_SECRET = "kz1gXUWTkU6gZJNy7gezdFh2eHx57iUw" #must update for ZeroTrustPlatform
KEYCLOAK_ADMIN_CLIENT_SECRET = "8zbAPYwbLfGXHI02HoORBzHkUNxJu5Sc" #must update for admin-cli

SERVER_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
API_BASE_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect"
AUTHORIZATION_URL = f"{API_BASE_URL}/auth"
REGISTRATION_URL = f"{API_BASE_URL}/registrations"
TOKEN_URL = f"{API_BASE_URL}/token"
REVOCATION_URL = f"{API_BASE_URL}/logout"