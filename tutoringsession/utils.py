# For models and views
import math
import os
import json
import urllib.parse
import urllib.request
from django.core.cache import cache

# Calculate radius between lat/long points
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(float, (lon1, lat1, lon2, lat2))
    R = 3958.8  # miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Calling Distance Matrix API
def _distance_matrix_request(origins, destinations, *, use_traffic=True, traffic_model="best_guess", units="imperial", timeout=7.0):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY")

    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "mode": "driving",
        "units": units,
        "key": api_key,
    }
    if use_traffic:
        params["departure_time"] = "now"
        params["traffic_model"] = traffic_model

    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, headers={"User-Agent": "GTJobSearch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Find road distance and time between 2 points
def get_road_distance_and_time(origin_lat, origin_lng, dest_lat, dest_lng, *, use_traffic=True, traffic_model="best_guess"):
    # Cache key (rounded coords help reduce cardinality)
    cache_key = None
    if cache:
        cache_key = f"dm1:{round(float(origin_lat),4)},{round(float(origin_lng),4)}->{round(float(dest_lat),4)},{round(float(dest_lng),4)}:{use_traffic}:{traffic_model}"
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        payload = _distance_matrix_request(
            [f"{origin_lat},{origin_lng}"],
            [f"{dest_lat},{dest_lng}"],
            use_traffic=use_traffic,
            traffic_model=traffic_model
        )
        if payload.get("status") != "OK":
            raise RuntimeError(payload.get("error_message") or payload.get("status"))

        elem = payload["rows"][0]["elements"][0]
        if elem.get("status") != "OK":
            raise RuntimeError(elem.get("status"))

        distance_m = elem.get("distance", {}).get("value")  # meters
        duration_s = elem.get("duration", {}).get("value")  # seconds (no traffic)
        duration_traf_s = elem.get("duration_in_traffic", {}).get("value") if use_traffic else None

        result = {
            "status": "OK",
            "distance_miles": distance_m / 1609.344 if distance_m is not None else None,
            "duration_minutes": duration_s / 60.0 if duration_s is not None else None,
            "duration_in_traffic_minutes": duration_traf_s / 60.0 if duration_traf_s is not None else None,
            "error": None
        }
        if cache and cache_key:
            ttl = 5*60 if use_traffic else 60*60
            cache.set(cache_key, result, ttl)
        return result

    except Exception as e:
        # Fallback: rough estimate using haversine @ ~30mph
        miles = haversine(origin_lng, origin_lat, dest_lng, dest_lat)
        fallback_minutes = (miles / 30.0) * 60.0
        result = {
            "status": "FALLBACK",
            "distance_miles": miles,
            "duration_minutes": fallback_minutes,
            "duration_in_traffic_minutes": None,
            "error": str(e)
        }
        if cache and cache_key:
            cache.set(cache_key, result, 15*60)
        return result

# Compute road dist/time now from one place to many other locations 
def batch_road_distance_and_time(origin_lat, origin_lng, destinations, *, use_traffic=True, traffic_model="best_guess"):
    # Build cache hits/misses
    to_fetch = []
    results = {}

    for (dlat, dlng, ident) in destinations:
        ck = None
        if cache:
            ck = f"dmN:{round(float(origin_lat),4)},{round(float(origin_lng),4)}->{round(float(dlat),4)},{round(float(dlng),4)}:{use_traffic}:{traffic_model}"
            cached = cache.get(ck)
            if cached:
                results[ident] = cached
                continue
        to_fetch.append((dlat, dlng, ident, ck))

    # Google allows many destinations in one call (commonly up to 25 according to sources)
    chunk_size = 25
    for i in range(0, len(to_fetch), chunk_size):
        chunk = to_fetch[i:i+chunk_size]
        if not chunk:
            continue

        dest_strings = [f"{dlat},{dlng}" for (dlat, dlng, _, _) in chunk]
        try:
            payload = _distance_matrix_request(
                [f"{origin_lat},{origin_lng}"], dest_strings,
                use_traffic=use_traffic, traffic_model=traffic_model
            )
            ok = payload.get("status") == "OK"
            rows = payload.get("rows", [])
            if not ok or not rows:
                raise RuntimeError(payload.get("error_message") or payload.get("status"))

            elems = rows[0].get("elements", [])
            for (item, elem) in zip(chunk, elems):
                dlat, dlng, ident, ck = item
                if elem.get("status") != "OK":
                    raise RuntimeError(elem.get("status"))
                distance_m = elem.get("distance", {}).get("value")
                duration_s = elem.get("duration", {}).get("value")
                duration_traf_s = elem.get("duration_in_traffic", {}).get("value") if use_traffic else None
                res = {
                    "status": "OK",
                    "distance_miles": distance_m/1609.344 if distance_m is not None else None,
                    "duration_minutes": duration_s/60.0 if duration_s is not None else None,
                    "duration_in_traffic_minutes": duration_traf_s/60.0 if duration_traf_s is not None else None,
                    "error": None
                }
                results[ident] = res
                if cache and ck:
                    ttl = 5*60 if use_traffic else 60*60
                    cache.set(ck, res, ttl)

        except Exception as e:
            # Fallback for the whole chunk
            for (dlat, dlng, ident, ck) in chunk:
                miles = haversine(origin_lng, origin_lat, dlng, dlat)
                fallback_minutes = (miles/30.0)*60.0
                res = {
                    "status": "FALLBACK",
                    "distance_miles": miles,
                    "duration_minutes": fallback_minutes,
                    "duration_in_traffic_minutes": None,
                    "error": str(e)
                }
                results[ident] = res
                if cache and ck:
                    cache.set(ck, res, 15*60)

    return results