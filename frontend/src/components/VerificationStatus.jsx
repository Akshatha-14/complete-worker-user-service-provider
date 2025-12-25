import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";

export default function VerificationStatus({ userRole, currentWorkerID }) {
  const location = useLocation();
  const query = new URLSearchParams(location.search);

  // Determine which worker ID to check
  const workerId = userRole === "worker" ? currentWorkerID : query.get("workerID");

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch worker status on load or when workerId changes
  useEffect(() => {
    if (!workerId) return;
    fetchStatus();
  }, [workerId,fetchStatus]);

  const fetchStatus = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`http://localhost:8000/api/workers/${workerId}/status/`);
      if (!res.ok) throw new Error("Worker not found or API error");
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Verifier updates a verification step
  const updateStatus = async (step, value) => {
    if (userRole !== "verifier") return;

    try {
      const res = await fetch(`http://localhost:8000/api/workers/${workerId}/status/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [step]: value }),
      });
      if (!res.ok) throw new Error("Failed to update status");
      const updated = await res.json();
      setStatus(updated);
    } catch (err) {
      alert(err.message);
    }
  };

  if (!workerId) return <p>Worker ID not provided.</p>;
  if (loading) return <p>Loading...</p>;
  if (error) return <p className="text-red-500">{error}</p>;
  if (!status) return null;

  const steps = [
    { key: "is_doc_verified", label: "Document" },
    { key: "is_union_verified", label: "Union Card" },
    { key: "is_demo_verified", label: "Demo" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-r from-[#0a174e] via-[#161f39] to-[#1a213a] flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-8">
        <h2 className="text-3xl font-extrabold text-blue-900 mb-6 text-center">
          Worker Verification Status
        </h2>

        <p className="text-lg mb-4">Worker ID: {workerId}</p>

        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.key} className="flex items-center justify-between">
              <span>{step.label} Verified:</span>
              <span className={status[step.key] ? "text-green-600 font-semibold" : "text-red-600 font-semibold"}>
                {status[step.key] ? "✅ Yes" : "❌ No"}
              </span>

              {/* Only verifiers see approve/reject buttons */}
              {userRole === "verifier" && (
                <div className="space-x-2">
                  <button
                    className="bg-green-600 text-white px-2 py-1 rounded"
                    onClick={() => updateStatus(step.key, true)}
                  >
                    Approve
                  </button>
                  <button
                    className="bg-red-600 text-white px-2 py-1 rounded"
                    onClick={() => updateStatus(step.key, false)}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Next step / progress message */}
        <div className="mt-4 text-blue-900 font-semibold">
          {status.is_doc_verified && !status.is_union_verified && "Next Step: Union Card Verification"}
          {status.is_doc_verified && status.is_union_verified && !status.is_demo_verified && "Next Step: Demo Verification"}
          {status.is_doc_verified && status.is_union_verified && status.is_demo_verified && "🎉 Fully Verified!"}
        </div>
      </div>
    </div>
  );
}
