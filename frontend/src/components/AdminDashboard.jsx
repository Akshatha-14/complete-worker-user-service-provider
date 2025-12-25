// src/components/AdminDashboard.js
import React, { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import { motion } from "framer-motion";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from "chart.js";
import api from "../api";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const AdminDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("main");
  const [pageLoading, setPageLoading] = useState(false);
  const [users, setUsers] = useState([]);
  const [workers, setWorkers] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [userFilter, setUserFilter] = useState("");
  const [workerFilter, setWorkerFilter] = useState("");
  const [bookingFilter, setBookingFilter] = useState("");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await api.get("/admin/dashboard/");
        setDashboardData(res.data);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  const fetchUsers = async () => {
    setPageLoading(true);
    try {
      const res = await api.get("/admin/users/");
      setUsers(res.data.users || []);
    } catch (err) {
      console.error(err);
      setUsers([]);
    } finally {
      setPageLoading(false);
    }
  };

  const fetchWorkers = async () => {
    setPageLoading(true);
    try {
      const res = await api.get("/admin/workers/");
      setWorkers(res.data.workers || []);
    } catch (err) {
      console.error(err);
      setWorkers([]);
    } finally {
      setPageLoading(false);
    }
  };

  const fetchBookings = async () => {
    setPageLoading(true);
    try {
      const res = await api.get("/admin/bookings/");
      setBookings(res.data.bookings || []);
    } catch (err) {
      console.error(err);
      setBookings([]);
    } finally {
      setPageLoading(false);
    }
  };

  // -----------------------------
  // Filtered Data
  // -----------------------------
  const filteredUsers = users.filter(u =>
    u.name?.toLowerCase().includes(userFilter.toLowerCase()) ||
    u.email?.toLowerCase().includes(userFilter.toLowerCase())
  );

  const filteredWorkers = workers.filter(w =>
    w.name?.toLowerCase().includes(workerFilter.toLowerCase()) ||
    w.service?.service_type?.toLowerCase().includes(workerFilter.toLowerCase())
  );

  const filteredBookings = bookings.filter(b =>
    b.user?.name?.toLowerCase().includes(bookingFilter.toLowerCase()) ||
    b.worker?.user?.name?.toLowerCase().includes(bookingFilter.toLowerCase()) ||
    b.service?.service_type?.toLowerCase().includes(bookingFilter.toLowerCase())
  );

  // -----------------------------
  // Subpage Views
  // -----------------------------
  const UsersView = () => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-4">
      <div className="flex justify-between items-center mb-4">
        <button onClick={() => setView("main")} className="text-white bg-gradient-to-r from-blue-800 to-blue-600 px-4 py-2 rounded shadow hover:scale-105 transition">
          &larr; Back
        </button>
        <input
          type="text"
          placeholder="Filter users..."
          value={userFilter}
          onChange={e => setUserFilter(e.target.value)}
          className="px-3 py-2 rounded shadow border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <h2 className="text-2xl font-bold text-blue-900 mb-4">Users</h2>
      {pageLoading ? <div className="text-blue-700">Loading Users...</div> :
        filteredUsers.length === 0 ? <div className="text-blue-700">No Users Found</div> :
          <div className="overflow-x-auto rounded-lg shadow-lg">
            <table className="w-full table-auto border-collapse bg-gradient-to-r from-blue-100 to-blue-50">
              <thead className="bg-blue-900 text-white">
                <tr>
                  <th className="border px-4 py-2">ID</th>
                  <th className="border px-4 py-2">Name</th>
                  <th className="border px-4 py-2">Email</th>
                  <th className="border px-4 py-2">Phone</th>
                  <th className="border px-4 py-2">Joined At</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(u => (
                  <tr key={u.id} className="hover:bg-blue-200 transition-colors">
                    <td className="border px-4 py-2">{u.id}</td>
                    <td className="border px-4 py-2">{u.name || "-"}</td>
                    <td className="border px-4 py-2">{u.email || "-"}</td>
                    <td className="border px-4 py-2">{u.phone || "-"}</td>
                    <td className="border px-4 py-2">{u.date_joined || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
      }
    </motion.div>
  );

  const WorkersView = () => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-4">
      <div className="flex justify-between items-center mb-4">
        <button onClick={() => setView("main")} className="text-white bg-gradient-to-r from-blue-800 to-blue-600 px-4 py-2 rounded shadow hover:scale-105 transition">
          &larr; Back
        </button>
        <input
          type="text"
          placeholder="Filter workers..."
          value={workerFilter}
          onChange={e => setWorkerFilter(e.target.value)}
          className="px-3 py-2 rounded shadow border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <h2 className="text-2xl font-bold text-blue-900 mb-4">Workers</h2>
      {pageLoading ? <div className="text-blue-700">Loading Workers...</div> :
        filteredWorkers.length === 0 ? <div className="text-blue-700">No Workers Found</div> :
          <div className="overflow-x-auto rounded-lg shadow-lg">
            <table className="w-full table-auto border-collapse bg-gradient-to-r from-blue-100 to-blue-50">
              <thead className="bg-blue-900 text-white">
                <tr>
                  <th className="border px-4 py-2">ID</th>
                  <th className="border px-4 py-2">Name</th>
                  <th className="border px-4 py-2">Service</th>
                  <th className="border px-4 py-2">Available</th>
                  <th className="border px-4 py-2">Cost/Hour</th>
                  <th className="border px-4 py-2">Rating</th>
                </tr>
              </thead>
              <tbody>
                {filteredWorkers.map(w => (
                  <tr key={w.id} className="hover:bg-blue-200 transition-colors">
                    <td className="border px-4 py-2">{w.id}</td>
                    <td className="border px-4 py-2">{w.name}</td>
                    <td className="border px-4 py-2">{w.service?.service_type || "-"}</td>
                    <td className="border px-4 py-2">{w.available ? "✅" : "❌"}</td>
                    <td className="border px-4 py-2">{w.costPerHour ?? "-"}</td>
                    <td className="border px-4 py-2">{w.rating ? `${w.rating} ⭐` : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
      }
    </motion.div>
  );

  const BookingsView = () => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="p-4">
      <div className="flex justify-between items-center mb-4">
        <button onClick={() => setView("main")} className="text-white bg-gradient-to-r from-blue-800 to-blue-600 px-4 py-2 rounded shadow hover:scale-105 transition">
          &larr; Back
        </button>
        <input
          type="text"
          placeholder="Filter bookings..."
          value={bookingFilter}
          onChange={e => setBookingFilter(e.target.value)}
          className="px-3 py-2 rounded shadow border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <h2 className="text-2xl font-bold text-blue-900 mb-4">Bookings</h2>
      {pageLoading ? <div className="text-blue-700">Loading Bookings...</div> :
        filteredBookings.length === 0 ? <div className="text-blue-700">No Bookings Found</div> :
          <div className="overflow-x-auto rounded-lg shadow-lg">
            <table className="w-full table-auto border-collapse bg-gradient-to-r from-blue-100 to-blue-50">
              <thead className="bg-blue-900 text-white">
                <tr>
                  <th className="border px-4 py-2">ID</th>
                  <th className="border px-4 py-2">User</th>
                  <th className="border px-4 py-2">Worker</th>
                  <th className="border px-4 py-2">Service</th>
                  <th className="border px-4 py-2">Time</th>
                  <th className="border px-4 py-2">Status</th>
                  <th className="border px-4 py-2">Total</th>
                </tr>
              </thead>
              <tbody>
                {filteredBookings.map(b => (
                  <tr key={b.id} className="hover:bg-blue-200 transition-colors">
                    <td className="border px-4 py-2">{b.id}</td>
                    <td className="border px-4 py-2">{b.user?.name || "-"}</td>
                    <td className="border px-4 py-2">{b.worker?.user?.name || "-"}</td>
                    <td className="border px-4 py-2">{b.service?.service_type || "-"}</td>
                    <td className="border px-4 py-2">{b.booking_time || "-"}</td>
                    <td className="border px-4 py-2">
                      <span className={`px-2 py-1 rounded-full text-white text-sm
                        ${b.status === "Completed" ? "bg-green-500" :
                          b.status === "Pending" ? "bg-yellow-500" :
                          b.status === "Cancelled" ? "bg-red-500" : "bg-gray-500"}`}>
                        {b.status || "-"}
                      </span>
                    </td>
                    <td className="border px-4 py-2">{b.total ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
      }
    </motion.div>
  );

  // -----------------------------
  // Main Dashboard
  // -----------------------------
  if (loading) return <div className="text-blue-900 p-4">Loading...</div>;
  if (!dashboardData) return <div className="text-blue-900 p-4">No Data Available</div>;
  if (view === "users") return <UsersView />;
  if (view === "workers") return <WorkersView />;
  if (view === "bookings") return <BookingsView />;

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-blue-100">
      {/* Navbar */}
      <nav className="bg-gradient-to-r from-[#0B1E4F] to-[#1E3A8A] text-white p-4 shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="bg-white rounded-full w-10 h-10 flex items-center justify-center text-blue-900 font-bold shadow-md">A</div>
            <span className="text-2xl font-bold">Admin Dashboard</span>
          </div>
          <div className="flex items-center space-x-4">
            <span className="hidden md:block">Welcome, <strong>{dashboardData.admin?.name || "Admin"}</strong></span>
            <div className="relative group">
              <img
                src={dashboardData.admin?.avatar || "https://i.pravatar.cc/40"}
                alt="Admin Avatar"
                className="w-10 h-10 rounded-full border-2 border-white cursor-pointer"
              />
              <div className="absolute right-0 mt-2 w-40 bg-white text-gray-800 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none group-hover:pointer-events-auto">
                <button className="block w-full text-left px-4 py-2 hover:bg-gray-100">Profile</button>
                <button className="block w-full text-left px-4 py-2 hover:bg-gray-100">Settings</button>
                <button className="block w-full text-left px-4 py-2 hover:bg-gray-100 text-red-600">Logout</button>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[ 
            { title: "Total Users", value: dashboardData.total_users, view: "users" },
            { title: "Total Workers", value: dashboardData.total_workers, view: "workers" },
            { title: "Total Bookings", value: dashboardData.total_bookings, view: "bookings" }
          ].map(card => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.05 }}
              className="bg-gradient-to-r from-[#1E3A8A] to-[#0B1E4F] text-white shadow-lg rounded-lg p-6 flex flex-col justify-between"
            >
              <h3 className="text-lg font-semibold">{card.title}</h3>
              <p className="text-3xl font-bold my-4">{card.value ?? 0}</p>
              <button
                onClick={() => {
                  setView(card.view);
                  if (card.view === "users") fetchUsers();
                  if (card.view === "workers") fetchWorkers();
                  if (card.view === "bookings") fetchBookings();
                }}
                className="bg-white text-blue-900 px-4 py-2 rounded shadow hover:scale-105 transition font-semibold"
              >
                View
              </button>
            </motion.div>
          ))}
        </div>

        {/* Growth Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white shadow-lg rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-2 text-blue-900">User Growth (Last 7 Days)</h3>
            <Line
              data={{
                labels: dashboardData.user_growth_dates || [],
                datasets: [
                  { label: "New Users", data: dashboardData.user_growth_counts || [], borderColor: "#1E40AF", fill: false }
                ]
              }}
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white shadow-lg rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-2 text-blue-900">Worker Growth (Last 7 Days)</h3>
            <Line
              data={{
                labels: dashboardData.worker_growth_dates || [],
                datasets: [
                  { label: "New Workers", data: dashboardData.worker_growth_counts || [], borderColor: "#1E3A8A", fill: false }
                ]
              }}
            />
          </motion.div>
        </div>

        {/* Top Workers */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white shadow-lg rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-2 text-blue-900">Top Workers</h3>
          {dashboardData.top_workers && dashboardData.top_workers.length > 0 ? (
            <ul className="list-disc list-inside space-y-1 text-blue-800">
              {dashboardData.top_workers.map(w => (
                <li key={w.id}>
                  {w.name || "-"} - Rating: {w.average_rating ?? "-"} ⭐ - Services: {w.services?.join(", ") || "-"}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-blue-700">No Top Workers Available</div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default AdminDashboard;
