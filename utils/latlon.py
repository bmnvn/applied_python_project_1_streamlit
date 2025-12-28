def latlon_to_lat_and_lon(latlon):
    lat, lon = None, None

    if isinstance(latlon, tuple):
        lat, lon = latlon
    if isinstance(latlon, dict):
        lat, lon = latlon['lat'], latlon['lon']
    if isinstance(latlon, list):
        lat, lon = latlon[0], latlon[1]
    
    return lat, lon