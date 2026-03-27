import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Html, Line, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';

// --- Constants ---
const AU_SCALE = 30;
const EARTH_ORBIT_PERIOD = 25; // Slower period for better clickability
const SUN_RADIUS = 5;
const EARTH_RADIUS = 2.5; // Slightly larger for visibility
const ASTEROID_RADIUS = 1.2;
const CLICK_HIT_SCALE = 2.5; // Invisible hit area multiplier

// --- Helper: Calculate Orbital Position ---
const calculatePosition = (elements, time, periodScale) => {
  const { a, e, i, omega, w, M } = elements;
  
  // Convert elements to radians
  const iRad = (i * Math.PI) / 180;
  const omegaRad = (omega * Math.PI) / 180;
  const wRad = (w * Math.PI) / 180;
  
  // a in units
  const aScale = a * AU_SCALE;
  
  // Calculate Mean Anomaly at time t
  // P = a^(1.5) periods relative to Earth
  const period = EARTH_ORBIT_PERIOD * Math.pow(a, 1.5);
  const meanMotion = (2 * Math.PI) / period;
  const currentM = ( (M * Math.PI) / 180 + meanMotion * time) % (2 * Math.PI);
  
  // Solve Kepler's Equation for Eccentric Anomaly E: M = E - e*sin(E)
  let E = currentM;
  for (let step = 0; step < 5; step++) {
    E = E - (E - e * Math.sin(E) - currentM) / (1 - e * Math.cos(E));
  }
  
  // Position in orbital plane
  const xOrb = aScale * (Math.cos(E) - e);
  const yOrb = aScale * Math.sqrt(1 - e * e) * Math.sin(E);
  
  // Rotate to 3D space
  // x = xOrb * (cos(om)*cos(w) - sin(om)*sin(w)*cos(i)) - yOrb * (cos(om)*sin(w) + sin(om)*cos(w)*cos(i))
  // y = xOrb * (sin(om)*cos(w) + cos(om)*sin(w)*cos(i)) - yOrb * (sin(om)*sin(w) - cos(om)*cos(w)*cos(i))
  // z = xOrb * (sin(w)*sin(i)) + yOrb * (cos(w)*sin(i))
  
  const cosOm = Math.cos(omegaRad);
  const sinOm = Math.sin(omegaRad);
  const cosW = Math.cos(wRad);
  const sinW = Math.sin(wRad);
  const cosI = Math.cos(iRad);
  const sinI = Math.sin(iRad);
  
  const x = xOrb * (cosOm * cosW - sinOm * sinW * cosI) - yOrb * (cosOm * sinW + sinOm * cosW * cosI);
  const z = xOrb * (sinOm * cosW + cosOm * sinW * cosI) - yOrb * (sinOm * sinW - cosOm * cosW * cosI);
  const y = xOrb * (sinW * sinI) + yOrb * (cosW * sinI);
  
  return new THREE.Vector3(x, y, z);
};

// --- Component: Orbit Path ---
const OrbitPath = ({ elements, color = "white", opacity = 0.3, segments = 128 }) => {
  const points = useMemo(() => {
    const { a, e, i, omega, w } = elements;
    const iRad = (i * Math.PI) / 180;
    const omegaRad = (omega * Math.PI) / 180;
    const wRad = (w * Math.PI) / 180;
    const aScale = a * AU_SCALE;
    
    const pts = [];
    for (let step = 0; step <= segments; step++) {
      const E = (step / segments) * 2 * Math.PI;
      const xOrb = aScale * (Math.cos(E) - e);
      const yOrb = aScale * Math.sqrt(1 - e * e) * Math.sin(E);
      
      const cosOm = Math.cos(omegaRad);
      const sinOm = Math.sin(omegaRad);
      const cosW = Math.cos(wRad);
      const sinW = Math.sin(wRad);
      const cosI = Math.cos(iRad);
      const sinI = Math.sin(iRad);
      
      const x = xOrb * (cosOm * cosW - sinOm * sinW * cosI) - yOrb * (cosOm * sinW + sinOm * cosW * cosI);
      const z = xOrb * (sinOm * cosW + cosOm * sinW * cosI) - yOrb * (sinOm * sinW - cosOm * cosW * cosI);
      const y = xOrb * (sinW * sinI) + yOrb * (cosW * sinI);
      
      pts.push(new THREE.Vector3(x, y, z));
    }
    return pts;
  }, [elements, segments]);
  
  return <Line points={points} color={color} lineWidth={1} transparent opacity={opacity} />;
};

