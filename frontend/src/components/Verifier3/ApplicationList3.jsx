import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../api";

export default function ApplicationList3() {
  const [applications, setApplications] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [loadingApps, setLoadingApps] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);

  // Fetch stats on mount
  useEffect(() => {
    fetchStats();
  }, []);

  // Refetch apps on filter changes
  useEffect(() => {
    const t = setTimeout(() => fetchApplications(), 300);
    return () => clearTimeout(t);
  }, [search, status, locationFilter]);

  // Fetch dashboard statistics
  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const res = await api.get("/verifier3/statistics/");
      setStatistics(res.data);
    } catch (err) {
      console.error("Error fetching stats:", err);
      setStatistics(null);
    } finally {
      setLoadingStats(false);
    }
  };

  // Fetch applications list
  const fetchApplications = async () => {
    try {
      setLoadingApps(true);
      const params = {};
      if (search) params.search = search;
      if (status) params.application_status = status;
      if (locationFilter) params.location = locationFilter;

      const res = await api.get("/verifier3/applications/", { params });
      const now = new Date();

      // Filter approved workers visible only for 2 days
      const filtered = res.data.filter((app) => {
        if (app.application_status === "approved" && app.approved_at) {
          const approvedAt = new Date(app.approved_at);
          const diffDays = (now - approvedAt) / (1000 * 60 * 60 * 24);
          return diffDays <= 2;
        }
        return app.application_status !== "approved";
      });

      setApplications(filtered);
    } catch (err) {
      console.error("Error fetching applications:", err);
      setApplications([]);
    } finally {
      setLoadingApps(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* === Header === */}
        <div>
          <h1 className="text-3xl font-bold">Verifier 3 Dashboard</h1>
          <p className="text-gray-600">
            Final verification stage — approve or reject worker applications.
          </p>
        </div>

        {/* === Statistics === */}
        {loadingStats ? (
          <div className="text-center text-gray-500">Loading statistics...</div>
        ) : statistics ? (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded shadow text-center">
              <p className="text-sm text-gray-600">Total Reviews</p>
              <p className="text-2xl font-bold">{statistics.total_reviews ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded shadow text-center">
              <p className="text-sm text-gray-600">Approved</p>
              <p className="text-2xl font-bold text-green-600">
                {statistics.approved_reviews ?? 0}
              </p>
            </div>
            <div className="bg-white p-4 rounded shadow text-center">
              <p className="text-sm text-gray-600">Rejected</p>
              <p className="text-2xl font-bold text-red-600">
                2
              </p>
            </div>
            <div className="bg-white p-4 rounded shadow text-center">
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-2xl font-bold text-yellow-600">
               2
              </p>
            </div>
           
          </div>
        ) : (
          <div className="text-center text-gray-500">No statistics found</div>
        )}

        {/* === Filters === */}
        <div className="bg-white p-4 rounded shadow">
          <div className="flex flex-col md:flex-row gap-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email"
              className="flex-1 border p-2 rounded"
            />
            <input
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              placeholder="Filter by location"
              className="px-4 py-2 border rounded w-64"
            />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="px-4 py-2 border rounded w-48"
            >
              <option value="">All Statuses</option>
              <option value="stage3_review">Pending</option>
              <option value="approved">Approved (Last 2 days)</option>
              <option value="stage3_rejected">Rejected</option>
            </select>
            <button
              onClick={() => {
                fetchApplications();
                fetchStats();
              }}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* === Applications Table === */}
        <div className="bg-white rounded shadow overflow-x-auto">
          {loadingApps ? (
            <div className="p-8 text-center text-gray-500">
              Loading applications...
            </div>
          ) : applications.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No applications found
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Skills
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Applied
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">{app.name}</td>
                    <td className="px-6 py-4">{app.email}</td>
                    <td className="px-6 py-4 truncate max-w-xs">{app.skills}</td>
                    <td className="px-6 py-4 font-medium">
                      {app.application_status?.replace("_", " ").toUpperCase()}
                    </td>
                    <td className="px-6 py-4">
                      {new Date(app.applied_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/verifier3/applications/${app.id}`}
                        className="text-blue-600 hover:underline"
                      >
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
