
import { useEffect, useState } from 'react'
import {
  AlertCircle,
  RefreshCw,
  QrCode,
  Bus,
  MapPin,
  Printer,
  Copy,
  CheckCircle,
} from 'lucide-react'
import { getConductorQRCode } from '../../services/conductorApi'

export default function ConductorQRCode() {
  const [qrData, setQrData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  async function loadQRCode() {
    try {
      setLoading(true)
      setError('')

      const data = await getConductorQRCode()
      setQrData(data)
    } catch (err) {
      setError(err.message || 'Could not generate the QR code.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQRCode()
  }, [])

  async function copyURL() {
    if (!qrData?.qr_url) return

    try {
      await navigator.clipboard.writeText(qrData.qr_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Could not copy the passenger URL. Please copy it manually.')
    }
  }

  function printQRCode() {
    if (!qrData?.qr_image) return

    const printWindow = window.open('', '_blank')

    if (!printWindow) {
      setError('Please allow pop-ups to print the QR code.')
      return
    }

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Matatu Passenger QR Code</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              text-align: center;
              padding: 35px;
              color: #0f172a;
            }
            img {
              width: 320px;
              height: 320px;
              object-fit: contain;
            }
            h1 { font-size: 24px; }
            p { font-size: 16px; }
            .url {
              overflow-wrap: anywhere;
              font-size: 12px;
            }
            @media print {
              body { padding: 10px; }
            }
          </style>
        </head>
        <body>
          <h1>Smart Matatu</h1>
          <h2>${qrData.matatu.registration_number}</h2>
          <p>Scan after boarding to select your destination.</p>
          <img src="${qrData.qr_image}" alt="Passenger QR Code" />
          <p class="url">${qrData.qr_url}</p>
          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `)

    printWindow.document.close()
  }

  return (
    <main className="mx-auto w-full max-w-5xl p-5 sm:p-8">
      <header className="mb-8">
        <h1 className="flex items-center gap-3 text-2xl font-bold text-slate-900">
          <QrCode className="text-emerald-600" size={28} />
          Matatu Passenger QR Code
        </h1>

        <p className="mt-1 text-slate-600">
          Generate and print the QR code passengers scan after boarding
          your assigned matatu.
        </p>
      </header>

      {loading && (
        <p className="text-slate-600">Generating your QR code...</p>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} />
            <p>{error}</p>
          </div>

          <button
            type="button"
            onClick={loadQRCode}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-white hover:bg-emerald-700"
          >
            <RefreshCw size={16} />
            Try again
          </button>
        </div>
      )}

      {!loading && !error && qrData && (
        <>
          <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-start gap-3">
              <Bus className="mt-1 text-emerald-600" size={25} />

              <div>
                <h2 className="font-semibold text-slate-800">
                  Assigned Matatu
                </h2>

                <p className="mt-1 text-xl font-bold text-slate-900">
                  {qrData.matatu.registration_number}
                </p>

                <p className="mt-1 flex items-center gap-2 text-slate-600">
                  <MapPin size={16} />
                  Route: {qrData.matatu.route_name}
                </p>
              </div>
            </div>
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="flex flex-col items-center rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Passenger QR Code
              </h2>

              <p className="mt-1 text-center text-sm text-slate-600">
                Scan this code to open the passenger destination page.
              </p>

              <div className="mt-5 rounded-xl border border-slate-200 bg-white p-3">
                <img
                  src={qrData.qr_image}
                  alt="Passenger QR Code"
                  className="h-64 w-64 object-contain"
                />
              </div>

              <button
                type="button"
                onClick={printQRCode}
                className="mt-5 inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-3 font-semibold text-white transition hover:bg-emerald-700"
              >
                <Printer size={19} />
                Print QR Code
              </button>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Passenger Entry Link
              </h2>

              <p className="mt-2 text-sm text-slate-600">
                This is the address stored inside your QR code.
              </p>

              <div className="mt-4 break-all rounded-lg bg-slate-100 p-4 text-sm text-slate-800">
                {qrData.qr_url}
              </div>

              <button
                type="button"
                onClick={copyURL}
                className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 font-medium text-slate-700 transition hover:bg-slate-50"
              >
                {copied ? (
                  <>
                    <CheckCircle size={17} className="text-emerald-600" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy size={17} />
                    Copy passenger link
                  </>
                )}
              </button>

              <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <h3 className="font-semibold text-emerald-900">
                  How to use this QR code
                </h3>

                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-emerald-900">
                  <li>Print the QR code.</li>
                  <li>Attach it behind the passenger seats.</li>
                  <li>Passengers scan it after boarding.</li>
                  <li>Passengers select their destination.</li>
                </ol>
              </div>

              <p className="mt-4 text-xs text-slate-500">
                The QR code identifies your assigned matatu. It does not
                authenticate passengers or replace passenger access
                credentials.
              </p>
            </div>
          </section>
        </>
      )}
    </main>
  )
}
