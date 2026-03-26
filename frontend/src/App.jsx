import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Neo from "./pages/Neo";
import Spectra from "./pages/Spectra";
import Meteor from "./pages/Meteor";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/neo" element={<Neo />} />
      <Route path="/spectra" element={<Spectra />} />
      <Route path="/meteor" element={<Meteor />} />
    </Routes>
  );
}

export default App;
