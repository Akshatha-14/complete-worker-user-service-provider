// src/components/Verifier2/ApplicationList2.jsx
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api';

export default function ApplicationList2() {
  const [applications, setApplications] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [loadingApps, setLoadingApps] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    // debounce search/filter slightly
    const t = setTimeout(() => fetchApplications(), 200);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, statusFilter, locationFilter]);

  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const res = await api.get('/verifier2/reviews/statistics/');
      setStatistics(res.data);
    } catch (err) {
      console.error('Failed to fetch verifier2 stats', err);
      setStatistics(null);
    } finally {
      setLoadingStats(false);
    }
  };

  const fetchApplications = async () => {
    try {
      setLoadingApps(true);
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (statusFilter) params.application_status = statusFilter;
      if (locationFilter) params.location = locationFilter;

      const res = await api.get('/verifier2/applications/', { params });
      setApplications(res.data);
    } catch (err) {
      console.error('Failed to fetch verifier2 apps', err);
      setApplications([]);
    } finally {
      setLoadingApps(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Verifier 2 Dashboard</h1>
          <p className="text-gray-600">Identity & Union Verification (Stage 2)</p>
        </div>

        {statistics && (
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-600">Total Reviewed</p>
              <p className="text-2xl font-bold text-blue-600">{statistics.total_reviewed ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-600">Approved</p>
              <p className="text-2xl font-bold text-green-600">{statistics.approved ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-600">Rejected</p>
              <p className="text-2xl font-bold text-red-600">{statistics.rejected ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-2xl font-bold text-yellow-600">{statistics.pending ?? 0}</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <p className="text-sm text-gray-600">Approval Rate</p>
              <p className="text-2xl font-bold text-purple-600">{statistics.approval_rate ?? 0}%</p>
            </div>
          </div>
        )}

        <div className="bg-white p-4 rounded shadow">
          <div className="flex flex-col md:flex-row gap-3">
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 px-4 py-2 border rounded"
            />
            <input
              type="text"
              placeholder="Filter by location..."
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              className="px-4 py-2 border rounded w-64"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-4 py-2 border rounded w-48"
            >
              <option value="">All Statuses</option>
              <option value="stage2_review">Pending</option>
              <option value="approved">Approved</option>
              <option value="stage2_rejected">Rejected</option>
            </select>
            <button
              onClick={() => { fetchApplications(); fetchStats(); }}
              className="px-6 py-2 bg-blue-600 text-white rounded"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="bg-white rounded shadow overflow-x-auto">
          {loadingApps ? (
            <div className="p-8 text-center">Loading applications...</div>
          ) : applications.length === 0 ? (
            <div className="p-8 text-center text-gray-600">No applications found</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applicant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Skills</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Applied</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium">{app.name}</div>
                      <div className="text-xs text-gray-500">ID: #{app.id}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">{app.email}</div>
                      <div className="text-sm text-gray-500">{app.phone}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">{app.address || 'N/A'}</div>
                      {app.latitude && app.longitude && (
                        <div className="text-xs text-gray-400">📍 {app.latitude}, {app.longitude}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm truncate max-w-xs">{app.skills}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                        { (app.application_status || 'stage2_review').replace('_', ' ').toUpperCase() }
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(app.applied_at).toLocaleDateString()}
                      <div className="text-xs text-gray-400">{app.days_pending} days ago</div>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium">
                      <Link to={`/verifier2/applications/${app.id}`} className="text-blue-600 hover:underline">Review →</Link>
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
