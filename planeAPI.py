import requests

response = requests.get("https://opensky-network.org/api/states/all")
if response.status_code == 200:
    print(response.json())
