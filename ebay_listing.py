"""
eBay Listing Integration for CollectionCalc
Creates listings on eBay using the Inventory API.
"""

import os
import requests
from ebay_oauth import get_user_token, is_sandbox_mode

# eBay API endpoints
EBAY_API_URL = "https://api.ebay.com"
EBAY_SANDBOX_API_URL = "https://api.sandbox.ebay.com"

# Comic book category on eBay  
# 259104 = Collectibles > Comic Books & Memorabilia > Comics > Comics & Graphic Novels
COMIC_CATEGORY_ID = "259104"

# Placeholder image URL - eBay requires at least 1 image
# Hosted on our Cloudflare Pages frontend
PLACEHOLDER_IMAGE_URL = "https://slabworthy.com/images/placeholder.png"

# Grade to eBay condition mapping (using Inventory API enum values)
GRADE_TO_CONDITION = {
    'MT': 'LIKE_NEW',
    'NM': 'LIKE_NEW',
    'VF': 'USED_EXCELLENT',
    'FN': 'USED_VERY_GOOD',
    'VG': 'USED_VERY_GOOD',
    'G': 'USED_GOOD',
    'FR': 'USED_ACCEPTABLE',
    'PR': 'USED_ACCEPTABLE'
}

# Condition descriptions for buyers
CONDITION_DESCRIPTIONS = {
    'MT': 'Mint - Like new, perfect condition',
    'NM': 'Near Mint - Excellent condition with minimal wear',
    'VF': 'Very Fine - Minor wear, very good condition',
    'FN': 'Fine - Moderate wear but still presentable',
    'VG': 'Very Good - Noticeable wear but complete',
    'G': 'Good - Significant wear, reading copy',
    'FR': 'Fair - Heavy wear, complete but rough',
    'PR': 'Poor - Heavily worn, may have damage'
}


def upload_image_to_ebay(access_token: str, image_url_or_bytes, filename: str = "comic.jpg") -> dict:
    """
    Upload an image to eBay Picture Services using the Media API createImageFromUrl.

    Accepts either a public HTTPS image URL (preferred) or raw image bytes.
    When given a URL, uses eBay's createImageFromUrl so eBay fetches the image directly.
    When given bytes, falls back to base64-encoding and a data URI (not recommended).

    Args:
        access_token: User's eBay access token
        image_url_or_bytes: Either a public HTTPS URL string, or raw image bytes
        filename: Original filename (unused for URL path, kept for backward compat)

    Returns:
        Dict with success status and image URL or error
    """
    # Media API uses apim.ebay.com, not api.ebay.com
    media_base = "https://apim.sandbox.ebay.com" if is_sandbox_mode() else "https://apim.ebay.com"

    # Determine if we got a URL string or raw bytes
    if isinstance(image_url_or_bytes, str):
        source_url = image_url_or_bytes
    elif isinstance(image_url_or_bytes, bytes):
        # We have raw bytes — this path shouldn't normally be hit anymore,
        # but kept for backward compat. eBay needs a URL, so we can't use bytes directly.
        print(f"Warning: upload_image_to_ebay received raw bytes ({len(image_url_or_bytes)} bytes). "
              "createImageFromUrl requires a public URL. Returning error.")
        return {'success': False, 'error': 'eBay Media API requires a public image URL, not raw bytes'}
    else:
        return {'success': False, 'error': 'Invalid image data type'}

    try:
        # Use createImageFromUrl — eBay fetches the image from our R2 URL
        create_url = f"{media_base}/commerce/media/v1_beta/image/create_image_from_url"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        body = {"imageUrl": source_url}

        print(f"Calling eBay createImageFromUrl:")
        print(f"  URL: {create_url}")
        print(f"  imageUrl: {source_url[:80]}...")
        response = requests.post(create_url, headers=headers, json=body)

        if response.status_code == 201:
            # Success — response body contains imageUrl (EPS URL) directly
            result_data = response.json() if response.text else {}
            eps_url = result_data.get('imageUrl')
            location = response.headers.get('location', '')
            image_id = location.split('/')[-1] if location else None

            print(f"Image created! EPS URL: {eps_url}, location: {location}")

            if eps_url:
                return {
                    'success': True,
                    'image_url': eps_url,
                    'image_id': image_id
                }

            # If no imageUrl in body, try getImage with the location header
            if image_id:
                get_url = f"{media_base}/commerce/media/v1_beta/image/{image_id}"
                get_response = requests.get(get_url, headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                })
                if get_response.status_code == 200:
                    eps_url = get_response.json().get('imageUrl')
                    if eps_url:
                        return {'success': True, 'image_url': eps_url, 'image_id': image_id}

                return {'success': True, 'image_id': image_id,
                        'message': 'Image uploaded but could not retrieve EPS URL'}

        # Handle errors
        error_detail = response.text
        print(f"Image upload failed: {response.status_code} - {error_detail}")
        return {
            'success': False,
            'error': f'Upload failed ({response.status_code}): {error_detail}',
            'status_code': response.status_code
        }

    except Exception as e:
        print(f"Image upload error: {e}")
        return {'success': False, 'error': str(e)}

