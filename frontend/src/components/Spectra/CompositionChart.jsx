import React, { useState } from 'react';
import axios from 'axios';
import { Chart as ChartJS, registerables } from 'chart.js';
import { Doughnut as Chart } from 'react-chartjs-2';
import { Upload, Activity, Loader2, Info, Zap } from 'lucide-react';

ChartJS.register(...registerables);

// Rule 1: Normalize class labels to specific standard asteroid classes
const normalizeClassLabel = (label) => {
  // Map raw model output to valid asteroid classes
  const labelMap = {
    "A": "S",      // A (A-type) → S-type for our simplified model
    "B": "C",      // B (B-type) → C-type for our simplified model
    "O": "Other",  // O → Other (unclassified)
    "S": "S",
    "C": "C",
    "X": "X",
    "M": "S",      // M-type → S-type (both silicate-based)
    "V": "S",      // V-type → S-type (basaltic = silicate)
    "Q": "S",      // Q-type → S-type
    "D": "C",      // D-type → C-type (dark primitive)
    "T": "C",      // T-type → C-type
    "P": "C"       // P-type → C-type
  };
  return labelMap[label] || "Other";
};

// Rule 3: Updated formatting function for valid classes
const formatTypeLabel = (type) => {
  const map = {
    "S": "S-type (Silicaceous)",
    "C": "C-type (Carbonaceous)",
    "X": "X-type (Unclassified)",
    "Other": "Other"
  };
  return map[type] || `${type}-type`;
};

