import DarkSkyMap from "../components/Meteor/DarkSkyMap";

export default function Meteor() {
  return (
    <div className="min-h-screen bg-[#05060a] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-950 to-black p-6 lg:p-12">
      <div className="max-w-[1600px] mx-auto space-y-12">
        {/* Header Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-widest animate-fade-in">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
            Observation Intelligence
          </div>
          <h1 className="text-4xl lg:text-7xl font-black italic tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white via-white to-white/40 drop-shadow-2xl">
            DARK SKY HEATMAP
          </h1>
          <p className="max-w-2xl mx-auto text-gray-400 text-sm font-medium tracking-wide leading-relaxed">
            Real-time starlight density mapping across the Indian subcontinent. Discover pristine observation 
            zones and escape urban light pollution for the best meteor shower experience.
          </p>
        </div>

        {/* Map Component */}
        <div className="animate-in fade-in slide-in-from-bottom-5 duration-700">
           <DarkSkyMap />
        </div>

        {/* Footer Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-12 border-t border-white/5">
            <div className="p-6 rounded-[32px] bg-white/5 border border-white/5 space-y-2">
                <h4 className="text-white font-bold text-sm tracking-tight underline decoration-indigo-500 underline-offset-8">Precision Mapping</h4>
                <p className="text-xs text-gray-400 leading-relaxed">Utilizing the Bortle Dark-Sky Scale to quantify starlight visibility and light scatter levels.</p>
            </div>
            <div className="p-6 rounded-[32px] bg-white/5 border border-white/5 space-y-2">
                <h4 className="text-white font-bold text-sm tracking-tight underline decoration-blue-500 underline-offset-8">Ideal Conditions</h4>
                <p className="text-xs text-gray-400 leading-relaxed">Bortle 1-4 sites are critical for seeing fine structures of the Milky Way and faint meteor streaks.</p>
            </div>
            <div className="p-6 rounded-[32px] bg-white/5 border border-white/5 space-y-2">
                <h4 className="text-white font-bold text-sm tracking-tight underline decoration-purple-500 underline-offset-8">Smart Proximity</h4>
                <p className="text-xs text-gray-400 leading-relaxed">Location logic calculates travel distances from Delhi (Capital) to ensure accessibility awareness.</p>
            </div>
        </div>
      </div>
    </div>
  );
}
