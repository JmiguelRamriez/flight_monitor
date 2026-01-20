
import os
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = "3GP0nQ51XZxmMGXO56N3uW3bsWNTrGrG"
CLIENT_SECRET = "tX7YlePTODMFiLXa"
HOST = "https://test.api.amadeus.com"

print(f"Testing connection to {HOST}")
print(f"Client ID: {CLIENT_ID[:5]}... (len={len(CLIENT_ID) if CLIENT_ID else 0})")

# 1. Auth
url = f"{HOST}/v1/security/oauth2/token"
try:
    print("Requesting token...")
    response = requests.post(url, data={
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })
    print(f"Auth Status: {response.status_code}")
    if response.status_code != 200:
        print(response.text)
        exit(1)
    
    token = response.json()['access_token']
    print("Token obtained successfully.")
except Exception as e:
    print(f"Auth Error: {e}")
    exit(1)

# 2. Locations
try:
    print("Requesting locations (JP)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try with keyword matching the country code
    print("Attempt 1: keyword='JP'")
    params = {
        "keyword": "JP",
        "subType": "AIRPORT",
        "countryCode": "JP",
        "view": "LIGHT",
        "page[limit]": 5
    }
    response = requests.get(f"{HOST}/v1/reference-data/locations", headers=headers, params=params)
    print(f"Status 1: {response.status_code}")
    if response.status_code == 200:
        print(response.json())
        
    # Try with keyword='Tokyo' just to see
    print("Attempt 2: keyword='Tokyo'")
    params = {
        "keyword": "Tokyo",
        "subType": "AIRPORT",
        "countryCode": "JP",
        "view": "LIGHT",
        "page[limit]": 5
    }
    response = requests.get(f"{HOST}/v1/reference-data/locations", headers=headers, params=params)
    print(f"Status 2: {response.status_code}")
    if response.status_code == 200:
        print(response.json())

except Exception as e:
    print(f"Locations Error: {e}")
