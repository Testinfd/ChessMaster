import aiohttp
import logging
import json
from info import SHORTENER_ENABLED, SHORTENER_API, SHORTENER_DOMAIN, SHORTENER_API_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def shorten_url(url):
    """Shorten a URL using the configured URL shortener service."""
    if not SHORTENER_ENABLED or not SHORTENER_API or not SHORTENER_API_KEY:
        return url
        
    try:
        async with aiohttp.ClientSession() as session:
            # Prepare the request based on the shortener API format
            if "v.gd" in SHORTENER_API.lower() or "is.gd" in SHORTENER_API.lower():
                # For v.gd / is.gd
                params = {
                    "format": "json",
                    "url": url
                }
                async with session.get(SHORTENER_API, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("shorturl", url)
            
            elif "tinyurl" in SHORTENER_API.lower():
                # For TinyURL
                params = {
                    "url": url
                }
                headers = {
                    "Authorization": f"Bearer {SHORTENER_API_KEY}"
                }
                async with session.post(SHORTENER_API, json=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("data", {}).get("tiny_url", url)
            
            elif "bitly" in SHORTENER_API.lower():
                # For Bit.ly
                headers = {
                    "Authorization": f"Bearer {SHORTENER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "long_url": url,
                    "domain": SHORTENER_DOMAIN or "bit.ly"
                }
                async with session.post(SHORTENER_API, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("link", url)
            
            # Generic API endpoint
            else:
                headers = {
                    "API-Key": SHORTENER_API_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "url": url,
                    "domain": SHORTENER_DOMAIN
                }
                async with session.post(SHORTENER_API, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("shortenedUrl", url)
    
    except Exception as e:
        logger.error(f"Error shortening URL: {e}")
    
    # Return original URL if shortening failed
    return url 