const CompositionChart = () => {
  const [file, setFile] = useState(null);
  // Rule 1: State variables
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [classificationResult, setClassificationResult] = useState(null);
  const [chartMinerals, setChartMinerals] = useState([]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  // Rule 4: Pure function for mineral mapping
  const getMineralBreakdown = (type) => {
    const mappings = {
      'S-type': [{ name: 'Olivine', value: 45 }, { name: 'Pyroxene', value: 30 }, { name: 'Iron-Nickel', value: 15 }, { name: 'Other', value: 10 }],
      'C-type': [{ name: 'Carbonaceous', value: 50 }, { name: 'Silicates', value: 30 }, { name: 'Water/Ice', value: 15 }, { name: 'Other', value: 5 }],
      'X-type': [{ name: 'Iron-Nickel', value: 60 }, { name: 'Silicates', value: 25 }, { name: 'Olivine', value: 10 }, { name: 'Other', value: 5 }],
      'Other': [{ name: 'Unclassified', value: 100 }],
    };
    return mappings[type] || mappings['Other'];
  };

  // Mineral Colors for Premium Look
  const mineralColors = {
    'Olivine': '#27ae60',
    'Pyroxene': '#2ecc71',
    'Iron-Nickel': '#95a5a6',
    'Other': '#bdc3c7',
    'Carbonaceous': '#34495e',
    'Silicates': '#f39c12',
    'Water/Ice': '#3498db',
    'Basalt': '#c0392b',
    'Unclassified': '#475569'
  };

  const handleClassify = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/v1/spectra/classify', formData);
      
      // Rule 2: Normalize the raw response
      const rawLabel = typeof response.data === 'string' ? response.data : (response.data.type || response.data.predicted_class || 'O');
      const normalizedLabel = normalizeClassLabel(rawLabel);
      
      setClassificationResult(normalizedLabel);
      console.log('Raw label:', rawLabel, '→ Normalized:', normalizedLabel);

      // Rule 7: Update minerals using normalized label
      const chartKey = normalizedLabel === 'Other' ? 'Other' : `${normalizedLabel}-type`;
      setChartMinerals(getMineralBreakdown(chartKey));
    } catch (err) {
      // Rule 8: Error handling
      setError("Classification failed. Please try a valid SPEX .spc file.");
    } finally {
      setLoading(false);
    }
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '70%',
    plugins: {
      legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: 'Outfit' } } },
      tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', padding: 12 }
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto p-10 font-outfit text-white min-h-screen">
      <div className="mb-12 text-center">
        <h2 className="text-4xl font-black italic tracking-tighter mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">
          ASTEROID MINERAL ANALYZER
        </h2>
        <p className="text-gray-400 text-sm tracking-widest uppercase">Deep Space Spectroscopic Classification</p>
      </div>

      {/* Input Section */}
      <div className="glass-panel p-8 rounded-[40px] border border-white/10 mb-10 shadow-2xl overflow-hidden relative">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-600 to-indigo-600"></div>
        <div className="flex flex-col md:flex-row items-center gap-8">
          <div className="flex-1 w-full space-y-2">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest px-1">Source Dataset (.spc)</span>
            <div className={`p-4 border-2 border-dashed rounded-2xl flex items-center gap-4 transition-all ${file ? 'border-green-500/30 bg-green-500/5' : 'border-white/10 bg-white/5'}`}>
              <Upload className={`w-5 h-5 ${file ? 'text-green-400' : 'text-gray-400'}`} />
            <label className="flex-1 relative cursor-pointer py-2">
              <input
                type="file"
                accept=".spc"
                onChange={handleFileChange}
                onClick={(e) => (e.target.value = null)}
                className="hidden"
              />
              <span className="text-sm truncate opacity-60 block">{file ? file.name : "Choose SPEX format file (.spc)"}</span>
            </label>
            </div>
          </div>
          <button
            onClick={handleClassify}
            disabled={loading || !file}
            className="px-10 py-5 bg-white text-black font-black rounded-2xl hover:bg-gray-200 hover:scale-105 active:scale-95 transition-all disabled:opacity-20 flex items-center gap-3 shadow-xl"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
            CLASSIFY SIGNATURE
          </button>
        </div>
        {error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-xl text-sm flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
            <Info className="w-4 h-4"/>
            {error}
          </div>
        )}
      </div>

      {loading && (
        <div className="py-20 flex flex-col items-center justify-center">
          <div className="relative">
            <Loader2 className="w-16 h-16 text-blue-500 animate-spin mb-4"/>
            <div className="absolute inset-0 w-16 h-16 bg-blue-500/20 blur-xl animate-pulse"></div>
          </div>
          <p className="text-blue-400 font-bold tracking-widest animate-pulse">ANALYZING SPECIMEN...</p>
        </div>
      )}

      {/* Rule 4: Pending status message */}
      {!loading && !classificationResult && (
        <div className="py-20 text-center opacity-40 italic flex flex-col items-center gap-4">
          <Activity className="w-12 h-12 text-gray-600 mb-2" />
          <p className="text-xl font-bold tracking-tight">Classification pending — upload a file to begin.</p>
        </div>
      )}

      {!loading && classificationResult && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-5 duration-500">
          {/* Rule 4: Result Card with specific structure */}
          <div className="result-card glass-panel p-10 rounded-[40px] border border-white/10 flex flex-col justify-center relative overflow-hidden">
            <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/10 blur-[80px]"></div>
            <div className="classification-result space-y-8 relative z-10">
              <h3 className="text-[10px] font-bold text-blue-400 uppercase tracking-[0.4em] mb-4 block underline underline-offset-8 decoration-blue-500/30">
                Classification Result
              </h3>
              <div className="type-badge text-5xl font-black italic text-white tracking-tighter transition-all">
                {formatTypeLabel(classificationResult)}
              </div>
              <div className="p-4 bg-white/5 rounded-2xl border border-white/5 flex items-center gap-4">
                <Zap className="w-5 h-5 text-blue-400" />
                <p className="text-xs text-gray-400 italic">"Gaseous and solid mineral analysis reveals significant yields of rare space elements."</p>
              </div>
            </div>
          </div>

          {/* Chart Card */}
          <div className="glass-panel p-10 rounded-[40px] border border-white/10 flex flex-col items-center shadow-2xl min-h-[450px] relative overflow-hidden">
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-indigo-500/5 blur-[80px]"></div>
            <h3 className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.4em] mb-10 text-center relative z-10">Mineralogical Characterization</h3>
            <div className="w-full h-[300px] relative flex items-center justify-center z-10">
              {/* Rule 5 & 6: Reactive data and Key prop for re-rendering */}
              <Chart
                key={classificationResult || 'default'}
                data={{
                  labels: chartMinerals.map(m => m.name),
                  datasets: [{
                    data: chartMinerals.map(m => m.value),
                    backgroundColor: chartMinerals.map(m => mineralColors[m.name] || '#ffffff'),
                    borderColor: 'rgba(0,0,0,0.5)',
                    borderWidth: 2,
                    hoverOffset: 20
                  }]
                }}
                options={options}
              />
              <div className="absolute flex flex-col items-center justify-center pointer-events-none translate-y-[-10px]">
                <span className="text-[9px] font-bold text-blue-500 uppercase tracking-widest mb-1">Taxon</span>
                <span className="text-4xl font-black italic">
                  {classificationResult}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CompositionChart;
