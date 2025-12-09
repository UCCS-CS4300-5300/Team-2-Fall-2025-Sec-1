from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import requests
import json


def closest_satellite(request):
    """Render the closest satellite page"""
    # Get saved satellites for logged-in users
    saved_satellites = []
    if request.user.is_authenticated:
        from saved_page.models import SavedSatellite
        saved_satellites = list(SavedSatellite.objects.filter(user=request.user).values(
            'satellite_id', 'name', 'latitude', 'longitude', 'altitude'
        ))

    context = {
        'saved_satellites': saved_satellites,
        'saved_satellites_json': json.dumps(saved_satellites),
    }
    return render(request, 'satellite_tracking/closest_satellite.html', context)


@require_http_methods(["POST"])
def get_closest_satellite_api(request):
    """
    API endpoint to get the N closest satellites to given coordinates
    Uses N2YO.com API to fetch satellite data
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        altitude = float(data.get('altitude', 0))  # Default altitude to 0 (sea level)
        num_satellites = int(data.get('num_satellites', 5))  # Default to 5 satellites

        # Validate coordinates
        if not (-90 <= latitude <= 90):
            return JsonResponse({'error': 'Latitude must be between -90 and 90'}, status=400)
        if not (-180 <= longitude <= 180):
            return JsonResponse({'error': 'Longitude must be between -180 and 180'}, status=400)

        # Validate num_satellites
        if num_satellites < 1 or num_satellites > 50:
            return JsonResponse({'error': 'Number of satellites must be between 1 and 50'}, status=400)

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

        # Sort satellites by altitude (closest to furthest)
        satellites = sorted(satellite_data['above'], key=lambda s: s.get('satalt', float('inf')))

        # Get the N closest satellites
        closest_satellites = satellites[:num_satellites]

        # Format the response with detailed information for all satellites
        result = {
            'success': True,
            'location': {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude
            },
            'satellites': [
                {
                    'name': sat.get('satname', 'Unknown'),
                    'id': sat.get('satid'),
                    'altitude': sat.get('satalt', 0),  # km above ground
                    'azimuth': sat.get('sataz', 0),    # degrees
                    'elevation': sat.get('satel', 0),  # degrees above horizon
                    'right_ascension': sat.get('satra', 0),
                    'declination': sat.get('satdec', 0),
                    'latitude': sat.get('satlat', 0),
                    'longitude': sat.get('satlng', 0),
                }
                for sat in closest_satellites
            ],
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


@require_http_methods(["GET"])
def get_satellite_position_api(request):
    """
    API endpoint to get current position of a specific satellite by ID
    """
    try:
        satellite_id = request.GET.get('satellite_id')
        if not satellite_id:
            return JsonResponse({'error': 'satellite_id parameter required'}, status=400)

        # Observer coordinates (default to 0,0 for orbital data)
        observer_lat = float(request.GET.get('observer_lat', 0))
        observer_lng = float(request.GET.get('observer_lng', 0))
        observer_alt = float(request.GET.get('observer_alt', 0))

        # Get API key
        api_key = settings.N2YO_API_KEY
        if not api_key:
            return JsonResponse({'error': 'N2YO API key not configured'}, status=500)

        # N2YO API for satellite positions
        # API: /positions/{id}/{observer_lat}/{observer_lng}/{observer_alt}/{seconds}/&apiKey={api_key}
        seconds = 1  # Get current position
        api_url = f"https://api.n2yo.com/rest/v1/satellite/positions/{satellite_id}/{observer_lat}/{observer_lng}/{observer_alt}/{seconds}/&apiKey={api_key}"

        # Make request
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        satellite_data = response.json()

        # Format response
        if 'positions' in satellite_data and len(satellite_data['positions']) > 0:
            pos = satellite_data['positions'][0]
            result = {
                'success': True,
                'satellite': {
                    'id': satellite_data.get('info', {}).get('satid'),
                    'name': satellite_data.get('info', {}).get('satname'),
                    'latitude': pos.get('satlatitude'),
                    'longitude': pos.get('satlongitude'),
                    'altitude': pos.get('sataltitude'),
                    'azimuth': pos.get('azimuth'),
                    'elevation': pos.get('elevation'),
                    'right_ascension': pos.get('ra'),
                    'declination': pos.get('dec'),
                    'timestamp': pos.get('timestamp'),
                }
            }
            return JsonResponse(result)
        else:
            return JsonResponse({'error': 'No position data available'}, status=404)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Failed to fetch satellite data: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)
