import {Bus,ShieldCheck,Users,ArrowRight} from 'lucide-react';



function Landing(){
    return(
        
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        
<div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
  <Bus className="w-8 h-8 text-white" />
</div>


<h1 className="text-4xl font-extrabold mb-3 text-white">
  Matatu <span className="text-blue-500">Smart</span>
</h1>


<p className="text-slate-400 text-base mb-8 leading-relaxed">
  Kenya's smart transit management platform. Track journeys, manage passengers, and coordinate your fleet in real time.
</p>
 <div className="space-y-4">
  
  <a
    href="/passenger"
    className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-2xl p-5 text-left"
  >
    <div className="flex items-center gap-4">
      <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
        <Users className="w-6 h-6 text-blue-400" />
      </div>
      <div>
        <p className="text-base font-semibold">Passenger</p>
        <p className="text-sm text-slate-400">Scan & track your journey</p>
      </div>
    </div>
    <ArrowRight className="w-5 h-5 text-slate-500" />
  </a>

  
  <a
    href="/conductor"
    className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-2xl p-5 text-left"
  >
    <div className="flex items-center gap-4">
      <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center">
        <Bus className="w-6 h-6 text-emerald-400" />
      </div>
      <div>
        <p className="text-base font-semibold">Conductor</p>
        <p className="text-sm text-slate-400">Manage onboard passengers</p>
      </div>
    </div>
    <ArrowRight className="w-5 h-5 text-slate-500" />
  </a>

  
  <a
    href="/admin"
    className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-2xl p-5 text-left"
  >
    <div className="flex items-center gap-4">
      <div className="w-12 h-12 bg-amber-500/10 rounded-xl flex items-center justify-center">
        <ShieldCheck className="w-6 h-6 text-amber-400" />
      </div>
      <div>
        <p className="text-base font-semibold">Administrator</p>
        <p className="text-sm text-slate-400">Fleet & route management</p>
      </div>
    </div>
    <ArrowRight className="w-5 h-5 text-slate-500" />
  </a>
</div>
      </div>
    </div>

    
    );

}
export default Landing;