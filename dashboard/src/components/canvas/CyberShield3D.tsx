import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import type { ThreatSeverity } from '../../types/intelligence';

interface CyberShield3DProps {
  threatLevel: ThreatSeverity;
  phishingScore: number;
}

export const CyberShield3D: React.FC<CyberShield3DProps> = ({
  threatLevel,
  phishingScore
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 280;
    const height = container.clientHeight || 280;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 120;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    // Pick colors based on threat level
    let primaryColorHex = 0x10b981; // Safe green
    let accentColorHex = 0x00f0ff; // Cyan
    if (threatLevel === 'CRITICAL' || threatLevel === 'HIGH') {
      primaryColorHex = 0xf43f5e; // Rose red
      accentColorHex = 0xff0055;
    } else if (threatLevel === 'MEDIUM') {
      primaryColorHex = 0xf59e0b; // Amber
      accentColorHex = 0xfbbf24;
    }

    // Outer wireframe icosahedron
    const icoGeo = new THREE.IcosahedronGeometry(36, 1);
    const icoWire = new THREE.WireframeGeometry(icoGeo);
    const icoLine = new THREE.LineSegments(
      icoWire,
      new THREE.LineBasicMaterial({
        color: primaryColorHex,
        transparent: true,
        opacity: 0.65,
        linewidth: 1.5,
      })
    );
    group.add(icoLine);

    // Inner glowing core
    const coreGeo = new THREE.OctahedronGeometry(20, 0);
    const coreMat = new THREE.MeshBasicMaterial({
      color: accentColorHex,
      wireframe: true,
      transparent: true,
      opacity: 0.8,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    group.add(coreMesh);

    // Orbiting sensor rings
    const ringGeo1 = new THREE.TorusGeometry(45, 0.6, 16, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: primaryColorHex,
      transparent: true,
      opacity: 0.4,
    });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
    group.add(ring1);

    const ringGeo2 = new THREE.TorusGeometry(49, 0.5, 16, 64);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: accentColorHex,
      transparent: true,
      opacity: 0.3,
    });
    const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
    ring2.rotation.x = Math.PI / 2;
    group.add(ring2);

    // Floating data particles
    const particleCount = 60;
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const radius = 55 + Math.random() * 15;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.random() * Math.PI;

      particlePositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      particlePositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      particlePositions[i * 3 + 2] = radius * Math.cos(phi);
    }
    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: primaryColorHex,
      size: 2,
      transparent: true,
      opacity: 0.7,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    group.add(particles);

    // Mouse tilt tracking
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      mouseX = (x / rect.width) * 0.8;
      mouseY = (y / rect.height) * 0.8;
    };
    container.addEventListener('mousemove', handleMouseMove);

    // Animation loop
    let animationFrameId: number;
    let time = 0;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      time += 0.015;

      icoLine.rotation.x += 0.005;
      icoLine.rotation.y += 0.008;

      coreMesh.rotation.x -= 0.01;
      coreMesh.rotation.y -= 0.012;

      ring1.rotation.x = Math.sin(time * 0.5) * 0.4;
      ring1.rotation.y += 0.006;

      ring2.rotation.y += 0.005;
      ring2.rotation.z += 0.004;

      particles.rotation.y += 0.002;

      // Subtle smooth tilt towards cursor
      group.rotation.y += (mouseX - group.rotation.y) * 0.05;
      group.rotation.x += (-mouseY - group.rotation.x) * 0.05;

      renderer.render(scene, camera);
    };
    animate();

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
      container.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [threatLevel]);

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      <div ref={containerRef} className="w-full h-full flex items-center justify-center cursor-pointer" />
      
      {/* Central HUD Badge */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
        <div className="font-mono text-[10px] uppercase tracking-wider text-slate-400">
          HEURISTIC THREAT INDEX
        </div>
        <div
          className={`font-mono text-3xl font-extrabold tracking-tight ${
            threatLevel === 'CRITICAL' || threatLevel === 'HIGH'
              ? 'text-rose-400 drop-shadow-[0_0_12px_rgba(244,63,94,0.6)]'
              : threatLevel === 'MEDIUM'
              ? 'text-amber-400 drop-shadow-[0_0_12px_rgba(245,158,11,0.6)]'
              : 'text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.6)]'
          }`}
        >
          {phishingScore}%
        </div>
        <div
          className={`text-[11px] font-semibold uppercase px-2 py-0.5 rounded border mt-1 ${
            threatLevel === 'CRITICAL'
              ? 'bg-rose-950/60 text-rose-300 border-rose-500/40'
              : threatLevel === 'HIGH'
              ? 'bg-rose-900/40 text-rose-300 border-rose-500/30'
              : threatLevel === 'MEDIUM'
              ? 'bg-amber-950/50 text-amber-300 border-amber-500/30'
              : 'bg-emerald-950/50 text-emerald-300 border-emerald-500/30'
          }`}
        >
          {threatLevel}
        </div>
      </div>
    </div>
  );
};
