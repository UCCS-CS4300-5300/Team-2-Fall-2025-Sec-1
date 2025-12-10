/**
 * Orbital Tracker - 3D Satellite Visualization
 * Uses Three.js for rendering and satellite.js for orbital calculations
 */

const OrbitalTracker = (function() {
    // Configuration
    const EARTH_RADIUS = 1;
    const EARTH_SEGMENTS = 48;
    const ORBIT_SEGMENTS = 128;
    const SCALE_FACTOR = EARTH_RADIUS / 6371; // km to scene units
    const API_URL = '/satellite-tracking/api/orbital-tracker-satellites/';
    const EARTH_MODEL_URL = '/static/satellite_tracking/Earth_Model.glb'; // Path to the GLB file

    // Scene objects
    let scene, camera, renderer, controls;
    let earth, earthGrid, earthModel;
    let satellites = [];
    let orbitLines = [];
    let animationId = null;

    // State
    let isInitialized = false;
    let gridVisible = true;
    let selectedTarget = 'all';
    let userLocation = null;
    let isAuthenticated = false;
    let useRealisticEarth = false; // Toggle between hologram and realistic Earth
    let gltfLoader = null;
    let modelLoading = false; // Lock to prevent double loading

    // Colors for satellites (high contrast with purple/pink background)
    const SATELLITE_COLORS = [
        0x00ff00, // Bright Green
        0x00ffff, // Cyan
        0xffff00, // Yellow
        0xff6600, // Orange
        0x00ff88, // Mint Green
        0x88ffff, // Light Cyan
        0xffaa00, // Amber
        0x00ffaa, // Aquamarine
    ];

    /**
     * Initialize the 3D scene
     */
    function init() {
        console.log('Initializing orbital tracker...');
        const container = document.getElementById('orbital-viewport');

        if (!container) {
            console.error('Container element not found');
            return;
        }

        if (isInitialized) {
            console.log('Already initialized');
            return;
        }

        // Reset scene variables to ensure no ghost objects from previous page loads
        earth = null;
        earthGrid = null;
        earthModel = null;
        satellites = [];
        orbitLines = [];
        modelLoading = false;

        console.log('Container dimensions:', container.clientWidth, 'x', container.clientHeight);

        // Check authentication status from data attribute
        const trackerElement = document.getElementById('orbital-tracker');
        if (trackerElement) {
            isAuthenticated = trackerElement.dataset.authenticated === 'true';
            console.log('User authenticated:', isAuthenticated);
        }

        // Create scene
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x000000);
        console.log('Scene created');

        // Create camera
        const aspect = container.clientWidth / container.clientHeight;
        camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
        camera.position.set(0, 0, 4);
        camera.lookAt(0, 0, 0);
        console.log('Camera created');

        // Create renderer
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // Clear any existing canvas first
        while (container.firstChild && container.firstChild.tagName === 'CANVAS') {
            container.removeChild(container.firstChild);
        }

        container.appendChild(renderer.domElement);
        console.log('Renderer created and added to DOM');

        // Initialize GLTF Loader if available
        if (typeof THREE.GLTFLoader !== 'undefined') {
            gltfLoader = new THREE.GLTFLoader();
            console.log('GLTFLoader initialized from THREE.GLTFLoader');
        } else if (typeof GLTFLoader !== 'undefined') {
            gltfLoader = new GLTFLoader();
            console.log('GLTFLoader initialized from global GLTFLoader');
        } else {
            console.warn('GLTFLoader not available - realistic Earth mode disabled');
        }

        // Create Earth (hologram by default)
        createEarth();
        console.log('Earth created');

        // Create grid
        createEarthGrid();
        console.log('Grid created');

        // Add strong ambient light for overall brightness
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
        scene.add(ambientLight);

        // Add main directional light (sun) - very bright
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.5);
        directionalLight.position.set(5, 3, 5);
        scene.add(directionalLight);
        
        // Add a second directional light from the opposite side for fill
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.8);
        fillLight.position.set(-5, -3, -5);
        scene.add(fillLight);
        
        // Add a third light from above
        const topLight = new THREE.DirectionalLight(0xffffff, 0.6);
        topLight.position.set(0, 5, 0);
        scene.add(topLight);
        
        // Add hemisphere light for natural sky/ground lighting
        const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.8);
        scene.add(hemisphereLight);
        console.log('Lights added');

        // Setup mouse controls
        setupMouseControls(container);
        console.log('Mouse controls setup');

        // Setup UI controls
        setupUIControls();
        console.log('UI controls setup');

        // Handle resize
        window.addEventListener('resize', onWindowResize);

        isInitialized = true;
        console.log('Initialization complete, starting animation');

        // Start animation loop
        animate();

        // Fetch initial satellites from API
        console.log('Fetching satellites from:', API_URL);
        fetchSatellites();
    }

    /**
     * Fetch satellites from the API
     */
    function fetchSatellites() {
        console.log('fetchSatellites called');
        const loadingEl = document.getElementById('orbital-loading');
        const loadingText = loadingEl?.querySelector('.orbital-loading-text');

        if (loadingText) {
            loadingText.textContent = 'Fetching satellite data...';
        }

        fetch(API_URL)
            .then(response => response.json())
            .then(data => {
                // Hide loading, show info overlay
                if (loadingEl) loadingEl.style.display = 'none';
                document.getElementById('orbital-info-overlay').style.display = 'block';

                if (data.success && data.satellites) {
                    clearSatellites();
                    data.satellites.forEach((sat, index) => {
                        addSatellite(sat, index);
                    });
                    document.getElementById('sat-count').textContent = data.satellites.length;
                    document.getElementById('sig-status').textContent = 'OK';

                    if (data.satellites.length === 1) {
                        selectTarget(data.satellites[0].id);
                    }
                } else {
                    document.getElementById('sig-status').textContent = 'ERR';
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                if (loadingEl) loadingEl.style.display = 'none';
                document.getElementById('orbital-info-overlay').style.display = 'block';
                document.getElementById('sig-status').textContent = 'ERR';
            });
    }

    /**
     * Create wireframe Earth (hologram mode)
     */
    function createEarth() {
        // Wireframe sphere for Earth
        const geometry = new THREE.SphereGeometry(EARTH_RADIUS, EARTH_SEGMENTS, EARTH_SEGMENTS);
        const material = new THREE.MeshBasicMaterial({
            color: 0xf472b6, // Pink
            wireframe: true,
            transparent: true,
            opacity: 0.3
        });
        earth = new THREE.Mesh(geometry, material);
        earth.name = 'hologramEarth';
        scene.add(earth);

        // Add solid core for better visibility
        const coreGeometry = new THREE.SphereGeometry(EARTH_RADIUS * 0.98, 32, 32);
        const coreMaterial = new THREE.MeshBasicMaterial({
            color: 0x1a0a14, // Dark pink-tinted
            transparent: true,
            opacity: 0.9
        });
        const core = new THREE.Mesh(coreGeometry, coreMaterial);
        core.name = 'hologramCore';
        scene.add(core);
    }

    /**
     * Load the realistic Earth GLB model
     */
    function loadRealisticEarth() {
        if (!gltfLoader) {
            return Promise.reject(new Error('GLTFLoader not available'));
        }

        // 1. Return existing if loaded and force it into the current scene if missing
        if (earthModel) {
            // Check if model is actually in the current scene
            const inScene = scene.getObjectByName('realisticEarth');
            if (!inScene) {
                console.log('Model exists in memory but not scene, re-adding...');
                scene.add(earthModel);
            }
            return Promise.resolve(earthModel);
        }

        // 2. Return promise if currently loading
        if (modelLoading) {
            return new Promise((resolve) => {
                const checkLoad = setInterval(() => {
                    if (!modelLoading && earthModel) {
                        clearInterval(checkLoad);
                        resolve(earthModel);
                    }
                }, 100);
            });
        }

        modelLoading = true;

        return new Promise((resolve, reject) => {
            console.log('Loading Earth model from:', EARTH_MODEL_URL);
            
            gltfLoader.load(
                EARTH_MODEL_URL,
                (gltf) => {
                    console.log('Earth model loaded successfully');
                    
                    earthModel = gltf.scene;
                    earthModel.name = 'realisticEarth';
                    
                    // IMPORTANT: Ensure it is HIDDEN initially
                    earthModel.visible = false;
                    earthModel.traverse((child) => {
                        child.visible = false;
                    });
                    
                    // Scale and center
                    const box = new THREE.Box3().setFromObject(earthModel);
                    const size = box.getSize(new THREE.Vector3());
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const scale = (EARTH_RADIUS * 2) / maxDim;
                    
                    earthModel.position.set(0, 0, 0);
                    earthModel.rotation.set(0, 0, 0);
                    earthModel.scale.setScalar(scale);
                    
                    const newBox = new THREE.Box3().setFromObject(earthModel);
                    const newCenter = newBox.getCenter(new THREE.Vector3());
                    earthModel.position.sub(newCenter);
                    
                    // Fix materials
                    earthModel.traverse((child) => {
                        if (child.isMesh && child.material) {
                            child.material = child.material.clone();
                            child.material.side = THREE.FrontSide;
                            child.material.depthWrite = true;
                            child.material.depthTest = true;
                            child.material.transparent = false;
                            
                            if (child.material.color) child.material.color.multiplyScalar(1.5);
                            if (child.material.emissive) child.material.emissive.setHex(0x222222);
                            
                            child.material.needsUpdate = true;
                            child.frustumCulled = false;
                        }
                    });
                    
                    scene.add(earthModel);
                    modelLoading = false;
                    resolve(earthModel);
                },
                undefined,
                (error) => {
                    console.error('Error loading Earth model:', error);
                    modelLoading = false;
                    reject(error);
                }
            );
        });
    }

    /**
     * Toggle between hologram and realistic Earth
     */
    function toggleEarthMode(useRealistic, isHiddenSwitch = false) {
        console.log('=== toggleEarthMode called with:', useRealistic, '===');
        useRealisticEarth = useRealistic;
        
        // Get hologram elements
        const hologramEarth = scene.getObjectByName('hologramEarth');
        const hologramCore = scene.getObjectByName('hologramCore');
        const loadingOverlay = document.getElementById('earth-model-loading');
        
        if (useRealistic) {
            console.log('Switching to 3D mode...');
            
            // Case 1: Model is already loaded
            if (earthModel) {
                // Immediate clean switch
                if (hologramEarth) hologramEarth.visible = false;
                if (hologramCore) hologramCore.visible = false;
                if (earthGrid) earthGrid.visible = false; // Ensure grid is off!
                
                earthModel.visible = true;
                earthModel.traverse((child) => child.visible = true);
            } 
            // Case 2: Model needs to load (First Time)
            else {
                if (loadingOverlay && !isHiddenSwitch) loadingOverlay.style.display = 'flex';
                
                loadRealisticEarth()
                    .then((model) => {
                        if (!useRealisticEarth) {
                            if (loadingOverlay) loadingOverlay.style.display = 'none';
                            return;
                        }

                        // === THE PRIMING SEQUENCE ===
                        console.log('Model loaded, starting priming sequence...');

                        // Step 1: Force 3D Visible (Hidden behind loading screen)
                        if (hologramEarth) hologramEarth.visible = false;
                        if (hologramCore) hologramCore.visible = false;
                        if (earthGrid) earthGrid.visible = false; // Grid OFF
                        
                        model.visible = true;
                        model.traverse(c => c.visible = true);
                        
                        // Step 2: Switch BACK to Holo briefly
                        setTimeout(() => {
                            if (!useRealisticEarth) return; 
                            
                            // Hide 3D
                            model.visible = false;
                            model.traverse(c => c.visible = false);
                            
                            // Show Holo & Grid (if user enabled it)
                            if (hologramEarth) hologramEarth.visible = true;
                            if (hologramCore) hologramCore.visible = true;
                            if (earthGrid && gridVisible) earthGrid.visible = true;

                            // Step 3: Final Reveal of 3D Model
                            setTimeout(() => {
                                if (!useRealisticEarth) return;

                                // Hide Holo permanently
                                if (hologramEarth) hologramEarth.visible = false;
                                if (hologramCore) hologramCore.visible = false;
                                
                                // FORCE GRID OFF (This fixes the "grid on model" bug)
                                if (earthGrid) earthGrid.visible = false;
                                
                                // Show 3D permanently
                                model.visible = true;
                                model.traverse(c => c.visible = true);

                                // Remove Loading Screen
                                if (loadingOverlay) loadingOverlay.style.display = 'none';
                                console.log('Priming sequence complete, 3D model active.');
                                
                            }, 100); 
                        }, 100); 
                    })
                    .catch((err) => {
                        console.error('Load failed:', err);
                        if (loadingOverlay) loadingOverlay.style.display = 'none';
                        toggleEarthMode(false);
                    });
            }
        } else {
            console.log('Switching to HOLO mode...');
            
            // 1. Hide 3D Model
            if (earthModel) {
                earthModel.visible = false;
                earthModel.traverse((child) => child.visible = false);
            }
            
            // 2. Show Hologram
            if (hologramEarth) hologramEarth.visible = true;
            if (hologramCore) hologramCore.visible = true;
            if (earthGrid && gridVisible) earthGrid.visible = true;
        }
        
        // Update Buttons
        if (!isHiddenSwitch) {
            const holoBtn = document.getElementById('view-holo-btn');
            const threeDBtn = document.getElementById('view-3d-btn');
            
            if (holoBtn && threeDBtn) {
                if (useRealistic) {
                    holoBtn.classList.remove('active');
                    threeDBtn.classList.add('active');
                } else {
                    holoBtn.classList.add('active');
                    threeDBtn.classList.remove('active');
                }
            }
        }
    }

    /**
     * Create grid lines around Earth
     */
    function createEarthGrid() {
        earthGrid = new THREE.Group();

        // Equator
        const equatorGeometry = new THREE.BufferGeometry();
        const equatorPoints = [];
        for (let i = 0; i <= 64; i++) {
            const angle = (i / 64) * Math.PI * 2;
            equatorPoints.push(new THREE.Vector3(
                Math.cos(angle) * EARTH_RADIUS * 1.01,
                0,
                Math.sin(angle) * EARTH_RADIUS * 1.01
            ));
        }
        equatorGeometry.setFromPoints(equatorPoints);
        const equatorMaterial = new THREE.LineBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.4 });
        const equator = new THREE.Line(equatorGeometry, equatorMaterial);
        earthGrid.add(equator);

        // Latitude lines
        const latitudes = [-60, -30, 30, 60];
        latitudes.forEach(lat => {
            const latRad = (lat * Math.PI) / 180;
            const radius = Math.cos(latRad) * EARTH_RADIUS * 1.01;
            const height = Math.sin(latRad) * EARTH_RADIUS * 1.01;

            const latGeometry = new THREE.BufferGeometry();
            const latPoints = [];
            for (let i = 0; i <= 64; i++) {
                const angle = (i / 64) * Math.PI * 2;
                latPoints.push(new THREE.Vector3(
                    Math.cos(angle) * radius,
                    height,
                    Math.sin(angle) * radius
                ));
            }
            latGeometry.setFromPoints(latPoints);
            const latLine = new THREE.Line(latGeometry, new THREE.LineBasicMaterial({
                color: 0x8b5cf6,
                transparent: true,
                opacity: 0.25
            }));
            earthGrid.add(latLine);
        });

        // Longitude lines
        for (let i = 0; i < 12; i++) {
            const lonRad = (i / 12) * Math.PI * 2;
            const lonGeometry = new THREE.BufferGeometry();
            const lonPoints = [];
            for (let j = 0; j <= 64; j++) {
                const latRad = ((j / 64) * Math.PI) - Math.PI / 2;
                lonPoints.push(new THREE.Vector3(
                    Math.cos(latRad) * Math.cos(lonRad) * EARTH_RADIUS * 1.01,
                    Math.sin(latRad) * EARTH_RADIUS * 1.01,
                    Math.cos(latRad) * Math.sin(lonRad) * EARTH_RADIUS * 1.01
                ));
            }
            lonGeometry.setFromPoints(lonPoints);
            const lonLine = new THREE.Line(lonGeometry, new THREE.LineBasicMaterial({
                color: 0x8b5cf6,
                transparent: true,
                opacity: 0.25
            }));
            earthGrid.add(lonLine);
        }

        scene.add(earthGrid);
    }

    /**
     * Setup mouse drag controls for rotation
     */
    function setupMouseControls(container) {
        let isDragging = false;
        let previousMousePosition = { x: 0, y: 0 };
        let rotation = { x: 0, y: 0 };

        container.addEventListener('mousedown', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaMove = {
                x: e.clientX - previousMousePosition.x,
                y: e.clientY - previousMousePosition.y
            };

            rotation.y += deltaMove.x * 0.005;
            rotation.x += deltaMove.y * 0.005;

            // Clamp vertical rotation
            rotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotation.x));

            // Update camera position
            const distance = camera.position.length();
            camera.position.x = distance * Math.sin(rotation.y) * Math.cos(rotation.x);
            camera.position.y = distance * Math.sin(rotation.x);
            camera.position.z = distance * Math.cos(rotation.y) * Math.cos(rotation.x);
            camera.lookAt(0, 0, 0);

            previousMousePosition = { x: e.clientX, y: e.clientY };
        });

        container.addEventListener('mouseup', () => {
            isDragging = false;
        });

        container.addEventListener('mouseleave', () => {
            isDragging = false;
        });

        // Touch support
        container.addEventListener('touchstart', (e) => {
            isDragging = true;
            previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        });

        container.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            e.preventDefault();

            const deltaMove = {
                x: e.touches[0].clientX - previousMousePosition.x,
                y: e.touches[0].clientY - previousMousePosition.y
            };

            rotation.y += deltaMove.x * 0.005;
            rotation.x += deltaMove.y * 0.005;
            rotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotation.x));

            const distance = camera.position.length();
            camera.position.x = distance * Math.sin(rotation.y) * Math.cos(rotation.x);
            camera.position.y = distance * Math.sin(rotation.x);
            camera.position.z = distance * Math.cos(rotation.y) * Math.cos(rotation.x);
            camera.lookAt(0, 0, 0);

            previousMousePosition = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        });

        container.addEventListener('touchend', () => {
            isDragging = false;
        });

        // Mouse wheel zoom
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomSpeed = 0.1;
            const distance = camera.position.length();
            const newDistance = distance + (e.deltaY > 0 ? zoomSpeed : -zoomSpeed);
            const clampedDistance = Math.max(1.5, Math.min(10, newDistance));
            camera.position.normalize().multiplyScalar(clampedDistance);
        });
    }

    /**
     * Setup UI control buttons
     */
    function setupUIControls() {
        // Zoom in
        document.getElementById('cam-zoom-in')?.addEventListener('click', () => {
            const distance = Math.max(1.5, camera.position.length() - 0.5);
            camera.position.normalize().multiplyScalar(distance);
        });

        // Zoom out
        document.getElementById('cam-zoom-out')?.addEventListener('click', () => {
            const distance = Math.min(10, camera.position.length() + 0.5);
            camera.position.normalize().multiplyScalar(distance);
        });

        // Reset camera
        document.getElementById('cam-reset')?.addEventListener('click', () => {
            camera.position.set(0, 0, 4);
            camera.lookAt(0, 0, 0);
        });

        // ALL target button
        document.getElementById('tgt-all')?.addEventListener('click', () => {
            selectTarget('all');
        });

        // HOLO button - switch to hologram view
        const holoBtn = document.getElementById('view-holo-btn');
        if (holoBtn) {
            holoBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleEarthMode(false);
            });
        }

        // 3D button - switch to 3D Earth model
        const threeDBtn = document.getElementById('view-3d-btn');
        if (threeDBtn) {
            threeDBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleEarthMode(true);
            });
        }
    }

    /**
     * Convert lat/lon/alt to 3D position
     */
    function latLonAltToVector3(lat, lon, alt) {
        const latRad = (lat * Math.PI) / 180;
        const lonRad = (-lon * Math.PI) / 180; // Negate for correct orientation
        const radius = EARTH_RADIUS + (alt * SCALE_FACTOR);

        return new THREE.Vector3(
            radius * Math.cos(latRad) * Math.sin(lonRad),
            radius * Math.sin(latRad),
            radius * Math.cos(latRad) * Math.cos(lonRad)
        );
    }

    /**
     * Add a satellite to the scene
     */
    function addSatellite(satData, colorIndex) {
        const color = SATELLITE_COLORS[colorIndex % SATELLITE_COLORS.length];

        // Create satellite dot
        const geometry = new THREE.SphereGeometry(0.03, 16, 16);
        const material = new THREE.MeshBasicMaterial({ color: color });
        const satellite = new THREE.Mesh(geometry, material);

        // Create orbit path first to get the orbit points
        const orbitData = createOrbitPath(satData, color);

        // Find the closest point on the orbit to the satellite's current position
        const currentPos = latLonAltToVector3(satData.latitude, satData.longitude, satData.altitude);
        let closestIndex = 0;
        let minDistance = Infinity;

        orbitData.points.forEach((point, index) => {
            const dist = currentPos.distanceTo(point);
            if (dist < minDistance) {
                minDistance = dist;
                closestIndex = index;
            }
        });

        // Position satellite on the orbit path
        satellite.position.copy(orbitData.points[closestIndex]);

        // Calculate speed
        const baseSpeed = ORBIT_SEGMENTS / 5400;

        // Store satellite data including orbit information
        satellite.userData = {
            id: satData.id,
            name: satData.name,
            latitude: satData.latitude,
            longitude: satData.longitude,
            altitude: satData.altitude,
            color: color,
            orbitPoints: orbitData.points,
            orbitIndex: closestIndex,
            orbitSpeed: baseSpeed + (colorIndex * baseSpeed * 0.05)
        };

        scene.add(satellite);
        satellites.push(satellite);

        // Add target button
        addTargetButton(satData, colorIndex);

        return satellite;
    }

    /**
     * Create an orbital path for a satellite
     * Returns both the orbit line and the array of points
     */
    function createOrbitPath(satData, color) {
        const points = [];
        const altitude = satData.altitude;
        const radius = EARTH_RADIUS + (altitude * SCALE_FACTOR);

        // Estimate inclination from current latitude (simplified)
        const inclination = Math.abs(satData.latitude) * 1.2; // Rough estimate
        const inclinationRad = (Math.min(inclination, 90) * Math.PI) / 180;

        // Create orbit ellipse
        for (let i = 0; i <= ORBIT_SEGMENTS; i++) {
            const angle = (i / ORBIT_SEGMENTS) * Math.PI * 2;

            // Rotate the orbit based on inclination
            const x = radius * Math.cos(angle);
            const y = radius * Math.sin(angle) * Math.sin(inclinationRad);
            const z = radius * Math.sin(angle) * Math.cos(inclinationRad);

            // Rotate to align with satellite's longitude
            const lonRad = (-satData.longitude * Math.PI) / 180;
            const rotatedX = x * Math.cos(lonRad) - z * Math.sin(lonRad);
            const rotatedZ = x * Math.sin(lonRad) + z * Math.cos(lonRad);

            points.push(new THREE.Vector3(rotatedX, y, rotatedZ));
        }

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({
            color: color,
            transparent: true,
            opacity: 0.6
        });
        const orbit = new THREE.Line(geometry, material);
        orbit.userData = { satelliteId: satData.id };

        scene.add(orbit);
        orbitLines.push(orbit);

        return {
            orbit: orbit,
            points: points
        };
    }

    /**
     * Add a target button for a satellite
     */
    function addTargetButton(satData, colorIndex) {
        const targetButtons = document.getElementById('target-buttons');
        if (!targetButtons) return;

        // Check if button already exists
        if (document.getElementById(`tgt-${satData.id}`)) return;

        const color = SATELLITE_COLORS[colorIndex % SATELLITE_COLORS.length];
        const btn = document.createElement('button');
        btn.className = 'control-btn orange';
        btn.id = `tgt-${satData.id}`;
        btn.dataset.target = satData.id;
        btn.textContent = satData.name.substring(0, 6).toUpperCase();
        btn.style.borderColor = `#${color.toString(16).padStart(6, '0')}`;
        btn.style.color = `#${color.toString(16).padStart(6, '0')}`;

        // Store satellite data on button for tooltip
        btn.dataset.satName = satData.name;
        btn.dataset.satId = satData.id;
        btn.dataset.satAltitude = satData.altitude;
        btn.dataset.satLatitude = satData.latitude;
        btn.dataset.satLongitude = satData.longitude;

        btn.addEventListener('click', () => selectTarget(satData.id));

        // Add hover event listeners for tooltip
        btn.addEventListener('mouseenter', showSatelliteTooltip);
        btn.addEventListener('mouseleave', hideSatelliteTooltip);
        btn.addEventListener('mousemove', updateTooltipPosition);

        targetButtons.appendChild(btn);
    }

    /**
     * Show satellite tooltip on hover
     */
    function showSatelliteTooltip(event) {
        const btn = event.currentTarget;
        const tooltip = document.getElementById('satellite-tooltip');
        if (!tooltip) return;

        // Update tooltip content
        document.getElementById('tooltip-name').textContent = btn.dataset.satName;
        document.getElementById('tooltip-id').textContent = btn.dataset.satId;
        document.getElementById('tooltip-altitude').textContent = `${parseFloat(btn.dataset.satAltitude).toFixed(2)} km`;
        document.getElementById('tooltip-lat').textContent = `${parseFloat(btn.dataset.satLatitude).toFixed(4)}°`;
        document.getElementById('tooltip-lon').textContent = `${parseFloat(btn.dataset.satLongitude).toFixed(4)}°`;

        // Position and show tooltip
        updateTooltipPosition(event);
        tooltip.classList.add('show');
    }

    /**
     * Hide satellite tooltip
     */
    function hideSatelliteTooltip() {
        const tooltip = document.getElementById('satellite-tooltip');
        if (tooltip) {
            tooltip.classList.remove('show');
        }
    }

    /**
     * Update tooltip position to follow mouse
     */
    function updateTooltipPosition(event) {
        const tooltip = document.getElementById('satellite-tooltip');
        if (!tooltip || !tooltip.classList.contains('show')) return;

        const tracker = document.getElementById('orbital-tracker');
        const trackerRect = tracker.getBoundingClientRect();

        // Position relative to the tracker container
        const x = event.clientX - trackerRect.left + 15;
        const y = event.clientY - trackerRect.top + 15;

        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y}px`;
    }

    /**
     * Select a target satellite
     */
    function selectTarget(targetId) {
        selectedTarget = targetId;

        // Update button states
        document.querySelectorAll('#target-buttons .control-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.target === targetId.toString() ||
                (targetId === 'all' && btn.id === 'tgt-all'));
        });

        // Update visibility
        satellites.forEach(sat => {
            const isVisible = targetId === 'all' || sat.userData.id === targetId;
            sat.visible = isVisible;
        });

        orbitLines.forEach(orbit => {
            const isVisible = targetId === 'all' || orbit.userData.satelliteId === targetId;
            orbit.visible = isVisible;
        });

        // Update info display
        if (targetId === 'all') {
            document.getElementById('orbital-target-display').textContent = 'TGT: ALL';
            document.getElementById('orbital-lat-display').textContent = 'LAT: --';
            document.getElementById('orbital-lon-display').textContent = 'LON: --';
            document.getElementById('orbital-alt-display').textContent = 'ALT: --';
        } else {
            const sat = satellites.find(s => s.userData.id === targetId);
            if (sat) {
                document.getElementById('orbital-target-display').textContent = `TGT: ${sat.userData.name.substring(0, 8)}`;
                document.getElementById('orbital-lat-display').textContent = `LAT: ${sat.userData.latitude.toFixed(2)}`;
                document.getElementById('orbital-lon-display').textContent = `LON: ${sat.userData.longitude.toFixed(2)}`;
                document.getElementById('orbital-alt-display').textContent = `ALT: ${sat.userData.altitude.toFixed(1)}`;
            }
        }
    }

    /**
     * Clear all satellites from the scene
     */
    function clearSatellites() {
        satellites.forEach(sat => scene.remove(sat));
        satellites = [];

        orbitLines.forEach(orbit => scene.remove(orbit));
        orbitLines = [];

        // Clear target buttons except ALL
        const targetButtons = document.getElementById('target-buttons');
        if (targetButtons) {
            const allBtn = document.getElementById('tgt-all');
            targetButtons.innerHTML = '';
            if (allBtn) targetButtons.appendChild(allBtn);
        }
    }

    /**
     * Add user location marker
     */
    function addUserLocation(lat, lon) {
        userLocation = { lat, lon };

        // Remove existing user marker and connection line
        const existingMarker = scene.getObjectByName('userMarker');
        if (existingMarker) scene.remove(existingMarker);

        const existingRing = scene.getObjectByName('userRing');
        if (existingRing) scene.remove(existingRing);

        const existingLine = scene.getObjectByName('userSatelliteLine');
        if (existingLine) scene.remove(existingLine);

        // Create user location marker
        const position = latLonAltToVector3(lat, lon, 50); // Slightly above surface
        const geometry = new THREE.SphereGeometry(0.025, 16, 16);
        const material = new THREE.MeshBasicMaterial({
            color: 0xff0000,
            transparent: true,
            opacity: 1
        });
        const marker = new THREE.Mesh(geometry, material);
        marker.position.copy(position);
        marker.name = 'userMarker';
        scene.add(marker);

        // Add pulsing ring
        const ringGeometry = new THREE.RingGeometry(0.035, 0.045, 32);
        const ringMaterial = new THREE.MeshBasicMaterial({
            color: 0xff0000,
            transparent: true,
            opacity: 0.7,
            side: THREE.DoubleSide
        });
        const ring = new THREE.Mesh(ringGeometry, ringMaterial);
        ring.position.copy(position);
        ring.lookAt(0, 0, 0);
        ring.name = 'userRing';
        scene.add(ring);

        // Store user position for line connection
        marker.userData.position = position;
    }

    /**
     * Add a connection line from user location to satellite
     */
    function addUserToSatelliteLine(satelliteId) {
        // Remove existing line
        const existingLine = scene.getObjectByName('userSatelliteLine');
        if (existingLine) scene.remove(existingLine);

        // Find the user marker
        const userMarker = scene.getObjectByName('userMarker');
        if (!userMarker) return;

        // Find the satellite
        const satellite = satellites.find(sat => sat.userData.id === satelliteId);
        if (!satellite) return;

        // Create a line from user to satellite
        const points = [
            userMarker.position.clone(),
            satellite.position.clone()
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineDashedMaterial({
            color: 0xff0000,
            dashSize: 0.05,
            gapSize: 0.03,
            transparent: true,
            opacity: 0.6,
            linewidth: 2
        });

        const line = new THREE.Line(geometry, material);
        line.computeLineDistances(); // Required for dashed lines
        line.name = 'userSatelliteLine';
        line.userData.satelliteId = satelliteId;
        scene.add(line);
    }

    /**
     * Update the user-to-satellite connection line
     */
    function updateUserToSatelliteLine() {
        const line = scene.getObjectByName('userSatelliteLine');
        if (!line) return;

        const userMarker = scene.getObjectByName('userMarker');
        if (!userMarker) return;

        const satellite = satellites.find(sat => sat.userData.id === line.userData.satelliteId);
        if (!satellite) return;

        // Update line positions
        const positions = line.geometry.attributes.position.array;
        positions[0] = userMarker.position.x;
        positions[1] = userMarker.position.y;
        positions[2] = userMarker.position.z;
        positions[3] = satellite.position.x;
        positions[4] = satellite.position.y;
        positions[5] = satellite.position.z;

        line.geometry.attributes.position.needsUpdate = true;
        line.computeLineDistances(); // Update for dashed line animation
    }

    /**
     * Animation loop
     */
    function animate() {
        animationId = requestAnimationFrame(animate);

        // Slow rotation of Earth (hologram)
        const hologramEarth = scene.getObjectByName('hologramEarth');
        const hologramCore = scene.getObjectByName('hologramCore');
        
        if (hologramEarth && hologramEarth.visible) {
            hologramEarth.rotation.y += 0.0005;
        }
        if (hologramCore && hologramCore.visible) {
            hologramCore.rotation.y += 0.0005;
        }
        if (earthGrid && earthGrid.visible) {
            earthGrid.rotation.y += 0.0005;
        }
        
        // Rotate realistic Earth model
        if (earthModel && earthModel.visible) {
            earthModel.rotation.y += 0.0005;
        }

        // Update satellites positions (follow orbit paths)
        satellites.forEach((sat) => {
            if (!sat.userData.orbitPoints || sat.userData.orbitPoints.length === 0) return;

            // Move to next point on orbit path
            sat.userData.orbitIndex += sat.userData.orbitSpeed;

            // Wrap around when reaching the end
            if (sat.userData.orbitIndex >= sat.userData.orbitPoints.length) {
                sat.userData.orbitIndex = 0;
            }

            // Get current and next point for smooth interpolation
            const currentIdx = Math.floor(sat.userData.orbitIndex);
            const nextIdx = (currentIdx + 1) % sat.userData.orbitPoints.length;
            const t = sat.userData.orbitIndex - currentIdx; // fractional part

            const currentPoint = sat.userData.orbitPoints[currentIdx];
            const nextPoint = sat.userData.orbitPoints[nextIdx];

            // Interpolate position for smooth movement
            sat.position.lerpVectors(currentPoint, nextPoint, t);

            // Update stored lat/lon data based on new position
            const radius = sat.position.length();
            const newLat = Math.asin(sat.position.y / radius) * (180 / Math.PI);
            const newLon = -Math.atan2(sat.position.x, sat.position.z) * (180 / Math.PI);
            sat.userData.latitude = newLat;
            sat.userData.longitude = newLon;

            // Update button tooltip data if it exists
            const btn = document.getElementById(`tgt-${sat.userData.id}`);
            if (btn) {
                btn.dataset.satLatitude = newLat;
                btn.dataset.satLongitude = newLon;
            }
        });

        // Update user ring pulse
        const userRing = scene.getObjectByName('userRing');
        if (userRing) {
            const scale = 1 + Math.sin(Date.now() * 0.003) * 0.2;
            userRing.scale.set(scale, scale, scale);
        }

        // Update connection line between user and satellite
        updateUserToSatelliteLine();

        renderer.render(scene, camera);
    }

    /**
     * Handle window resize
     */
    function onWindowResize() {
        const container = document.getElementById('orbital-viewport');
        if (!container || !camera || !renderer) return;

        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }

    /**
     * Show the orbital tracker
     */
    function show() {
        const tracker = document.getElementById('orbital-tracker');
        if (tracker) {
            tracker.style.display = 'block';
            if (!isInitialized) {
                setTimeout(init, 100); // Small delay to ensure container is visible
            }
        }
    }

    /**
     * Hide the orbital tracker
     */
    function hide() {
        const tracker = document.getElementById('orbital-tracker');
        if (tracker) {
            tracker.style.display = 'none';
        }
    }

    /**
     * Update with satellite data from the closest satellite API
     * This adds the found satellite to the existing display
     */
    function updateWithSatelliteData(data) {
        if (!isInitialized) {
            // Wait for initialization
            setTimeout(() => updateWithSatelliteData(data), 200);
            return;
        }

        // Check if this satellite already exists
        const existingSat = satellites.find(s => s.userData.id === data.satellite?.id);

        // Add the closest satellite if it doesn't already exist
        if (data.satellite && !existingSat) {
            addSatellite({
                id: data.satellite.id,
                name: data.satellite.name,
                latitude: data.satellite.latitude,
                longitude: data.satellite.longitude,
                altitude: data.satellite.altitude
            }, satellites.length);

            // Update satellite count
            document.getElementById('sat-count').textContent = satellites.length;
        }

        // Add user location if available
        if (data.location) {
            addUserLocation(data.location.latitude, data.location.longitude);
        }

        // Select the found satellite and add connection line
        if (data.satellite) {
            selectTarget(data.satellite.id);
            // Add connection line from user to this closest satellite
            addUserToSatelliteLine(data.satellite.id);
        }
    }

    /**
     * Set the path to the Earth model (for custom paths)
     */
    function setEarthModelPath(path) {
        // Update the constant (we use a closure variable to allow changes)
        Object.defineProperty(this, 'EARTH_MODEL_URL', { value: path, writable: true });
    }

    /**
     * Preload the Earth model
     */
    function preloadEarthModel() {
        if (!earthModel && gltfLoader) {
            return loadRealisticEarth();
        }
        return Promise.resolve(earthModel);
    }

    /**
     * Destroy the tracker
     */
    function destroy() {
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        if (renderer) {
            const container = document.getElementById('orbital-viewport');
            if (container && renderer.domElement) {
                container.removeChild(renderer.domElement);
            }
            renderer.dispose();
        }
        window.removeEventListener('resize', onWindowResize);
        
        // Clean up references
        earth = null;
        earthGrid = null;
        earthModel = null;
        satellites = [];
        orbitLines = [];
        
        isInitialized = false;
    }

    // Public API
    return {
        init,
        show,
        hide,
        updateWithSatelliteData,
        addSatellite,
        clearSatellites,
        addUserLocation,
        selectTarget,
        destroy,
        fetchSatellites,
        isInitialized: () => isInitialized,
        // New Earth model methods
        toggleEarthMode,
        loadRealisticEarth,
        preloadEarthModel,
        isRealisticMode: () => useRealisticEarth,
        // Grid toggle
        toggleGrid: function() {
            gridVisible = !gridVisible;
            if (earthGrid && !useRealisticEarth) {
                earthGrid.visible = gridVisible;
            }
            const gridBtn = document.getElementById('grid-toggle');
            if (gridBtn) {
                gridBtn.classList.toggle('active', gridVisible);
            }
            console.log('Grid visibility toggled to:', gridVisible);
            return gridVisible;
        },
        isGridVisible: () => gridVisible
    };
})();

// Make it globally available
window.OrbitalTracker = OrbitalTracker;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const trackerElement = document.getElementById('orbital-tracker');
    if (trackerElement) {
        // Check if Three.js is loaded
        if (typeof THREE === 'undefined') {
            console.error('Three.js not loaded');
            const loadingEl = document.getElementById('orbital-loading');
            if (loadingEl) {
                const loadingText = loadingEl.querySelector('.orbital-loading-text');
                if (loadingText) {
                    loadingText.textContent = 'Error: Three.js not loaded';
                }
            }
            return;
        }

        // Add a small delay to ensure everything is fully loaded and rendered
        setTimeout(() => {
            try {
                OrbitalTracker.init();
            } catch (error) {
                console.error('Error initializing orbital tracker:', error);
                const loadingEl = document.getElementById('orbital-loading');
                if (loadingEl) {
                    const loadingText = loadingEl.querySelector('.orbital-loading-text');
                    if (loadingText) {
                        loadingText.textContent = 'Initialization error';
                    }
                }
            }
        }, 100);
    }
});