import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Tooltip, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const BORTLE_COLORS = {
  1: "#ffffff",
  2: "#d4e8ff",
  3: "#a8d4ff",
  4: "#6ab4ff",
  5: "#ffdd44",
  6: "#ffaa00",
  7: "#ff6600",
  8: "#ff2200",
  9: "#aa0000"
};

const getBortleRating = (bortle) => {
  if (bortle <= 2) return "Milky Way clearly visible";
  if (bortle <= 4) return "Dark rural sky";
  if (bortle <= 6) return "Suburban sky";
  return "City sky (Heavy light pollution)";
};

const DarkSkyMap = ({ onCitySelect = () => {} }) => {
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch dark sky map data from backend
    fetch('/api/meteor/darkmap')
      .then(res => res.json())
      .then(data => {
        setCities(data.cities || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load dark sky map:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '500px', borderRadius: '12px', overflow: 'hidden', border: '1px solid #1f2937' }}>
      {loading && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            Loading Dark Sky Map...
        </div>
      )}
      
      <MapContainer 
        center={[22.5, 82.0]} 
        zoom={5} 
        scrollWheelZoom={false} 
        zoomControl={false}
        style={{ height: '100%', width: '100%', background: '#080808' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        <ZoomControl position="topright" />

        {cities.map((city) => (
          <CircleMarker
            key={city.name}
            center={[city.lat, city.lon]}
            radius={6}
            pathOptions={{
              fillColor: BORTLE_COLORS[city.bortle] || BORTLE_COLORS[9],
              fillOpacity: 0.8,
              stroke: false
            }}
            eventHandlers={{
                click: () => onCitySelect(city.name)
            }}
          >
            <Tooltip direction="top" offset={[0, -5]} opacity={1} permanent={false}>
              <div style={{ padding: '4px', textAlign: 'left', minWidth: '150px' }}>
                <div style={{ fontWeight: 'bold', fontSize: '14px', marginBottom: '4px' }}>{city.name}</div>
                <div style={{ fontSize: '12px', color: '#666' }}>{city.state}</div>
                <hr style={{ margin: '8px 0', border: '0', borderTop: '1px solid #eee' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span>Bortle {city.bortle}</span>
                    <span style={{ color: '#4488ff', fontWeight: 'bold' }}>{city.limiting_mag} mag</span>
                </div>
                <div style={{ fontSize: '11px', fontStyle: 'italic', color: BORTLE_COLORS[city.bortle] }}>
                    {getBortleRating(city.bortle)}
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        ))}

        {/* Legend Overlay */}
        <div className="leaflet-bottom leaflet-right" style={{ pointerEvents: 'auto', marginBottom: '20px', marginRight: '20px' }}>
          <div style={{
            background: 'rgba(0,0,0,0.7)',
            backdropFilter: 'blur(8px)',
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.1)',
            width: '180px'
          }}>
            <div style={{ color: '#fff', fontSize: '11px', fontWeight: 'bold', marginBottom: '10px' }}>India Sky Light Pollution</div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', width: '100%', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                    {Object.values(BORTLE_COLORS).map((color, i) => (
                        <div key={i} style={{ flex: 1, backgroundColor: color }} />
                    ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#9ca3af', fontSize: '9px', marginTop: '4px' }}>
                    <span>Darkest (Bortle 1)</span>
                    <span>Brightest city sky</span>
                </div>
            </div>

            <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: '#e5e7eb' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#fff' }} />
                    Prime viewing (B1-2)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: '#e5e7eb' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ffdd44' }} />
                    Suburb (B5)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', color: '#e5e7eb' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#aa0000' }} />
                    Extreme pollution (B9)
                </div>
            </div>
          </div>
        </div>
      </MapContainer>
    </div>
  );
};

export default DarkSkyMap;
