import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

function App() {
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [activeTab, setActiveTab] = useState('search');
  const [processingState, setProcessingState] = useState({ id: null, type: null });

  // MODAL STATES
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [rawJobText, setRawJobText] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);

  // CHAT STATES
  const [activeChatTab, setActiveChatTab] = useState('strategy'); // 'strategy' or 'interview'
  const [chatMessages, setChatMessages] = useState([]);
  const [interviewMessages, setInterviewMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  const [showRawDesc, setShowRawDesc] = useState(false);

  // Auto-scroll for both chat rooms
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, interviewMessages, activeChatTab]);

  // Load both histories when a job is clicked
  useEffect(() => {
    if (selectedJob) {
      setShowRawDesc(false);
      setActiveChatTab('strategy'); // Reset to strategy view when opening a new job
      
      // Parse Strategy History
      if (selectedJob.chat_history) {
        try {
          const parsedHistory = typeof selectedJob.chat_history === 'string' 
            ? JSON.parse(selectedJob.chat_history) 
            : selectedJob.chat_history;
          setChatMessages(parsedHistory || []);
        } catch (e) {
          console.error("Strategy Parse Error:", e);
          setChatMessages([]);
        }
      } else {
        setChatMessages([]);
      }

      // Parse Interview History
      if (selectedJob.interview_history) {
        try {
          const parsedInterview = typeof selectedJob.interview_history === 'string'
            ? JSON.parse(selectedJob.interview_history)
            : selectedJob.interview_history;
          setInterviewMessages(parsedInterview || []);
        } catch (e) {
          console.error("Interview Parse Error:", e);
          setInterviewMessages([]);
        }
      } else {
        setInterviewMessages([]);
      }
    }
  }, [selectedJob]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [jobsRes, appsRes] = await Promise.all([
        axios.get('http://127.0.0.1:8000/api/jobs'),
        axios.get('http://127.0.0.1:8000/api/applications')
      ]);
      setJobs(jobsRes.data);
      setApplications(appsRes.data);
    } catch (err) {
      console.error("API Error:", err);
      setError("Failed to connect to the backend. Ensure the Python server is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDownload = async (job, type) => {
    try {
      setProcessingState({ id: job.id, type: type });
      const payload = {
        job_id: job.id,
        company_name: job.company || "Unknown",
        job_title: job.title || "Unknown",
        job_description: job.description || "No description provided."
      };
      const endpoint = type === 'cv' ? 'http://127.0.0.1:8000/api/optimize-cv' : 'http://127.0.0.1:8000/api/cover-letter';
      const filePrefix = type === 'cv' ? 'Optimized_CV' : 'Cover_Letter';
      const response = await axios.post(endpoint, payload, { responseType: 'blob' });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const safeCompanyName = (job.company || "Company").replace(/[^a-zA-Z0-9]/g, '_');
      link.setAttribute('download', `${filePrefix}_${safeCompanyName}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      console.error("Download Error:", err);
      alert("An error occurred while generating the document. Please check the console.");
    } finally {
      setProcessingState({ id: null, type: null });
    }
  };

  const handleMarkAsApplied = async (job, e) => {
    if(e) e.stopPropagation(); 
    try {
      setProcessingState({ id: job.id, type: 'apply' });
      await axios.post('http://127.0.0.1:8000/api/jobs', {
        company: job.company,
        job_title: job.title
      });
      alert(`Application for ${job.company} saved successfully!`);
      fetchData(); 
    } catch (err) {
      console.error("Save Error:", err);
      alert("Failed to save the application status.");
    } finally {
      setProcessingState({ id: null, type: null });
    }
  };

  const handleExtractJob = async () => {
    if (!rawJobText.trim()) {
      alert("Please paste some text first!");
      return;
    }
    try {
      setProcessingState({ id: 'extract', type: 'magic' });
      await axios.post('http://127.0.0.1:8000/api/extract-job', { raw_text: rawJobText });
      setIsAddModalOpen(false);
      setRawJobText("");
      fetchData(); 
    } catch (err) {
      console.error("Extraction Error:", err);
      alert("Scout AI failed to process the text. Check console.");
    } finally {
      setProcessingState({ id: null, type: null });
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !selectedJob) return;

    const userMessage = chatInput.trim();
    setChatInput("");
    setIsChatLoading(true);

    if (activeChatTab === 'strategy') {
      // 1. STRATEGY ROOM LOGIC
      setChatMessages(prev => [...prev, { sender: 'user', text: userMessage }]);
      try {
        const response = await axios.post('http://127.0.0.1:8000/api/chat', {
          job_id: selectedJob.id,
          user_message: userMessage,
          company: selectedJob.company || "Unknown Company",
          job_description: selectedJob.description || ""
        });
        setChatMessages(prev => [...prev, { 
          sender: 'ai', 
          text: response.data.ai_answer,
          isBoss: response.data.routed_to_pro 
        }]);
        fetchData();
      } catch (err) {
        console.error("Chat Error:", err);
        setChatMessages(prev => [...prev, { sender: 'ai', text: "⚠️ Connection to the AI Council failed." }]);
      } finally {
        setIsChatLoading(false);
      }
    } else {
      // 2. INTERVIEW ROOM LOGIC
      setInterviewMessages(prev => [...prev, { sender: 'user', text: userMessage }]);
      try {
        const response = await axios.post('http://127.0.0.1:8000/api/interview-chat', {
          job_id: selectedJob.id,
          user_message: userMessage
        });
        setInterviewMessages(prev => [...prev, { 
          sender: 'ai', 
          text: response.data.answer // Matches your Python return statement
        }]);
        fetchData();
      } catch (err) {
        console.error("Interview Chat Error:", err);
        setInterviewMessages(prev => [...prev, { sender: 'ai', text: "⚠️ Connection to the Manager failed." }]);
      } finally {
        setIsChatLoading(false);
      }
    }
  };

  const currentMessages = activeChatTab === 'strategy' ? chatMessages : interviewMessages;

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans text-slate-800">
      <div className="max-w-6xl mx-auto">
        
        <div className="flex flex-col md:flex-row justify-between items-center mb-8 bg-white p-4 rounded-2xl shadow-sm border border-slate-200 gap-4">
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">💼 AI Job Assistant</h1>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setActiveTab('search')} className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'search' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>🔍 Job Search</button>
            <button onClick={() => setActiveTab('tracker')} className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'tracker' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>📊 Tracker ({applications.length})</button>
            <button onClick={() => alert("Select a job from the list and open the 'Interview Room' tab inside it to begin!")} className="px-4 py-2 rounded-lg font-medium transition-colors bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 ml-2">🎯 Interview Room</button>
            <div className="w-px h-8 bg-slate-200 mx-2 hidden md:block"></div>
            <button onClick={() => setIsAddModalOpen(true)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors shadow-sm">➕ Add Job</button>
            <button onClick={fetchData} className="px-4 py-2 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors font-medium">{loading ? "🔄..." : "Refresh"}</button>
          </div>
        </div>

        {error && <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl">⚠️ {error}</div>}

        {activeTab === 'search' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {loading ? <div className="col-span-full text-center py-20 text-slate-500">Loading...</div> : jobs.length > 0 ? jobs.map((job, index) => {
                const isApplied = applications.some(app => app.company === job.company && app.job_title === job.title);
                return (
                  <div key={index} onClick={() => setSelectedJob(job)} className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-400 hover:shadow-md cursor-pointer transition-all flex flex-col relative h-40">
                    {job.ai_score && <div className={`absolute top-4 right-4 text-xs font-bold px-2.5 py-1 rounded-full ${job.ai_score >= 80 ? 'bg-green-100 text-green-700' : job.ai_score >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>{job.ai_score}% Match</div>}
                    <h3 className="text-lg font-bold text-slate-900 line-clamp-1 pr-20">{job.title || "Untitled"}</h3>
                    <p className="text-slate-500 text-sm font-medium mb-auto mt-1 flex items-center gap-1">🏢 {job.company || "Unknown"}</p>
                    <div className="mt-4 flex justify-between items-center">
                      <span className="text-xs text-slate-400 font-medium">Click for details & Chat</span>
                      {isApplied ? <span className="text-xs font-bold text-green-600 bg-green-50 px-3 py-1.5 rounded-lg">Applied ✅</span> : <button onClick={(e) => handleMarkAsApplied(job, e)} disabled={processingState.id === job.id && processingState.type === 'apply'} className="text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 px-4 py-1.5 rounded-lg transition-colors">{processingState.id === job.id && processingState.type === 'apply' ? "⏳..." : "✅ Apply"}</button>}
                    </div>
                  </div>
                );
              }) : <div className="col-span-full text-center py-20 bg-white rounded-2xl border-2 border-dashed border-slate-300"><p className="text-slate-500">No active job postings.</p></div>
            }
          </div>
        )}

        {activeTab === 'tracker' && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
             <div className="p-6 border-b border-slate-100 bg-slate-50"><h2 className="text-lg font-bold text-slate-800">Application History</h2></div>
            {applications.length > 0 ? (
              <table className="w-full text-left">
                <thead><tr className="bg-slate-100 text-slate-600 text-sm uppercase"><th className="p-4">Company</th><th className="p-4">Position</th><th className="p-4">Date</th></tr></thead>
                <tbody>{applications.map((app, idx) => <tr key={idx} className="border-b last:border-0 hover:bg-slate-50"><td className="p-4 font-semibold">{app.company}</td><td className="p-4 text-slate-600">{app.job_title}</td><td className="p-4 text-slate-500">{app.applied_date}</td></tr>)}</tbody>
              </table>
            ) : <div className="text-center py-16 text-slate-500">You haven't applied to any jobs yet.</div>}
          </div>
        )}

        {isAddModalOpen && (
          <div className="fixed inset-0 bg-slate-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl p-6 max-w-2xl w-full shadow-2xl">
              <h2 className="text-2xl font-bold mb-2">✨ Magic Extractor</h2>
              <textarea value={rawJobText} onChange={(e) => setRawJobText(e.target.value)} placeholder="Paste raw text here..." className="w-full h-64 p-4 border rounded-xl mb-4 focus:ring-2 focus:ring-blue-500 outline-none resize-none bg-slate-50" />
              <div className="flex justify-end gap-3"><button onClick={() => setIsAddModalOpen(false)} className="px-5 py-2 rounded-xl font-semibold text-slate-600 hover:bg-slate-100">Cancel</button><button onClick={handleExtractJob} disabled={processingState.id === 'extract'} className="px-5 py-2 rounded-xl font-semibold bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-400">{processingState.id === 'extract' ? "Reading... ⏳" : "Extract & Save"}</button></div>
            </div>
          </div>
        )}

        {selectedJob && (
          <div className="fixed inset-0 bg-slate-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
            <div className="bg-white rounded-3xl w-full max-w-6xl shadow-2xl flex flex-col md:flex-row overflow-hidden h-[85vh]">
              
              {/* LEFT PANEL: JOB DETAILS */}
              <div className="w-full md:w-1/2 p-8 flex flex-col border-r border-slate-100 bg-white overflow-y-auto">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900 mb-1">{selectedJob.title}</h2>
                    <p className="text-lg text-slate-600 font-medium">🏢 {selectedJob.company}</p>
                  </div>
                </div>

                <div className="mb-6 bg-blue-50 border border-blue-100 p-5 rounded-2xl flex gap-4">
                  <span className="text-3xl">🎯</span>
                  <div>
                    <h4 className="text-sm font-bold text-blue-900 mb-2">Scout AI Strategy Analysis ({selectedJob.ai_score}% Match)</h4>
                    <p className="text-sm text-blue-800 leading-relaxed">{selectedJob.ai_reasoning || "Ready for strategy."}</p>
                  </div>
                </div>

                <div className="flex-1 mb-6">
                  <button onClick={() => setShowRawDesc(!showRawDesc)} className="text-sm font-bold text-slate-600 mb-2 flex items-center gap-2 hover:text-slate-900">
                    {showRawDesc ? "▼ Hide Raw Job Description" : "▶ Show Raw Job Description"}
                  </button>
                  {showRawDesc && (
                    <div className="text-xs text-slate-600 whitespace-pre-wrap bg-slate-50 p-4 rounded-xl border border-slate-100 h-48 overflow-y-auto">
                      {selectedJob.description || "No description."}
                    </div>
                  )}
                </div>

                <div className="pt-4 border-t border-slate-100 flex flex-col gap-3">
                  <p className="text-xs text-center font-bold text-slate-400 uppercase tracking-widest mb-1">Document Generator</p>
                  <div className="flex gap-2">
                    <button onClick={() => handleDownload(selectedJob, 'cv')} disabled={processingState.id === selectedJob.id} className="flex-1 py-3 rounded-xl font-bold bg-slate-900 text-white hover:bg-slate-800 shadow-md transition-all border border-slate-900">
                      {processingState.id === selectedJob.id && processingState.type === 'cv' ? "⏳..." : "📄 Generate CV"}
                    </button>
                    <button onClick={() => handleDownload(selectedJob, 'letter')} disabled={processingState.id === selectedJob.id} className="flex-1 py-3 rounded-xl font-bold bg-white text-slate-900 border-2 border-slate-900 hover:bg-slate-50 shadow-sm transition-all">
                      {processingState.id === selectedJob.id && processingState.type === 'letter' ? "⏳..." : "✉️ Write Letter"}
                    </button>
                  </div>
                  <button onClick={() => { handleMarkAsApplied(selectedJob, null); setSelectedJob(null); }} className="w-full py-3 mt-2 rounded-xl font-bold bg-green-100 text-green-700 hover:bg-green-200 transition-all">
                    ✅ Mark as Applied
                  </button>
                </div>
              </div>

              {/* RIGHT PANEL: CHAT TABS */}
              <div className="w-full md:w-1/2 flex flex-col bg-slate-50 h-full relative">
                
                {/* Custom Tab Header */}
                <div className="flex w-full bg-white z-10 shadow-sm">
                  <button onClick={() => setActiveChatTab('strategy')} className={`flex-1 py-4 text-sm font-bold flex justify-center items-center gap-2 transition-colors ${activeChatTab === 'strategy' ? 'text-blue-700 border-b-2 border-blue-600 bg-blue-50' : 'text-slate-500 hover:bg-slate-50'}`}>
                    🏛️ Strategy Room
                  </button>
                  <button onClick={() => setActiveChatTab('interview')} className={`flex-1 py-4 text-sm font-bold flex justify-center items-center gap-2 transition-colors ${activeChatTab === 'interview' ? 'text-purple-700 border-b-2 border-purple-600 bg-purple-50' : 'text-slate-500 hover:bg-slate-50'}`}>
                    🎯 Interview Room
                  </button>
                  <button onClick={() => setSelectedJob(null)} className="px-4 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">✕</button>
                </div>

                {/* Chat Display Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  {currentMessages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
                      <span className="text-5xl mb-4">{activeChatTab === 'strategy' ? '💬' : '🎤'}</span>
                      <p className="text-sm font-medium">
                        {activeChatTab === 'strategy' 
                          ? "Discuss CV strategy with the Manager, or ask Scout for quick job details." 
                          : "Start your technical/HR interview simulation with the Manager here."}
                      </p>
                    </div>
                  ) : (
                    currentMessages.map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] p-4 rounded-2xl ${
                          msg.sender === 'user' 
                            ? 'bg-blue-600 text-white rounded-tr-none' 
                            : (activeChatTab === 'interview' || msg.isBoss) 
                              ? 'bg-slate-900 text-white rounded-tl-none border border-slate-700 shadow-lg' 
                              : 'bg-white text-slate-800 rounded-tl-none border border-slate-200 shadow-sm'
                        }`}>
                          {msg.sender === 'ai' && (activeChatTab === 'interview' || msg.isBoss) && <div className="text-[10px] font-bold uppercase tracking-wider text-purple-300 mb-2 border-b border-slate-700 pb-1">👑 Manager AI (Pro)</div>}
                          {msg.sender === 'ai' && activeChatTab === 'strategy' && !msg.isBoss && <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2 border-b border-slate-100 pb-1">⚡ Scout AI (Flash)</div>}
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {isChatLoading && (
                    <div className="flex justify-start"><div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-sm flex gap-2 items-center"><div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div><div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div><div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div></div></div>
                  )}
                  <div ref={chatEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white border-t border-slate-200">
                  <div className="flex gap-2">
                    <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()} placeholder={activeChatTab === 'strategy' ? "Type a strategy question..." : "Answer the interview question..."} className="flex-1 p-3 bg-slate-100 border-none rounded-xl focus:ring-2 focus:ring-slate-900 outline-none text-sm" />
                    <button onClick={handleSendMessage} disabled={!chatInput.trim() || isChatLoading} className={`px-5 py-3 text-white rounded-xl font-bold disabled:bg-slate-300 transition-colors ${activeChatTab === 'strategy' ? 'bg-blue-600 hover:bg-blue-700' : 'bg-purple-600 hover:bg-purple-700'}`}>Send</button>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default App;