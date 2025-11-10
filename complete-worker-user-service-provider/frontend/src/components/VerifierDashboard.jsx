import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function VerifierDashboard() {
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    fetchWorkers();
  }, []);

  const fetchWorkers = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/api/workers/");
      if (!res.ok) throw new Error("Failed to fetch workers");
      const data = await res.json();
      setWorkers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyClick = (workerID) => {
    navigate(`/status?workerID=${workerID}`);
  };

  if (loading) return <p>Loading workers...</p>;
  if (error) return <p className="text-red-500">{error}</p>;

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h2 className="text-3xl font-bold mb-6 text-center text-blue-900">Verifier Dashboard</h2>
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-blue-200">
            <th className="border px-4 py-2">Worker ID</th>
            <th className="border px-4 py-2">Name</th>
            <th className="border px-4 py-2">Email</th>
            <th className="border px-4 py-2">Verification Status</th>
            <th className="border px-4 py-2">Action</th>
          </tr>
        </thead>
        <tbody>
          {workers.map((worker) => (
            <tr key={worker.id} className="text-center">
              <td className="border px-4 py-2">{worker.id}</td>
              <td className="border px-4 py-2">{worker.name}</td>
              <td className="border px-4 py-2">{worker.email}</td>
              <td className="border px-4 py-2">
                {worker.is_doc_verified && worker.is_union_verified && worker.is_demo_verified
                  ? "✅ Fully Verified"
                  : "❌ Pending"}
              </td>
              <td className="border px-4 py-2">
                <button
                  className="bg-blue-700 text-white px-3 py-1 rounded hover:bg-blue-800"
                  onClick={() => handleVerifyClick(worker.id)}
                >
                  Verify
                </button>
              </td>
            </tr>
          ))}
          {workers.length === 0 && (
            <tr>
              <td colSpan="5" className="text-center py-4">
                No workers found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
