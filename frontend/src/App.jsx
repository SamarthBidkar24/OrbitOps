import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/Home/HomePage";
import Neo from "./pages/Neo";
import Spectra from "./pages/Spectra";
import Meteor from "./pages/Meteor";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/neo" element={<Neo />} />
      <Route path="/spectra" element={<Spectra />} />
      <Route path="/meteor" element={<Meteor />} />
    </Routes>
  );
}

export default App;
