from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import requests
import json


def closest_satellite(request):
    """Render the closest satellite page"""
    return render(request, 'satellite_tracking/closest_satellite.html')


@require_http_methods(["POST"])
def get_closest_satellite_api(request):
    """
    API endpoint to get the closest satellite to given coordinates
    Uses N2YO.com API to fetch satellite data
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        altitude = float(data.get('altitude', 0))  # Default altitude to 0 (sea level)

        # Validate coordinates
        if not (-90 <= latitude <= 90):
            return JsonResponse({'error': 'Latitude must be between -90 and 90'}, status=400)
        if not (-180 <= longitude <= 180):
            return JsonResponse({'error': 'Longitude must be between -180 and 180'}, status=400)

        # Get API key from settings
        api_key = settings.N2YO_API_KEY
        if not api_key:
            return JsonResponse({'error': 'N2YO API key not configured'}, status=500)

        # N2YO API parameters
        # Get satellites above the location within a radius (in degrees)
        search_radius = 90  # Search radius in degrees
        category_id = 0  # 0 = All categories

        # Build the API URL for "above" endpoint
        # API: /above/{observer_lat}/{observer_lng}/{observer_alt}/{search_radius}/{category_id}/&apiKey={api_key}
        api_url = f"https://api.n2yo.com/rest/v1/satellite/above/{latitude}/{longitude}/{altitude}/{search_radius}/{category_id}/&apiKey={api_key}"

        # Make request to N2YO API
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        # Parse the response
        satellite_data = response.json()

        # Check if we got any satellites
        if 'above' not in satellite_data or len(satellite_data['above']) == 0:
            return JsonResponse({
                'error': 'No satellites found above this location',
                'latitude': latitude,
                'longitude': longitude
            }, status=404)

        # Find the closest satellite (lowest altitude from ground)
        satellites = satellite_data['above']
        closest = min(satellites, key=lambda s: s.get('satalt', float('inf')))

        # Format the response with detailed information
        result = {
            'success': True,
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude
            },
            'satellite': {
                'name': closest.get('satname', 'Unknown'),
                'id': closest.get('satid'),
                'altitude': closest.get('satalt', 0),  # km above ground
                'azimuth': closest.get('sataz', 0),    # degrees
                'elevation': closest.get('satel', 0),  # degrees above horizon
                'right_ascension': closest.get('satra', 0),
                'declination': closest.get('satdec', 0),
                'latitude': closest.get('satlat', 0),
                'longitude': closest.get('satlng', 0),
            },
            'total_satellites_found': len(satellites),
            'info': satellite_data.get('info', {})
        }

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid coordinate values: {str(e)}'}, status=400)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Failed to fetch satellite data: {str(e)}'}, status=500)
    except KeyError as e:
        return JsonResponse({'error': f'Missing required field: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
