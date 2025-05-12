import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = "https://weatherapi-com.p.rapidapi.com/forecast.json"
querystring = {"q":"Moscow","days":"2"}

headers = {
    "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
    "X-RapidAPI-Host": os.getenv('RAPIDAPI_HOST')
}

response = requests.get(url, headers=headers, params=querystring)
print(response.status_code)
print(response.json())