import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Track which job is processing and what type (cv or letter)
  const [processingState, setProcessingState] = useState({ id: null, type: null });

  const fetchJobs = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get('/api/jobs');
      setJobs(response.data);
    } catch (err) {
      console.error("API Error:", err);
      setError("Backend connection failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  // Updated function to handle file downloads
  const handleDownload = async (job, type) => {
    try {
      setProcessingState({ id: job.id, type: type });
      
      const payload = {
        company_name: job.company || "Unknown",
        job_title: job.title || "Unknown",
        job_description: job.description || "No description provided."
      };

      // Determine endpoint based on button clicked
      const endpoint = type === 'cv' ? '/api/optimize-cv' : '/api/cover-letter';
      const filePrefix = type === 'cv' ? 'Optimized_CV' : 'Cover_Letter';

      // CRITICAL: Tell Axios we are expecting a file (blob), not JSON
      const response = await axios.post(endpoint, payload, {
        responseType: 'blob' 
      });
      
      // Magic trick: Create a fake link in the browser to trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Clean up company name for the file name (remove spaces)
      const safeCompanyName = (job.company || "Company").replace(/[^a-zA-Z0-9]/g, '_');
      link.setAttribute('download', `${filePrefix}_${safeCompanyName}.docx`);
      
      document.body.appendChild(link);
      link.click();
      
      // Clean up the fake link after download
      link.parentNode.removeChild(link);

    } catch (err) {
      console.error("Download Error:", err);
      alert("Failed to generate document. Please check the console.");
    } finally {
      setProcessingState({ id: null, type: null });
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans">
      <div className="max-w-5xl mx-auto">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8 bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            💼 AI Job Assistant
          </h1>
          <button 
            onClick={fetchJobs}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors font-medium text-slate-600 flex items-center gap-2"
          >
            {loading ? "🔄 Loading..." : "🔄 Refresh"}
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
            ⚠️ {error}
          </div>
        )}

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {loading ? (
            <div className="col-span-full text-center py-20 text-slate-500 font-medium">Loading job market data...</div>
          ) : jobs.length > 0 ? (
            jobs.map((job, index) => (
              <div key={index} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-400 transition-all flex flex-col justify-between h-full">
                
                {/* Job Info */}
                <div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2 line-clamp-2">
                    {job.title || "Untitled Position"}
                  </h3>
                  <p className="text-slate-600 font-medium mb-6 flex items-center gap-2">
                    🏢 {job.company || "Unknown Company"}
                  </p>
                </div>
                
                {/* Action Buttons (Side by Side) */}
                <div className="flex gap-3 mt-auto">
                  <button 
                    onClick={() => handleDownload(job, 'cv')}
                    disabled={processingState.id === job.id}
                    className={`flex-1 py-2.5 rounded-xl font-semibold transition-all text-sm ${
                      processingState.id === job.id && processingState.type === 'cv'
                        ? "bg-slate-300 text-slate-500 cursor-not-allowed" 
                        : "bg-slate-900 text-white hover:bg-blue-600 shadow-md"
                    }`}
                  >
                    {processingState.id === job.id && processingState.type === 'cv' 
                      ? "⏳ Baking..." 
                      : "📄 Get CV"}
                  </button>

                  <button 
                    onClick={() => handleDownload(job, 'letter')}
                    disabled={processingState.id === job.id}
                    className={`flex-1 py-2.5 rounded-xl font-semibold transition-all text-sm border-2 ${
                      processingState.id === job.id && processingState.type === 'letter'
                        ? "bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed" 
                        : "bg-white text-slate-900 border-slate-900 hover:bg-slate-50 shadow-sm"
                    }`}
                  >
                    {processingState.id === job.id && processingState.type === 'letter' 
                      ? "⏳ Baking..." 
                      : "✉️ Cover Letter"}
                  </button>
                </div>

              </div>
            ))
          ) : (
            <div className="col-span-full text-center py-20 bg-white rounded-2xl border-2 border-dashed border-slate-300">
              <p className="text-slate-500 font-medium">No active job postings found in the database.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default App;