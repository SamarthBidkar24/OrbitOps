import React, { useEffect, useRef, useState, useMemo } from 'react';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Star, Info, ArrowRight, Shield, Zap, Navigation } from 'lucide-react';

// ─── BUG FIX 7: Fix broken default marker icons in Vite/Webpack ───────────────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl:       'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl:     'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// ─── BUG FIX 6: Correct Bortle class color mapping ───────────────────────────
const getBortleColor = (bortle) => {
  if (bortle <= 2) return '#000022'; // Darkest  — Hanle, Spiti
  if (bortle <= 4) return '#1a237e'; // Deep blue — Leh, Ooty
  if (bortle <= 6) return '#4a148c'; // Purple   — Jaipur, Pune
  return '#ff3d00';                  // Bright red — Mumbai, Delhi, Bangalore
};

// Bortle → readable label
const getBortleLabel = (bortle) => {
  if (bortle <= 2) return 'Pristine Dark Sky';
  if (bortle <= 4) return 'Rural Sky';
  if (bortle <= 6) return 'Suburban Sky';
  if (bortle <= 8) return 'City Sky';
  return 'Inner-City Sky';
};

// BUG FIX 7 — Detailed Bortle description for user city popup
const getBortleDescription = (bortle) => {
  const descs = {
    1: 'Excellent dark sky — Milky Way casts shadows',
    2: 'Truly dark sky — Milky Way clearly visible',
    3: 'Rural sky — some light pollution',
    4: 'Rural/Suburban transition',
    5: 'Suburban sky — Milky Way faint',
    6: 'Bright suburban sky',
    7: 'Suburban/Urban transition',
    8: 'City sky — only brightest stars visible',
    9: 'Inner city sky — no stars visible',
  };
  return descs[bortle] || descs[8];
};

// BUG FIX 2/findNearestCity — pure Euclidean nearest-city search
const findNearestCity = (lat, lon, cities) => {
  if (!cities || cities.length === 0) return null;
  let nearest = cities[0];
  let minDist = Infinity;
  cities.forEach((city) => {
    const dist = Math.sqrt(
      Math.pow(city.lat - lat, 2) + Math.pow(city.lon - lon, 2)
    );
    if (dist < minDist) { minDist = dist; nearest = city; }
  });
  return nearest;
};

// ─── BUG FIX 5: Fallback hardcoded cities if API fails ───────────────────────
const getFallbackCities = () => [
  { name: 'Mumbai',       lat: 19.0760, lon: 72.8777, bortle_class: 8, bortle: 8, population: 20000000, state: 'Maharashtra' },
  { name: 'Delhi',        lat: 28.7041, lon: 77.1025, bortle_class: 8, bortle: 8, population: 18000000, state: 'Delhi' },
  { name: 'Bangalore',    lat: 12.9716, lon: 77.5946, bortle_class: 7, bortle: 7, population: 12000000, state: 'Karnataka' },
  { name: 'Chennai',      lat: 13.0827, lon: 80.2707, bortle_class: 8, bortle: 8, population: 10000000, state: 'Tamil Nadu' },
  { name: 'Hyderabad',    lat: 17.3850, lon: 78.4867, bortle_class: 7, bortle: 7, population: 9000000,  state: 'Telangana' },
  { name: 'Pune',         lat: 18.5204, lon: 73.8567, bortle_class: 7, bortle: 7, population: 6000000,  state: 'Maharashtra' },
  { name: 'Ahmedabad',    lat: 23.0225, lon: 72.5714, bortle_class: 7, bortle: 7, population: 7000000,  state: 'Gujarat' },
  { name: 'Jaipur',       lat: 26.9124, lon: 75.7873, bortle_class: 6, bortle: 6, population: 3000000,  state: 'Rajasthan' },
  { name: 'Kolkata',      lat: 22.5726, lon: 88.3639, bortle_class: 8, bortle: 8, population: 14000000, state: 'West Bengal' },
  { name: 'Lucknow',      lat: 26.8467, lon: 80.9462, bortle_class: 7, bortle: 7, population: 3000000,  state: 'Uttar Pradesh' },
  { name: 'Ooty',         lat: 11.4100, lon: 76.6950, bortle_class: 3, bortle: 3, population: 88000,    state: 'Tamil Nadu' },
  { name: 'Coorg',        lat: 12.3375, lon: 75.8069, bortle_class: 4, bortle: 4, population: 50000,    state: 'Karnataka' },
  { name: 'Leh',          lat: 34.1526, lon: 77.5771, bortle_class: 2, bortle: 2, population: 30000,    state: 'Ladakh' },
  { name: 'Spiti Valley', lat: 32.2187, lon: 78.0422, bortle_class: 1, bortle: 1, population: 1000,     state: 'Himachal Pradesh' },
  { name: 'Hanle',        lat: 32.8353, lon: 78.9584, bortle_class: 1, bortle: 1, population: 300,      state: 'Ladakh' },
  { name: 'Jaisalmer',    lat: 26.9157, lon: 70.9083, bortle_class: 3, bortle: 3, population: 80000,    state: 'Rajasthan' },
  { name: 'Rann of Kutch',lat: 23.7337, lon: 69.8597, bortle_class: 2, bortle: 2, population: 5000,     state: 'Gujarat' },
  { name: 'Chikmagalur',  lat: 13.3161, lon: 75.7720, bortle_class: 3, bortle: 3, population: 120000,   state: 'Karnataka' },
  { name: 'Munnar',       lat: 10.0889, lon: 77.0595, bortle_class: 3, bortle: 3, population: 50000,    state: 'Kerala' },
  { name: 'Nainital',     lat: 29.3803, lon: 79.4636, bortle_class: 4, bortle: 4, population: 40000,    state: 'Uttarakhand' },
];

