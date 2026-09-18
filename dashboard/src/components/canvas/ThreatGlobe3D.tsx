import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface ThreatGlobe3DProps {
  threatCount?: number;
  activeThreatLevel?: 'CLEAN' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export const ThreatGlobe3D: React.FC<ThreatGlobe3DProps> = ({
  threatCount = 14,
  activeThreatLevel = 'CRITICAL'
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 450;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // 1. Globe wireframe sphere
    const sphereRadius = 75;
    const sphereGeometry = new THREE.SphereGeometry(sphereRadius, 36, 36);
    const sphereWireframe = new THREE.WireframeGeometry(sphereGeometry);
    const sphereLine = new THREE.LineSegments(
      sphereWireframe,
      new THREE.LineBasicMaterial({
        color: 0x1e293b,
        transparent: true,
        opacity: 0.35,
      })
    );
    globeGroup.add(sphereLine);

    // 2. Inner glow sphere
    const innerGeo = new THREE.SphereGeometry(sphereRadius * 0.98, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0x0a1120,
      transparent: true,
      opacity: 0.85,
    });
    const innerSphere = new THREE.Mesh(innerGeo, innerMat);
    globeGroup.add(innerSphere);

    // 3. Dot cloud representing global network nodes
    const dotCount = 1200;
    const dotPositions = new Float32Array(dotCount * 3);
    const dotColors = new Float32Array(dotCount * 3);

    for (let i = 0; i < dotCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / dotCount);
      const theta = Math.sqrt(dotCount * Math.PI) * phi;
      const r = sphereRadius + 0.5;

      const x = r * Math.cos(theta) * Math.sin(phi);
      const y = r * Math.sin(theta) * Math.sin(phi);
      const z = r * Math.cos(phi);

      dotPositions[i * 3] = x;
      dotPositions[i * 3 + 1] = y;
      dotPositions[i * 3 + 2] = z;

      // Subtle cyan-indigo gradient
      dotColors[i * 3] = 0.1; // R
      dotColors[i * 3 + 1] = 0.5 + Math.random() * 0.4; // G
      dotColors[i * 3 + 2] = 0.9; // B
    }

    const dotGeometry = new THREE.BufferGeometry();
    dotGeometry.setAttribute('position', new THREE.BufferAttribute(dotPositions, 3));
    dotGeometry.setAttribute('color', new THREE.BufferAttribute(dotColors, 3));

    const dotMaterial = new THREE.PointsMaterial({
      size: 1.6,
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
    });
    const points = new THREE.Points(dotGeometry, dotMaterial);
    globeGroup.add(points);

    // 4. Coordinates for major hubs (latitude, longitude)
    const hubs = [
      { name: 'San Francisco', lat: 37.77, lon: -122.41, type: 'support' },
      { name: 'London', lat: 51.50, lon: -0.12, type: 'support' },
      { name: 'Frankfurt', lat: 50.11, lon: 8.68, type: 'support' },
      { name: 'Tokyo', lat: 35.67, lon: 139.65, type: 'support' },
      { name: 'Singapore', lat: 1.35, lon: 103.81, type: 'support' },
      { name: 'Attack C2 - Seychelles', lat: -4.67, lon: 55.49, type: 'threat' },
      { name: 'Attack C2 - Eastern Europe', lat: 53.9, lon: 27.56, type: 'threat' },
      { name: 'Attacker Relay - Moldova', lat: 47.01, lon: 28.86, type: 'threat' },
    ];

    const latLonToVector3 = (lat: number, lon: number, radius: number) => {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      return new THREE.Vector3(
        -radius * Math.sin(phi) * Math.cos(theta),
        radius * Math.cos(phi),
        radius * Math.sin(phi) * Math.sin(theta)
      );
    };

    // Add glowing hub markers
    hubs.forEach((hub) => {
      const pos = latLonToVector3(hub.lat, hub.lon, sphereRadius + 1.2);
      const isThreat = hub.type === 'threat';
      const color = isThreat ? 0xf43f5e : 0x10b981;

      // Small sphere marker
      const markerGeo = new THREE.SphereGeometry(isThreat ? 2.4 : 1.8, 12, 12);
      const markerMat = new THREE.MeshBasicMaterial({ color });
      const marker = new THREE.Mesh(markerGeo, markerMat);
      marker.position.copy(pos);
      globeGroup.add(marker);

      // Pulsing halo ring around marker
      const ringGeo = new THREE.RingGeometry(2.5, 4.5, 16);
      const ringMat = new THREE.MeshBasicMaterial({
        color,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.7,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(pos);
      ring.lookAt(new THREE.Vector3(0, 0, 0));
      globeGroup.add(ring);
    });

    // 5. Connecting Attack & Support Telemetry Arcs
    const createArc = (start: THREE.Vector3, end: THREE.Vector3, color: number) => {
      const distance = start.distanceTo(end);
      const mid = start.clone().lerp(end, 0.5);
      const alt = sphereRadius + distance * 0.25;
      mid.normalize().multiplyScalar(alt);

      const curve = new THREE.QuadraticBezierCurve3(start, mid, end);
      const curvePoints = curve.getPoints(40);
      const curveGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const curveMat = new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity: 0.65,
        linewidth: 2,
      });
      return new THREE.Line(curveGeo, curveMat);
    };

    // Threat arcs (Red)
    const moldovaPos = latLonToVector3(47.01, 28.86, sphereRadius);
    const sfPos = latLonToVector3(37.77, -122.41, sphereRadius);
    const londonPos = latLonToVector3(51.50, -0.12, sphereRadius);
    const seychellesPos = latLonToVector3(-4.67, 55.49, sphereRadius);
    const frankfurtPos = latLonToVector3(50.11, 8.68, sphereRadius);

    globeGroup.add(createArc(moldovaPos, sfPos, 0xf43f5e));
    globeGroup.add(createArc(seychellesPos, londonPos, 0xf43f5e));
    // Safe support inter-hub telemetry arc (Teal)
    globeGroup.add(createArc(sfPos, frankfurtPos, 0x00f0ff));

    // 6. Orbiting equatorial cyber ring
    const ringGeometry = new THREE.RingGeometry(sphereRadius + 18, sphereRadius + 19.5, 64);
    const ringColorByLevel: Record<string, number> = {
      CRITICAL: 0xf43f5e, // red
      HIGH: 0xf59e0b,      // amber
      MEDIUM: 0xf59e0b,    // amber
      LOW: 0x00f0ff,       // cyan
      CLEAN: 0x00f0ff,     // cyan
    };
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: ringColorByLevel[activeThreatLevel] ?? 0x00f0ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.35,
    });
    const outerRing = new THREE.Mesh(ringGeometry, ringMaterial);
    outerRing.rotation.x = Math.PI / 2.3;
    globeGroup.add(outerRing);

    // 7. Interactive mouse drag
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      globeGroup.rotation.y += deltaX * 0.006;
      globeGroup.rotation.x += deltaY * 0.006;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    // Animation loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!isDragging) {
        globeGroup.rotation.y += 0.0028;
      }
      outerRing.rotation.z += 0.004;

      renderer.render(scene, camera);
    };
    animate();

    // Resize listener
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [activeThreatLevel]);

  return (
    <div className="relative w-full h-[400px] md:h-[450px] flex items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-b from-[#0B0F19]/80 to-[#07090E] border border-white/10 shadow-2xl">
      {/* Subtle Top Indicator */}
      <div className="absolute top-4 left-5 z-10 pointer-events-none flex flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-mono text-xs uppercase tracking-wider text-slate-300 font-semibold">
            Global Threat Radar {threatCount > 0 ? `(${threatCount} blocked)` : ''}
          </span>
        </div>
        <span className="font-mono text-[9px] text-slate-500 pl-4">
          Network topology illustrative — hub locations are not live geo-IP data
        </span>
      </div>

      {/* 3D WebGL Canvas Mount */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
    </div>
  );
};