// --- Component: Celestial Body ---
const Body = ({ elements, radius, color, onClick }) => {
  const meshRef = useRef();
  
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const pos = calculatePosition(elements, t);
    meshRef.current.position.copy(pos);
  });
  
  return (
    <group ref={meshRef}>
      <mesh onClick={onClick} onPointerOver={() => { document.body.style.cursor = 'pointer'; }} onPointerOut={() => { document.body.style.cursor = 'auto'; }}>
        <sphereGeometry args={[radius, 32, 32]} />
        <meshStandardMaterial 
          color={color} 
          roughness={0.5}
          metalness={0.1}
          emissive={color}
          emissiveIntensity={0.2}
        />
      </mesh>
      <Html distanceFactor={40} position={[0, radius + 2, 0]}>
        <div style={{ 
          color: '#3498db', 
          fontSize: '10px', 
          fontWeight: 'bold', 
          letterSpacing: '1px', 
          background: 'rgba(0,0,0,0.5)', 
          padding: '2px 6px', 
          borderRadius: '40px',
          border: '1px solid #3498db'
        }}>EARTH</div>
      </Html>
    </group>
  );
};

// --- Helper: Sun Glow ---
const SunGlow = () => {
  return (
    <group>
      {/* Core */}
      <mesh pos={[0, 0, 0]}>
        <sphereGeometry args={[SUN_RADIUS, 32, 32]} />
        <meshStandardMaterial 
          emissive={new THREE.Color("#ffdd00")} 
          emissiveIntensity={2} 
          color="#ffcc00" 
        />
        <pointLight intensity={15} distance={300} decay={2} color="#ffffff" />
      </mesh>
      {/* Outer Halo */}
      <mesh pos={[0, 0, 0]}>
        <sphereGeometry args={[SUN_RADIUS * 1.5, 32, 32]} />
        <meshBasicMaterial 
          color="#ffaa00" 
          transparent 
          opacity={0.15} 
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
      <mesh pos={[0, 0, 0]}>
        <sphereGeometry args={[SUN_RADIUS * 2.5, 32, 32]} />
        <meshBasicMaterial 
          color="#ffaa00" 
          transparent 
          opacity={0.05} 
          side={THREE.BackSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
};

// --- Palette of bright asteroid colors ---
const ASTEROID_COLORS = ["#00f2ff", "#ff00a6", "#7dff00", "#ffcc00", "#ff5e00", "#c400ff", "#00ff8c"];

// --- Component: Asteroid ---
const Asteroid = ({ elements, data, onSelect, isSelected, index }) => {
  const meshRef = useRef();
  const asteroidColor = useMemo(() => ASTEROID_COLORS[index % ASTEROID_COLORS.length], [index]);
  
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const pos = calculatePosition(elements, t);
    meshRef.current.position.copy(pos);
  });
  
  // Calculate marker position at the closest approach point
  // We'll estimate this as when M is zero (perihelion) for visual simplicity
  // unless we calculate the exact day's position. Let's use perihelion as the 'marker'.
  const approachPoint = useMemo(() => {
    return calculatePosition(elements, 0); // At T=0 relative to simulation epoch
  }, [elements]);
  
  return (
    <group>
      <OrbitPath 
        elements={elements} 
        color={isSelected ? "#ffa500" : asteroidColor} 
        opacity={isSelected ? 0.8 : 0.2} 
      />
      
      {isSelected && (
        <mesh position={approachPoint}>
          <ringGeometry args={[0.8, 1.2, 32]} />
          <meshBasicMaterial color="#ffa500" side={THREE.DoubleSide} transparent opacity={0.6} />
          <Html distanceFactor={25} position={[0, 2, 0]}>
            <div className="marker-label">APPROACH PT</div>
          </Html>
        </mesh>
      )}

      <group 
        ref={meshRef} 
        onClick={(e) => { e.stopPropagation(); onSelect(data); }}
        onPointerOver={() => { document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { document.body.style.cursor = 'auto'; }}
      >
        {/* Irregular body */}
        <mesh>
          <dodecahedronGeometry args={[ASTEROID_RADIUS, 1]} />
          <meshStandardMaterial 
            color={isSelected ? "#ffa500" : asteroidColor} 
            roughness={0.7} 
            emissive={isSelected ? "#ffa500" : asteroidColor}
            emissiveIntensity={isSelected ? 0.8 : 0.3}
          />
        </mesh>
        
        {/* Invisible larger hit area for easier clicking */}
        <mesh>
          <sphereGeometry args={[ASTEROID_RADIUS * CLICK_HIT_SCALE, 16, 16]} />
          <meshBasicMaterial transparent opacity={0} />
        </mesh>
      </group>
    </group>
  );
};

const OrbitalView = () => {
  const [neos, setNeos] = useState([]);
  const [selectedNeo, setSelectedNeo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.post('/api/v1/neo/predict', {
          date: "2026-03-27",
          observatory_index: 0
        });
        setNeos(res.data.top_neos);
        setLoading(false);
      } catch (err) {
        console.error("Failed to fetch NEOs", err);
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const earthElements = {
    a: 1.0, e: 0.0167, i: 0.0, omega: 0.0, w: 102.9, M: 357.5
  };

  return (
    <div className="orbital-view-container" style={{ width: '100%', height: '100vh', background: '#050505', position: 'relative', overflow: 'hidden' }}>
      {loading && (
        <div className="loader-overlay">
          <div className="loader-content">
            <div className="orbit-spinner"></div>
            <p>CONSTRUCTING SOLAR SYSTEM...</p>
          </div>
        </div>
      )}
      
      <Canvas camera={{ position: [60, 60, 60], fov: 45 }}>
        <color attach="background" args={['#050505']} />
        <fog attach="fog" args={['#050505', 100, 500]} />
        
        <Stars radius={300} depth={60} count={10000} factor={7} saturation={0} fade speed={1} />
        
        <SunGlow />
        
        <group>
          <OrbitPath elements={earthElements} color="#3498db" opacity={0.3} />
          <Body elements={earthElements} radius={EARTH_RADIUS} color="#3498db" />
        </group>
        
        {!loading && neos.map((neo, idx) => (
          <Asteroid 
            key={neo.name} 
            elements={neo.orbital_elements} 
            data={neo}
            index={idx}
            isSelected={selectedNeo?.name === neo.name}
            onSelect={setSelectedNeo}
          />
        ))}
        
        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          maxDistance={250} 
          minDistance={10} 
          enableDamping={true} 
          dampingFactor={0.05}
        />
      </Canvas>

      {/* Tooltip Card */}
      {selectedNeo && (
        <div className="neo-tooltip shadow-glow">
          <div className="tooltip-header">
            <h3>{selectedNeo.name}</h3>
            <button onClick={() => setSelectedNeo(null)}>×</button>
          </div>
          <div className="tooltip-body">
            <div className="data-row">
              <span className="label">DIAMETER</span>
              <span className="value">
                {selectedNeo.diameter_km < 1 
                  ? `${(selectedNeo.diameter_km * 1000).toFixed(selectedNeo.diameter_km < 0.01 ? 3 : 1)} m` 
                  : `${selectedNeo.diameter_km.toFixed(2)} km`}
              </span>
            </div>
            <div className="data-row">
              <span className="label">APPROACH DATE</span>
              <span className="value">{selectedNeo.close_approach_date}</span>
            </div>
            <div className="data-row">
              <span className="label">DISTANCE</span>
              <span className="value">{(selectedNeo.distance_km / 384400).toFixed(2)} LD</span>
            </div>
            <div className="divider"></div>
            <div className="data-row">
              <span className="label">VELOCITY</span>
              <span className="value">{selectedNeo.velocity_kms} km/s</span>
            </div>
            <div className="data-row">
              <span className="label">THREAT</span>
              <span className="value threat-badge" data-level={selectedNeo.threat_level}>
                {selectedNeo.threat_level.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="system-status">
        <span>STATUS: LIVE SIMULATION</span>
        <span>EPOCH: 2026.236</span>
        <span>SCALE: 1:30,000,000 KM</span>
      </div>

      <style jsx>{`
        .orbital-view-container {
          font-family: 'Outfit', sans-serif;
          color: white;
        }
        .loader-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0,0,0,0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
        }
        .loader-content {
          text-align: center;
          letter-spacing: 2px;
          color: #444;
          font-size: 11px;
        }
        .orbit-spinner {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          border: 1px solid #222;
          border-top-color: #ffa500;
          margin: 0 auto 15px;
          animation: spin 1s linear infinite;
        }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .neo-tooltip {
          position: absolute;
          top: 30px;
          right: 30px;
          width: 300px;
          background: rgba(10, 10, 10, 0.85);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 165, 0, 0.3);
          border-radius: 16px;
          padding: 20px;
          z-index: 10;
          animation: slideIn 0.3s ease-out;
        }
        .shadow-glow {
          box-shadow: 0 0 30px rgba(255, 165, 0, 0.1), 0 10px 40px rgba(0,0,0,0.5);
        }
        @keyframes slideIn { from { opacity: 0; transform: translateX(20px); } to { opacity: 1; transform: translateX(0); } }

        .tooltip-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        .tooltip-header h3 {
          margin: 0;
          font-size: 18px;
          letter-spacing: 1px;
          color: #ffa500;
        }
        .tooltip-header button {
          background: rgba(255,255,255,0.05);
          border: none;
          color: #666;
          width: 24px;
          height: 24px;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .tooltip-header button:hover { background: rgba(255,255,255,0.1); color: #fff; }

        .data-row {
          display: flex;
          justify-content: space-between;
          margin-bottom: 12px;
          font-size: 13px;
        }
        .label { color: #666; font-weight: 500; font-size: 11px; letter-spacing: 0.5px; }
        .value { color: #eee; font-weight: 400; }
        .divider { height: 1px; background: rgba(255,255,255,0.05); margin: 15px 0; }
        
        .threat-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 700;
        }
        .threat-badge[data-level='alert'] { background: rgba(255, 77, 77, 0.15); color: #ff4d4d; border: 1px solid rgba(255, 77, 77, 0.3); }
        .threat-badge[data-level='notice'] { background: rgba(77, 255, 77, 0.15); color: #4dff4d; border: 1px solid rgba(77, 255, 77, 0.3); }

        .system-status {
          position: absolute;
          bottom: 25px;
          left: 30px;
          display: flex;
          gap: 30px;
          color: #444;
          font-size: 10px;
          letter-spacing: 1.5px;
          font-weight: 600;
        }
        .marker-label {
          background: rgba(0, 0, 0, 0.8);
          padding: 4px 10px;
          border: 1px solid #ffa500;
          color: #ffa500;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 700;
          box-shadow: 0 0 10px rgba(255, 165, 0, 0.3);
          white-space: nowrap;
          pointer-events: none;
        }
      `}</style>
    </div>
  );
};

export default OrbitalView;
