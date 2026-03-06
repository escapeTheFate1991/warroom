"""Business discovery via Google Places, Yelp Fusion, and OpenStreetMap Overpass APIs."""

import httpx
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAIL_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.rating",
    "places.userRatingCount",
    "places.types",
    "places.primaryType",
    "places.location",
    "places.currentOpeningHours",
]

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Yelp — scraped from frontend, no API key needed

# Map common search queries to OSM tags
OSM_TAG_MAP: dict[str, str] = {
    "plumbers": "craft=plumber",
    "electricians": "craft=electrician",
    "hvac contractors": "craft=hvac",
    "roofers": "craft=roofer",
    "landscapers": "landuse=grass|shop=garden_centre",
    "general contractors": "craft=builder",
    "painters": "craft=painter",
    "pest control": "shop=pest_control",
    "cleaning services": "shop=cleaning",
    "moving companies": "shop=moving_company",
    "restaurants": "amenity=restaurant",
    "cafes & coffee shops": "amenity=cafe",
    "bars & nightclubs": "amenity=bar|amenity=nightclub",
    "bakeries": "shop=bakery",
    "food trucks": "amenity=fast_food",
    "catering services": "amenity=restaurant",
    "dentists": "amenity=dentist",
    "chiropractors": "healthcare=alternative",
    "veterinarians": "amenity=veterinary",
    "optometrists": "healthcare=optometrist",
    "medical clinics": "amenity=clinic",
    "physical therapy": "healthcare=physiotherapist",
    "mental health counselors": "healthcare=psychotherapist",
    "pharmacies": "amenity=pharmacy",
    "law firms": "office=lawyer",
    "accounting firms": "office=accountant",
    "insurance agents": "office=insurance",
    "financial advisors": "office=financial",
    "real estate agents": "office=estate_agent",
    "mortgage brokers": "office=financial",
    "auto repair shops": "shop=car_repair",
    "auto dealerships": "shop=car",
    "car wash": "amenity=car_wash",
    "towing services": "shop=car_repair",
    "hair salons": "shop=hairdresser",
    "barber shops": "shop=hairdresser",
    "nail salons": "shop=beauty",
    "spas & wellness": "leisure=spa|shop=beauty",
    "gyms & fitness centers": "leisure=fitness_centre",
    "yoga studios": "leisure=fitness_centre",
    "martial arts studios": "leisure=fitness_centre",
    "daycare centers": "amenity=kindergarten",
    "tutoring services": "amenity=school",
    "dog grooming": "shop=pet_grooming",
    "pet boarding": "amenity=animal_boarding",
    "photography studios": "craft=photographer",
    "wedding venues": "amenity=events_venue",
    "event planners": "amenity=events_venue",
    "florists": "shop=florist",
    "printing services": "shop=copyshop",
    "it services": "office=it",
    "web design agencies": "office=it",
    "marketing agencies": "office=advertising_agency",
    "staffing agencies": "office=employment_agency",
    "storage facilities": "shop=storage_rental",
    "hotels & motels": "tourism=hotel|tourism=motel",
}


@dataclass
class PlaceResult:
    place_id: str
    name: str
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    website: str = ""
    maps_url: str = ""
    rating: float = 0.0
    review_count: int = 0
    category: str = ""
    types: list[str] = field(default_factory=list)
    latitude: float = 0.0
    longitude: float = 0.0
    opening_hours: dict | None = None
    source: str = ""  # "google_places", "yelp", "openstreetmap"


def _parse_address_components(components: list[dict]) -> dict:
    result = {"city": "", "state": "", "zip": ""}
    type_map = {
        "locality": "city",
        "administrative_area_level_1": "state",
        "postal_code": "zip",
    }
    for component in components:
        for ctype in component.get("types", []):
            if ctype in type_map:
                key = type_map[ctype]
                result[key] = component.get("shortText", component.get("longText", ""))
    return result


def _parse_place(place: dict) -> PlaceResult:
    addr_parts = _parse_address_components(place.get("addressComponents", []))
    location = place.get("location", {})

    return PlaceResult(
        place_id=place.get("id", ""),
        name=place.get("displayName", {}).get("text", ""),
        address=place.get("formattedAddress", ""),
        city=addr_parts["city"],
        state=addr_parts["state"],
        zip_code=addr_parts["zip"],
        phone=place.get("nationalPhoneNumber", "") or place.get("internationalPhoneNumber", ""),
        website=place.get("websiteUri", ""),
        maps_url=place.get("googleMapsUri", ""),
        rating=place.get("rating", 0.0),
        review_count=place.get("userRatingCount", 0),
        category=place.get("primaryType", ""),
        types=place.get("types", []),
        latitude=location.get("latitude", 0.0),
        longitude=location.get("longitude", 0.0),
        opening_hours=place.get("currentOpeningHours"),
        source="google_places",
    )


