import OrbitalView from "../components/NEO/OrbitalView";

export default function Neo() {
  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      <OrbitalView />
      
      {/* Page Title Overlay */}
      <h1 style={{ 
        position: 'absolute', 
        top: '20px', 
        left: '30px', 
        margin: 0, 
        color: 'white', 
        zIndex: 5, 
        fontSize: '24px',
        letterSpacing: '3px',
        fontWeight: '200',
        textTransform: 'uppercase'
      }}>
        Neo Observation <span style={{ color: '#ffa500' }}>☄️</span>
      </h1>
    </div>
  );
}
