import React, { useState, useEffect } from "react";
import axios from "axios";
import { useRef } from "react";

// Helper to read CSRF token cookie for Django CSRF protection
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
function WorkerSettingsTab({ settings, setSettings, onSave }) {
  return (
    <section className="max-w-md mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4 text-[#143c5]">Settings</h2>
      <div className="bg-white rounded-2xl p-6 shadow border border-gray-200 space-y-5">
        <div className="flex items-center gap-4">
          {settings.avatar && (
            <img
              src={
                typeof settings.avatar === "string"
                  ? settings.avatar
                  : URL.createObjectURL(settings.avatar)
              }
              alt="Worker Avatar"
              className="w-16 h-16 rounded-full object-cover border-2 border-[#2566eb]"
            />
          )}
          <label>
            <span className="block font-semibold text-[#143c5] mb-1">Change Photo</span>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setSettings((prev) => ({ ...prev, avatar: e.target.files[0] }))}
            />
          </label>
        </div>
        <label className="block">
          <span className="font-semibold text-[#143c5] mb-1">Name</span>
          <input
            type="text"
            className="w-full p-2 border border-gray-300 rounded"
            value={settings.name || ""}
            onChange={(e) => setSettings((prev) => ({ ...prev, name: e.target.value }))}
          />
        </label>
        <label className="block">
          <span className="font-semibold text-[#143c5] mb-1">Email</span>
          <input
            type="email"
            className="w-full p-2 border border-gray-300 rounded"
            value={settings.email || ""}
            onChange={(e) => setSettings((prev) => ({ ...prev, email: e.target.value }))}
          />
        </label>
        <label className="block">
          <span className="font-semibold text-[#143c5] mb-1">Contact Number</span>
          <input
            type="text"
            className="w-full p-2 border border-gray-300 rounded"
            value={settings.contactNumber || ""}
            onChange={(e) => setSettings((prev) => ({ ...prev, contactNumber: e.target.value }))}
          />
        </label>
        <button
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          onClick={onSave}
        >
          Save Settings
        </button>
      </div>
    </section>
  );
}


