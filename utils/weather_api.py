import requests
import datetime
import numpy as np
from typing import Optional, Tuple, Any

from .latlon import latlon_to_lat_and_lon


# ===================
# API KEY
# ===================

_API_KEY = None

def set_api_key(key: str):
    global _API_KEY
    _API_KEY = key

def get_api_key() -> Optional[str]:
    global _API_KEY
    return _API_KEY

def validate_api_key(api_key):
    if not api_key or len(api_key.strip()) == 0:
        return False, "👀 API key is empty"
    
    # Проверка на работоспособность
    url = f"https://api.openweathermap.org/data/2.5/weather?lat=1.2&lon=3.4&appid={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, "✅ API key is valid"
        elif response.status_code == 401:
            return False, "❌ Invalid API key."
        else:
            return False, f"❌ API error: {response.status_code}"
    except Exception as e:
        return False, f"❌ Connection error: {str(e)}"



# ===================
# CONSTS
# ===================

month_to_season = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn"
}

latlon_cache_map = {}

latlon_cache_map.update({
    'Paris': {'lat': 48.8588897, 'lon': 2.3200410217200766},
    'Sydney': {'lat': -33.8698439, 'lon': 151.2082848},
    'Dubai': {'lat': 25.2653471, 'lon': 55.2924914},
    'Moscow': {'lat': 55.7504461, 'lon': 37.6174943},
    'Berlin': {'lat': 52.5170365, 'lon': 13.3888599},
    'Beijing': {'lat': 39.906217, 'lon': 116.3912757},
    'London': {'lat': 51.5073219, 'lon': -0.1276474},
    'Los Angeles': {'lat': 34.0536909, 'lon': -118.242766},
    'Cairo': {'lat': 30.0443879, 'lon': 31.2357257},
    'New York': {'lat': 40.7127281, 'lon': -74.0060152},
    'Tokyo': {'lat': 35.6828387, 'lon': 139.7594549},
    'Rio de Janeiro': {'lat': -22.9110137, 'lon': -43.2093727},
    'Mumbai': {'lat': 19.0785451, 'lon': 72.878176},
    'Mexico City': {'lat': 19.4326296, 'lon': -99.1331785},
    'Singapore': {'lat': 1.2899175, 'lon': 103.8519072}
})

def ensure_city_coordinates(cities):
    result = {}
    for city in cities:
        if city in latlon_cache_map:
            result[city] = latlon_cache_map[city]
        else:
            geocoding = request_geocoding_api(city, limit=1)
            if geocoding and len(geocoding) > 0:
                result[city] = latlon_cache_map[city]
            else:
                result[city] = None
    return result



# ===================
# (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧
# ===================

def fetch(url):
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching url [ {url} ]: {e}\n\n\n")
        return None
    
    return data

def make_weather_url_query(lat, lon):
    return f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={get_api_key()}"

def make_geocoding_url_query(city_name, limit=10):
    return f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit={limit}&appid={get_api_key()}"




# ===================
# o(*￣▽￣*)o
# ===================

def request_geocoding_api(city_name, limit=1):
    if city_name in latlon_cache_map:
        return latlon_cache_map[city_name]
    
    data = fetch(make_geocoding_url_query(city_name, limit=1))
    if data:
        latlon_cache_map[city_name] = {
            'lat': data[0]['lat'],
            'lon': data[0]['lon'],
        }
    return data

def request_weather_api(city_name=None, lat=None, lon=None, latlon=None):
    if latlon is not None and len(latlon) == 2:
        lat, lon = latlon_to_lat_and_lon(latlon)
    
    if lat is None or lon is None:
        if not city_name is None:
            if city_name in latlon_cache_map:
                lat, lon = latlon_to_lat_and_lon(latlon_cache_map[city_name])
            else:
                geocoding = request_geocoding_api(city_name, limit=1)
                if geocoding:
                    lat, lon = latlon_to_lat_and_lon(geocoding[0])
            
    if lat is None or lon is None:
        return None

    data = fetch(make_weather_url_query(lat, lon))
    return data

def get_current_temp_and_date(city_name=None, lat=None, lon=None, latlon=None):
    data = request_weather_api(city_name=city_name, lat=lat, lon=lon, latlon=latlon)
    if data:
        return data['main']['temp'], datetime.datetime.fromtimestamp(data['dt'])
    else:
        return None, None
    
def get_current_temp_and_season(city_name=None, lat=None, lon=None, latlon=None):
    temp, dt = get_current_temp_and_date(city_name=city_name, lat=lat, lon=lon, latlon=latlon)
    if temp:
        return temp, month_to_season[dt.month]
    else:
        return None, None




# ===================
# (∪.∪ )...zzz
# ===================

def get_city_season_mean_and_std(df, city, season):
    return df.loc[
        (df['city'] == city) & (df['season'] == season),
        ['city_season_temp_mean', 'city_season_temp_std']
    ].iloc[0]

def is_temp_outlier_for_city_season(df, temp, city, season):
    mean, std = get_city_season_mean_and_std(df, city, season)
    return (np.abs(mean - temp) > 2 * std)

def is_temp_outlier_for_city_season_with_stats(df, temp, city, season):
    mean, std = get_city_season_mean_and_std(df, city, season)
    is_outlier = (np.abs(mean - temp) > 2 * std)
    stats = {
        'mean': mean,
        'std': std,
        'lower_bound': mean - 2 * std,
        'upper_bound': mean + 2 * std,
    }
    return is_outlier, stats

def is_current_temp_outlier(df, city, verbose=False):
    if verbose: print(f'city = {city}')

    # проверка есть ли вообще город в df
    df_cities_set = set(df['city'].unique())
    if not city in df_cities_set:
        if verbose: print(f'city not found in df: {df_cities_set}')
        return None

    if city in latlon_cache_map:
        latlon = latlon_cache_map[city]
        if verbose: print(f'found {city} in latlon_cache_map = {latlon_cache_map[city]}')

        temp, season = get_current_temp_and_season(latlon=latlon)
        if verbose: print(f'got temp = {temp}, season = {season}')

    else:
        if verbose: print(f'no {city} in latlon_cache_map: {latlon_cache_map}')
        if verbose: print(f'fetching {city} lat and lon from api...')

        temp, season = get_current_temp_and_season(city_name=city)
        if verbose: print(f'got temp = {temp}, season = {season}, lat = {latlon_cache_map[city]["lat"]}, lon = {latlon_cache_map[city]["lon"]}')
    
    if temp:
        if verbose: mean, std = get_city_season_mean_and_std(df, city, season)
        if verbose: upper = mean + 2 * std
        if verbose: lower = mean - 2 * std
        if verbose: print(f'mean {city} temp in {season} = {mean}, std = {std}, outliers are outside range: ( {lower} .. {upper} )')

        return is_temp_outlier_for_city_season(df, temp, city, season)
    return None

# Тот же is_current_temp_outlier но возвращает всякое для удобства: temp + season + is_outlier + stats_dict
def get_current_temp_outlier_info(df, city):
    df_cities_set = set(df['city'].unique())
    if city not in df_cities_set:
        return None, None, None, None

    temp, season = get_current_temp_and_season(latlon=latlon_cache_map[city])
    
    if temp and season:
        mean, std = get_city_season_mean_and_std(df, city, season)
        is_outlier = np.abs(mean - temp) > 2 * std
        
        stats = {
            'mean': mean,
            'std': std,
            'lower_bound': mean - 2 * std,
            'upper_bound': mean + 2 * std
        }
        
        return temp, season, is_outlier, stats
    
    return None, None, None, None