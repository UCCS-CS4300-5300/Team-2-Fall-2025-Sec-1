// Satellite Tracking JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const manualLocationBtn = document.getElementById('manual-location-btn');
    const gpsBtn = document.getElementById('gps-btn');
    const dialog = document.getElementById('manual-location-dialog');
    const dialogClose = document.querySelector('.dialog-close');
    const coordinatesForm = document.getElementById('coordinates-form');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const satelliteInfo = document.getElementById('satellite-info');

    // Get CSRF token for POST requests
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    // Show dialog
    manualLocationBtn.addEventListener('click', function() {
        dialog.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    });

    // Close dialog
    function closeDialog() {
        dialog.style.display = 'none';
        document.body.style.overflow = '';
    }

    dialogClose.addEventListener('click', closeDialog);

    // Close dialog when clicking outside
    dialog.addEventListener('click', function(e) {
        if (e.target === dialog) {
            closeDialog();
        }
    });

    // Close dialog on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && dialog.style.display === 'flex') {
            closeDialog();
        }
    });

    // Handle manual location form submission
    coordinatesForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const latitude = parseFloat(document.getElementById('latitude').value);
        const longitude = parseFloat(document.getElementById('longitude').value);
        const altitude = parseFloat(document.getElementById('altitude').value) || 0;

        // Validate coordinates
        if (isNaN(latitude) || isNaN(longitude)) {
            showError('Please enter valid coordinates');
            return;
        }

        if (latitude < -90 || latitude > 90) {
            showError('Latitude must be between -90 and 90');
            return;
        }

        if (longitude < -180 || longitude > 180) {
            showError('Longitude must be between -180 and 180');
            return;
        }

        closeDialog();
        fetchClosestSatellite(latitude, longitude, altitude);
    });

    // Handle GPS button click
    gpsBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
            showError('Geolocation is not supported by your browser');
            return;
        }

        showLoading();

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                const altitude = position.coords.altitude || 0;

                fetchClosestSatellite(latitude, longitude, altitude);
            },
            function(error) {
                hideLoading();
                let errorMsg = 'Unable to retrieve your location';

                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Location permission denied. Please enable location services.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Location information is unavailable.';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Location request timed out.';
                        break;
                }

                showError(errorMsg);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });

    // Fetch closest satellites from API
    function fetchClosestSatellite(latitude, longitude, altitude) {
        showLoading();
        hideError();
        hideSatelliteInfo();

        // Get number of satellites from selector
        const numSatellites = parseInt(document.getElementById('num-satellites').value) || 5;

        const data = {
            latitude: latitude,
            longitude: longitude,
            altitude: altitude,
            num_satellites: numSatellites
        };

        fetch('/satellite-tracking/api/get-closest-satellite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err)).catch(() => {
                    return Promise.reject({ error: `HTTP Error ${response.status}: ${response.statusText}` });
                });
            }
            return response.json();
        })
        .then(data => {
            hideLoading();

            console.log('API Response:', data);

            if (data.success && data.satellites) {
                displaySatelliteInfo(data);
            } else {
                showError(data.error || 'Failed to fetch satellite data');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Full error object:', error);

            let errorMessage = 'An error occurred while fetching satellite data';

            if (error.error) {
                errorMessage = error.error;
            } else if (error.message) {
                errorMessage = error.message;
            } else if (typeof error === 'string') {
                errorMessage = error;
            }

            showError(errorMessage);
        });
    }

    // Current satellite data storage for save functionality
    let currentSatelliteData = null;
    let currentSatellites = [];

    // Display satellite information
    function displaySatelliteInfo(data) {
        console.log('displaySatelliteInfo called with:', data);

        const satellites = data.satellites;
        const loc = data.location;

        console.log('Satellites type:', typeof satellites);
        console.log('Satellites value:', satellites);
        console.log('Is array?', Array.isArray(satellites));

        if (!satellites || !Array.isArray(satellites) || satellites.length === 0) {
            console.error('No satellites in data:', data);
            showError('No satellite data received');
            return;
        }

        console.log(`Processing ${satellites.length} satellites`);

        // Store all satellites
        currentSatellites = satellites;

        // Display the first (closest) satellite in the info panel
        const sat = satellites[0];
        console.log('First satellite:', sat);
        console.log('First satellite ID:', sat ? sat.id : 'undefined');

        // Validate that we have required data
        if (!sat || !sat.id) {
            console.error('Satellite ID is missing:', sat);
            showError('Satellite data is incomplete - cannot save');
            return;
        }

        // Store current satellite data for saving
        currentSatelliteData = {
            satellite_id: sat.id,
            name: sat.name || 'Unknown',
            altitude: sat.altitude || 0,
            azimuth: sat.azimuth || 0,
            elevation: sat.elevation || 0,
            latitude: sat.latitude || 0,
            longitude: sat.longitude || 0
        };

        // Update satellite details
        document.getElementById('sat-name').textContent = sat.name;
        document.getElementById('sat-id').textContent = sat.id;
        document.getElementById('sat-altitude').textContent = `${sat.altitude.toFixed(2)} km`;

        // Update position
        document.getElementById('sat-lat').textContent = `${sat.latitude.toFixed(4)}°`;
        document.getElementById('sat-lng').textContent = `${sat.longitude.toFixed(4)}°`;
        document.getElementById('sat-elevation').textContent = `${sat.elevation.toFixed(2)}°`;

        // Update orientation
        document.getElementById('sat-azimuth').textContent = `${sat.azimuth.toFixed(2)}°`;
        document.getElementById('sat-ra').textContent = `${sat.right_ascension.toFixed(2)}°`;
        document.getElementById('sat-dec').textContent = `${sat.declination.toFixed(2)}°`;

        // Update user location
        document.getElementById('user-lat').textContent = `${loc.latitude.toFixed(4)}°`;
        document.getElementById('user-lng').textContent = `${loc.longitude.toFixed(4)}°`;
        document.getElementById('total-sats').textContent = data.total_satellites_found;

        // Show the info section
        satelliteInfo.style.display = 'block';

        // Check if satellite is already saved and update button state
        checkSatelliteSaveStatus(sat.id);

        // Dispatch event for orbital tracking visualization with all satellites
        window.dispatchEvent(new CustomEvent('satellitesFound', {
            detail: {
                satellites: satellites,
                location: loc
            }
        }));

        // Scroll to orbital tracking section
        const orbitalSection = document.getElementById('orbital-tracking');
        if (orbitalSection) {
            orbitalSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // Check if satellite is saved
    function checkSatelliteSaveStatus(satelliteId) {
        const saveBtn = document.getElementById('save-satellite-btn');
        if (!saveBtn) return;

        fetch(`/saved/api/check/satellite/?satellite_id=${satelliteId}`)
            .then(response => response.json())
            .then(data => {
                updateSaveButtonState(data.saved);
            })
            .catch(error => {
                console.error('Error checking save status:', error);
            });
    }

    // Update save button appearance
    function updateSaveButtonState(isSaved) {
        const saveBtn = document.getElementById('save-satellite-btn');
        const saveText = document.getElementById('save-satellite-text');
        if (!saveBtn || !saveText) return;

        if (isSaved) {
            saveBtn.classList.remove('location-btn-primary');
            saveBtn.classList.add('location-btn-secondary');
            saveBtn.querySelector('svg path').setAttribute('fill', 'currentColor');
            saveText.textContent = 'Saved';
        } else {
            saveBtn.classList.add('location-btn-primary');
            saveBtn.classList.remove('location-btn-secondary');
            saveBtn.querySelector('svg path').setAttribute('fill', 'none');
            saveText.textContent = 'Save Satellite';
        }
    }

    // Save/unsave satellite
    const saveBtn = document.getElementById('save-satellite-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            if (!currentSatelliteData) {
                showError('No satellite data to save');
                return;
            }

            // Validate satellite_id before sending
            if (!currentSatelliteData.satellite_id) {
                console.error('Satellite ID is missing in currentSatelliteData:', currentSatelliteData);
                showError('Cannot save satellite: missing satellite ID');
                return;
            }

            console.log('Saving satellite data:', currentSatelliteData);

            fetch('/saved/api/toggle/satellite/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(currentSatelliteData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Server error:', data.error);
                    showError(data.error);
                } else {
                    console.log('Save successful:', data);
                    updateSaveButtonState(data.saved);
                }
            })
            .catch(error => {
                console.error('Error saving satellite:', error);
                showError('Failed to save satellite. Check console for details.');
            });
        });
    }

    // UI Helper Functions
    function showLoading() {
        loadingIndicator.style.display = 'flex';
    }

    function hideLoading() {
        loadingIndicator.style.display = 'none';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';

        // Auto-hide after 5 seconds
        setTimeout(() => {
            hideError();
        }, 5000);
    }

    function hideError() {
        errorMessage.style.display = 'none';
    }

    function hideSatelliteInfo() {
        satelliteInfo.style.display = 'none';
    }

    // Listen for satellite clicks from the 3D visualization
    window.addEventListener('satelliteClicked', function(e) {
        const { id, name, data } = e.detail;

        console.log('Satellite clicked event received:', name, id);

        // Update the info panel with the clicked satellite
        if (data) {
            // Update satellite details
            document.getElementById('sat-name').textContent = name || 'Unknown';
            document.getElementById('sat-id').textContent = id || '-';
            document.getElementById('sat-altitude').textContent = data.altitude ? `${data.altitude.toFixed(2)} km` : '-';

            // Update position
            document.getElementById('sat-lat').textContent = data.latitude ? `${data.latitude.toFixed(4)}°` : '-';
            document.getElementById('sat-lng').textContent = data.longitude ? `${data.longitude.toFixed(4)}°` : '-';
            document.getElementById('sat-elevation').textContent = data.elevation ? `${data.elevation.toFixed(2)}°` : '-';

            // Update orientation
            document.getElementById('sat-azimuth').textContent = data.azimuth ? `${data.azimuth.toFixed(2)}°` : '-';
            document.getElementById('sat-ra').textContent = data.right_ascension ? `${data.right_ascension.toFixed(2)}°` : '-';
            document.getElementById('sat-dec').textContent = data.declination ? `${data.declination.toFixed(2)}°` : '-';

            // Update current satellite data for saving
            currentSatelliteData = {
                satellite_id: id,
                name: name || 'Unknown',
                altitude: data.altitude || 0,
                azimuth: data.azimuth || 0,
                elevation: data.elevation || 0,
                latitude: data.latitude || 0,
                longitude: data.longitude || 0
            };

            // Check if this satellite is already saved
            checkSatelliteSaveStatus(id);

            // Make sure info section is visible
            satelliteInfo.style.display = 'block';

            // Scroll to info section
            satelliteInfo.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
});
