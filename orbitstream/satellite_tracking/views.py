from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import requests
import json


def closest_satellite(request):
    """Render the closest satellite page"""
    context = {
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'satellite_tracking/closest_satellite.html', context)


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


def get_orbital_tracker_satellites(request):
    """
    API endpoint to get satellites for the orbital tracker.
    - For non-authenticated users: returns ISS position
    - For authenticated users: returns their saved satellites with current positions
    """
    try:
        api_key = settings.N2YO_API_KEY
        if not api_key:
            return JsonResponse({'error': 'N2YO API key not configured'}, status=500)

        satellites = []

        if request.user.is_authenticated:
            # Get user's saved satellites
            from saved_page.models import SavedSatellite
            saved_sats = SavedSatellite.objects.filter(user=request.user)

            for saved_sat in saved_sats:
                # Fetch current position for each saved satellite
                try:
                    # Use N2YO positions API to get current position
                    # /positions/{id}/{observer_lat}/{observer_lng}/{observer_alt}/{seconds}
                    api_url = f"https://api.n2yo.com/rest/v1/satellite/positions/{saved_sat.satellite_id}/0/0/0/1/&apiKey={api_key}"
                    response = requests.get(api_url, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        if 'positions' in data and len(data['positions']) > 0:
                            pos = data['positions'][0]
                            satellites.append({
                                'id': saved_sat.satellite_id,
                                'name': data.get('info', {}).get('satname', saved_sat.name),
                                'latitude': pos.get('satlatitude', 0),
                                'longitude': pos.get('satlongitude', 0),
                                'altitude': pos.get('sataltitude', 0),
                            })
                        else:
                            # Use stored position as fallback
                            satellites.append({
                                'id': saved_sat.satellite_id,
                                'name': saved_sat.name,
                                'latitude': saved_sat.latitude or 0,
                                'longitude': saved_sat.longitude or 0,
                                'altitude': saved_sat.altitude or 400,
                            })
                except Exception as e:
                    # Use stored position as fallback on error
                    satellites.append({
                        'id': saved_sat.satellite_id,
                        'name': saved_sat.name,
                        'latitude': saved_sat.latitude or 0,
                        'longitude': saved_sat.longitude or 0,
                        'altitude': saved_sat.altitude or 400,
                    })

            # If user has no saved satellites, show ISS as default
            if not satellites:
                satellites = get_iss_position(api_key)
        else:
            # For non-authenticated users, show ISS
            satellites = get_iss_position(api_key)

        return JsonResponse({
            'success': True,
            'satellites': satellites,
            'is_authenticated': request.user.is_authenticated,
        })

    except Exception as e:
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


def get_iss_position(api_key):
    """Helper function to get ISS current position"""
    ISS_NORAD_ID = 25544  # ISS NORAD catalog ID

    try:
        api_url = f"https://api.n2yo.com/rest/v1/satellite/positions/{ISS_NORAD_ID}/0/0/0/1/&apiKey={api_key}"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'positions' in data and len(data['positions']) > 0:
                pos = data['positions'][0]
                return [{
                    'id': ISS_NORAD_ID,
                    'name': data.get('info', {}).get('satname', 'ISS (ZARYA)'),
                    'latitude': pos.get('satlatitude', 0),
                    'longitude': pos.get('satlongitude', 0),
                    'altitude': pos.get('sataltitude', 420),
                }]
    except Exception:
        pass

    # Fallback ISS position if API fails
    return [{
        'id': ISS_NORAD_ID,
        'name': 'ISS (ZARYA)',
        'latitude': 0,
        'longitude': 0,
        'altitude': 420,
    }]
