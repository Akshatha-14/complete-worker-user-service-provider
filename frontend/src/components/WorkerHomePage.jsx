import { useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import axios from "axios";
import debounce from "lodash.debounce";
import React from "react";
import { MapPin, Phone, Calendar, FileText, Image as ImageIcon, CheckCircle, Wallet,RefreshCw} from "lucide-react";
const GEOAPIFY_API_KEY = "1dec767eff4b49419346e6adb2815a1d";

// Helper to read CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
// Fix default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

// Map updater to recenter map
function MapUpdater({ lat, lon }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], 16);
  }, [lat, lon, map]);
  return null;
}

// Draggable marker
function DraggableMarker({ position, setPosition, setAddress }) {
  const eventHandlers = {
    dragend: async (e) => {
      const latlng = e.target.getLatLng();
      setPosition([latlng.lat, latlng.lng]);
      try {
        const res = await axios.get(
          "https://api.geoapify.com/v1/geocode/reverse",
          {
            params: { lat: latlng.lat, lon: latlng.lng, apiKey: GEOAPIFY_API_KEY },
          }
        );
        if (res.data.features?.length > 0) {
          setAddress(res.data.features[0].properties.formatted);
        }
      } catch (err) {
        console.error("Failed to fetch address:", err);
      }
    },
  };
  return <Marker draggable position={position} eventHandlers={eventHandlers} />;
}

 function WorkerSettingsTab() {
  const [worker, setWorker] = useState(null);
  const [profileImage, setProfileImage] = useState(null);
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [location, setLocation] = useState({ lat: 12.9716, lon: 77.5946 });
  const [loading, setLoading] = useState(true);
  const [suggestions, setSuggestions] = useState([]);

  const getCookie = (name) => {
    const cookieValue = document.cookie
      .split("; ")
      .find((row) => row.startsWith(name + "="))
      ?.split("=")[1];
    return cookieValue ? decodeURIComponent(cookieValue) : null;
  };

  useEffect(() => {
    async function fetchWorker() {
      try {
        const res = await axios.get("http://localhost:8000/api/worker/settings/", {
          withCredentials: true,
        });
        const data = res.data;
        setWorker(data);
        setEmail(data.email || "");
        setPhone(data.phone || "");
        setAddress(data.address || "");
        if (data.location?.coordinates)
          setLocation({ lat: data.location.coordinates[1], lon: data.location.coordinates[0] });
        if (data.profile_image) setProfileImage(data.profile_image);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchWorker();
  }, []);

  // Auto-complete addresses using Geoapify
  const fetchSuggestions = debounce(async (query) => {
    if (!query) return setSuggestions([]);
    try {
      const res = await axios.get("https://api.geoapify.com/v1/geocode/autocomplete", {
        params: { text: query, apiKey: GEOAPIFY_API_KEY },
      });
      setSuggestions(res.data.features || []);
    } catch (err) {
      console.error(err);
    }
  }, 500);

  

const handleAddressChange = async (e) => {
  const value = e.target.value;
  setAddress(value);

  if (!value) {
    setSuggestions([]);
    return;
  }

  try {
    const res = await axios.get("https://api.geoapify.com/v1/geocode/autocomplete", {
      params: {
        text: value,
        apiKey: GEOAPIFY_API_KEY,
        limit: 5,
      },
    });
    setSuggestions(res.data.features || []);
  } catch (err) {
    console.error("Geoapify autocomplete error:", err);
  }
};




  const handleSelectSuggestion = (feature) => {
    setAddress(feature.properties.formatted);
    setLocation({
      lat: feature.properties.lat,
      lon: feature.properties.lon,
    });
    setSuggestions([]);
  };

  const handleSave = async () => {
    const csrfToken = getCookie("csrftoken");
    const formData = new FormData();
    formData.append("user", JSON.stringify({ email, phone }));
    formData.append("address", address);
    formData.append("location", JSON.stringify({ type: "Point", coordinates: [location.lon, location.lat] }));
    if (profileImage instanceof File) formData.append("profile_image", profileImage);

    try {
      const res = await axios.put("http://localhost:8000/api/worker/settings/", formData, {
        headers: { "Content-Type": "multipart/form-data", "X-CSRFToken": csrfToken },
        withCredentials: true,
      });
      setWorker(res.data);
      alert("Settings saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save settings");
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!worker) return <div>No worker data found.</div>;

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      <h2 className="text-2xl font-bold text-blue-700">Worker Settings</h2>

      {/* Profile Image */}
      <div className="flex items-center gap-4">
  {profileImage && (
    <img
      src={
        typeof profileImage === "string"
          ? profileImage.startsWith("http")
            ? profileImage
            : "http://localhost:8000" + profileImage // prepend backend URL
          : URL.createObjectURL(profileImage)
      }
      alt="Profile"
      className="w-20 h-20 rounded-full border-2 border-blue-600 object-cover"
    />
  )}
  <input type="file" onChange={(e) => setProfileImage(e.target.files[0])} />
</div>
      {/* Name */}
      <div>
        <label>Name</label>
        <input type="text" value={worker.name || ""} readOnly className="border p-2 w-full rounded bg-gray-100" />
      </div>

      {/* Email */}
      <div>
        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="border p-2 w-full rounded" />
      </div>

      {/* Phone */}
      <div>
        <label>Phone</label>
        <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className="border p-2 w-full rounded" />
      </div>

      {/* Address with autocomplete */}
      <div className="relative">
        <label>Address</label>
        <input type="text" value={address} onChange={handleAddressChange} className="border p-2 w-full rounded" />
        {suggestions.length > 0 && (
          <ul className="absolute z-10 bg-white border w-full max-h-40 overflow-auto mt-1">
            {suggestions.map((feature) => (
              <li key={feature.properties.place_id} onClick={() => handleSelectSuggestion(feature)} className="p-2 hover:bg-gray-200 cursor-pointer">
                {feature.properties.formatted}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Map */}
      <div className="h-64 w-full rounded-xl overflow-hidden border border-gray-300 shadow-sm">
        <MapContainer center={[location.lat, location.lon]} zoom={16} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <DraggableMarker position={[location.lat, location.lon]} setPosition={(pos) => setLocation({ lat: pos[0], lon: pos[1] })} setAddress={setAddress} />
          <MapUpdater lat={location.lat} lon={location.lon} />
        </MapContainer>
      </div>

      <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={handleSave}>Save Settings</button>
    </div>
  );
}






function WorkerNavbar({ 
  username, 
  activeTab, 
  onTabChange, 
  available, 
  toggleAvailability,
  totalEarnings = 0,
  onRefresh,
  hasActiveJob = false 
}) {
  const tabs = [
    { id: "home", label: "Home" },
    { id: "job", label: "Job" },
    { id: "earnings", label: `₹${totalEarnings.toLocaleString('en-IN')}` },
    { id: "settings", label: "Settings" },
  ];

  const handleRefresh = () => {
    if (onRefresh) onRefresh();
  };

  return (
    <header className="bg-gradient-to-r from-slate-900/95 via-blue-900/90 to-slate-900/95 text-white shadow-2xl shadow-black/30 sticky top-0 z-50 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-6xl mx-auto px-6 py-5">
        <div className="flex items-center justify-between gap-6">
          
          {/* Profile & Controls */}
          <div className="flex items-center gap-4 flex-1 min-w-0">
            {/* Profile Card */}
            <div className="group relative">
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500/20 via-indigo-500/20 to-purple-500/20 border-2 border-white/20 rounded-2xl flex items-center justify-center shadow-xl backdrop-blur-sm hover:shadow-2xl transition-all duration-300 hover:scale-105 hover:rotate-1">
                <span className="text-2xl font-black text-white drop-shadow-lg">
                  {username?.charAt(0)?.toUpperCase() || "W"}
                </span>
              </div>
            </div>

            {/* Profile Info */}
            <div className="min-w-0 flex-1">
              <h1 className="text-xl font-bold bg-gradient-to-r from-white via-blue-100 to-white/80 bg-clip-text text-transparent truncate leading-tight">
                {username || "Worker"}
              </h1>
              <p className="text-xs font-medium text-blue-200/90 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                Worker Dashboard
              </p>
            </div>
          </div>

          {/* Status Toggle & Refresh */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Professional Availability Toggle */}
            <button
              onClick={toggleAvailability}
              disabled={hasActiveJob}
              className={`group relative px-5 py-2.5 rounded-2xl font-semibold text-sm shadow-xl backdrop-blur-sm border-2 transition-all duration-400 overflow-hidden ${
                available && !hasActiveJob
                  ? "bg-emerald-500/90 hover:bg-emerald-500 border-emerald-400/50 shadow-emerald-500/30 hover:shadow-emerald-500/50 hover:scale-105 hover:-translate-y-0.5"
                  : "bg-slate-700/80 hover:bg-slate-600 border-slate-500/50 shadow-slate-500/20 hover:shadow-slate-500/40 hover:scale-105 hover:-translate-y-0.5"
              } ${hasActiveJob ? 'opacity-70 cursor-not-allowed shadow-slate-400/20' : ''}`}
              title={hasActiveJob ? "Complete current job first" : available ? "Go Offline" : "Go Online"}
              aria-label={`Toggle availability: ${hasActiveJob ? 'Busy' : available ? 'Available' : 'Unavailable'}`}
            >
              <span className="relative z-10 flex items-center gap-2">
                {hasActiveJob ? "🔒 BUSY" : available ? "🟢 Available" : "🔴 Unavailable"}
                {hasActiveJob && (
                  <div className="w-2 h-2 bg-orange-400 rounded-full animate-ping" />
                )}
              </span>
              <div className="absolute inset-0 bg-white/10 scale-0 group-hover:scale-150 transition-transform origin-center duration-300 rounded-2xl" />
            </button>

            {/* Refresh Button */}
            {onRefresh && (
              <button
                onClick={handleRefresh}
                className="p-3 bg-white/10 hover:bg-white/20 rounded-2xl backdrop-blur-sm border border-white/20 shadow-xl hover:shadow-2xl hover:scale-110 transition-all duration-400 group relative overflow-hidden"
                title="Refresh Dashboard (⌘R)"
                aria-label="Refresh dashboard data"
              >
                <RefreshCw className="w-5 h-5 group-hover:rotate-180 transition-all duration-700" />
                <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              </button>
            )}
          </div>

          {/* Tab Navigation - TEXT ONLY */}
          <nav className="flex items-center gap-2 bg-white/5 backdrop-blur-2xl px-3 py-2.5 rounded-3xl border border-white/10 shadow-2xl shadow-black/20">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`relative group font-semibold px-5 py-3 rounded-2xl transition-all duration-500 flex items-center justify-center text-sm shadow-lg backdrop-blur-sm border border-transparent overflow-hidden hover:shadow-xl min-w-[5rem] ${
                  activeTab === tab.id
                    ? "bg-gradient-to-r from-blue-500/40 via-white/10 to-blue-500/40 text-white !scale-[1.05] border-white/40 shadow-2xl shadow-blue-500/40"
                    : "text-white/95 hover:bg-white/10 hover:border-white/30 hover:text-white hover:scale-[1.03]"
                }`}
                aria-current={activeTab === tab.id ? "page" : undefined}
              >
                {/* FULL TEXT LABEL - NO ICON SPLIT */}
                <span className="font-bold tracking-wide">{tab.label}</span>
                
                {/* Active Glow Effect */}
                {activeTab === tab.id && (
                  <>
                    <div className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 to-transparent blur-xl -skew-x-12 animate-pulse" />
                    <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-emerald-400 rounded-full shadow-lg ring-2 ring-white/50 scale-110" />
                  </>
                )}
                
                {/* Hover Ripple */}
                <div className="absolute inset-0 bg-white/20 rounded-2xl scale-0 opacity-0 group-hover:scale-110 group-hover:opacity-100 transition-all duration-300 origin-center" />
              </button>
            ))}
          </nav>
        </div>
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

      {activeJob ? (
  <>
    You are currently working on:{" "}
    <span className="text-[#2563eb] font-bold">
      {activeJob.service?.service_type || "Unknown Service"}
    </span>
  </>
) : (
  <>
    You are <span className="text-[#2563eb] font-bold">Available</span> for new jobs!
  </>
)}


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

  if (!activeJob) {
    return (
      <section className="max-w-2xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-semibold text-blue-800 mb-3">No Active Job</h2>
        <div className="bg-blue-50 p-5 rounded-xl shadow text-blue-900 font-medium">
          You are currently available for booking.
        </div>
      </section>
    );
  }

  const { payment_method, payment_received, payment_status, status, photos = [] } = activeJob;

  const renderPhotoUrl = (photo) => {
    if (!photo) return null;
    if (typeof photo === "string") return photo.startsWith("http") ? photo : `${MEDIA_BASE_URL}${photo}`;
    if (photo.image_url) return photo.image_url.startsWith("http") ? photo.image_url : `${MEDIA_BASE_URL}${photo.image_url}`;
    console.warn("Unknown photo format:", photo);
    return null;
  };

  return (
    <section className="max-w-2xl mx-auto bg-white shadow-md rounded-2xl p-6 space-y-5">
      {/* Header */}
      <div className="flex justify-between items-center border-b pb-3">
        <h2 className="text-xl font-bold text-[#14305c]">
          {activeJob.service?.service_type || "Service"} for {activeJob.user?.name || "User"}
        </h2>
        <span
          className={`px-3 py-1 text-sm rounded-full ${
            status === "completed"
              ? "bg-green-100 text-green-700"
              : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {status === "completed" ? "Completed" : "In Progress"}
        </span>
      </div>

     {/* User Info */}
<div className="space-y-2 text-gray-700">
  <div className="flex items-center gap-2">
    <MapPin className="w-5 h-5 text-blue-700" />
    <span>
      <b>Address:</b> {activeJob.user?.address || "N/A"}
    </span>
  </div>

  {activeJob.user?.latitude && activeJob.user?.longitude && (
  <a
    href={`https://www.google.com/maps?q=${activeJob.user.latitude},${activeJob.user.longitude}`}
    target="_blank"
    rel="noopener noreferrer"
    className="text-blue-600 underline ml-7"
  >
    Open in Google Maps
  </a>
)}


  <div className="flex items-center gap-2">
    <Phone className="w-5 h-5 text-blue-700" />
    <span>
      <b>Phone:</b> {activeJob.user?.phone || "N/A"}
    </span>
  </div>

  <div className="flex items-center gap-2">
    <Calendar className="w-5 h-5 text-blue-700" />
    <span>
      <b>Date:</b>{" "}
      {activeJob.booking_time
        ? new Date(activeJob.booking_time).toLocaleString()
        : "N/A"}
    </span>
  </div>
</div>


      {/* Description */}
      <div className="border-t pt-3">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="w-5 h-5 text-blue-700" />
          <p className="font-semibold text-gray-700">Job Description</p>
        </div>
        <p className="text-gray-600 text-sm whitespace-pre-wrap leading-relaxed">
          {activeJob.description || "No description available."}
        </p>
      </div>

      {/* Equipment */}
      {activeJob.equipmentRequirement && (
        <div className="border-t pt-3">
          <p className="font-semibold text-gray-700 mb-1">Equipment Requirement</p>
          <p className="text-gray-600 text-sm">{activeJob.equipmentRequirement}</p>
        </div>
      )}

      {/* Photos */}
      {photos.length > 0 && (
        <div className="border-t pt-3">
          <div className="flex items-center gap-2 mb-2">
            <ImageIcon className="w-5 h-5 text-blue-700" />
            <p className="font-semibold text-gray-700">Photos</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {photos.map((photo, idx) => {
              const url = renderPhotoUrl(photo);
              if (!url) return null;
              return (
                <img
                  key={idx}
                  src={url}
                  alt={`Photo ${idx + 1}`}
                  className="w-24 h-24 object-cover rounded-xl border hover:scale-105 transition-transform cursor-pointer"
                  onClick={() => setSelectedPhoto(url)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Photo Modal */}
      {selectedPhoto && (
        <div
          className="fixed inset-0 bg-black bg-opacity-80 flex justify-center items-center z-50"
          onClick={() => setSelectedPhoto(null)}
        >
          <img
            src={selectedPhoto}
            alt="Full view"
            className="shadow-2xl rounded-xl max-h-[85vh] max-w-[90vw]"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Tariff Section */}
      <div className="border-t pt-3">
        <div className="flex items-center gap-2 mb-2">
          <Wallet className="w-5 h-5 text-blue-700" />
          <p className="font-semibold text-gray-700">Tariff Details</p>
        </div>
        <TariffEditor
          activeJob={activeJob}
          tariff={activeJob.tariffs || []}
          setTariff={onEditTariff}
          paymentStatus={paymentStatus}
          receiptSent={activeJob.receipt_sent}
          onSendReceipt={onPay}
          basePrice={activeJob.service?.base_price || 0}
        />
      </div>

      {/* Action Buttons */}
      <div className="space-y-3 pt-2">
        {payment_method === "cod" && !payment_received && (
          <button
            className="bg-yellow-500 hover:bg-yellow-600 text-white w-full py-3 rounded-xl font-semibold"
            onClick={onConfirmCodPayment}
          >
            Confirm COD Payment Received
          </button>
        )}

        {payment_status === "paid" && status !== "completed" && (
          <button
            className="bg-emerald-600 hover:bg-emerald-700 text-white w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2"
            onClick={onComplete}
          >
            <CheckCircle className="w-5 h-5" />
            Mark Job Complete
          </button>
        )}

        {status === "completed" && (
          <div className="p-3 rounded-xl bg-green-100 text-green-800 font-semibold text-center">
            Job Completed ✅
          </div>
        )}
      </div>
    </section>
  );
}

function EarningsTab({ earnings }) {
  if (!earnings || earnings.length === 0) {
    return (
      <section className="max-w-3xl mx-auto p-6 text-center">
        <h2 className="text-2xl font-semibold text-[#14305c] mb-3">Earnings</h2>
        <p className="text-gray-500 text-base">No completed jobs yet.</p>
      </section>
    );
  }

  // Sort earnings by date descending
  const sortedEarnings = [...earnings].sort(
    (a, b) => new Date(b.date) - new Date(a.date)
  );

  // Helper to convert any date to IST and show only date
  const formatDateIST = (dateStr) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    // IST offset: +5:30
    const istDate = new Date(date.getTime() + 5.5 * 60 * 60 * 1000);
    return istDate.toLocaleDateString("en-IN", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  return (
    <section className="max-w-3xl mx-auto p-6">
      <h2 className="text-2xl font-semibold text-[#14305c] mb-6">Earnings Summary</h2>

      {sortedEarnings.map((earning) => (
        <div
          key={earning.id}
          className="bg-white rounded-2xl shadow-sm border border-gray-200 mb-6 p-5 hover:shadow-md transition-all duration-300"
        >
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-2">
            <div>
              <h3 className="text-lg font-bold text-[#2563eb]">
                {earning.service?.service_type ?? earning.service?.name ?? "Unknown Service"}
              </h3>
              <p className="text-gray-700 text-sm">
                <b>Customer:</b> {earning.customer ?? "Unknown Customer"}
              </p>
            </div>

            <div className="px-4 py-1 rounded-full bg-emerald-100 text-emerald-700 font-semibold text-sm">
              + {earning.amount ?? 0} rupees
            </div>
          </div>

          {/* Details */}
          <div className="text-gray-700 text-sm mt-2 space-y-1">
            <p>
              <b>Date:</b> {formatDateIST(earning.date)}
            </p>

            <p>
              <b>Rating:</b>{" "}
              <span className="text-yellow-500 font-semibold">
                {earning.rating !== null && earning.rating !== undefined
                  ? earning.rating
                  : "—"}
              </span>
            </p>

            {/* Tariff Breakdown */}
            {earning.tariff && earning.tariff.length > 0 && (
              <div className="mt-2 border-t border-gray-100 pt-2">
                <p className="font-semibold text-gray-800 mb-1 text-sm">Tariff Breakdown:</p>
                <ul className="list-disc list-inside text-gray-600 text-sm">
                  {earning.tariff.map((t, i) => (
                    <li key={i}>
                      {t.label}: <span className="font-medium">{t.amount}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
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
      <h4 className="font-bold text-lg mb-3 text-[#14305c] text-center">Payment Receipt</h4>

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
  // 1. State declarations (FIRST)
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

  // 2. fetchHomepageData FUNCTION (SECOND - BEFORE useEffect & JSX)
  const fetchHomepageData = async () => {
    const csrftoken = getCookie("csrftoken");
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
        name: homepageData.settings?.name || homepageData.settings?.user?.name || "",
        email: homepageData.settings?.email || homepageData.settings?.user?.email || "",
        contactNumber: homepageData.settings?.contactNumber || homepageData.settings?.user?.phone || "",
      });
      setAvailable(homepageData.available);
      setPaymentStatus(homepageData.activeJob?.payment_status || "pending");
      setTariff(homepageData.activeJob?.tariffs || []);
      setEarnings(earningsData || []);
    } catch (err) {
      console.error("Fetch error:", err);
      setError("Failed to load dashboard data. Please refresh.");
    } finally {
      setLoading(false);
    }
  };

  // 3. useEffect (THIRD)
  useEffect(() => {
    fetchHomepageData();
  }, []);

  // 4. All other functions (FOURTH)
  const toggleAvailability = async () => {
    if (activeJob) {
      alert("Complete current job first!");
      return;
    }
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
      alert("Failed to update availability");
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
      const updatedJob = response.data;
      setActiveJob(updatedJob);
      setPaymentStatus("paid");
      setEarnings((prev) => [updatedJob, ...prev]);
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
      setActiveJob((prev) => ({
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
      await axios.put(
        "http://localhost:8000/api/worker/job/tariff/",
        { jobId: activeJob.id, tariff: updatedTariff },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      await axios.post(
        "http://localhost:8000/api/worker/bookings/send_receipt/",
        { bookingId: activeJob.id },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      const response = await axios.get(
        `http://localhost:8000/api/worker/job/${activeJob.id}/`,
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );
      const updatedJob = response.data;
      setActiveJob(updatedJob);
      setTariff(updatedTariff);
      setPaymentStatus(updatedJob.payment_status || "pending");
      if (updatedJob.payment_status === "paid" && !earnings.some((e) => e.id === updatedJob.id)) {
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
    setActiveJob(null);
    setPendingRequests((prev) => prev.filter((r) => r.id !== updatedJob.id));
    setAvailable(true);
    // Add to earnings if not already present
    if (!earnings.some((e) => e.id === updatedJob.id)) {
      setEarnings((prev) => [updatedJob, ...prev]);
    }
    alert("Job marked as completed!");
  } catch (error) {
    console.error("Failed to complete job", error);
    alert("Failed to complete job.");
  } finally {
    setCompletingJob(false);
  }
};

  // 5. Conditional renders (FIFTH)
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[#2563eb] mx-auto mb-6"></div>
          <p className="text-2xl font-semibold text-[#14305c] mb-2">Loading worker dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-6">⚠️</div>
          <h2 className="text-3xl font-bold text-gray-800 mb-4">{error}</h2>
          <button
            onClick={fetchHomepageData}
            className="bg-[#2563eb] text-white px-8 py-4 rounded-2xl font-bold text-lg hover:bg-[#1e4bb8] transition-all shadow-xl"
          >
            🔄 Retry Loading
          </button>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <h2 className="text-3xl font-bold text-gray-800 mb-4">No Profile Data</h2>
          <p className="text-xl text-gray-600 mb-8">Please complete your worker profile first.</p>
          <button
            onClick={fetchHomepageData}
            className="bg-[#2563eb] text-white px-8 py-4 rounded-2xl font-bold text-lg hover:bg-[#1e4bb8] transition-all shadow-xl"
          >
            🔄 Refresh Data
          </button>
        </div>
      </div>
    );
  }

  // 6. Main JSX (LAST)
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* ✅ fetchHomepageData is NOW DEFINED before this JSX */}
      <WorkerNavbar
        username={settings.name}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        available={available}
        toggleAvailability={toggleAvailability}
        totalEarnings={earnings.reduce((sum, e) => sum + Number(e.amount || 0), 0)}
        onRefresh={fetchHomepageData}
        hasActiveJob={!!activeJob}
      />

      <main className="pt-20 pb-14 px-4 max-w-7xl mx-auto">
        {activeTab === "home" && (
          <HomeTab
            settings={settings}
            activeJob={activeJob}
            totalBookings={earnings.length}
            avgRating={
              earnings.length && earnings.filter((e) => e.rating != null).length > 0
                ? (
                    earnings.reduce((sum, e) => sum + (e.rating || 0), 0) /
                    earnings.filter((e) => e.rating != null).length
                  ).toFixed(1)
                : "—"
            }
            ratingCount={earnings.filter((e) => e.rating != null).length}
            pendingRequests={pendingRequests}
            onAccept={handleAcceptJob}
            available={available}
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
        {activeTab === "settings" && <WorkerSettingsTab />}
      </main>
    </div>
  );
}

export default WorkerHomepage;
