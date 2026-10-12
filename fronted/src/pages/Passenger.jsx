import { useState, useEffect } from 'react';
import { Bus, History, ChevronUp, ChevronDown } from 'lucide-react';

export default function Passenger() {
  const [dest, setDest] = useState('');
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(false);
  const [trip, setTrip] = useState({ plate: '', route: '', code: '', stages: [] });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetch('/api/passenger/trip-info').then(r => r.json()).then(d => { setTrip(d); setConnected(true); }).catch(() => {});
    fetch('/api/passenger/history').then(r => r.json()).then(d => Array.isArray(d) && setHistory(d)).catch(() => {});
  }, []);

  const register = async (e) => {
    e.preventDefault();
    if (!dest) return;
    const res = await fetch('/api/passenger/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ destination: dest })
    });
    if (res.ok) {
      const item = await res.json();
      setHistory([item, ...history]);
      setDest('');
      setOpen(true);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-4 flex flex-col justify-between pb-20">
      <div className="max-w-md w-full space-y-4 mx-auto">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex justify-between items-center">
          <span className="font-bold flex items-center gap-2"><Bus className="w-5 text-blue-500"/> Matatu Smart</span>
          <span className={`text-xs px-2.5 py-1 rounded-full ${connected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>

        <div className="grid grid-cols-3 bg-slate-900 border border-slate-800 rounded-xl p-3 text-center text-sm font-bold">
          <div><p className="text-[10px] text-slate-500">PLATE</p>{trip.plate || '---'}</div>
          <div className="border-x border-slate-800"><p className="text-[10px] text-slate-500">ROUTE</p>{trip.route || '---'}</div>
          <div><p className="text-[10px] text-slate-500">TRIP</p><span className="text-blue-400">{trip.code || '---'}</span></div>
        </div>

        <form onSubmit={register} className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
          <h2 className="text-sm font-semibold">Select Destination</h2>
          <select value={dest} onChange={e => setDest(e.target.value)} disabled={!connected} className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm disabled:opacity-50" required>
            <option value="" disabled>{connected ? 'Select stage...' : 'Please connect to backend'}</option>
            {trip.stages?.map((s, i) => <option key={i} value={s.name || s}>{s.name || s}</option>)}
          </select>
          <button disabled={!connected} className="w-full bg-blue-600 hover:bg-blue-500 py-2.5 rounded-lg text-sm font-medium disabled:opacity-50">Register Journey</button>
        </form>
      </div>

      <div className="fixed bottom-0 left-0 right-0 flex justify-center p-3 bg-slate-950/80">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-xl">
          <button onClick={() => setOpen(!open)} className="w-full p-3 flex justify-between items-center text-sm">
            <span className="flex items-center gap-2"><History className="w-4 text-slate-400"/> History ({history.length})</span>
            {open ? <ChevronDown className="w-4"/> : <ChevronUp className="w-4"/>}
          </button>
          {open && (
            <div className="p-3 pt-0 space-y-2 max-h-48 overflow-y-auto border-t border-slate-800 text-sm">
              {!connected ? (
                <p className="text-xs text-amber-400 text-center py-3">Please connect to backend</p>
              ) : history.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-3">No history yet.</p>
              ) : (
                history.map((item, i) => (
                  <div key={i} className="flex justify-between bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                    <span>{item.destination}</span>
                    <span className="text-blue-400">{item.status}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}