function WorkerNavbar({ username, coinBalance, avatar, activeTab, onTabChange, available, toggleAvailability }) {
  const tabs = [
    { id: "home", label: "Home" },
    { id: "job", label: "Current Job" },
    { id: "earnings", label: "Earnings" },
    { id: "settings", label: "Settings" },
  ];
  return (
    <header className="bg-gradient-to-r from-[#14305c] via-[#2563eb] to-[#14305c] text-white p-5 shadow-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          
          <div>
            <span className="text-lg font-bold">{username}</span>
            <div className="text-xs text-blue-200">Worker Panel</div>
          </div>
          {/* Availability toggle button */}
          <button
            onClick={toggleAvailability}
            className={`ml-4 px-3 py-1 rounded font-semibold transition ${
              available ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"
            }`}
            title={available ? "Mark Unavailable" : "Mark Available"}
          >
            {available ? "Available" : "Unavailable"}
          </button>
        </div>
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`font-semibold px-4 py-2 rounded transition ${
                activeTab === tab.id ? "bg-[#2563eb] text-white shadow-lg" : "hover:bg-[#14305c] hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        
      </div>
    </header>
  );
}


function HomeTab({ settings, activeJob, totalBookings, avgRating, ratingCount, pendingRequests, onAccept }) {
  const [avatarURL, setAvatarURL] = useState(null);

  useEffect(() => {
    if (!settings) {
      setAvatarURL(null);
      return;
    }
    if (typeof settings.avatar === "string" && settings.avatar.trim() !== "") {
      setAvatarURL(settings.avatar);
      return;
    }
    if (settings.avatar instanceof Blob) {
      const url = URL.createObjectURL(settings.avatar);
      setAvatarURL(url);
      return () => URL.revokeObjectURL(url);
    }
    setAvatarURL(null);
  }, [settings]);

  return (
    <section className="max-w-5xl mx-auto p-6">
      <h2 className="text-4xl font-bold text-[#14305c] text-center mb-6">
        Welcome, {settings.name || "Worker"}!
      </h2>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <span className="block text-blue-900 font-semibold text-lg">Bookings</span>
          <span className="text-3xl text-[#2563eb] font-bold">{totalBookings}</span>
        </div>
        <div className="bg-white rounded-xl shadow-lg p-6 text-center">
          <span className="block text-blue-900 font-semibold text-lg">Rating</span>
          <span className="text-3xl text-yellow-500 font-bold">{avgRating}</span>
          <span className="block text-sm text-gray-600">{ratingCount} reviews</span>
        </div>
      </div>

      {/* Avatar */}
      {avatarURL && (
        <div className="flex justify-center mb-6">
          <img
            src={avatarURL}
            alt="worker"
            className="w-28 h-28 rounded-full border-4 border-[#2563eb] object-cover shadow-md"
          />
        </div>
      )}

      {/* Active Job / Availability */}
      <div className="text-center text-gray-700 text-lg mb-6">
        {activeJob ? (
          <>
            You are currently working on:{" "}
            <span className="text-[#2563eb] font-bold">{activeJob.service.service_type}</span>
          </>
        ) : (
          <>
            You are <span className="text-[#2563eb] font-bold">Available</span> for new jobs!
          </>
        )}
      </div>

      {/* Pending requests */}
      {!activeJob && pendingRequests?.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold text-[#14305c] mb-4">Pending Job Requests</h3>
          <ul className="space-y-3">
            {pendingRequests.map((job) => (
              <li
                key={job.id}
                className="flex justify-between items-center bg-gray-50 p-4 rounded-lg shadow-sm hover:shadow-md transition"
              >
                <div className="text-gray-700">
                  <span className="font-semibold">{job.service.service_type}</span> for{" "}
                  <span className="font-medium">{job.user.name}</span>
                </div>
                <button
                  onClick={() => onAccept(job.id)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
                >
                  Accept
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}





function CurrentJobTab({
  activeJob,
  onComplete,
  onConfirmCodPayment,
  onEditTariff,
  paymentStatus,
  onPay,
}) {
  const MEDIA_BASE_URL = "http://localhost:8000/";
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  if (!activeJob)
    return (
      <section className="max-w-2xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-bold text-[#14305c] mb-4">No Active Job</h2>
        <div className="bg-white p-5 rounded-xl shadow text-blue-900 font-medium">
          Available for booking.
        </div>
      </section>
    );

  const { payment_method, payment_received, payment_status, status, photos = [] } = activeJob;

  const renderPhotoUrl = (photo) => {
    if (!photo) return null;
    if (typeof photo === "string") return photo.startsWith("http") ? photo : `${MEDIA_BASE_URL}${photo}`;
    if (photo.image_url) return photo.image_url.startsWith("http") ? photo.image_url : `${MEDIA_BASE_URL}${photo.image_url}`;
    console.warn("Unknown photo format or null URL:", photo);
    return null;
  };

  const handleOpenGoogleMaps = () => {
    if (!activeJob.job_location) return;
    const [lng, lat] = activeJob.job_location.coordinates;
    window.open(`https://www.google.com/maps?q=${lat},${lng}`, "_blank");
  };

  return (
    <section className="max-w-2xl mx-auto p-6">
      <div className="font-bold text-lg mb-2">
        {activeJob.service?.service_type || "Service"} for {activeJob.user?.name || "User"}
      </div>
      <div><b>Address:</b> {activeJob.user?.address || "N/A"}</div>
      <div>
        <b>Location:</b>{" "}
        {activeJob.job_location ? (
          <a
            href={`https://www.google.com/maps/search/?api=1&query=${activeJob.job_location.coordinates[1]},${activeJob.job_location.coordinates[0]}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-700 underline"
          >
            Open in Google Maps
          </a>
        ) : (
          <span>No location available</span>
        )}
      </div>
      <div><b>Phone:</b> {activeJob.user?.phone || "N/A"}</div>
      <div><b>Date:</b> {activeJob.booking_time ? new Date(activeJob.booking_time).toLocaleString() : "N/A"}</div>

      <div className="px-5 py-3 border-t border-gray-100 flex-1">
        <p className="font-semibold text-gray-700 mb-1">Job Description</p>
        <p className="text-gray-600 text-sm whitespace-pre-wrap">{activeJob.description || "N/A"}</p>
      </div>

      {activeJob.equipmentRequirement && (
        <div className="px-5 py-2 border-t border-gray-100">
          <p className="font-semibold text-gray-700 mb-1">Equipment Requirement:</p>
          <p className="text-gray-600 text-sm">{activeJob.equipmentRequirement}</p>
        </div>
      )}

      {/* Photos */}
      {photos.length > 0 && (
        <div className="mt-3">
          <p className="font-semibold text-gray-700 mb-2">Photos:</p>
          <div className="flex flex-wrap gap-2">
            {photos.map((photo, idx) => {
              const url = renderPhotoUrl(photo);
              if (!url) return null;
              return (
                <img
                  key={idx}
                  src={url}
                  alt={`Booking Photo ${idx + 1}`}
                  className="w-20 h-20 object-cover rounded border cursor-pointer hover:scale-105 transition-transform"
                  onClick={() => setSelectedPhoto(url)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Simple photo modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-80 flex justify-center items-center z-50"
          onClick={() => setSelectedPhoto(null)}
        >
          <img
            src={selectedPhoto}
            alt="Enlarged"
            className="shadow-lg rounded max-h-[80vh] max-w-[90vw]"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Tariff Editor */}
      <TariffEditor
        activeJob={activeJob}
        tariff={activeJob.tariffs || []}
        setTariff={onEditTariff}
        paymentStatus={paymentStatus}
        receiptSent={activeJob.receipt_sent}
        onSendReceipt={onPay}
        basePrice={activeJob.service?.base_price || 0}
      />

      {/* Payment & Completion Buttons */}
      {payment_method === "cod" && !payment_received && (
        <button
          className="bg-yellow-500 text-white px-4 py-2 rounded mt-4 font-semibold w-full"
          onClick={onConfirmCodPayment}
        >
          Confirm COD Payment Received
        </button>
      )}

      {payment_status === "paid" && status !== "completed" && (
        <button
          className="bg-emerald-600 text-white px-4 py-2 rounded mt-4 font-semibold w-full"
          onClick={onComplete}
        >
          Mark Job Complete
        </button>
      )}

      {status === "completed" && (
        <div className="p-3 mt-4 rounded bg-green-100 text-green-800 font-semibold text-center">
          Job Completed
        </div>
      )}
    </section>
  );
}



function EarningsTab({ earnings }) {
  if (!earnings || earnings.length === 0) {
    return (
      <section className="max-w-3xl mx-auto p-4">
        <h2 className="text-2xl font-bold mb-6 text-[#14305c]">Earnings</h2>
        <p className="text-gray-600">No jobs completed yet.</p>
      </section>
    );
  }

  // Sort earnings by date descending (most recent first)
  const sortedEarnings = [...earnings].sort((a, b) => new Date(b.date) - new Date(a.date));

  return (
    <section className="max-w-3xl mx-auto p-4">
      <h2 className="text-2xl font-bold mb-6 text-[#14305c]">Earnings</h2>

      {sortedEarnings.map((earning) => (
        <div key={earning.id} className="bg-white rounded-xl shadow border border-gray-200 mb-6 p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-2 gap-2">
            <div>
              <span className="font-bold text-[#2563eb]">
                {earning.service?.service_type ?? earning.service?.name ?? "Unknown Service"}
              </span>
              <span className="text-gray-600 ml-2 block sm:inline">
                {earning.customer ?? "Unknown Customer"}
              </span>
            </div>

            <div className="px-3 py-1 rounded bg-emerald-100 text-emerald-800 font-semibold text-sm">
              +{earning.amount ?? 0} coins
            </div>
          </div>

          <div className="mb-1">
            <b>Date:</b> {earning.date ? new Date(earning.date).toLocaleString() : "N/A"}
          </div>
          
          <div className="mb-1">
            <b>Rating:</b>{" "}
            <span className="text-yellow-500 font-bold">
              {earning.rating !== null && earning.rating !== undefined ? earning.rating : "—"}
            </span>
          </div>

          {earning.tariff && earning.tariff.length > 0 && (
            <div className="mb-1 text-sm text-gray-700">
              {earning.tariff.map((t, i) => (
                <span key={i} className="inline-block pr-4">
                  {t.label}: {t.amount}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  );
}


function TariffEditor({ activeJob, tariff, setTariff, onSendReceipt, basePrice, sendingReceipt }) {
  const [localTariff, setLocalTariff] = React.useState(tariff || []);

  React.useEffect(() => {
    setLocalTariff(tariff || []);
  }, [tariff]);

  const handleSendReceipt = async () => {
    await setTariff(localTariff);
    if (onSendReceipt) await onSendReceipt(localTariff);
  };

  const handleAddItem = () => setLocalTariff([...localTariff, { label: "", amount: 0, explanation: "" }]);
  const handleChange = (idx, field, value) =>
    setLocalTariff(localTariff.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));
  const handleDelete = (idx) => setLocalTariff(localTariff.filter((_, i) => i !== idx));

  const total = localTariff.reduce((sum, item) => sum + Number(item.amount || 0), 0) + Number(basePrice);

  return (
    <div className="my-4 p-4 rounded-lg shadow-md bg-white max-w-md mx-auto">
      <h4 className="font-bold text-lg mb-3 text-[#14305c] text-center">Tariff Receipt</h4>

      {localTariff.map((item, idx) => (
        <div key={idx} className="flex flex-col sm:flex-row gap-2 mb-3 items-stretch sm:items-center bg-gray-50 p-2 rounded">
          <input
            type="text"
            value={item.label}
            placeholder="Label (e.g., Labor)"
            onChange={(e) => handleChange(idx, "label", e.target.value)}
            className="border px-2 py-2 rounded w-full sm:w-1/3 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="number"
            value={item.amount}
            placeholder="Amount"
            onChange={(e) => handleChange(idx, "amount", e.target.value)}
            className="border px-2 py-2 rounded w-full sm:w-1/4 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="text"
            value={item.explanation}
            placeholder="Explanation (optional)"
            onChange={(e) => handleChange(idx, "explanation", e.target.value)}
            className="border px-2 py-2 rounded w-full sm:flex-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            className="text-red-600 font-semibold px-2 py-1 rounded hover:bg-red-100 transition"
            onClick={() => handleDelete(idx)}
          >
            Delete
          </button>
        </div>
      ))}

      <button
        className="w-full mb-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded transition"
        onClick={handleAddItem}
      >
        + Add Line
      </button>

      <div className="text-center text-lg font-bold mb-3">
        Total: <span className="text-[#2563eb]">{total} coins</span>
      </div>

      <button
        className="w-full px-4 py-2 rounded text-white font-semibold bg-[#2563eb] hover:bg-[#1e4bb8] transition"
        onClick={handleSendReceipt}
        disabled={sendingReceipt}
      >
        {sendingReceipt ? "Sending..." : "Send Receipt (Pay)"}
      </button>
    </div>
  );
}

function WorkerHomepage() {
  const [activeTab, setActiveTab] = useState("home");
  const [activeJob, setActiveJob] = useState(null);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [earnings, setEarnings] = useState([]);
  const [settings, setSettings] = useState(null);
  const [available, setAvailable] = useState(true);
  const [paymentStatus, setPaymentStatus] = useState("pending");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completingJob, setCompletingJob] = useState(false);
  const [sendingReceipt, setSendingReceipt] = useState(false);
  const [tariff, setTariff] = useState([]);

  const receiptSent = activeJob?.receipt_sent || false;
  const disableEditing = paymentStatus === "paid" || receiptSent;

  useEffect(() => {
    const csrftoken = getCookie("csrftoken");

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [homepageResponse, earningsResponse] = await Promise.all([
          axios.get("http://localhost:8000/api/worker/homepage/", {
            withCredentials: true,
            headers: { "X-CSRFToken": csrftoken },
          }),
          axios.get("http://localhost:8000/api/worker/earnings/", {
            withCredentials: true,
            headers: { "X-CSRFToken": csrftoken },
          }),
        ]);

        const homepageData = homepageResponse.data;
        const earningsData = earningsResponse.data;

        setActiveJob(homepageData.activeJob);
        setPendingRequests(homepageData.pendingRequests || []);
        setSettings({
  ...homepageData.settings,
  name: homepageData.settings.name || homepageData.settings.user?.name || "",
  email: homepageData.settings.email || homepageData.settings.user?.email || "",
  contactNumber: homepageData.settings.contactNumber || homepageData.settings.user?.phone || ""
});

        setAvailable(homepageData.available);
        setPaymentStatus(homepageData.activeJob?.payment_status || "pending");
        setTariff(homepageData.activeJob?.tariffs || []);
        setEarnings(earningsData || []);
      } catch (error) {
        setError("Failed to load data.");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const toggleAvailability = async () => {
    if (activeJob) return;
    const csrftoken = getCookie("csrftoken");
    try {
      const response = await axios.post(
        "http://localhost:8000/api/worker/availability/",
        { available: !available },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      setAvailable(response.data.available);
    } catch (error) {
      console.error("Error updating availability", error);
    }
  };

  const handleAcceptJob = async (jobId) => {
    if (activeJob || !available) return;
    const csrftoken = getCookie("csrftoken");
    try {
      const response = await axios.post(
        "http://localhost:8000/api/worker/job/accept/",
        { jobId },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      setActiveJob(response.data);
      setPendingRequests((prev) => prev.filter((r) => r.id !== jobId));
      setAvailable(false);
      setPaymentStatus("pending");
      setTariff(response.data.tariffs || []);
      setActiveTab("job");
    } catch (error) {
      console.error("Error accepting job", error);
    }
  };

  

  const handleConfirmCodPayment = async () => {
  if (!activeJob) return alert("No active job.");

  const csrftoken = getCookie("csrftoken");

  try {
    const response = await axios.post(
      "http://localhost:8000/api/worker/confirm_cod_payment/",
      { bookingId: activeJob.id },
      { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
    );

    // Backend should return updated booking
    const updatedJob = response.data;

    setActiveJob(updatedJob);
    setPaymentStatus("paid");

    // Add to earnings immediately
    setEarnings((prev) => [updatedJob, ...prev]);

    // Allow worker to take new jobs
    setAvailable(true);

    alert("COD payment confirmed and job marked as completed!");
  } catch (error) {
    console.error(error);
    alert("Failed to confirm COD payment.");
  }
};
  const handleEditTariff = async (newTariff) => {
    if (!activeJob) return;
    const csrftoken = getCookie("csrftoken");
    try {
      const response = await axios.put(
        "http://localhost:8000/api/worker/job/tariff/",
        { jobId: activeJob.id, tariff: newTariff },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      setActiveJob(prev => ({
  ...prev,
  tariffs: response.data.tariffs || prev.tariffs,
  payment_status: response.data.payment_status || prev.payment_status,
}));

    } catch (error) {
      console.error("Error saving tariff", error);
    }
  };
const handleSendReceipt = async (updatedTariff) => {
  if (!activeJob) return;
  setSendingReceipt(true);

  const csrftoken = getCookie("csrftoken");

  try {
    // 1️⃣ Update tariff
    await axios.put(
      "http://localhost:8000/api/worker/job/tariff/",
      { jobId: activeJob.id, tariff: updatedTariff },
      { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
    );

    // 2️⃣ Send receipt
    await axios.post(
      "http://localhost:8000/api/worker/bookings/send_receipt/",
      { bookingId: activeJob.id },
      { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
    );

    // 3️⃣ Fetch updated booking (with payment status)
    const response = await axios.get(
      `http://localhost:8000/api/worker/job/${activeJob.id}/`,
      { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
    );

    const updatedJob = response.data;

    setActiveJob(updatedJob);
    setTariff(updatedTariff);
    setPaymentStatus(updatedJob.payment_status || "pending");

    // If job is completed after receipt, add to earnings
    if (updatedJob.payment_status === "paid" && !earnings.some(e => e.id === updatedJob.id)) {
      setEarnings((prev) => [updatedJob, ...prev]);
    }

    alert("Receipt sent successfully!");
  } catch (error) {
    console.error(error);
    alert("Failed to send receipt.");
  } finally {
    setSendingReceipt(false);
  }
};

// Complete job (for online payments)
const handleCompleteJob = async () => {
  if (!activeJob) return alert("No active job.");

  if (!activeJob.payment_received && activeJob.payment_method !== "cod") {
    return alert("Cannot complete job. Payment is pending.");
  }

  setCompletingJob(true);
  const csrftoken = getCookie("csrftoken");

  try {
    const response = await axios.post(
      "http://localhost:8000/api/worker/job/complete/",
      { jobId: activeJob.id },
      { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
    );

    const updatedJob = response.data;

    // Update earnings and reset activeJob
    setEarnings((prev) => [updatedJob, ...prev]);
    setActiveJob(null);
    setPaymentStatus("pending");
    setTariff([]);
    setAvailable(true);

    alert("Job marked as completed!");
  } catch (error) {
    console.error(error);
    alert("Failed to complete job.");
  } finally {
    setCompletingJob(false);
  }
};



  async function handleSaveWorkerSettings(settings) {
    const csrfToken = getCookie("csrftoken");
    try {
      const payload = {
        user: {
          name: settings.name || "",
          email: settings.email || "",
          phone: settings.contactNumber || "",
        },
        is_available: settings.is_available,
      };
      const response = await axios.put("http://localhost:8000/api/worker/settings/", payload, {
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        withCredentials: true,
      });
      console.log("Saved settings response:", response.data);
      setSettings((prev) => ({
        ...prev,
        ...response.data,
        name: response.data.user?.name || prev.name,
        email: response.data.user?.email || prev.email,
        contactNumber: response.data.user?.phone || prev.contactNumber,
      }));
      alert("Settings updated successfully.");
    } catch (error) {
      console.error("Failed to update settings:", error.response?.data || error.message);
      alert(`Failed to update settings: ${JSON.stringify(error.response?.data)}`);
    }
  }

  if (loading) {
    return (
      <div className="loading-spinner text-center p-6 text-lg text-[#14305c]">
        Loading worker data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-message p-6 text-center text-red-600 font-semibold">
        {error}
      </div>
    );
  }

  if (!settings) {
    return <div>No settings data found.</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <WorkerNavbar
        username={settings.name}
        avatar={typeof settings.avatar === "string" ? settings.avatar : null}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        available={available}
        toggleAvailability={toggleAvailability}
        coinBalance={settings.coinBalance}
      />

      <main className="pt-6 pb-14">
        {activeTab === "home" && (
          <HomeTab
            settings={settings}
            earnings={earnings}
            activeJob={activeJob}
            totalBookings={earnings.length}
            avgRating={
              earnings.length
                ? (
                  earnings.reduce((sum, e) => sum + (e.rating || 0), 0) /
                  earnings.filter((e) => e.rating != null).length
                ).toFixed(2)
                : "—"
            }
            ratingCount={earnings.filter((e) => e.rating != null).length}
            pendingRequests={pendingRequests}
            onAccept={handleAcceptJob}
          />
        )}

        {activeTab === "job" && (
          <CurrentJobTab
            activeJob={activeJob}
            onComplete={handleCompleteJob}
            onConfirmCodPayment={handleConfirmCodPayment}
            onEditTariff={handleEditTariff}
            paymentStatus={paymentStatus}
            onPay={handleSendReceipt}
            sendingReceipt={sendingReceipt}
            completingJob={completingJob}
          />
        )}

        {activeTab === "earnings" && <EarningsTab earnings={earnings} />}

        {activeTab === "settings" && (
          <WorkerSettingsTab
            settings={settings}
            setSettings={setSettings}
            onSave={() => handleSaveWorkerSettings(settings)}
          />
        )}
      </main>
    </div>
  );
}

export default WorkerHomepage;