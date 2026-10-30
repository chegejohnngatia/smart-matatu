
import { useCallback, useEffect, useState } from "react";
import {
  Wallet,
  CircleDollarSign,
  Clock3,
  Plus,
  CheckCircle2,
  History,
  UserRound,
  CalendarClock,
  AlertCircle,
  Check,
  LoaderCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

const MATATU_ID =
  import.meta.env.VITE_CONDUCTOR_MATATU_ID || "1";

export default function ConductorBalances() {
  const [pendingBalances, setPendingBalances] = useState([]);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState([]);
  const [history, setHistory] = useState([]);
  const [passengerId, setPassengerId] = useState("");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [payingId, setPayingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showHistory, setShowHistory] = useState(false);

  const loadBalances = useCallback(async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conductor/balances/${MATATU_ID}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to load balances.");
      }

      setPendingBalances(data.pending_balances || []);
setAwaitingConfirmation(data.awaiting_confirmation || []);
setHistory(data.history || []);
      setError("");
    } catch (err) {
      setError(err.message || "Could not connect to the server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isLoading = false;

    const refreshBalances = async () => {
      if (isLoading) return;

      isLoading = true;

      try {
        await loadBalances();
      } finally {
        isLoading = false;
      }
    };

    refreshBalances();

    const intervalId = window.setInterval(refreshBalances, 1000);

    return () => window.clearInterval(intervalId);
  }, [loadBalances]);

  async function handleAddBalance(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!passengerId.trim() || !amount.trim()) {
      setError("Enter the passenger ID and amount owed.");
      return;
    }

    const numericAmount = Number(amount);

    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError("Enter a valid amount greater than zero.");
      return;
    }

    try {
      setSaving(true);

      const response = await fetch(
        `${API_BASE_URL}/api/conductor/balances/${MATATU_ID}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            passenger_id: passengerId.trim(),
            amount: numericAmount,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to add balance.");
      }

      setPassengerId("");
      setAmount("");
      setMessage(
        `KSh ${Number(data.amount).toLocaleString()} added for ${data.passenger_id}.`
      );

      await loadBalances();
    } catch (err) {
      setError(err.message || "Could not add the balance.");
    } finally {
      setSaving(false);
    }
  }

  async function handleMarkPaid(balance) {
    const confirmed = window.confirm(
      `Confirm that you have returned KSh ${Number(balance.amount).toLocaleString()} to ${balance.passenger_id}?`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      setPayingId(balance.balance_id);

      const response = await fetch(
        `${API_BASE_URL}/api/conductor/balances/${balance.balance_id}/pay`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ matatu_id: Number(MATATU_ID) }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update balance.");
      }

      setMessage(`Balance for ${balance.passenger_id} marked as paid.`);
      await loadBalances();
    } catch (err) {
      setError(err.message || "Could not update the balance.");
    } finally {
      setPayingId(null);
    }
  }

  function formatAmount(value) {
    return `KSh ${Number(value).toLocaleString("en-KE", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })}`;
  }

  function formatDate(value) {
    if (!value) return "Not recorded";

    const date = new Date(String(value).replace(" ", "T"));

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleString("en-KE", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const totalPending = pendingBalances.reduce(
    (total, balance) => total + Number(balance.amount || 0),
    0
  );

  if (loading) {
    return (
      <div className="flex min-h-72 items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <LoaderCircle
            size={30}
            className="animate-spin text-emerald-600"
          />
          <p className="text-sm font-medium">
            Loading balance records...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Page heading */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-700">
            <Wallet size={17} />
            Conductor workspace
          </div>

          <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Passenger Balances
          </h2>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Track change owed to passengers and keep a record of completed
            repayments for your vehicle.
          </p>
        </div>
      </div>

      

      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-500">
                Outstanding amount
              </p>
              <p className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
                {formatAmount(totalPending)}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Total change still owed
              </p>
            </div>

            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <CircleDollarSign size={23} />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-500">
                Pending repayments
              </p>
              <p className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
                {pendingBalances.length}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Balances awaiting repayment
              </p>
            </div>

            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
              <Clock3 size={23} />
            </div>
          </div>
        </div>
      </div>

      {/* Add balance */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-5 sm:px-6">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
            <Plus size={21} />
          </div>

          <div>
            <h3 className="font-bold text-slate-900">
              Record a new balance
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Enter the passenger ID and the amount to return.
            </p>
          </div>
        </div>

        
    <form
      onSubmit={handleAddBalance}
      className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-[1fr_1fr_auto] lg:items-end"
    >
      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 sm:col-span-2 lg:col-span-3"
        >
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {message && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 sm:col-span-2 lg:col-span-3"
        >
          <CheckCircle2 size={19} className="mt-0.5 shrink-0" />
          <p>{message}</p>
        </div>
      )}

          <div>
            <label
              htmlFor="passenger-id"
              className="mb-2 block text-sm font-semibold text-slate-700"
            >
              Passenger ID
            </label>

            <div className="relative">
              <UserRound
                size={18}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
              />

              <input
                id="passenger-id"
                type="text"
                value={passengerId}
                onChange={(event) => setPassengerId(event.target.value)}
                placeholder="e.g. P001"
                required
                className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-10 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="balance-amount"
              className="mb-2 block text-sm font-semibold text-slate-700"
            >
              Amount owed (KSh)
            </label>

            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-400">
                KSh
              </span>

              <input
                id="balance-amount"
                type="number"
                min="0.01"
                step="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                placeholder="e.g. 50"
                required
                className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-14 pr-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? (
              <LoaderCircle size={17} className="animate-spin" />
            ) : (
              <Plus size={17} />
            )}
            {saving ? "Adding balance..." : "Add balance"}
          </button>
        </form>
      </section>

      {/* Pending balances */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <Clock3 size={21} />
            </div>

            <div>
              <h3 className="font-bold text-slate-900">
                Pending balances
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Amounts that still need to be returned.
              </p>
            </div>
          </div>

          <span className="inline-flex w-fit items-center rounded-full bg-amber-50 px-3 py-1.5 text-xs font-bold text-amber-700 ring-1 ring-inset ring-amber-200">
            {pendingBalances.length} pending
          </span>
        </div>

        {pendingBalances.length === 0 ? (
          <div className="flex flex-col items-center px-5 py-12 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
              <CheckCircle2 size={28} />
            </div>

            <h4 className="mt-4 font-semibold text-slate-900">
              No pending balances
            </h4>

            <p className="mt-1 max-w-sm text-sm leading-6 text-slate-500">
              There are currently no outstanding repayments recorded for
              this vehicle.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {pendingBalances.map((balance) => (
              <article
                key={balance.balance_id}
                className="flex flex-col gap-4 p-5 transition hover:bg-slate-50/70 sm:flex-row sm:items-center sm:justify-between sm:px-6"
              >
                <div className="flex min-w-0 items-start gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
                    <UserRound size={21} />
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-bold text-slate-900">
                        {balance.passenger_id}
                      </h4>

                      <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
                        Pending
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500">
                      <span className="inline-flex items-center gap-1.5">
                        <CalendarClock size={14} />
                        Recorded {formatDate(balance.created_at)}
                      </span>

                      {balance.journey_id != null && (
                        <span>Journey #{balance.journey_id}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 sm:border-0 sm:pt-0">
                  <div className="sm:text-right">
                    <p className="text-xs font-medium text-slate-500">
                      Amount owed
                    </p>
                    <p className="mt-1 text-xl font-bold text-slate-900">
                      {formatAmount(balance.amount)}
                    </p>
                  </div>

                  <button
                    type="button"
                    disabled={payingId === balance.balance_id}
                    onClick={() => handleMarkPaid(balance)}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {payingId === balance.balance_id ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <Check size={16} />
                    )}
                    {payingId === balance.balance_id
                      ? "Updating..."
                      : "Mark as paid"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      
      {/* Awaiting Passenger Confirmation */}
      <section className="overflow-hidden rounded-2xl border border-amber-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 border-b border-amber-100 bg-amber-50 p-5 sm:px-6">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
            <CalendarClock size={21} />
          </span>

          <div>
            <h2 className="font-bold text-slate-900">
              Awaiting Passenger Confirmation
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Repayments recorded by the conductor that passengers have not yet confirmed.
            </p>
          </div>

          <span className="ml-auto rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-800">
            {awaitingConfirmation.length}
          </span>
        </div>

        {awaitingConfirmation.length === 0 ? (
          <div className="p-8 text-center">
            <p className="font-medium text-slate-700">
              No repayments awaiting confirmation
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Repayments recorded by the conductor will appear here until the passenger confirms receipt.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {awaitingConfirmation.map((balance) => (
              <article
                key={balance.balance_id}
                className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-slate-900">
                      Passenger {balance.passenger_id}
                    </h3>

                    <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
                      Awaiting confirmation
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500">
                    <span className="inline-flex items-center gap-1.5">
                      <CalendarClock size={14} />
                      Repayment recorded {formatDate(balance.paid_at)}
                    </span>

                    {balance.journey_id != null && (
                      <span>Journey #{balance.journey_id}</span>
                    )}
                  </div>
                </div>

                <div className="sm:text-right">
                  <p className="text-xs font-medium text-slate-500">
                    Amount recorded
                  </p>
                  <p className="mt-1 text-xl font-bold text-slate-900">
                    {formatAmount(balance.amount)}
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Paid history */}

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <button
          type="button"
          onClick={() => setShowHistory((current) => !current)}
          aria-expanded={showHistory}
          className="flex w-full items-center justify-between gap-4 p-5 text-left transition hover:bg-slate-50 sm:px-6"
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
              <History size={21} />
            </span>

            <span>
              <span className="block font-bold text-slate-900">
                Paid history
              </span>
              <span className="mt-1 block text-sm text-slate-500">
                Review completed repayments.
              </span>
            </span>
          </span>

          <span className="flex shrink-0 items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-600">
              {history.length} records
            </span>

            {showHistory ? (
              <ChevronUp size={18} className="text-slate-400" />
            ) : (
              <ChevronDown size={18} className="text-slate-400" />
            )}
          </span>
        </button>

        {showHistory && (
          <div className="border-t border-slate-100">
            {history.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-slate-500">
                No paid balances have been recorded yet.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {history.map((balance) => (
                  <article
                    key={balance.balance_id}
                    className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-700">
                        <CheckCircle2 size={20} />
                      </div>

                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="font-semibold text-slate-900">
                            {balance.passenger_id}
                          </h4>

                          <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                            Paid
                          </span>
                        </div>

                        <p className="mt-1 text-xs text-slate-500">
                          Paid {formatDate(balance.paid_at)}
                        </p>

                        {balance.journey_id != null && (
                          <p className="mt-1 text-xs text-slate-500">
                            Journey #{balance.journey_id}
                          </p>
                        )}
                      </div>
                    </div>

                    <p className="text-lg font-bold text-emerald-700 sm:text-right">
                      {formatAmount(balance.amount)}
                    </p>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
