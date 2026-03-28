import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

// ---- Configuration ----
const LERP_FACTOR = 0.05;
const FLOAT_AMPLITUDE = 0.5;
const FLOAT_FREQUENCY = 0.0015;
const ROTATION_SPEED = 0.0004;

export function initAstronautScene(canvasElement, modelPath) {
  // ---- State ----
  const mouse = new THREE.Vector2();
  const targetPosition = new THREE.Vector3();
  let astronaut = null;
  let scene, camera, renderer;
  let animationId = null;

  function init() {
    // 1. Scene setup
    scene = new THREE.Scene();

    // 2. Camera setup
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    // 3. Renderer setup
    const canvas = canvasElement;
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xffffff, 2);
    mainLight.position.set(5, 5, 5);
    scene.add(mainLight);

    const purpleLight = new THREE.PointLight(0x8a2be2, 5, 20);
    purpleLight.position.set(-5, 2, 2);
    scene.add(purpleLight);

    const blueLight = new THREE.PointLight(0x00ffff, 3, 20);
    blueLight.position.set(5, -2, 2);
    scene.add(blueLight);

    // 5. Starfield background
    createStarfield();

    // 6. Loading the Model
    const gltfLoader = new GLTFLoader();
    const loadingOutput = document.getElementById('loading-text');

    gltfLoader.load(
      modelPath,
      (gltf) => {
        astronaut = gltf.scene;

        // Center and scale model if necessary
        const box = new THREE.Box3().setFromObject(astronaut);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Normalize scale so it fits the scene nicely
        const maxDim = Math.max(size.x, size.y, size.z);
        const factor = 4 / maxDim;
        astronaut.scale.set(factor, factor, factor);

        // Position center
        astronaut.position.x = -center.x * factor;
        astronaut.position.y = -center.y * factor;
        astronaut.position.z = -center.z * factor;

        // Group for easier manipulation
        const group = new THREE.Group();
        group.add(astronaut);
        scene.add(group);

        astronaut = group;

        // Hide loader
        const loaderEl = document.getElementById('loader');
        if (loaderEl) loaderEl.classList.add('hidden');
      },
      (xhr) => {
        if (loadingOutput) {
          if (xhr.total > 0) {
            const percent = Math.round((xhr.loaded / xhr.total) * 100);
            loadingOutput.textContent = `Syncing Bio-Signs... (${percent}%)`;
          } else {
            const mbs = (xhr.loaded / (1024 * 1024)).toFixed(1);
            loadingOutput.textContent = `Syncing Bio-Signs... (${mbs} MB)`;
          }
        }
      },
      (error) => {
        console.error('Error loading astronaut model:', error);
        if (loadingOutput) {
          loadingOutput.textContent = 'ERROR LOADING SYSTEMS';
          loadingOutput.style.color = 'red';
        }
      }
    );

    // 7. Event Listeners
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('resize', onWindowResize);

    // Start animation loop
    animate();
  }

  function createStarfield() {
    const starsGeometry = new THREE.BufferGeometry();
    const starsMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.015,
      sizeAttenuation: true,
    });

    const starVertices = [];
    for (let i = 0; i < 1500; i++) {
      const x = (Math.random() - 0.5) * 100;
      const y = (Math.random() - 0.5) * 100;
      const z = (Math.random() - 0.5) * 100;
      starVertices.push(x, y, z);
    }

    starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starVertices, 3));
    const stars = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(stars);
  }

  function onMouseMove(event) {
    // Normalize mouse coordinates to [-1, 1]
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
  }

  function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  function animate() {
    animationId = requestAnimationFrame(animate);

    const time = Date.now();

    if (astronaut) {
      // 1. Calculate target based on mouse
      targetPosition.x = mouse.x * 2.5;
      targetPosition.y = mouse.y * 1.5;

      // 2. Linear Interpolation for smooth "floaty" movement
      astronaut.position.lerp(targetPosition, LERP_FACTOR);

      // 3. Constant idle floating (sine wave)
      astronaut.position.y += Math.sin(time * FLOAT_FREQUENCY) * 0.005;
      astronaut.position.x += Math.cos(time * FLOAT_FREQUENCY * 0.7) * 0.003;

      // 4. Subtle rotation following the mouse direction + idle spin
      const targetRotationZ = mouse.x * 0.2;
      const targetRotationX = -mouse.y * 0.2;

      // Smoothly rotate the astronaut to "face" the movement slightly
      astronaut.rotation.z = THREE.MathUtils.lerp(astronaut.rotation.z, targetRotationZ, LERP_FACTOR);
      astronaut.rotation.x = THREE.MathUtils.lerp(astronaut.rotation.x, targetRotationX, LERP_FACTOR);

      // Continuous idle spin
      astronaut.rotation.y += ROTATION_SPEED;
    }

    renderer.render(scene, camera);
  }

  init();

  // Return cleanup function
  return () => {
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('resize', onWindowResize);
    if (animationId !== null) {
      cancelAnimationFrame(animationId);
    }
    if (renderer) {
      renderer.dispose();
    }
  };
}
