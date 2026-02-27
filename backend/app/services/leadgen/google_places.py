"""Google Places API integration for business discovery."""

import httpx
import logging
import random
from dataclasses import dataclass, field
import os

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
    )


def _generate_mock_businesses(query: str, location: str, max_results: int) -> list[PlaceResult]:
    """Generate realistic mock businesses when no Google API key is available."""
    city, state = location, ""
    if "," in location:
        city, state = [x.strip() for x in location.split(",", 1)]
    
    # Mock business name templates
    prefixes = ["Elite", "Premier", "Professional", "First Choice", "Quality", "Trusted", "Family", "Quick", "Affordable"]
    suffixes = ["LLC", "Inc", "& Co", "Services", "Solutions", "Pros", "Express", "Plus"]
    
    businesses = []
    for i in range(min(max_results, random.randint(10, 20))):
        name = f"{random.choice(prefixes)} {city} {query.title()}"
        if random.random() < 0.3:  # 30% chance of suffix
            name += f" {random.choice(suffixes)}"
        
        # Mock address
        street_num = random.randint(100, 9999)
        street_names = ["Main St", "Oak Ave", "First St", "Broadway", "Market St", "State Hwy", "Commerce Blvd"]
        address = f"{street_num} {random.choice(street_names)}"
        zip_code = f"{random.randint(10000, 99999)}"
        
        # Mock phone (local area code)
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        
        # 60% have websites
        website = ""
        if random.random() < 0.6:
            domain = name.lower().replace(" ", "").replace("&", "and")[:15]
            website = f"https://www.{domain}.com"
        
        businesses.append(PlaceResult(
            place_id=f"mock_{i}_{hash(name) % 100000}",
            name=name,
            address=f"{address}, {city}, {state} {zip_code}",
            city=city,
            state=state,
            zip_code=zip_code,
            phone=phone,
            website=website,
            maps_url=f"https://maps.google.com/?q={name.replace(' ', '+')}",
            rating=round(random.uniform(3.2, 4.8), 1),
            review_count=random.randint(5, 150),
            category=query,
            types=[query.replace(" ", "_"), "establishment"],
            latitude=round(random.uniform(30.0, 45.0), 6),
            longitude=round(random.uniform(-120.0, -70.0), 6),
        ))
    
    return businesses


async def search_places(query: str, location: str, max_results: int = 60) -> list[PlaceResult]:
    """Search Google Places API for businesses matching query in location."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # Use mock data if no API key
    if not api_key:
        logger.info("No GOOGLE_MAPS_API_KEY found, generating mock data for '%s in %s'", query, location)
        return _generate_mock_businesses(query, location, max_results)

    search_text = f"{query} in {location}"
    results: list[PlaceResult] = []
    page_token = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(results) < max_results:
            body: dict = {"textQuery": search_text, "maxResultCount": 20}
            if page_token:
                body["pageToken"] = page_token

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": ",".join(PLACES_DETAIL_FIELDS),
            }

            response = await client.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers)

            if response.status_code != 200:
                logger.error("Places API error %d: %s", response.status_code, response.text)
                break

            data = response.json()
            places = data.get("places", [])

            for place in places:
                results.append(_parse_place(place))

            page_token = data.get("nextPageToken")
            if not page_token or not places:
                break

    logger.info("Found %d places for '%s'", len(results), search_text)
    return results[:max_results]