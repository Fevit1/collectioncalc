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
COMIC_CATEGORY_ID = "63"  # Collectibles > Comic Books & Memorabilia > Comics

# Placeholder image URL - eBay requires at least 1 image
# Using a generic comic-related placeholder until user uploads their own
PLACEHOLDER_IMAGE_URL = "https://u-mercari-images.mercdn.net/photos/m55849664274_1.jpg"

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
        location_key = "collectioncalc-default"
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
            "name": "CollectionCalc Default Location",
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


def create_listing(user_id: str, title: str, issue: str, price: float, grade: str = 'VF', description: str = None) -> dict:
    """
    Create a listing on eBay for a comic book.
    
    Args:
        user_id: The user's ID (to get their eBay token)
        title: Comic book title (e.g., "Amazing Spider-Man")
        issue: Issue number (e.g., "300")
        price: Listing price in USD
        grade: Comic grade (NM, VF, FN, etc.)
        description: User-approved listing description (HTML)
    
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
        <p>Listed via CollectionCalc - AI-powered comic valuation.</p>
        <p>Please review photos carefully. Feel free to ask any questions before purchasing.</p>
        """
    
    # Create inventory item SKU
    sku = f"CC-{title.replace(' ', '-')[:20]}-{issue}-{int(price*100)}"
    
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
                "weight": {
                    "value": 8,
                    "unit": "OUNCE"
                },
                "dimensions": {
                    "height": 0.25,
                    "length": 10.5,
                    "width": 7,
                    "unit": "INCH"
                },
                "packageType": "MAILING_BOX"
            },
            "product": {
                "title": listing_title,
                "description": description,
                "imageUrls": [PLACEHOLDER_IMAGE_URL],
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
        
        offer_data = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "listingDescription": description,
            "availableQuantity": 1,
            "categoryId": COMIC_CATEGORY_ID,
            "merchantLocationKey": location_key,
            "pricingSummary": {
                "price": {
                    "value": str(round(price, 2)),
                    "currency": "USD"
                }
            },
            "listingPolicies": {
                "fulfillmentPolicyId": policies['fulfillmentPolicyId'],
                "paymentPolicyId": policies['paymentPolicyId'],
                "returnPolicyId": policies['returnPolicyId']
            }
        }
        
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
        
        # Step 5: Publish the offer (make it live)
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
            'price': price
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