def _parse_location(location: str) -> tuple[str, str]:
    """Parse 'City, ST' into (city, state)."""
    city, state = location.strip(), ""
    if "," in location:
        parts = [x.strip() for x in location.split(",", 1)]
        city = parts[0]
        state = parts[1] if len(parts) > 1 else ""
    return city, state


def _build_osm_tags(query: str) -> list[tuple[str, str]]:
    """Convert a search query to OSM key=value tag pairs."""
    query_lower = query.lower().strip()
    tag_str = OSM_TAG_MAP.get(query_lower, "")
    if not tag_str:
        # Fallback: search amenity, shop, office, craft with fuzzy name match
        return []

    tags = []
    for part in tag_str.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            tags.append((k, v))
    return tags


async def _get_google_maps_key() -> str:
    """Get Google Maps API key from settings DB, falling back to env var."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text as sa_text
        engine = create_async_engine("postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge", pool_size=1)
        async with engine.begin() as conn:
            result = await conn.execute(sa_text("SELECT value FROM public.settings WHERE key = 'google_maps_api_key'"))
            row = result.fetchone()
            await engine.dispose()
            if row and row[0]:
                return row[0]
    except Exception as exc:
        logger.warning("Failed to read Google Maps key from DB: %s", exc)
    return os.getenv("GOOGLE_MAPS_API_KEY", "")


async def _search_google_places(query: str, location: str, max_results: int, radius_km: int = 25) -> list[PlaceResult]:
    """Search Google Places API (requires google_maps_api_key in settings or GOOGLE_MAPS_API_KEY env)."""
    api_key = await _get_google_maps_key()
    if not api_key:
        logger.warning("No Google Maps API key found in settings DB or environment")
        return []

    search_text = f"{query} in {location}"
    results: list[PlaceResult] = []
    page_token = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(results) < max_results:
            body: dict = {"textQuery": search_text, "maxResultCount": 20}
            if page_token:
                body["pageToken"] = page_token

            # Use locationBias to expand search radius beyond exact city
            # First geocode the location to get lat/lng, then set radius
            if not page_token and radius_km and radius_km > 0:
                geo_resp = await client.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={"address": location, "key": api_key},
                )
                if geo_resp.status_code == 200:
                    geo_data = geo_resp.json()
                    geo_results = geo_data.get("results", [])
                    if geo_results:
                        loc = geo_results[0].get("geometry", {}).get("location", {})
                        if loc.get("lat") and loc.get("lng"):
                            body["locationBias"] = {
                                "circle": {
                                    "center": {"latitude": loc["lat"], "longitude": loc["lng"]},
                                    "radius": radius_km * 1000,  # Convert km to meters
                                }
                            }
                            logger.info("Using locationBias: %s with %dkm radius", location, radius_km)

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": ",".join(PLACES_DETAIL_FIELDS),
            }

            try:
                response = await client.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers)
            except httpx.HTTPError as exc:
                logger.error("Google Places HTTP error: %s", exc)
                break

            if response.status_code != 200:
                logger.error("Google Places API error %d: %s", response.status_code, response.text)
                break

            data = response.json()
            places = data.get("places", [])
            for place in places:
                results.append(_parse_place(place))

            page_token = data.get("nextPageToken")
            if not page_token or not places:
                break

    logger.info("Google Places returned %d results for '%s in %s'", len(results), query, location)
    return results[:max_results]


async def _search_yelp(query: str, location: str, max_results: int) -> list[PlaceResult]:
    """Scrape Yelp search results page (no API key needed)."""
    import re as _re
    results: list[PlaceResult] = []
    city, state = _parse_location(location)

    # Yelp search URL — same as what a browser hits
    yelp_url = "https://www.yelp.com/search"
    offset = 0

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        while len(results) < max_results:
            params = {
                "find_desc": query,
                "find_loc": location,
                "start": offset,
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            try:
                response = await client.get(yelp_url, params=params, headers=headers)
            except httpx.HTTPError as exc:
                logger.error("Yelp scrape HTTP error: %s", exc)
                break

            if response.status_code != 200:
                logger.warning("Yelp scrape status %d, stopping", response.status_code)
                break

            html = response.text

            # Yelp embeds business data as JSON in script tags
            # Look for the search results JSON blob
            json_matches = _re.findall(r'<!--({.+?})-->', html)
            if not json_matches:
                # Try alternate: Yelp sometimes uses __PRELOADED_STATE__ or inline JSON-LD
                ld_matches = _re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, _re.DOTALL)
                for ld in ld_matches:
                    try:
                        ld_data = __import__("json").loads(ld)
                        if isinstance(ld_data, list):
                            for item in ld_data:
                                if item.get("@type") == "LocalBusiness" and len(results) < max_results:
                                    addr = item.get("address", {})
                                    geo = item.get("geo", {})
                                    agg = item.get("aggregateRating", {})
                                    results.append(PlaceResult(
                                        place_id=f"yelp_scrape_{len(results)}",
                                        name=item.get("name", ""),
                                        address=f"{addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}, {addr.get('addressRegion', '')} {addr.get('postalCode', '')}".strip(", "),
                                        city=addr.get("addressLocality", city),
                                        state=addr.get("addressRegion", state),
                                        zip_code=addr.get("postalCode", ""),
                                        phone=item.get("telephone", ""),
                                        website="",
                                        maps_url=item.get("url", ""),
                                        rating=float(agg.get("ratingValue", 0)),
                                        review_count=int(agg.get("reviewCount", 0)),
                                        category=query,
                                        types=[],
                                        latitude=float(geo.get("latitude", 0)),
                                        longitude=float(geo.get("longitude", 0)),
                                        source="yelp",
                                    ))
                    except (ValueError, TypeError, KeyError):
                        continue

            if not results and not json_matches:
                # Last resort: parse basic info from HTML patterns
                biz_names = _re.findall(r'class="css-[^"]*"[^>]*>([^<]{2,60})</a>\s*</h3>', html)
                for name in biz_names[:max_results]:
                    if name and len(results) < max_results:
                        results.append(PlaceResult(
                            place_id=f"yelp_scrape_{len(results)}",
                            name=name.strip(),
                            address="",
                            city=city,
                            state=state,
                            category=query,
                            source="yelp",
                        ))

            # Yelp shows 10 results per page
            offset += 10
            if offset >= max_results or len(results) >= max_results:
                break
            # Don't hammer Yelp
            import asyncio as _aio
            await _aio.sleep(0.5)

    logger.info("Yelp scrape returned %d results for '%s in %s'", len(results), query, location)
    return results[:max_results]


async def _search_openstreetmap(query: str, location: str, max_results: int) -> list[PlaceResult]:
    """Search OpenStreetMap Overpass API (completely free, no key needed)."""
    city, state = _parse_location(location)
    tags = _build_osm_tags(query)

    if not tags:
        # Fallback: use Nominatim search for the query + location
        return await _search_osm_nominatim(query, location, max_results)

    results: list[PlaceResult] = []

    # Build area search — try city first, include state for disambiguation
    area_name = city
    area_filter = f'area[name="{area_name}"]'
    if state:
        # Use a broader search with state context
        area_filter = f'area[name="{area_name}"]'

    async with httpx.AsyncClient(timeout=60.0) as client:
        for tag_key, tag_value in tags:
            if len(results) >= max_results:
                break

            overpass_query = f"""
