// Orbital Tracking 3D Visualization
(function() {
  'use strict';

  const ISS_SATID = '25544';
  let scene, camera, renderer, controls;
  let earth, grid;
  let satellites = new Map(); // Map of satid -> {mesh, orbit, visible, data}
  let animationId;
  let currentClosestSat = null;
  let colorIndex = 0;

  // Color palette for satellites
  const satelliteColors = [
    '#00ff00', // Green
    '#00ffff', // Cyan
    '#ff00ff', // Magenta
    '#ffff00', // Yellow
    '#ff9900', // Orange
    '#0099ff', // Blue
    '#ff0099', // Pink
    '#99ff00', // Lime
    '#9900ff', // Purple
    '#00ff99', // Turquoise
  ];

  // Get next unique color
  function getNextColor() {
    const color = satelliteColors[colorIndex % satelliteColors.length];
    colorIndex++;
    return color;
  }

  // Initialize Three.js scene
  function initScene() {
    console.log('Initializing orbital tracking scene...');

    // Check if Three.js is loaded
    if (typeof THREE === 'undefined') {
      console.error('Three.js is not loaded!');
      return;
    }
    console.log('Three.js loaded successfully');

    const container = document.getElementById('orbital-canvas');
    if (!container) {
      console.error('Canvas element not found!');
      return;
    }
    console.log('Canvas element found:', container);

    // Get parent dimensions for proper sizing
    const parent = container.parentElement;
    const width = parent.clientWidth || 800;
    const height = parent.clientHeight || 600;

    console.log('Canvas dimensions:', width, 'x', height);

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    // Camera
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000);
    camera.position.set(0, 0, 800);
    camera.lookAt(0, 0, 0);

    // Renderer
    renderer = new THREE.WebGLRenderer({ canvas: container, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040, 2);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 1);
    pointLight.position.set(500, 500, 500);
    scene.add(pointLight);

    // Create Earth
    createEarth();

    // Create grid
    createGrid();

    // Mouse controls
    setupMouseControls();

    // Window resize
    window.addEventListener('resize', onWindowResize);

    // Start animation loop
    animate();

    console.log('Scene initialized successfully');
    console.log('Camera position:', camera.position);
    console.log('Scene children:', scene.children.length);

    // Load ISS by default
    console.log('Loading ISS satellite...');
    loadSatellite(ISS_SATID, 'ISS', getNextColor());

    // For logged-in users with saved satellites
    if (window.isAuthenticated && window.savedSatellites) {
      window.savedSatellites.forEach(sat => {
        if (sat.satellite_id && sat.satellite_id !== ISS_SATID) {
          loadSatellite(sat.satellite_id, sat.name, getNextColor());
        }
      });
    }
  }

  // Create Earth sphere
  function createEarth() {
    console.log('Creating Earth sphere...');
    const geometry = new THREE.SphereGeometry(100, 32, 32);
    const material = new THREE.MeshPhongMaterial({
      color: 0x003300,
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    });
    earth = new THREE.Mesh(geometry, material);
    scene.add(earth);

    // Add glowing edge
    const edgeGeometry = new THREE.SphereGeometry(101, 32, 32);
    const edgeMaterial = new THREE.MeshBasicMaterial({
      color: 0x00ff00,
      wireframe: true,
      transparent: true,
      opacity: 0.3,
    });
    const edgeMesh = new THREE.Mesh(edgeGeometry, edgeMaterial);
    earth.add(edgeMesh);
    console.log('Earth sphere created');
  }

  // Create spherical grid (latitude/longitude lines)
  function createGrid() {
    console.log('Creating spherical grid...');
    grid = new THREE.Group();

    // Latitude lines (horizontal circles)
    const latitudes = 18; // Every 10 degrees
    for (let i = 0; i <= latitudes; i++) {
      const lat = (i / latitudes) * Math.PI; // 0 to PI
      const radius = 100 * Math.sin(lat);
      const y = 100 * Math.cos(lat);

      if (i > 0 && i < latitudes) { // Skip poles
        const geometry = new THREE.CircleGeometry(radius, 64);
        const edges = new THREE.EdgesGeometry(geometry);
        const line = new THREE.LineSegments(
          edges,
          new THREE.LineBasicMaterial({ color: 0x00ff00, transparent: true, opacity: 0.3 })
        );
        line.rotation.x = Math.PI / 2;
        line.position.y = y;
        grid.add(line);
      }
    }

    // Longitude lines (vertical semicircles)
    const longitudes = 24; // Every 15 degrees
    for (let i = 0; i < longitudes; i++) {
      const curve = new THREE.EllipseCurve(
        0, 0,
        100, 100,
        0, Math.PI, // Half circle
        false,
        0
      );
      const points = curve.getPoints(50);
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(
        geometry,
        new THREE.LineBasicMaterial({ color: 0x00ff00, transparent: true, opacity: 0.3 })
      );
      line.rotation.y = (i / longitudes) * Math.PI * 2;
      line.rotation.x = Math.PI / 2;
      grid.add(line);
    }

    scene.add(grid);
    console.log('Spherical grid created with', grid.children.length, 'lines');
  }

  // Setup mouse controls for rotation
  function setupMouseControls() {
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let mouseDownPosition = { x: 0, y: 0 };
    const canvas = renderer.domElement;

    canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
      mouseDownPosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      earth.rotation.y += deltaX * 0.01;
      earth.rotation.x += deltaY * 0.01;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('mouseup', (e) => {
      // Check if it was a click (not a drag)
      const deltaX = Math.abs(e.clientX - mouseDownPosition.x);
      const deltaY = Math.abs(e.clientY - mouseDownPosition.y);

      if (deltaX < 5 && deltaY < 5) {
        // It's a click, check for satellite intersection
        handleSatelliteClick(e);
      }

      isDragging = false;
    });

    canvas.addEventListener('mouseleave', () => {
      isDragging = false;
    });

    // Mouse wheel zoom
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY * 0.1;
      camera.position.z = Math.max(200, Math.min(1500, camera.position.z + delta));
    });
  }

  // Handle satellite click with raycasting
  function handleSatelliteClick(event) {
    const canvas = renderer.domElement;
    const rect = canvas.getBoundingClientRect();

    // Calculate mouse position in normalized device coordinates (-1 to +1)
    const mouse = new THREE.Vector2();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    // Create raycaster
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);

    // Get all satellite meshes
    const satelliteMeshes = [];
    for (const [, sat] of satellites.entries()) {
      if (sat.visible && sat.mesh) {
        satelliteMeshes.push(sat.mesh);
      }
    }

    // Check for intersections
    const intersects = raycaster.intersectObjects(satelliteMeshes, true);

    if (intersects.length > 0) {
      // Find the parent satellite mesh (not the glow mesh)
      let clickedMesh = intersects[0].object;
      while (clickedMesh.parent && !clickedMesh.userData.satelliteId) {
        clickedMesh = clickedMesh.parent;
      }

      if (clickedMesh.userData && clickedMesh.userData.satelliteId) {
        const satData = clickedMesh.userData;
        console.log('Clicked satellite:', satData.satelliteName, satData.satelliteId);

        // Update info panel with clicked satellite data
        updateInfoPanel(satData.satelliteId, satData.satelliteData);

        // Dispatch event to update the satellite info card
        window.dispatchEvent(new CustomEvent('satelliteClicked', {
          detail: {
            id: satData.satelliteId,
            name: satData.satelliteName,
            data: satData.satelliteData
          }
        }));
      }
    }
  }

  // Window resize handler
  function onWindowResize() {
    const container = document.getElementById('orbital-canvas');
    if (!container || !camera || !renderer) return;

    const parent = container.parentElement;
    const width = parent.clientWidth || 800;
    const height = parent.clientHeight || 600;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    console.log('Canvas resized to:', width, 'x', height);
  }

  // Animation loop
  function animate() {
    animationId = requestAnimationFrame(animate);

    // Slowly rotate Earth
    earth.rotation.y += 0.001;

    // Update satellites
    updateSatellitePositions();

    renderer.render(scene, camera);
  }

  // Load satellite data
  async function loadSatellite(satId, name, color = '#00ff00') {
    console.log(`Loading satellite ${name} (ID: ${satId}) with color ${color}`);
    try {
      const response = await fetch(`/satellite-tracking/api/get-satellite-position/?satellite_id=${satId}`);
      const data = await response.json();

      console.log(`Satellite ${name} data:`, data);

      if (data.success && data.satellite) {
        createSatellite(satId, name, data.satellite, color);
        updateInfoPanel(satId, data.satellite);
        console.log(`Satellite ${name} created successfully`);
      } else {
        console.warn(`Failed to load satellite ${name}:`, data);
      }
    } catch (error) {
      console.error(`Error loading satellite ${satId}:`, error);
    }
  }

  // Create satellite mesh and orbit
  function createSatellite(satId, name, data, color, isClosest = false) {
    // Remove existing satellite if present
    if (satellites.has(satId)) {
      const existing = satellites.get(satId);
      scene.remove(existing.mesh);
      if (existing.orbit) scene.remove(existing.orbit);
    }

    // Satellite marker (larger and glowing)
    const geometry = new THREE.SphereGeometry(5, 16, 16);
    const material = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.9
    });
    const satelliteMesh = new THREE.Mesh(geometry, material);

    // Store satellite ID and data for click interaction
    satelliteMesh.userData = {
      satelliteId: satId,
      satelliteName: name,
      satelliteData: data,
      isClosest: isClosest
    };

    // Add glow effect
    const glowGeometry = new THREE.SphereGeometry(7, 16, 16);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.3
    });
    const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial);
    satelliteMesh.add(glowMesh);

    // Position satellite based on lat/lon/alt
    if (data.latitude !== undefined && data.longitude !== undefined && data.altitude !== undefined) {
      const position = latLonAltToVector3(data.latitude, data.longitude, data.altitude);
      satelliteMesh.position.copy(position);
    }

    // Create orbital path with realistic inclination
    // Use a varied inclination based on satellite altitude for visual variety
    const inclination = 30 + (Math.abs(parseFloat(satId)) % 60); // 30-90 degrees
    const orbitPath = createOrbitPath(data.altitude || 400, color, inclination);

    // Rotate orbit randomly around Y axis for visual variety
    orbitPath.rotation.y = (Math.abs(parseFloat(satId)) % 360) * (Math.PI / 180);

    scene.add(satelliteMesh);
    scene.add(orbitPath);

    satellites.set(satId, {
      mesh: satelliteMesh,
      orbit: orbitPath,
      visible: true,
      data: data,
      name: name,
      color: color,
      isClosest: isClosest
    });
  }

  // Create orbital path wrapped around Earth sphere
  function createOrbitPath(altitude, color, inclination = 51.6) {
    const radius = 100 + (altitude / 50); // Scale altitude to scene

    // Create orbital path as a 3D curve around the sphere
    const segments = 128;
    const points = [];

    for (let i = 0; i <= segments; i++) {
      const angle = (i / segments) * Math.PI * 2;

      // Position on orbital plane
      const x = radius * Math.cos(angle);
      const y = radius * Math.sin(angle);
      const z = 0;

      // Apply inclination rotation
      const incRad = inclination * (Math.PI / 180);
      const rotatedX = x;
      const rotatedY = y * Math.cos(incRad) - z * Math.sin(incRad);
      const rotatedZ = y * Math.sin(incRad) + z * Math.cos(incRad);

      points.push(new THREE.Vector3(rotatedX, rotatedY, rotatedZ));
    }

    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.6,
      linewidth: 2
    });

    const orbit = new THREE.Line(geometry, material);
    return orbit;
  }

  // Convert lat/lon/alt to 3D position
  function latLonAltToVector3(lat, lon, alt) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const radius = 100 + (alt / 50); // Scale altitude

    const x = -radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x, y, z);
  }

  // Update satellite positions
  async function updateSatellitePositions() {
    // Update every 5 seconds
    if (!window.lastSatelliteUpdate || Date.now() - window.lastSatelliteUpdate > 5000) {
      window.lastSatelliteUpdate = Date.now();

      for (const [satId, sat] of satellites.entries()) {
        if (sat.visible) {
          try {
            const response = await fetch(`/satellite-tracking/api/get-satellite-position/?satellite_id=${satId}`);
            const data = await response.json();

            if (data.success && data.satellite) {
              const position = latLonAltToVector3(
                data.satellite.latitude,
                data.satellite.longitude,
                data.satellite.altitude
              );
              sat.mesh.position.copy(position);
              sat.data = data.satellite;
            }
          } catch (error) {
            console.error(`Error updating satellite ${satId}:`, error);
          }
        }
      }
    }
  }

  // Update info panel
  function updateInfoPanel(satId, data) {
    const sat = satellites.get(satId);
    if (!sat) return;

    document.getElementById('current-target').textContent = sat.name;
    document.getElementById('target-lat').textContent = data.latitude ? data.latitude.toFixed(2) : '--';
    document.getElementById('target-lon').textContent = data.longitude ? data.longitude.toFixed(2) : '--';
    document.getElementById('target-alt').textContent = data.altitude ? data.altitude.toFixed(1) : '--';
  }

  // Camera controls
  document.getElementById('cam-zoom-in')?.addEventListener('click', () => {
    camera.position.z = Math.max(200, camera.position.z - 50);
  });

  document.getElementById('cam-zoom-out')?.addEventListener('click', () => {
    camera.position.z = Math.min(1500, camera.position.z + 50);
  });

  document.getElementById('cam-reset')?.addEventListener('click', () => {
    camera.position.set(0, 0, 800);
    camera.lookAt(0, 0, 0);
    earth.rotation.set(0, 0, 0);
  });

  // Grid toggle
  document.getElementById('grid-toggle')?.addEventListener('click', function() {
    grid.visible = !grid.visible;
    this.classList.toggle('active');
    this.textContent = grid.visible ? 'GRID ON' : 'GRID OFF';
  });

  // Target satellite buttons
  document.querySelectorAll('.tgt-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const target = this.dataset.target;
      const satId = this.dataset.satid;

      // Remove active class from all buttons
      document.querySelectorAll('.tgt-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      if (target === 'ALL') {
        // Show all satellites
        for (const [, sat] of satellites.entries()) {
          sat.mesh.visible = true;
          sat.orbit.visible = true;
          sat.visible = true;
        }
        // Update info panel with ISS
        const iss = satellites.get(ISS_SATID);
        if (iss) updateInfoPanel(ISS_SATID, iss.data);
      } else {
        // Show only selected satellite
        for (const [satIdKey, sat] of satellites.entries()) {
          const shouldShow = satIdKey === satId;
          sat.mesh.visible = shouldShow;
          sat.orbit.visible = shouldShow;
          sat.visible = shouldShow;
        }
        // Update info panel
        if (satId && satId !== 'closest') {
          const sat = satellites.get(satId);
          if (sat) updateInfoPanel(satId, sat.data);
        }
      }
    });
  });

  // Hook into closest satellite finder to show all satellites
  window.addEventListener('satellitesFound', (e) => {
    console.log('satellitesFound event received:', e.detail);

    const receivedSatellites = e.detail.satellites;

    if (!receivedSatellites || !Array.isArray(receivedSatellites)) {
      console.error('Invalid satellites data received:', receivedSatellites);
      return;
    }

    console.log('Received satellites array:', receivedSatellites);
    console.log('Number of satellites:', receivedSatellites.length);

    // Clear existing closest satellites (but keep ISS and saved ones)
    const toRemove = [];
    for (const [satId, sat] of satellites.entries()) {
      if (sat.isClosest) {
        toRemove.push(satId);
      }
    }
    toRemove.forEach(satId => {
      const sat = satellites.get(satId);
      if (sat) {
        scene.remove(sat.mesh);
        if (sat.orbit) scene.remove(sat.orbit);
        satellites.delete(satId);
      }
    });

    // Load all closest satellites with unique colors
    receivedSatellites.forEach((sat, index) => {
      console.log(`Processing satellite ${index + 1}:`, sat);

      if (!sat || !sat.id) {
        console.error(`Satellite ${index + 1} missing required data:`, sat);
        return;
      }

      const satId = sat.id.toString();
      const color = getNextColor();
      const name = sat.name || `SAT-${index + 1}`;

      console.log(`Creating satellite ${index + 1}: ID=${satId}, Name=${name}, Color=${color}`);

      // Create satellite directly with the data we have
      try {
        createSatellite(satId, name, sat, color, true);
        console.log(`Successfully created satellite: ${name}`);
      } catch (error) {
        console.error(`Error creating satellite ${name}:`, error);
      }
    });

    console.log(`Loaded ${receivedSatellites.length} closest satellites`);
    console.log('Current satellites in scene:', satellites.size);
  });

  // Keep backward compatibility with single satellite
  window.addEventListener('satelliteFound', (e) => {
    const closestBtn = document.getElementById('tgt-closest');
    if (closestBtn && !window.isAuthenticated) {
      closestBtn.style.display = 'block';
      currentClosestSat = e.detail;

      // Load closest satellite with unique color
      if (currentClosestSat && currentClosestSat.id) {
        loadSatellite(currentClosestSat.id.toString(), 'CSS', getNextColor());
      }
    }
  });

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScene);
  } else {
    initScene();
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', () => {
    if (animationId) cancelAnimationFrame(animationId);
    renderer.dispose();
  });

})();
