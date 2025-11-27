import os
import requests

def get_place_info(place_name, country=None, city=None):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY 환경변수가 설정되지 않았습니다.")

    # 지역 힌트 추가
    query = f"{place_name} {country or ''} {city or ''}".strip()

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address,geometry",
        "language": "ko",
        "key": api_key
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    if data.get("status") != "OK" or not data.get("candidates"):
        return None

    place = data["candidates"][0]
    loc = place["geometry"]["location"]

    return {
        "name": place.get("name"),
        "address": place.get("formatted_address"),
        "place_id": place.get("place_id"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng")
    }
