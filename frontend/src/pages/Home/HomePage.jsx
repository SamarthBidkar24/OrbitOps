import { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { initAstronautScene } from './astronautScene';
import ChatWidget from '../../components/ChatWidget/ChatWidget';
import './HomePage.css';

export default function HomePage() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (canvasRef.current && !initialized.current) {
      initialized.current = true;
      const dispose = initAstronautScene(canvasRef.current, '/models/astronaut.glb');
      return () => {
        dispose();
        initialized.current = false;
      };
    }
  }, []);

  return (
    <div className="app">
      {/* Loader */}
      <div className="loader" id="loader">
        <div className="spinner"></div>
        <div className="loading-text" id="loading-text">Initializing Systems... (0%)</div>
      </div>

      {/* Main UI */}
      <div className="ui-container">
        <h1>OrbitOps</h1>
        <p>Explore the space like never before using ML</p>
      </div>

      {/* Left Panel - 3 Clickable Blocks */}
      <div className="side-panel left">
        <div className="block" onClick={() => navigate('/neo')}>
          <div className="block-glow"></div>
          <h3>NEO</h3>
          <p>Live tracking of Near-Earth Objects. Monitor orbital trajectories and assess potential impact threats in real-time.</p>
        </div>

        <div className="block" onClick={() => navigate('/spectra')}>
          <div className="block-glow"></div>
          <h3>Astrospectra</h3>
          <p>AI-driven spectroscopic classification. Upload spectral signatures to determine asteroid mineral compositions.</p>
        </div>

        <div className="block" onClick={() => navigate('/meteor')}>
          <div className="block-glow"></div>
          <h3>DARK SKY HEATMAP</h3>
          <p>Real-time starlight density mapping across the Indian subcontinent. Discover pristine observation zones and escape urban light pollution for the best meteor shower experience.</p>
        </div>
      </div>

      {/* Right Panel */}
      <div className="side-panel right">
        <div className="block about-guide">
          <div className="block-glow"></div>
          <h3>About &amp; Guide</h3>
          <p>
            OrbitOps is an advanced, AI-driven planetary defense and exploration platform. It aggregates deep-space sensor telemetry, predictive asteroid modeling, and real-time starlight mapping to empower both astronomers and space defense enthusiasts.
            <br /><br />
            <strong>Guide:</strong> Move your cursor to navigate. Observe the subtle inertia and axial shifts.
          </p>
        </div>
      </div>

      {/* Instructions */}
      <div className="instructions" id="instructions-container">
        MOVE YOUR MOUSE AROUND TO EXPLORE ZERO GRAVITY
      </div>

      {/* Three.js Canvas */}
      <canvas ref={canvasRef} id="three-canvas"></canvas>

      {/* Embedded Chat Widget */}
      <ChatWidget />
    </div>
  );
}