[out:json][timeout:30];
{area_filter}->.searchArea;
(
  node["{tag_key}"="{tag_value}"]["name"](area.searchArea);
  way["{tag_key}"="{tag_value}"]["name"](area.searchArea);
);
out body center {max_results};
"""
            try:
                response = await client.post(
                    OVERPASS_URL,
                    data={"data": overpass_query},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            except httpx.HTTPError as exc:
                logger.error("Overpass API HTTP error: %s", exc)
                continue

            if response.status_code != 200:
                logger.error("Overpass API error %d: %s", response.status_code, response.text[:200])
                continue

            data = response.json()
            elements = data.get("elements", [])

            for elem in elements:
                if len(results) >= max_results:
                    break

                tags_data = elem.get("tags", {})
                name = tags_data.get("name", "")
                if not name:
                    continue

                # Get coordinates (node has lat/lon directly, way has center)
                lat = elem.get("lat", 0.0) or elem.get("center", {}).get("lat", 0.0)
                lon = elem.get("lon", 0.0) or elem.get("center", {}).get("lon", 0.0)

                # Build address from available tags
                street = tags_data.get("addr:street", "")
                housenumber = tags_data.get("addr:housenumber", "")
                addr_city = tags_data.get("addr:city", city)
                addr_state = tags_data.get("addr:state", state)
                addr_zip = tags_data.get("addr:postcode", "")
                address_parts = []
                if housenumber and street:
                    address_parts.append(f"{housenumber} {street}")
                elif street:
                    address_parts.append(street)
                if addr_city:
                    address_parts.append(addr_city)
                if addr_state:
                    address_parts.append(addr_state)
                if addr_zip:
                    address_parts.append(addr_zip)

                phone = tags_data.get("phone", "") or tags_data.get("contact:phone", "")
                website = tags_data.get("website", "") or tags_data.get("contact:website", "")
                osm_id = elem.get("id", 0)
                osm_type = elem.get("type", "node")

                results.append(PlaceResult(
                    place_id=f"osm_{osm_type}_{osm_id}",
                    name=name,
                    address=", ".join(address_parts) if address_parts else "",
                    city=addr_city,
                    state=addr_state,
                    zip_code=addr_zip,
                    phone=phone,
                    website=website,
                    maps_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                    rating=0.0,
                    review_count=0,
                    category=query,
                    types=[f"{tag_key}:{tag_value}"],
                    latitude=lat,
                    longitude=lon,
                    source="openstreetmap",
                ))

    logger.info("OpenStreetMap returned %d results for '%s in %s'", len(results), query, location)
    return results[:max_results]


async def _search_osm_nominatim(query: str, location: str, max_results: int) -> list[PlaceResult]:
    """Fallback: use Nominatim geocoding search for business types not in OSM tag map."""
    search_text = f"{query} in {location}"
    city, state = _parse_location(location)
    results: list[PlaceResult] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            params = {
                "q": search_text,
                "format": "json",
                "limit": min(max_results, 50),  # Nominatim max is 50
                "addressdetails": 1,
            }
            headers = {"User-Agent": "WarRoom-LeadGen/1.0"}
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            logger.error("Nominatim HTTP error: %s", exc)
            return []

        if response.status_code != 200:
            logger.error("Nominatim error %d: %s", response.status_code, response.text[:200])
            return []

        data = response.json()
        for item in data:
            addr = item.get("address", {})
            name = item.get("display_name", "").split(",")[0]

            results.append(PlaceResult(
                place_id=f"osm_nominatim_{item.get('osm_id', 0)}",
                name=name,
                address=item.get("display_name", ""),
                city=addr.get("city", "") or addr.get("town", "") or addr.get("village", city),
                state=addr.get("state", state),
                zip_code=addr.get("postcode", ""),
                phone="",
                website="",
                maps_url=f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item.get('osm_id', 0)}",
                rating=0.0,
                review_count=0,
                category=query,
                types=[item.get("type", ""), item.get("class", "")],
                latitude=float(item.get("lat", 0.0)),
                longitude=float(item.get("lon", 0.0)),
                source="openstreetmap",
            ))

    logger.info("Nominatim returned %d results for '%s'", len(results), search_text)
    return results[:max_results]


def _deduplicate_results(results: list[PlaceResult]) -> list[PlaceResult]:
    """Remove duplicates across sources by matching name + city (case-insensitive)."""
    seen: set[str] = set()
    deduped: list[PlaceResult] = []
    for place in results:
        key = f"{place.name.lower().strip()}|{place.city.lower().strip()}"
        if key not in seen:
            seen.add(key)
            deduped.append(place)
    return deduped


async def search_places(query: str, location: str, max_results: int = 60, radius_km: int = 25) -> list[PlaceResult]:
    """Search for businesses matching query in location.

    Sources tried in order of priority:
    1. Google Places API (if google_maps_api_key in settings DB)
    2. Yelp (scraped from frontend, no API key needed)
    3. OpenStreetMap Overpass API (always available, no key needed)

    Results are deduplicated across sources. The `source` field on each
    PlaceResult indicates where it came from.
    """
    all_results: list[PlaceResult] = []
    sources_tried: list[str] = []
    sources_used: list[str] = []

    # 1. Google Places (primary)
    google_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if google_key:
        sources_tried.append("google_places")
        google_results = await _search_google_places(query, location, max_results, radius_km)
        if google_results:
            sources_used.append(f"google_places({len(google_results)})")
            all_results.extend(google_results)
    else:
        logger.info("No GOOGLE_MAPS_API_KEY — skipping Google Places")

    # 2. Yelp scrape (secondary, fills gaps — no API key needed)
    remaining = max_results - len(all_results)
    if remaining > 0:
        sources_tried.append("yelp")
        yelp_results = await _search_yelp(query, location, remaining)
        if yelp_results:
            sources_used.append(f"yelp({len(yelp_results)})")
            all_results.extend(yelp_results)

    # 3. OpenStreetMap Overpass (tertiary, always available)
    remaining = max_results - len(all_results)
    if remaining > 0:
        sources_tried.append("openstreetmap")
        osm_results = await _search_openstreetmap(query, location, remaining)
        if osm_results:
            sources_used.append(f"openstreetmap({len(osm_results)})")
            all_results.extend(osm_results)

    # Deduplicate across sources
    deduped = _deduplicate_results(all_results)

    if not deduped:
        logger.warning(
            "No results found for '%s in %s' — tried sources: %s",
            query, location, ", ".join(sources_tried) or "none",
        )
    else:
        logger.info(
            "search_places('%s', '%s'): %d results from %s (tried: %s)",
            query, location, len(deduped),
            ", ".join(sources_used),
            ", ".join(sources_tried),
        )

    return deduped[:max_results]