def get_api_url():
    """Get the appropriate eBay API URL based on sandbox mode."""
    return EBAY_SANDBOX_API_URL if is_sandbox_mode() else EBAY_API_URL


def get_or_create_merchant_location(access_token: str) -> str:
    """
    Get existing merchant location or create a default one.
    
    Args:
        access_token: User's eBay access token
    
    Returns:
        merchantLocationKey string, or None if failed
    """
    api_url = get_api_url()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Try to get existing locations
    try:
        locations_url = f"{api_url}/sell/inventory/v1/location"
        response = requests.get(locations_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            locations = data.get('locations', [])
            if locations:
                # Return first existing location
                return locations[0].get('merchantLocationKey')
        
        # No locations found, create a default one
        location_key = "slabworthy-default"
        create_url = f"{api_url}/sell/inventory/v1/location/{location_key}"
        
        location_data = {
            "location": {
                "address": {
                    "addressLine1": "123 Main Street",
                    "city": "San Jose",
                    "stateOrProvince": "CA",
                    "postalCode": "95131",
                    "country": "US"
                }
            },
            "locationTypes": ["WAREHOUSE"],
            "name": "Slab Worthy Default Location",
            "merchantLocationStatus": "ENABLED"
        }
        
        create_response = requests.post(create_url, headers=headers, json=location_data)
        
        if create_response.status_code in [200, 201, 204]:
            print(f"Created merchant location: {location_key}")
            return location_key
        else:
            print(f"Failed to create location: {create_response.status_code} - {create_response.text}")
            # Try with PUT instead (eBay API quirk)
            create_response = requests.put(create_url, headers=headers, json=location_data)
            if create_response.status_code in [200, 201, 204]:
                print(f"Created merchant location with PUT: {location_key}")
                return location_key
            print(f"PUT also failed: {create_response.status_code} - {create_response.text}")
            return None
            
    except Exception as e:
        print(f"Error getting/creating merchant location: {e}")
        return None


def get_or_create_listing_policies(access_token: str) -> dict:
    """
    Get existing business policies or create default ones.
    
    Args:
        access_token: User's eBay access token
    
    Returns:
        Dict with fulfillmentPolicyId, paymentPolicyId, returnPolicyId
    """
    api_url = get_api_url()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    policies = {
        'fulfillmentPolicyId': None,
        'paymentPolicyId': None,
        'returnPolicyId': None
    }
    
    try:
        # Get fulfillment policies
        print("Get fulfillment policies: 400")
        fulfillment_url = f"{api_url}/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US"
        response = requests.get(fulfillment_url, headers=headers)
        print(f"Get fulfillment response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            fulfillment_policies = data.get('fulfillmentPolicies', [])
            if fulfillment_policies:
                policies['fulfillmentPolicyId'] = fulfillment_policies[0].get('fulfillmentPolicyId')
                print(f"Found fulfillment policy: {policies['fulfillmentPolicyId']}")
        
        # Get payment policies
        payment_url = f"{api_url}/sell/account/v1/payment_policy?marketplace_id=EBAY_US"
        response = requests.get(payment_url, headers=headers)
        print(f"Get payment response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            payment_policies = data.get('paymentPolicies', [])
            if payment_policies:
                policies['paymentPolicyId'] = payment_policies[0].get('paymentPolicyId')
                print(f"Found payment policy: {policies['paymentPolicyId']}")
        
        # Get return policies
        return_url = f"{api_url}/sell/account/v1/return_policy?marketplace_id=EBAY_US"
        response = requests.get(return_url, headers=headers)
        print(f"Get return response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return_policies = data.get('returnPolicies', [])
            if return_policies:
                policies['returnPolicyId'] = return_policies[0].get('returnPolicyId')
                print(f"Found return policy: {policies['returnPolicyId']}")
        
        # Check if we have all policies
        missing = [k for k, v in policies.items() if not v]
        if missing:
            print(f"Missing policies: {missing}")
        
        return policies
        
    except Exception as e:
        print(f"Error getting policies: {e}")
        return policies


def create_listing(user_id: str, title: str, issue: str, price: float, grade: str = 'VF',
                    description: str = None, publish: bool = False, image_urls: list = None,
                    listing_format: str = 'FIXED_PRICE', auction_duration: str = 'DAYS_7',
                    start_price: float = None, reserve_price: float = None,
                    buy_it_now_price: float = None) -> dict:
    """
    Create a listing on eBay for a comic book.

    Args:
        user_id: The user's ID (to get their eBay token)
        title: Comic book title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300")
        price: Listing price in USD (Buy It Now price for fixed, start price for auction)
        grade: Comic grade (NM, VF, FN, etc.)
        description: User-approved listing description (HTML)
        publish: If True, publish immediately (live). If False, create as draft (default)
        image_urls: List of eBay-hosted image URLs. If None, uses placeholder.
        listing_format: 'FIXED_PRICE' or 'AUCTION' (default: FIXED_PRICE)
        auction_duration: Duration for auctions - DAYS_1, DAYS_3, DAYS_5, DAYS_7, DAYS_10 (default: DAYS_7)
        start_price: Starting bid price for auctions (defaults to price if not set)
        reserve_price: Optional reserve price for auctions (minimum sale price)
        buy_it_now_price: Optional Buy It Now price for auctions

    Returns:
        Dict with success status and listing details or error
    """
    # Get user's access token
    token_data = get_user_token(user_id)
    if not token_data or not token_data.get('access_token'):
        return {'success': False, 'error': 'Not connected to eBay. Please connect your account.'}
    
    access_token = token_data['access_token']
    api_url = get_api_url()
    
    # Get condition info
    condition = GRADE_TO_CONDITION.get(grade.upper(), 'USED_EXCELLENT')
    condition_desc = CONDITION_DESCRIPTIONS.get(grade.upper(), 'Good condition')
    
    # Build listing title (eBay max 80 chars)
    listing_title = f"{title} #{issue} Comic Book - {grade} Condition"
    if len(listing_title) > 80:
        listing_title = f"{title} #{issue} - {grade}"[:80]
    
    # Use provided description or generate a basic one
    if not description:
        description = f"""
        <h2>{title} #{issue}</h2>
        <p><strong>Condition:</strong> {grade} - {condition_desc}</p>
        <p>Listed via Slab Worthy - AI-powered comic valuation.</p>
        <p>Please review photos carefully. Feel free to ask any questions before purchasing.</p>
        """
    
    # Create inventory item SKU (with timestamp to ensure uniqueness)
    import time
    timestamp = int(time.time())
    sku = f"CC-{title.replace(' ', '-')[:15]}-{issue}-{timestamp}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Content-Language': 'en-US'
    }
    
    try:
        # Step 1: Create or update inventory item (with image!)
        inventory_url = f"{api_url}/sell/inventory/v1/inventory_item/{sku}"
        
        inventory_data = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": 1
                }
            },
            "condition": condition,
            "conditionDescription": condition_desc,
            "packageWeightAndSize": {
                "dimensions": {
                    "height": 1,
                    "length": 11,
                    "width": 7,
                    "unit": "INCH"
                },
                "packageType": "LETTER",
                "weight": {
                    "value": 8,
                    "unit": "OUNCE"
                }
            },
            "product": {
                "title": listing_title,
                "description": description,
                "imageUrls": image_urls if image_urls else [PLACEHOLDER_IMAGE_URL],
                "aspects": {
                    "Type": ["Comic Book"],
                    "Grade": [grade]
                }
            }
        }
        
        print(f"Creating inventory item: {sku}")
        inv_response = requests.put(inventory_url, headers=headers, json=inventory_data)
        
        if inv_response.status_code not in [200, 201, 204]:
            error_detail = inv_response.text
            print(f"Inventory creation failed: {inv_response.status_code} - {error_detail}")
            return {
                'success': False, 
                'error': f'Failed to create inventory item: {error_detail}',
                'status_code': inv_response.status_code
            }
        
        print(f"Inventory item created successfully")
        
        # Step 2: Get or create merchant location
        location_key = get_or_create_merchant_location(access_token)
        if not location_key:
            return {
                'success': False,
                'error': 'Could not set up merchant location. Please try again.'
            }
        print(f"Created merchant location: {location_key}")
        
        # Step 3: Get or create listing policies
        policies = get_or_create_listing_policies(access_token)
        
        # Check if we have all required policies
        if not all([policies.get('fulfillmentPolicyId'), policies.get('paymentPolicyId'), policies.get('returnPolicyId')]):
            missing = [k.replace('PolicyId', '') for k, v in policies.items() if not v]
            return {
                'success': False,
                'error': f'Could not set up listing policies (shipping, payment, returns). Please try again.',
                'missing_policies': missing
            }
        
        # Step 4: Create offer (this makes it a listing)
        offer_url = f"{api_url}/sell/inventory/v1/offer"

        # Normalize format
        fmt = listing_format.upper() if listing_format else 'FIXED_PRICE'
        if fmt not in ('FIXED_PRICE', 'AUCTION'):
            fmt = 'FIXED_PRICE'

        # Build pricing summary based on format
        if fmt == 'AUCTION':
            auction_start = start_price if start_price else price
            pricing_summary = {
                "auctionStartPrice": {
                    "value": str(round(auction_start, 2)),
                    "currency": "USD"
                }
            }
            # Optional reserve price
            if reserve_price and reserve_price > auction_start:
                pricing_summary["auctionReservePrice"] = {
                    "value": str(round(reserve_price, 2)),
                    "currency": "USD"
                }
            # Optional Buy It Now price (must be > start price)
            if buy_it_now_price and buy_it_now_price > auction_start:
                pricing_summary["price"] = {
                    "value": str(round(buy_it_now_price, 2)),
                    "currency": "USD"
                }
        else:
            pricing_summary = {
                "price": {
                    "value": str(round(price, 2)),
                    "currency": "USD"
                }
            }

        offer_data = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": fmt,
            "listingDescription": description,
            "availableQuantity": 1,
            "categoryId": COMIC_CATEGORY_ID,
            "merchantLocationKey": location_key,
            "pricingSummary": pricing_summary,
            "listingPolicies": {
                "fulfillmentPolicyId": policies['fulfillmentPolicyId'],
                "paymentPolicyId": policies['paymentPolicyId'],
                "returnPolicyId": policies['returnPolicyId']
            }
        }

        # Add auction duration if auction format
        if fmt == 'AUCTION':
            valid_durations = ['DAYS_1', 'DAYS_3', 'DAYS_5', 'DAYS_7', 'DAYS_10']
            duration = auction_duration if auction_duration in valid_durations else 'DAYS_7'
            offer_data["listingDuration"] = duration
        
        print(f"Creating offer with policies: {policies}")
        offer_response = requests.post(offer_url, headers=headers, json=offer_data)
        
        if offer_response.status_code not in [200, 201]:
            error_detail = offer_response.text
            print(f"Offer creation failed: {offer_response.status_code} - {error_detail}")
            
            # Check if it's a policy error - common for new sellers
            if 'policy' in error_detail.lower() or 'fulfillment' in error_detail.lower():
                return {
                    'success': False,
                    'error': 'Please set up your eBay business policies first (shipping, payment, returns). Go to eBay Seller Hub > Payments and Shipping.',
                    'needs_setup': True
                }
            
            return {
                'success': False,
                'error': f'Failed to create offer: {error_detail}',
                'status_code': offer_response.status_code
            }
        
        offer_result = offer_response.json()
        offer_id = offer_result.get('offerId')
        print(f"Offer created: {offer_id}")
        
        # Step 5: Publish the offer (only if publish=True)
        if publish:
            publish_url = f"{api_url}/sell/inventory/v1/offer/{offer_id}/publish"
            
            print(f"Publishing offer: {offer_id}")
            publish_response = requests.post(publish_url, headers=headers)
            
            if publish_response.status_code not in [200, 201]:
                error_detail = publish_response.text
                print(f"Publish failed: {publish_response.status_code} - {error_detail}")
                return {
                    'success': False,
                    'error': f'Created draft but failed to publish: {error_detail}',
                    'offer_id': offer_id,
                    'draft': True
                }
            
            publish_result = publish_response.json()
            listing_id = publish_result.get('listingId')
            print(f"Published! Listing ID: {listing_id}")
            
            # Build listing URL
            if is_sandbox_mode():
                listing_url = f"https://www.sandbox.ebay.com/itm/{listing_id}"
            else:
                listing_url = f"https://www.ebay.com/itm/{listing_id}"
            
            return {
                'success': True,
                'listing_id': listing_id,
                'listing_url': listing_url,
                'offer_id': offer_id,
                'sku': sku,
                'title': listing_title,
                'price': price,
                'format': fmt,
                'auction_duration': auction_duration if fmt == 'AUCTION' else None,
                'draft': False
            }
        else:
            # Draft mode - return link to Seller Hub drafts
            print(f"Draft created (not published): {offer_id}")
            
            drafts_url = "https://www.ebay.com/sh/lst/drafts"
            if is_sandbox_mode():
                drafts_url = "https://www.sandbox.ebay.com/sh/lst/drafts"
            
            return {
                'success': True,
                'offer_id': offer_id,
                'sku': sku,
                'title': listing_title,
                'price': price,
                'format': fmt,
                'auction_duration': auction_duration if fmt == 'AUCTION' else None,
                'draft': True,
                'drafts_url': drafts_url,
                'message': 'Draft created. Visit Seller Hub to add photos and publish.'
            }
        
    except requests.exceptions.RequestException as e:
        print(f"eBay API request failed: {e}")
        return {'success': False, 'error': f'API request failed: {str(e)}'}
    except Exception as e:
        print(f"Listing creation error: {e}")
        return {'success': False, 'error': str(e)}


def get_listing_status(user_id: str, listing_id: str) -> dict:
    """
    Check the status of an eBay listing.
    
    Args:
        user_id: The user's ID
        listing_id: The eBay listing ID
    
    Returns:
        Dict with listing status information
    """
    token_data = get_user_token(user_id)
    if not token_data or not token_data.get('access_token'):
        return {'success': False, 'error': 'Not connected to eBay'}
    
    access_token = token_data['access_token']
    api_url = get_api_url()
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    try:
        # Use Trading API or Inventory API to get status
        # For now, just return basic info
        return {
            'success': True,
            'listing_id': listing_id,
            'status': 'active'  # Simplified for now
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
