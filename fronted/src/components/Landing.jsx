import { Link } from 'react-router-dom';
import { Bus, ShieldCheck, Users, ArrowRight } from 'lucide-react';

function Landing() {
  return (
    <div className="min-h-screen bg-base-200 text-base-content flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <div className="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Bus className="w-8 h-8 text-white" />
        </div>

        <h1 className="text-4xl font-extrabold mb-3">
          Matatu <span className="text-primary">Smart</span>
        </h1>

        <p className="text-base-content/65 text-base mb-8 leading-relaxed">
          Kenya's smart transit management platform. Track journeys, manage passengers, and coordinate your fleet in real time.
        </p>

        <div className="space-y-4">
          <Link
            to="/passenger"
            className="flex items-center justify-between bg-base-100 border border-base-300 rounded-2xl p-5 text-left transition hover:border-primary"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <Users className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-base font-semibold">Passenger</p>
                <p className="text-sm text-base-content/65">Scan & track your journey</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-base-content/50" />
          </Link>

          <Link
            to="/conductor"
            className="flex items-center justify-between bg-base-100 border border-base-300 rounded-2xl p-5 text-left transition hover:border-primary"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <Bus className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-base font-semibold">Conductor</p>
                <p className="text-sm text-base-content/65">Manage onboard passengers</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-base-content/50" />
          </Link>

          <Link
            to="/admin"
            className="flex items-center justify-between bg-base-100 border border-base-300 rounded-2xl p-5 text-left transition hover:border-primary"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-primary" />
              </div>
              <div>
                <p className="text-base font-semibold">Administrator</p>
                <p className="text-sm text-base-content/65">Fleet & route management</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-base-content/50" />
          </Link>
        </div>
      </div>
    </div>
  );
}

export default Landing;
