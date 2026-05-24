import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.js';

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const sceneRoot = document.querySelector('[data-three-scene="clinical-network"]');
const main = sceneRoot && sceneRoot.closest('main');

if (sceneRoot && main) {
  main.classList.add('has-three-scene');
  main.style.position = main.style.position || 'relative';
  main.style.isolation = 'isolate';
  sceneRoot.style.position = sceneRoot.style.position || 'relative';
  sceneRoot.style.zIndex = sceneRoot.style.zIndex || '1';

  const host = document.createElement('div');
  host.className = 'clinical-three-scene';
  host.setAttribute('aria-hidden', 'true');
  Object.assign(host.style, {
    position: 'absolute',
    inset: '0',
    zIndex: '0',
    overflow: 'hidden',
    pointerEvents: 'none',
  });
  main.insertBefore(host, main.firstChild);

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    preserveDrawingBuffer: window.location.search.includes('verify3d=1'),
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  Object.assign(renderer.domElement.style, {
    display: 'block',
    width: '100%',
    height: '100%',
  });
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 120);
  camera.position.set(0, 0.4, 20);

  const group = new THREE.Group();
  scene.add(group);

  const nodeCount = window.innerWidth < 768 ? 38 : 72;
  const nodePositions = [];
  const nodeGeometry = new THREE.SphereGeometry(0.055, 12, 12);
  const nodeMaterial = new THREE.MeshBasicMaterial({
    color: 0x2563eb,
    transparent: true,
    opacity: 0.34,
  });
  const alertMaterial = new THREE.MeshBasicMaterial({
    color: 0xba1a1a,
    transparent: true,
    opacity: 0.24,
  });

  for (let i = 0; i < nodeCount; i += 1) {
    const band = i / nodeCount;
    const angle = band * Math.PI * 6.2;
    const radius = 4.2 + Math.sin(i * 1.7) * 1.8;
    const x = Math.cos(angle) * radius + (Math.random() - 0.5) * 4.8;
    const y = (Math.random() - 0.5) * 7.2;
    const z = Math.sin(angle) * radius + (Math.random() - 0.5) * 3.5;

    nodePositions.push(new THREE.Vector3(x, y, z));

    const node = new THREE.Mesh(nodeGeometry, i % 11 === 0 ? alertMaterial : nodeMaterial);
    node.position.set(x, y, z);
    node.userData.baseY = y;
    node.userData.phase = Math.random() * Math.PI * 2;
    group.add(node);
  }

  const linePositions = [];
  const lineColors = [];
  const primary = new THREE.Color(0x004ac6);
  const secondary = new THREE.Color(0x10b981);
  const warning = new THREE.Color(0xf59e0b);

  for (let i = 0; i < nodePositions.length; i += 1) {
    for (let j = i + 1; j < nodePositions.length; j += 1) {
      const distance = nodePositions[i].distanceTo(nodePositions[j]);
      if (distance > 3.15 || Math.random() > 0.28) continue;

      linePositions.push(
        nodePositions[i].x, nodePositions[i].y, nodePositions[i].z,
        nodePositions[j].x, nodePositions[j].y, nodePositions[j].z,
      );

      const color = i % 13 === 0 ? warning : (j % 7 === 0 ? secondary : primary);
      lineColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
    }
  }

  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
  lineGeometry.setAttribute('color', new THREE.Float32BufferAttribute(lineColors, 3));

  const lineMaterial = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.16,
  });
  const network = new THREE.LineSegments(lineGeometry, lineMaterial);
  group.add(network);

  const streamGeometry = new THREE.BufferGeometry();
  const streamCount = window.innerWidth < 768 ? 90 : 150;
  const streamPositions = new Float32Array(streamCount * 3);
  const streamSeeds = [];

  for (let i = 0; i < streamCount; i += 1) {
    const seed = {
      x: (Math.random() - 0.5) * 17,
      y: (Math.random() - 0.5) * 8,
      z: (Math.random() - 0.5) * 8,
      speed: 0.0018 + Math.random() * 0.0025,
      phase: Math.random() * Math.PI * 2,
    };
    streamSeeds.push(seed);
    streamPositions[i * 3] = seed.x;
    streamPositions[i * 3 + 1] = seed.y;
    streamPositions[i * 3 + 2] = seed.z;
  }

  streamGeometry.setAttribute('position', new THREE.BufferAttribute(streamPositions, 3));
  const streamMaterial = new THREE.PointsMaterial({
    color: 0x0f766e,
    size: 0.035,
    transparent: true,
    opacity: 0.26,
    depthWrite: false,
  });
  const stream = new THREE.Points(streamGeometry, streamMaterial);
  group.add(stream);

  let width = 0;
  let height = 0;
  let mouseX = 0;
  let mouseY = 0;
  let frameId = null;

  function resize() {
    const rect = main.getBoundingClientRect();
    width = Math.max(1, Math.floor(rect.width));
    height = Math.max(1, Math.floor(rect.height));
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
    group.position.set(width < 768 ? 1.2 : 4.2, -0.4, 0);
    group.scale.setScalar(width < 768 ? 0.92 : 1.18);
  }

  function render(time) {
    const t = time || 0;
    group.rotation.y = Math.sin(t * 0.00018) * 0.18 + mouseX * 0.16;
    group.rotation.x = Math.cos(t * 0.00014) * 0.06 + mouseY * 0.08;

    group.children.forEach((child) => {
      if (!child.isMesh) return;
      child.position.y = child.userData.baseY + Math.sin(t * 0.001 + child.userData.phase) * 0.08;
    });

    const positions = stream.geometry.attributes.position.array;
    for (let i = 0; i < streamSeeds.length; i += 1) {
      const seed = streamSeeds[i];
      positions[i * 3] = seed.x + Math.sin(t * seed.speed + seed.phase) * 0.75;
      positions[i * 3 + 1] = seed.y + Math.cos(t * seed.speed * 0.8 + seed.phase) * 0.35;
      positions[i * 3 + 2] = seed.z + Math.sin(t * seed.speed * 0.7) * 0.45;
    }
    stream.geometry.attributes.position.needsUpdate = true;

    renderer.render(scene, camera);
    if (!prefersReducedMotion) frameId = window.requestAnimationFrame(render);
  }

  function onPointerMove(event) {
    const rect = main.getBoundingClientRect();
    mouseX = ((event.clientX - rect.left) / rect.width - 0.5) * 0.8;
    mouseY = ((event.clientY - rect.top) / rect.height - 0.5) * -0.8;
  }

  resize();

  if (!prefersReducedMotion) {
    frameId = window.requestAnimationFrame(render);
    window.addEventListener('pointermove', onPointerMove, { passive: true });
  } else {
    render(0);
  }

  window.addEventListener('resize', resize, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (prefersReducedMotion) return;
    if (document.hidden && frameId) {
      window.cancelAnimationFrame(frameId);
      frameId = null;
      return;
    }
    if (!document.hidden && !frameId) frameId = window.requestAnimationFrame(render);
  });
}
