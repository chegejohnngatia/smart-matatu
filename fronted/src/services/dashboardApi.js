/* Demo data boundary. Replace this with actual FastAPI responses when endpoints are ready. */
export const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

export const demoDashboardData = {
  stats: { matatus: 128, activeTrips: 34, users: 1248, availableVehicles: 76, maintenanceVehicles: 8 },
  matatus: [
    { id:'M001', name:'Toyota Hiace', type:'14-seater minibus', registration:'KDA 214A', route:'Kisii – Siaya', capacity:14, crew:'J. Ochieng / P. Otieno', status:'Available' },
    { id:'M002', name:'Toyota Hiace', type:'14-seater minibus', registration:'KDB 483C', route:'Siaya – Kisumu', capacity:14, crew:'M. Onyango / A. Auma', status:'On trip' },
    { id:'M003', name:'Nissan Caravan', type:'14-seater minibus', registration:'KDC 092D', route:'Kisii – Kisumu', capacity:14, crew:'D. Ouma / C. Akinyi', status:'Maintenance' },
    { id:'M004', name:'Toyota Hiace', type:'14-seater minibus', registration:'KDE 771B', route:'Siaya – Bondo', capacity:14, crew:'F. Otieno / S. Adhiambo', status:'Available' },
    { id:'M005', name:'Nissan Caravan', type:'25-seater minibus', registration:'KDF 305E', route:'Kisumu – Siaya', capacity:25, crew:'R. Onyango / B. Auma', status:'On trip' },
    { id:'M006', name:'Toyota Hiace', type:'14-seater minibus', registration:'KDG 612F', route:'Kisii – Siaya', capacity:14, crew:'E. Ouma / L. Atieno', status:'Available' }
  ],
  routes: [
    { id:'R001', name:'Kisii – Siaya', origin:'Kisii', destination:'Siaya', distance:'115 km', stages:8, vehicles:18, status:'Active' },
    { id:'R002', name:'Siaya – Kisumu', origin:'Siaya', destination:'Kisumu', distance:'75 km', stages:6, vehicles:12, status:'Active' },
    { id:'R003', name:'Kisii – Kisumu', origin:'Kisii', destination:'Kisumu', distance:'121 km', stages:9, vehicles:15, status:'Active' },
    { id:'R004', name:'Siaya – Bondo', origin:'Siaya', destination:'Bondo', distance:'26 km', stages:4, vehicles:7, status:'Active' },
    { id:'R005', name:'Kisumu – Kakamega', origin:'Kisumu', destination:'Kakamega', distance:'52 km', stages:5, vehicles:9, status:'Inactive' }
  ],
  trips: [
    { id:'TR-2026-1042', registration:'KDB 483C', route:'Siaya – Kisumu', driver:'M. Onyango', progress:68, distanceTravelled:'51 km', distanceRemaining:'24 km', eta:'32 min', gpsUpdated:'20 sec ago', status:'In progress' },
    { id:'TR-2026-1043', registration:'KDF 305E', route:'Kisumu – Siaya', driver:'R. Onyango', progress:42, distanceTravelled:'31 km', distanceRemaining:'44 km', eta:'54 min', gpsUpdated:'35 sec ago', status:'In progress' },
    { id:'TR-2026-1044', registration:'KDG 612F', route:'Kisii – Siaya', driver:'E. Ouma', progress:23, distanceTravelled:'26 km', distanceRemaining:'89 km', eta:'1 hr 42 min', gpsUpdated:'18 sec ago', status:'In progress' },
    { id:'TR-2026-1045', registration:'KDA 214A', route:'Kisii – Siaya', driver:'J. Ochieng', progress:100, distanceTravelled:'115 km', distanceRemaining:'0 km', eta:'Arrived', gpsUpdated:'4 min ago', status:'Completed' },
    { id:'TR-2026-1046', registration:'KDE 771B', route:'Siaya – Bondo', driver:'F. Otieno', progress:0, distanceTravelled:'0 km', distanceRemaining:'26 km', eta:'Pending', gpsUpdated:'—', status:'Scheduled' }
  ],
  users: [
    { id:'U001', name:'Mary Akinyi', email:'mary.akin@example.test', role:'Passenger', joined:'08 Oct 2026', status:'Active' },
    { id:'U002', name:'Martin Onyango', email:'martin.onyango@example.test', role:'Conductor', joined:'06 Oct 2026', status:'Active' },
    { id:'U003', name:'David Ouma', email:'david.ouma@example.test', role:'Driver', joined:'04 Oct 2026', status:'Active' },
    { id:'U004', name:'Admin User', email:'admin@example.test', role:'Admin', joined:'01 Oct 2026', status:'Active' },
    { id:'U005', name:'Peter Otieno', email:'peter.otieno@example.test', role:'Passenger', joined:'29 Sep 2026', status:'Suspended' },
    { id:'U006', name:'Catherine Auma', email:'catherine.auma@example.test', role:'Conductor', joined:'25 Sep 2026', status:'Active' }
  ],
  alerts: [
    { id:'A001', level:'warning', title:'Vehicle maintenance due', description:'KDC 092D is marked for maintenance.', time:'12 min ago' },
    { id:'A002', level:'danger', title:'GPS signal delayed', description:'One trip has not reported a recent location.', time:'18 min ago' },
    { id:'A003', level:'info', title:'New route awaiting review', description:'A proposed corridor needs administrator review.', time:'1 hr ago' }
  ]
};

// Proposed endpoint only: confirm its path and response shape with the backend team.
export async function getDashboardData() {
  const response = await fetch(`${API_URL}/admin/dashboard`);
  if (!response.ok) throw new Error(`Dashboard API failed: ${response.status}`);
  return response.json();
}