// ─── Haversine distance (km) ──────────────────────────────────────────────────
const haversineKm = (lat1, lon1, lat2, lon2) => {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
    Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
};

const DELHI = [28.6139, 77.209];

// ─── Star divIcon HTML helper ─────────────────────────────────────────────────
const makeStarIconHtml = (rank) => `
  <div style="position:relative;width:36px;height:36px;
              display:flex;align-items:center;justify-content:center;">
    <svg width="36" height="36" viewBox="0 0 24 24" fill="#FFD700"
         stroke="#7c5a00" stroke-width="0.8"
         style="filter:drop-shadow(0 0 5px rgba(255,215,0,0.9))">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02
                       12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
    </svg>
    <span style="position:absolute;top:12px;font-size:9px;font-weight:900;
                 color:#1a0a00;line-height:1;user-select:none;">${rank}</span>
  </div>`;

// ─── Legend config ────────────────────────────────────────────────────────────
const LEGEND = [
  { color: '#000022', label: 'Bortle 1–2  Pristine' },
  { color: '#1a237e', label: 'Bortle 3–4  Rural' },
  { color: '#4a148c', label: 'Bortle 5–6  Suburban' },
  { color: '#ff3d00', label: 'Bortle 7+   City' },
];

// ─────────────────────────────────────────────────────────────────────────────
export default function DarkSkyMap() {
  const mapContainerRef = useRef(null); // DOM node for the map div
  const leafletMapRef   = useRef(null); // L.Map instance
  const markersRef      = useRef([]);   // track added layers for cleanup
  const userMarkerRef   = useRef(null); // BUG FIX 6 — ref for gold user marker

  const [cities,    setCities]    = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [flyTarget, setFlyTarget] = useState(null);

  // BUG FIX 3 — State variables for user location
  const [userCity,   setUserCity]   = useState(null);
  const [mapCenter,  setMapCenter]  = useState([20.5937, 78.9629]); // India center
  const [zoom,       setZoom]       = useState(5);

  // ── BUG FIX 4 — Geolocation helpers (defined inside component to access state setters) ──
  const fetchUserLocationByIP = React.useCallback(async (cityList) => {
    try {
      const response = await fetch('https://ipapi.co/json/');
      const data = await response.json();
      const { latitude, longitude, city } = data;
      console.log('IP-based location:', city, latitude, longitude);
      const nearest = findNearestCity(latitude, longitude, cityList);
      setUserCity(nearest);
      setMapCenter([latitude, longitude]);
      setZoom(7);
    } catch (error) {
      console.error('IP location failed:', error);
      // Final fallback — use Mumbai (not Delhi) as generic default
      const defaultCity = cityList.find((c) => c.name === 'Mumbai') || cityList[0];
      if (defaultCity) {
        setUserCity(defaultCity);
        setMapCenter([defaultCity.lat, defaultCity.lon]);
        setZoom(5);
      }
    }
  }, []);

  const getUserLocation = React.useCallback((cityList) => {
    if (!navigator.geolocation) {
      fetchUserLocationByIP(cityList);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        console.log('User location:', latitude, longitude);
        const nearest = findNearestCity(latitude, longitude, cityList);
        setUserCity(nearest);
        setMapCenter([latitude, longitude]);
        setZoom(7);
      },
      (err) => {
        console.warn('Geolocation error:', err.message);
        fetchUserLocationByIP(cityList);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  }, [fetchUserLocationByIP]);

  // ── Fetch cities then trigger geolocation ──
  useEffect(() => {
    const fetchCities = async () => {
      try {
        const response = await axios.get('/api/v1/meteor/darkmap');
        console.log('Darkmap API Response:', response.data);
        const raw = response.data;
        const list = Array.isArray(raw) ? raw : (raw?.cities ?? []);
        const normalised = list.map((c) => ({
          ...c,
          bortle_class: c.bortle_class ?? c.bortle ?? 5,
          bortle:       c.bortle       ?? c.bortle_class ?? 5,
        }));
        const cityList = normalised.length > 0 ? normalised : getFallbackCities();
        if (normalised.length === 0) console.warn('API empty — using fallback');
        setCities(cityList);
        getUserLocation(cityList); // BUG FIX 4 — call after cities are ready
      } catch (error) {
        console.error('Failed to fetch darkmap:', error);
        const cityList = getFallbackCities();
        setCities(cityList);
        getUserLocation(cityList);
      } finally {
        setLoading(false);
      }
    };
    fetchCities();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── BUG FIX 8: Initialise map AFTER data loads, destroy on unmount ──
  useEffect(() => {
    // Don't run until we have both the DOM node and the city data
    if (!mapContainerRef.current || loading) return;
    // Don't double-init
    if (leafletMapRef.current) return;

    // BUG FIX 3: Use standard OSM tile URL (always works, no CDN issues)
    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([20.5937, 78.9629], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    leafletMapRef.current = map;

    // ── City circle markers ──
    cities.forEach((city) => {
      const bortle = city.bortle_class ?? city.bortle ?? 5;
      const pop    = city.population ?? 0;
      const radius = Math.max(5, Math.min(20, Math.sqrt(pop) / 80));

      const cm = L.circleMarker([city.lat, city.lon], {
        radius,
        color:       getBortleColor(bortle),
        fillColor:   getBortleColor(bortle),
        fillOpacity: 0.75,
        weight:      0.8,
        opacity:     0.9,
      })
      .bindTooltip(
        `<b style="font-size:13px">${city.name}</b><br/>
         Bortle ${bortle} — ${getBortleLabel(bortle)}<br/>
         <span style="font-size:11px;color:#94a3b8">
           Best view: ${bortle <= 4 ? 'Right here!' : 'None nearby'}
         </span>`,
        { direction: 'top', offset: [0, -6] }
      )
      .bindPopup(
        `<div style="font-family:system-ui;min-width:200px;padding:4px">
           <p style="font-weight:900;font-size:15px;margin:0 0 3px">${city.name}</p>
           <p style="font-size:12px;color:#4f46e5;font-weight:700;margin:0 0 3px">
             Bortle ${bortle} — ${getBortleLabel(bortle)}
           </p>
           ${bortle >= 7
             ? `<p style="font-size:11px;color:#64748b;font-style:italic;margin:0 0 3px">
                  City lights drown out most stars. Drive ~150 km to the nearest dark spot.
                </p>`
             : ''}
           ${bortle <= 4
             ? `<p style="font-size:11px;color:#16a34a;font-style:italic;margin:0 0 3px">
                  Excellent sky — Milky Way likely visible!
                </p>`
             : ''}
           <p style="font-size:10px;color:#94a3b8;margin:4px 0 0">
             Best view: ${bortle <= 4 ? 'Right here!' : 'None nearby'}
           </p>
         </div>`
      )
      .addTo(map);

      markersRef.current.push(cm);
    });

    // ── Initial blue dot at India center (replaced by gold user marker later) ──
    const userIcon = L.divIcon({
      html: `<div style="width:12px;height:12px;border-radius:50%;
                          background:rgba(99,102,241,0.4);border:1px solid rgba(255,255,255,0.2);"></div>`,
      className: '',
      iconSize:   [12, 12],
      iconAnchor: [6, 6],
    });
    const centerDot = L.marker([20.5937, 78.9629], { icon: userIcon, zIndexOffset: 10, interactive: false }).addTo(map);
    markersRef.current.push(centerDot);

    return () => {
      map.remove();
      leafletMapRef.current = null;
      markersRef.current = [];
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, cities]); // re-run when cities arrive

  // ── Fly to target when sidebar item clicked ──
  useEffect(() => {
    if (!flyTarget || !leafletMapRef.current) return;
    leafletMapRef.current.flyTo(flyTarget, 9, { duration: 1.4 });
  }, [flyTarget]);

  // ── BUG FIX 5 — Gold pulsing marker for user's detected city ──
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!userCity || !map) return;

    // Remove previous user marker
    if (userMarkerRef.current) {
      map.removeLayer(userMarkerRef.current);
      userMarkerRef.current = null;
    }

    const bortle = userCity.bortle_class ?? userCity.bortle ?? 5;

    // Gold pulsing circleMarker
    const goldMarker = L.circleMarker([userCity.lat, userCity.lon], {
      radius:      14,
      color:       '#ffd700',
      fillColor:   '#ffd700',
      fillOpacity: 0.55,
      weight:      3,
    })
    .bindPopup(
      `<div style="font-family:system-ui;min-width:200px;padding:4px">
         <p style="font-weight:900;font-size:15px;margin:0 0 3px;color:#1a0a00">
           📍 You are near: ${userCity.name}
         </p>
         <p style="font-size:12px;color:#4f46e5;font-weight:700;margin:0 0 3px">
           Bortle ${bortle}
         </p>
         <p style="font-size:11px;color:#374151;margin:0">
           ${getBortleDescription(bortle)}
         </p>
       </div>`,
      { maxWidth: 240 }
    )
    .addTo(map);

    userMarkerRef.current = goldMarker;

    // Fly to user's actual location after map is ready
    map.flyTo([userCity.lat, userCity.lon], zoom, { duration: 1.2 });
    console.log(`User city set: ${userCity.name} — Bortle ${bortle}`);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userCity]);

  // ── Top 10 darkest spots for sidebar ──
  const topSpots = useMemo(() => {
    const sorted = [...cities].sort(
      (a, b) => (a.bortle_class ?? a.bortle ?? 9) - (b.bortle_class ?? b.bortle ?? 9)
    );
    return sorted.slice(0, 10).map((c, i) => ({
      ...c,
      rank: i + 1,
      km:   haversineKm(DELHI[0], DELHI[1], c.lat, c.lon),
    }));
  }, [cities]);

  // ── Add numbered star markers for top 10 once map is ready ──
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map || topSpots.length === 0) return;

    // Remove any previously added star markers (stored with a flag)
    if (map._starMarkers) {
      map._starMarkers.forEach((m) => map.removeLayer(m));
    }
    map._starMarkers = [];

    topSpots.forEach((spot) => {
      const starIcon = L.divIcon({
        html:       makeStarIconHtml(spot.rank),
        className:  '',
        iconSize:   [36, 36],
        iconAnchor: [18, 18],
        popupAnchor:[0, -20],
      });

      const m = L.marker([spot.lat, spot.lon], { icon: starIcon, zIndexOffset: 500 })
        .bindPopup(
          `<div style="font-family:system-ui;min-width:210px;padding:4px">
             <span style="display:inline-block;background:#fbbf24;color:#1a0a00;
                          font-size:9px;font-weight:900;padding:2px 7px;
                          border-radius:4px;margin-bottom:5px;
                          text-transform:uppercase;letter-spacing:.06em">
               Dark Sky Rank #${spot.rank}
             </span>
             <p style="font-weight:900;font-size:16px;margin:0 0 3px">${spot.name}</p>
             <p style="font-size:12px;color:#16a34a;font-weight:700;margin:0 0 5px">
               Bortle ${spot.bortle_class ?? spot.bortle} — You can see the Milky Way clearly.
             </p>
             <p style="font-size:10px;color:#6366f1;font-weight:700;
                        text-transform:uppercase;letter-spacing:.07em;margin:0">
               ${spot.km} km from Delhi
             </p>
           </div>`
        )
        .addTo(map);

      map._starMarkers.push(m);
    });
  }, [topSpots]); // re-runs when topSpots resolves

  // ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ height: 720 }}
           className="flex items-center justify-center gap-4 rounded-3xl
                      bg-black/20 border border-white/5">
        <Zap className="w-8 h-8 text-blue-400 animate-spin" />
        <span className="text-blue-400 font-bold tracking-widest uppercase text-sm">
          Loading Celestial Radiance Data…
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-6 w-full" style={{ height: 720 }}>

      {/* ══ MAP PANEL ══════════════════════════════════════════════ */}
      <div className="flex-1 relative rounded-[32px] overflow-hidden
                      border border-white/10 shadow-2xl bg-[#0a0c12]">

        {/* Live badge */}
        <div className="absolute top-4 left-4 z-[1000] pointer-events-none">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full
                          bg-black/70 backdrop-blur-sm border border-white/10">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[10px] font-bold tracking-widest text-white/70 uppercase">
              Starlight Density · Live
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-[1000] pointer-events-none">
          <div className="px-3 py-2.5 rounded-xl bg-black/80 backdrop-blur-sm
                          border border-white/10 space-y-1.5">
            {LEGEND.map(({ color, label }) => (
              <div key={color} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ background: color }} />
                <span className="text-[10px] text-white/55 font-medium leading-none">
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* BUG FIX 2: Map container div — explicit height so Leaflet renders */}
        <div
          ref={mapContainerRef}
          style={{ height: '100%', width: '100%' }}
        />
      </div>

      {/* ══ SIDEBAR ════════════════════════════════════════════════ */}
      <div
        className="lg:w-96 w-full flex flex-col rounded-[32px] border border-white/10
                   shadow-2xl overflow-hidden relative"
        style={{ background: 'rgba(8,10,16,0.97)', backdropFilter: 'blur(28px)' }}
      >
        {/* Top accent */}
        <div className="absolute top-0 left-0 right-0 h-[3px]
                        bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-600" />

        {/* Header */}
        <div className="px-6 pt-7 pb-4 border-b border-white/[0.06] flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex-shrink-0">
              <Star className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h2 className="text-base font-black italic tracking-tight text-white leading-none">
                CELESTIAL HAVENS
              </h2>
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mt-0.5">
                Top 10 Indian Dark Sky Spots
              </p>
            </div>
          </div>
        </div>

        {/* Spots list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1.5 dark-scrollbar">
          {topSpots.map((spot) => {
            const bortle = spot.bortle_class ?? spot.bortle ?? 5;
            return (
              <button
                key={spot.rank}
                onClick={() => setFlyTarget([spot.lat, spot.lon])}
                className="w-full group flex items-center gap-3 px-4 py-3 rounded-2xl
                           border border-white/[0.05] bg-white/[0.02]
                           hover:bg-white/[0.07] hover:border-indigo-500/30
                           transition-all duration-200 text-left cursor-pointer"
              >
                {/* Rank badge */}
                <div
                  className="w-9 h-9 flex-shrink-0 rounded-xl flex items-center justify-center
                             font-black text-sm text-white group-hover:scale-105
                             transition-transform shadow-md shadow-indigo-600/20"
                  style={{ background: 'linear-gradient(135deg,#3730a3,#6366f1)' }}
                >
                  {spot.rank}
                </div>

                {/* Name + meta */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-white truncate
                                group-hover:text-indigo-300 transition-colors leading-none mb-1">
                    {spot.name}
                  </p>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className="px-1.5 py-px rounded text-[9px] font-bold uppercase tracking-wider text-white"
                      style={{ background: getBortleColor(bortle) }}
                    >
                      Bortle {bortle}
                    </span>
                    <span className="text-[10px] text-gray-500 truncate">
                      {spot.km} km {'\u00b7'} {spot.state || 'India'}
                    </span>
                  </div>
                </div>

                <ArrowRight className="w-4 h-4 text-gray-700 group-hover:text-indigo-400
                                       group-hover:translate-x-0.5 transition-all flex-shrink-0" />
              </button>
            );
          })}
        </div>

        {/* Footer guide */}
        <div className="px-4 pb-5 pt-2 flex-shrink-0">
          <div
            className="p-4 rounded-2xl border border-indigo-500/20 relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg,rgba(67,56,202,0.22),rgba(99,102,241,0.08))',
            }}
          >
            <Shield className="absolute -bottom-3 -right-3 w-14 h-14 text-white/[0.03] rotate-12" />
            <div className="flex items-center gap-2 mb-1.5">
              <Info className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-widest">
                Observer's Guide
              </span>
            </div>
            <p className="text-[11px] text-indigo-100/55 leading-relaxed">
              Spots ranked 1–3 show naked-eye Milky Way on New Moon nights.
              Click any spot to fly the map there.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
