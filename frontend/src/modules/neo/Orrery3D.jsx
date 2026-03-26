import React, { useRef, useState, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Torus, Line, Html, Text } from '@react-three/drei';
import * as THREE from 'three';

const THREAT_COLORS = {
  monitor: '#00ff88',
  watch: '#ffaa00',
  alert: '#ff3333'
};

const NEOOrbit = ({ neo, timeScale }) => {
  const { a, e, i, q } = neo.orbital_elements || { a: 1.2, e: 0.3, i: 10, q: 0.9 };
  const color = THREAT_COLORS[neo.threat_level] || THREAT_COLORS.monitor;
  const [hovered, setHovered] = useState(false);

  // Scale: 1 AU = 4 units
  const auScale = 4;
  const xRadius = a * auScale;
  const yRadius = a * auScale * Math.sqrt(1 - Math.pow(e, 2));
  const centerX = a * e * auScale; // Shift center so sun is at focus

  const curve = useMemo(() => {
    return new THREE.EllipseCurve(
      centerX, 0,
      xRadius, yRadius,
      0, 2 * Math.PI,
      false, 0
    );
  }, [centerX, xRadius, yRadius]);

  const points = useMemo(() => curve.getPoints(100).map(p => new THREE.Vector3(p.x, 0, p.y)), [curve]);
  
  const neoRef = useRef();
  
  useFrame((state) => {
    const t = (state.clock.getElapsedTime() * timeScale * (1 / (a * a))) % (2 * Math.PI);
    const point = curve.getPoint(t / (2 * Math.PI));
    if (neoRef.current) {
        neoRef.current.position.set(point.x, 0, point.y);
    }
  });

  return (
    <group rotation={[THREE.MathUtils.degToRad(i), 0, 0]}>
      {/* Orbit Line */}
      <Line points={points} color={color} lineWidth={1} transparent opacity={0.4} />
      
      {/* NEO Sphere */}
      <mesh 
        ref={neoRef}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2} />
        
        {hovered && (
          <Html distanceFactor={10} position={[0, 0.2, 0]}>
            <div style={{
              background: 'rgba(0,0,0,0.85)',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '6px',
              border: `1px solid ${color}`,
              whiteSpace: 'nowrap',
              fontFamily: 'Inter, sans-serif',
              fontSize: '12px',
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{neo.name}</div>
              <div style={{ color: '#aaa' }}>Dist: {(neo.distance_km / 1e6).toFixed(2)}M km</div>
              <div style={{ color, textTransform: 'uppercase', fontSize: '10px', marginTop: '2px' }}>
                Threat: {neo.threat_level}
              </div>
            </div>
          </Html>
        )}
      </mesh>
    </group>
  );
};

const Earth = ({ timeScale }) => {
  const earthRef = useRef();
  const earthGroupRef = useRef();
  
  useFrame((state) => {
    const t = (state.clock.getElapsedTime() * (2 * Math.PI / 30)); // 30s period
    if (earthGroupRef.current) {
        earthGroupRef.current.rotation.y = t;
    }
    if (earthRef.current) {
        earthRef.current.rotation.y += 0.01;
    }
  });

  return (
    <group ref={earthGroupRef}>
      <mesh ref={earthRef} position={[4, 0, 0]}>
        <sphereGeometry args={[0.15, 32, 32]} />
        <meshStandardMaterial color="#2233ff" roughness={0.5} />
        <Html position={[0, 0.25, 0]} center>
            <div style={{ color: '#00ff88', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <div style={{ width: '4px', height: '4px', background: '#00ff88', borderRadius: '50%' }} />
                Earth
            </div>
        </Html>
      </mesh>
    </group>
  );
};

const Orrery3D = ({ neos = [] }) => {
  return (
    <div style={{ width: '100%', height: '500px', position: 'relative', background: '#000', borderRadius: '12px', overflow: 'hidden' }}>
      <Canvas camera={{ position: [0, 8, 16], fov: 45 }}>
        <color attach="background" args={['#000000']} />
        
        <ambientLight intensity={0.2} />
        <pointLight position={[0, 0, 0]} intensity={2.5} color="#ffcc00" />
        
        {/* Sun */}
        <mesh position={[0, 0, 0]}>
          <sphereGeometry args={[0.4, 32, 32]} />
          <meshStandardMaterial color="#ffcc00" emissive="#ffaa00" emissiveIntensity={2} />
        </mesh>
        
        {/* Earth Orbit Ring */}
        <Torus args={[4, 0.005, 16, 100]} rotation={[Math.PI / 2, 0, 0]}>
          <meshBasicMaterial color="#4488ff" transparent opacity={0.3} />
        </Torus>
        
        <Earth />
        
        {/* NEOs */}
        {neos.map((neo, idx) => (
          <NEOOrbit key={neo.name || idx} neo={neo} timeScale={0.2} />
        ))}
        
        <OrbitControls enablePan={false} maxDistance={40} minDistance={5} />
      </Canvas>
      
      {/* Legend Overlay */}
      <div style={{
        position: 'absolute',
        bottom: '20px',
        left: '20px',
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(8px)',
        padding: '12px',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        zIndex: 10
      }}>
        <div style={{ color: '#fff', fontSize: '12px', fontWeight: '600', marginBottom: '4px' }}>NEO Threat Scale</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#ccc' }}>
          <div style={{ width: '8px', height: '8px', background: THREAT_COLORS.alert, borderRadius: '50%' }} />
          Alert (High Risk)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#ccc' }}>
          <div style={{ width: '8px', height: '8px', background: THREAT_COLORS.watch, borderRadius: '50%' }} />
          Watch (Caution)
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: '#ccc' }}>
          <div style={{ width: '8px', height: '8px', background: THREAT_COLORS.monitor, borderRadius: '50%' }} />
          Monitor (Safe)
        </div>
      </div>
    </div>
  );
};

export default Orrery3D;
