import React, { useState, useEffect,useRef } from "react";
import axios from "axios";
import forge from "node-forge";
import PaymentOptions from "./PaymentOptions"; 
import { Toaster, toast } from "react-hot-toast";
import ChatbotModal from './ChatbotModel'; 
import '@geoapify/geocoder-autocomplete/styles/minimal.css'
import { MapContainer, TileLayer, Marker, useMap,useMapEvents } from "react-leaflet";
import L from "leaflet";
import { GeoapifyGeocoderAutocomplete } from "@geoapify/react-geocoder-autocomplete";

import { motion } from "framer-motion";
import { FiUser, FiPhone, FiMapPin, FiSave } from "react-icons/fi";
// 🧭 Fix default marker icon for Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});
function DraggableMarker({ position, setPosition }) {
  const markerRef = React.useRef(null);

  useMapEvents({
    dragend() {
      const marker = markerRef.current;
      if (marker != null) {
        const latLng = marker.getLatLng();
        setPosition([latLng.lat, latLng.lng]);
      }
    },
  });return (
    <Marker
      draggable
      position={position}
      ref={markerRef}
      eventHandlers={{
        dragend: (e) => {
          const { lat, lng } = e.target.getLatLng();
          setPosition([lat, lng]);
        },
      }}
    />
  );
}
// Helper to recenter the map when lat/lon change
function MapRecenter({ lat, lon }) {
  const map = useMapEvents({});
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true });
  }, [lat, lon, map]);
  return null;
}

// 🗺️ Component to update map instantly
function MapUpdater({ lat, lon }) {
  const map = useMap();
  useEffect(() => {
    if (lat && lon) {
      map.flyTo([lat, lon], 16, { duration: 0.5 });
    }
  }, [lat, lon, map]);
  return null;
}


const GEOAPIFY_API_KEY = "1dec767eff4b49419346e6adb2815a1d"; // Replace with your key


// Your RSA public key PEM for encrypting AES key in booking
const RSA_PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAr2E29Tw7ZaCeefy0wq64
mtrnP3XgZUB4SexrQzZlW9yQ5T5f8AAhoxH8AK+Sa7N89sx6tjzqFZKHR/r8R8yH
BAO7h4k72wii6gtDIVRXY/c8m5/WOafKNESf5+EtGmZNTlL2riOaNuZCKmlspBxE
OM2V1sAfum4VjrCv4D44UJs6VeWyMV74ucwtLw2Y+7abJJMGzxgchn1gPWAKQL8H
gWQSMmMYSSbs4LgnezpfbZgzc3aCQml86cn/8SbZxX3JuNlSu7G2R/r49TG5yb+1
dM0t8BldFdFG5nt6mduH29+vOTxv0ccPrXaMoRM/E8PhJIxTDW0DZsSwHYUNfM8A
MQIDAQAB
-----END PUBLIC KEY-----
`;

// Encryption helpers
function encryptAESKeyWithRSA(aesKeyBytes) {
  const publicKey = forge.pki.publicKeyFromPem(RSA_PUBLIC_KEY_PEM);
  const encrypted = publicKey.encrypt(aesKeyBytes, "RSA-OAEP");
  return forge.util.encode64(encrypted);
}

function aesEncrypt(data, aesKeyBytes) {
  const iv = forge.random.getBytesSync(16);
  const cipher = forge.cipher.createCipher("AES-CBC", aesKeyBytes);
  cipher.start({ iv: iv });
  cipher.update(forge.util.createBuffer(data, "utf8"));
  cipher.finish();

  const encryptedBytes = iv + cipher.output.getBytes();
  return forge.util.encode64(encryptedBytes);
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(trimmed.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Booking Details modal
function BookingDetails({ bookingId, onClose }) {
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    async function fetchBooking() {
      const response = await fetch(`http://localhost:8000/api/user/bookings/${bookingId}/`);
      const data = await response.json();
      setBooking(data);
    }
    fetchBooking();
  }, [bookingId]);

  if (!booking) return <div>Loading booking...</div>;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md overflow-auto">
        <h2 className="text-xl font-bold mb-4">Booking Details</h2>
        <p><strong>Booking ID:</strong> {booking.id}</p>
        <p><strong>Worker ID:</strong> {booking.worker_id}</p>
        <p><strong>Worker Phone:</strong> {booking.worker_phone}</p>
        <p><strong>Service:</strong> {booking.service?.service_type}</p>
        <p><strong>Tariff:</strong> ₹{booking.tariff_coins}</p>
        <p><strong>Status:</strong> {booking.status}</p>
        <p><strong>Payment Status:</strong> {booking.payment_status}</p>
        <button
          className="mt-4 bg-blue-700 text-white px-4 py-2 rounded hover:bg-blue-800"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}
function PhotoPreview({ photos, onDelete }) {
  const [modalPhoto, setModalPhoto] = React.useState(null);

  return (
    <>
      <div className="flex flex-wrap gap-2 mt-2">
        {photos.map((file, idx) => {
          const url = typeof file === "string" ? file : URL.createObjectURL(file);
          return (
            <div key={idx} className="relative">
              <img
                src={url}
                alt={`Photo ${idx + 1}`}
                className="w-20 h-20 object-cover rounded cursor-pointer border"
                onClick={() => setModalPhoto(url)}
              />
              <button
                type="button"
                title="Delete Photo"
                className="absolute top-1 right-1 bg-white text-red-600 rounded-full w-6 h-6 flex items-center justify-center shadow"
                onClick={() => onDelete(idx)}
              >
                &times;
              </button>
            </div>
          );
        })}
      </div>
      {modalPhoto && (
        <div
          onClick={() => setModalPhoto(null)}
          className="fixed inset-0 bg-black bg-opacity-75 flex justify-center items-center z-50 cursor-pointer"
        >
          <img src={modalPhoto} alt="Preview" className="max-w-full max-h-full rounded" />
        </div>
      )}
    </>
  );
}


// Booking Modal for user
function UserBooking({ worker, userId, onClose }) {
  const [contactDates, setContactDates] = useState([]);
  const [description, setDescription] = useState("");
  const [photos, setPhotos] = useState([]);
  const [equipmentRequirement, setEquipmentRequirement] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

const handleDeletePhoto = (idx) => {
  setPhotos((prev) => prev.filter((_, i) => i !== idx));
};

  const toggleSlot = (slot) => {
    if (contactDates.includes(slot)) {
      setContactDates(contactDates.filter((s) => s !== slot));
    } else if (contactDates.length < 2) {
      setContactDates([...contactDates, slot]);
    } else {
      alert("You can select up to 2 options.");
    }
  };

  const handlePhotoChange = (e) => {
  const selectedFiles = Array.from(e.target.files);
  const combinedFiles = [...photos, ...selectedFiles];
  if (combinedFiles.length > 5) {
    alert("You can upload a maximum of 5 photos");
  }
  setPhotos(combinedFiles.slice(0, 5));
};


  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (contactDates.length === 0) {
      setErrorMsg("Please select at least one contact option.");
      return;
    }
    if (!description.trim()) {
      setErrorMsg("Please provide a job description.");
      return;
    }
// In UserBooking (your parent component)


    setLoading(true);
    try {
      const aesKeyBytes = forge.random.getBytesSync(32);
      const encryptedKey = encryptAESKeyWithRSA(aesKeyBytes);

      const encryptedData = {
        userId: aesEncrypt(userId.toString(), aesKeyBytes),
        workerId: aesEncrypt(worker.id.toString(), aesKeyBytes),
        contactDates: aesEncrypt(JSON.stringify(contactDates), aesKeyBytes),
        description: aesEncrypt(description, aesKeyBytes),
        equipmentRequirement: aesEncrypt(equipmentRequirement, aesKeyBytes),
      };

      const formData = new FormData();
      formData.append("key", encryptedKey);
      formData.append("data", JSON.stringify(encryptedData));
      photos.forEach((photo) => formData.append("photos", photo));

      const csrfToken = getCookie("csrftoken");

      await axios.post("http://localhost:8000/api/bookings/", formData, {
        headers: { "X-CSRFToken": csrfToken },
        withCredentials: true,
      });

      setSuccessMsg("Request sent! The worker will contact you soon.");
      setContactDates([]);
      setDescription("");
      setPhotos([]);
      setEquipmentRequirement("");

      setTimeout(onClose, 2500);
    } catch (error) {
      setErrorMsg(error?.response?.data?.error || "Failed to submit booking");
    } finally {
      setLoading(false);
    }
  };

  const dateOptions = ["Morning (8 AM – 12 PM)", "Afternoon (12 PM – 4 PM)", "Choose him for a longer duration"];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex justify-center items-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg overflow-auto">
        <h2 className="text-xl font-bold mb-4">Book {worker.name}</h2>
        <form onSubmit={handleSubmit}>
          <fieldset className="mb-4">
            <legend className="font-semibold mb-2">Select up to 2 contact date options:</legend>
            {dateOptions.map((option) => (
              <label key={option} className="block mb-1">
                <input
                  type="checkbox"
                  value={option}
                  checked={contactDates.includes(option)}
                  onChange={() => toggleSlot(option)}
                  className="mr-2"
                />
                {option}
              </label>
            ))}
          </fieldset>

          <label className="block mb-4">
            <span className="font-semibold">Job Description:</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              required
              className="w-full mt-1 border border-gray-300 rounded px-2 py-1"
            />
          </label>

          <label className="block mb-4">
  <span className="font-semibold">Equipment Requirement (optional):</span>
  <input
    type="text"
    value={equipmentRequirement}
    onChange={(e) => setEquipmentRequirement(e.target.value)}
    placeholder="Specify any equipment needed"
    className="w-full mt-1 border border-gray-300 rounded px-2 py-1"
  />
</label>

          <label className="block mb-4">
  <span className="font-semibold">Photos (optional, up to 5):</span>
  <input
    type="file"
    multiple
    accept="image/*"
    onChange={handlePhotoChange}
    className="mt-1"
    
  />
</label>

<PhotoPreview photos={photos} onDelete={handleDeletePhoto} />



          {errorMsg && <div className="text-red-600 mb-2">{errorMsg}</div>}
          {successMsg && <div className="text-green-600 mb-2">{successMsg}</div>}

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border rounded hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-700 text-white rounded hover:bg-blue-800 disabled:opacity-50"
            >
              {loading ? "Submitting..." : "Send Request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}




function HomeTab({ onBook, recommendedWorkers, allWorkers = [], loading, userInfo }) {
  const [search, setSearch] = useState("");
  const [searchWorkers, setSearchWorkers] = useState([]); // Separate state for search results
  const [searchLoading, setSearchLoading] = useState(false);
  const [nextSearchUrl, setNextSearchUrl] = useState(null);

  // Deduplicate recommended workers by unique ID (strings)
  const uniqueRecommended = [];
  const recommendedIds = new Set();
  for (const worker of recommendedWorkers) {
    const idStr = String(worker.id);
    if (!recommendedIds.has(idStr)) {
      uniqueRecommended.push(worker);
      recommendedIds.add(idStr);
    }
  }

  // Helper to safely toLowerCase any string
  const safeToLower = (str) => (str ? String(str).toLowerCase() : "");

  // Filter recommended workers by search or show all if search empty
  const filteredRecommended = search
    ? uniqueRecommended.filter((w) => {
        const name = safeToLower(w.name);
        const serviceType = safeToLower(w.service?.service_type);
        const description = safeToLower(w.description);
        const searchLower = search.toLowerCase();
        return (
          name.includes(searchLower) ||
          serviceType.includes(searchLower) ||
          description.includes(searchLower)
        );
      })
    : uniqueRecommended;

  // Show only first 50 other workers (excluding recommended) when no search
  const limitedOthers = !search 
    ? allWorkers
        .filter((w) => !recommendedIds.has(String(w.id)))
        .slice(0, 50)
    : searchWorkers;

  // Handle search - fetch from backend with query params
  useEffect(() => {
    if (!search.trim() || !userInfo?.id) {
      setSearchWorkers([]);
      setNextSearchUrl(null);
      return;
    }

    const fetchSearchResults = async () => {
      setSearchLoading(true);
      try {
        // Search API endpoint - adjust URL to your backend search endpoint
        const response = await axios.get(
          `http://localhost:8000/api/workers/search/?q=${encodeURIComponent(search)}&limit=50`,
          { 
            withCredentials: true,
            headers: { 
              'X-CSRFToken': getCookie('csrftoken') 
            }
          }
        );

        const searchData = response.data;
        const mappedWorkers = searchData.results?.map((w) => ({
          id: w.id,
          name: w.name,
          service: { service_type: w.servicetype || w.service?.servicetype },
          avatar: w.avatar || `https://i.pravatar.cc/80?u=${w.id}`,
          rating: w.rating || 0,
          costPerHour: w.costperhour || w.charge || 0,
          available: w.available !== false || w.isavailable !== false,
          description: w.description || "",
          address: w.address || w.get_address || "Not provided",

          difficulty: w.difficulty || "Standard"
        })) || [];

        setSearchWorkers(mappedWorkers);
        setNextSearchUrl(searchData.next);
      } catch (error) {
        console.error('Search error:', error);
        setSearchWorkers([]);
        setNextSearchUrl(null);
      } finally {
        setSearchLoading(false);
      }
    };

    const timeoutId = setTimeout(fetchSearchResults, 300); // Debounce search
    return () => clearTimeout(timeoutId);
  }, [search, userInfo?.id]);

  if (loading) return <div className="text-center py-12">Loading recommended professionals...</div>;

  if (filteredRecommended.length === 0 && limitedOthers.length === 0 && !search) {
    return (
      <section className="max-w-6xl mx-auto pt-4 pb-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-blue-900">Recommended Professionals</h2>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or service..."
            className="border border-gray-300 rounded-md px-4 py-2 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <p className="text-gray-500 text-center py-12">No professionals available. Try searching!</p>
      </section>
    );
  }

  return (
    <section className="max-w-6xl mx-auto pt-4 pb-8">
      {/* Search input and heading */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-blue-900">
          {search ? `Search Results for "${search}"` : "Recommended Professionals"}
        </h2>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or service..."
          className="border border-gray-300 rounded-md px-4 py-2 w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Recommended workers grid */}
      {filteredRecommended.length > 0 && (
        <div className="mb-12">
        
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            {filteredRecommended.map((worker) => (
              <WorkerCard key={worker.id} worker={worker} onBook={onBook} />
            ))}
          </div>
        </div>
      )}

      {/* Other Professionals / Search Results */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-blue-900">
            {search ? "Search Results" : "Other Professionals"}
            {!search && limitedOthers.length === 50 && (
              <span className="text-sm text-gray-500 ml-2">(Showing first 50)</span>
            )}
          </h2>
          {search && searchLoading && (
            <span className="text-sm text-blue-600">Searching...</span>
          )}
        </div>

        {limitedOthers.length === 0 ? (
          <p className="text-gray-500 mb-8 text-center py-8">
            {search 
              ? `No professionals found for "${search}". Try different keywords.` 
              : "No other professionals available."
            }
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
            {limitedOthers.map((worker) => (
              <WorkerCard key={worker.id} worker={worker} onBook={onBook} />
            ))}
          </div>
        )}
      </div>

      {/* Show 50 limit indicator */}
      {!search && limitedOthers.length === 50 && (
        <div className="mt-8 text-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            Showing first 50 professionals.{" "}
            <span 
              className="font-semibold cursor-pointer hover:underline"
              onClick={() => setSearch("")}
            >
              Search to see more
            </span>
          </p>
        </div>
      )}
    </section>
  );
}

function WorkerCard({ worker, onBook }) {
  return (
    <div
      className={`relative bg-white rounded-2xl shadow-xl border border-gray-200 flex flex-col items-center p-6 transition-all duration-300 hover:shadow-2xl hover:scale-[1.02] ${
        !worker.available ? "opacity-50" : ""
      }`}
    >
      <img
        src={worker.avatar}
        alt={worker.name}
        className="mb-3 w-20 h-20 rounded-full border-2 border-blue-300 object-cover shadow-lg"
        onError={(e) => {
          e.target.src = `https://i.pravatar.cc/80?u=${worker.id}`;
        }}
      />
      <div className="absolute right-3 top-3">
        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
          worker.available 
            ? "bg-green-100 text-green-700" 
            : "bg-gray-100 text-gray-500"
        }`}>
          {worker.available ? "Available" : "Unavailable"}
        </span>
      </div>
      
      <div className="w-full text-center mb-4">
        <span className="text-lg font-semibold text-gray-800 block leading-tight">
          {worker.name}
        </span>
        <div className="text-gray-500 text-sm mt-1">
          {worker.service?.service_type || "Service not specified"}
        </div>
        <span className="mt-2 inline-block px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">
          {worker.address || "not specified"} 
        </span>
      </div>
      
      <div className="flex items-center justify-center gap-2 mb-3 text-sm">
        <span className="font-medium text-yellow-500">{worker.rating || 0} ★</span>
        <span className="text-gray-400 mx-1">|</span>
        <span className="font-semibold text-blue-700">
          {worker.costPerHour || 0} rupees/hr
        </span>
      </div>
      
      
      <button
        className={`w-full px-4 py-2 rounded-xl font-semibold text-sm transition-all duration-200 ${
          worker.available 
            ? "bg-gradient-to-r from-[#001f3f] to-[#003366] text-white shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]"
            : "bg-gray-200 text-gray-500 cursor-not-allowed"
        }`}
        onClick={() => worker.available && onBook(worker)}
        disabled={!worker.available}
        type="button"
      >
        Book Now
      </button>
    </div>
  );
}




function BookingHistory() {
  const MEDIA_BASE_URL = "http://localhost:8000/media/";

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [cancelVisible, setCancelVisible] = useState({});

  useEffect(() => {
    fetchBookingHistory();
  }, []);

  const fetchBookingHistory = async () => {
    try {
      const response = await axios.get("http://localhost:8000/api/user/bookings/", {
        withCredentials: true,
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      setBookings(response.data);

      const now = new Date();
      const visibility = {};
      response.data.forEach((b) => {
        const bookingTime = new Date(b.booking_time);
        const diffMinutes = (now - bookingTime) / 1000 / 60;
        visibility[b.id] = diffMinutes <= 5 && b.status === "booked";

        const timeLeft = 5 * 60 * 1000 - (now - bookingTime);
        if (timeLeft > 0) {
          setTimeout(() => {
            setCancelVisible((prev) => ({ ...prev, [b.id]: false }));
          }, timeLeft);
        }
      });
      setCancelVisible(visibility);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch booking history.");
    } finally {
      setLoading(false);
    }
  };

  const cancelBooking = async (bookingId) => {
    const csrfToken = getCookie("csrftoken");
    try {
      await axios.post(
        `http://localhost:8000/api/bookings/${bookingId}/cancel/`,
        {},
        { headers: { "X-CSRFToken": csrfToken }, withCredentials: true }
      );
      setBookings((prev) =>
        prev.map((b) => (b.id === bookingId ? { ...b, status: "Cancelled" } : b))
      );
      setCancelVisible((prev) => ({ ...prev, [bookingId]: false }));
      toast.success("Booking cancelled successfully!");
    } catch (err) {
      console.error(err);
      toast.error("Failed to cancel booking.");
    }
  };

  const renderPhotoUrl = (photo) => {
    if (!photo) return null;
    if (typeof photo === "string") return photo.startsWith("http") ? photo : `${MEDIA_BASE_URL}${photo}`;
    if (photo.image_url) return photo.image_url.startsWith("http") ? photo.image_url : `${MEDIA_BASE_URL}${photo.image_url}`;
    return null;
  };

  if (loading)
    return (
      <div className="flex justify-center items-center min-h-screen text-gray-500 text-lg">
        Loading booking history...
      </div>
    );

  if (error)
    return (
      <div className="flex justify-center items-center min-h-screen text-red-600 text-lg">
        {error}
      </div>
    );

  if (!bookings.length)
    return (
      <div className="flex justify-center items-center min-h-screen text-gray-500 text-lg">
        No booking history found.
      </div>
    );

  return (
  <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-100 py-10 px-4 sm:px-8">
    <Toaster position="top-right" />
    <h2 className="text-3xl md:text-4xl font-bold text-center text-blue-700 mb-10">
      Your Booking History
    </h2>

    <div className="space-y-6 max-w-[1400px] mx-auto">
      {bookings.map((booking) => (
        <div
          key={booking.id}
          className="w-full bg-white/90 backdrop-blur-md border border-blue-100 rounded-2xl shadow-xl p-4 flex flex-col md:flex-row gap-4 hover:shadow-2xl transition-transform duration-300"
        >
          {/* Service & Status */}
          <div className="md:w-1/6 flex flex-col justify-between">
            <p className="font-bold text-gray-800 text-lg">
              {booking.service?.service_type || booking.service}
            </p>
            <span
              className={`px-2 py-1 rounded-full text-xs font-semibold mt-2 ${
                booking.status === "booked"
                  ? "bg-yellow-200 text-yellow-800 animate-pulse"
                  : booking.status === "completed"
                  ? "bg-green-200 text-green-800"
                  : booking.status === "in_progress"
                  ? "bg-blue-200 text-blue-800"
                  : "bg-red-200 text-red-800"
              }`}
            >
              {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
            </span>
          </div>

          {/* Worker Info */}
          <div className="md:w-1/4 flex items-center gap-4">
            <img
              src={
                booking.worker.avatar
                  ? booking.worker.avatar.startsWith("http")
                    ? booking.worker.avatar
                    : `${MEDIA_BASE_URL}${booking.worker.avatar}`
                  : `https://i.pravatar.cc/80?u=${booking.worker.id}`
              }
              alt={booking.worker.name || "Worker"}
              className="w-20 h-20 rounded-full border-2 border-blue-300 object-cover shadow flex-shrink-0"
              onError={(e) => {
                e.target.src = `https://i.pravatar.cc/80?u=${booking.worker.id}`;
              }}
            />
            <div>
              <p className="font-semibold text-gray-700">
                {booking.worker?.user?.name || booking.worker?.name || "Unknown Worker"}
              </p>
              <p className="text-gray-500 text-sm">Phone: {booking.worker?.user?.phone || "N/A"}</p>
              <p className="text-gray-500 text-sm">
                Booked on:{" "}
                {new Date(booking.booking_time).toLocaleString([], {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            </div>
          </div>

          {/* Job Details */}
          <div className="md:w-1/3">
            <p className="font-semibold text-gray-700 mb-1">Job Details</p>
            <p className="text-gray-600 text-sm whitespace-pre-wrap">
              {booking.details || "No details provided."}
            </p>
          </div>

          {/* Uploaded Photos */}
          <div className="md:w-1/6">
            <p className="font-semibold text-gray-700 mb-1">Photos</p>
            <div className="flex flex-wrap gap-2">
              {booking.photos?.map((photo, idx) => {
                const url = renderPhotoUrl(photo);
                if (!url) return null;
                return (
                  <img
                    key={idx}
                    src={url}
                    alt={`Photo ${idx + 1}`}
                    className="w-16 h-16 object-cover rounded border cursor-pointer hover:scale-105 transition-transform"
                    onClick={() => setSelectedPhoto(url)}
                  />
                );
              })}
            </div>
          </div>

          {/* Tariffs & Actions */}
          <div className="md:w-1/6 flex flex-col justify-between gap-2">
            <div>
              <p className="font-semibold text-gray-700 mb-1">Tariff</p>
              {booking.tariffs?.length > 0 ? (
                booking.tariffs.map((t, idx) => (
                  <div key={idx} className="flex justify-between text-gray-600 text-sm">
                    <span>{t.label}</span>
                    <span>₹{t.amount} </span>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-sm">No tariffs</p>
              )}
              <div className="mt-1 font-bold text-gray-800">Total: ₹{booking.total || 0} </div>
            </div>

            <div className="flex flex-wrap gap-2 mt-2">
              {cancelVisible[booking.id] && booking.status !== "Cancelled" && (
                <button
                  className="bg-red-600 text-white px-3 py-1 rounded-lg font-semibold hover:bg-red-700 hover:scale-105 transition-transform"
                  onClick={() => cancelBooking(booking.id)}
                >
                  Cancel Booking
                </button>
              )}

              {!booking.payment_received &&
                booking.status === "in_progress" &&
                booking.tariffs?.length > 0 && (
                  <button
                    onClick={() => setSelectedBooking(booking)}
                    className="bg-blue-600 text-white px-3 py-1 rounded-lg font-semibold hover:bg-blue-700 hover:scale-105 transition-transform"
                  >
                    Pay Now
                  </button>
                )}

              {(booking.payment_status === "paid" || booking.status === "completed") && !booking.rating && (
                <button
                  onClick={() => setSelectedBooking(booking)}
                  className="bg-yellow-500 text-black px-3 py-1 rounded-lg font-semibold hover:bg-yellow-600 hover:scale-105 transition-transform"
                >
                  Provide Rating
                </button>
              )}

              {booking.payment_received && <span className="text-green-600 font-semibold">Paid</span>}
              {booking.rating && <span className="text-gray-700 font-medium">Rating: {booking.rating} ★</span>}
            </div>
          </div>
        </div>
      ))}
    </div>

    {/* Payment Modal */}
    {selectedBooking && (
      <PaymentOptions
        booking={selectedBooking}
        onPaymentSuccess={() => {
          setSelectedBooking(null);
          fetchBookingHistory();
        }}
        onCancel={() => setSelectedBooking(null)}
      />
    )}

    {/* Photo Modal */}
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
  </div>
);
}

 function SettingsTab({ userInfo, onSave }) {
  const [formData, setFormData] = useState({
    username: userInfo.username || "",
    phone: userInfo.phone || "",
    address: userInfo.address || "",
    locationLat: userInfo.location?.coordinates?.[1] || 12.9716,
    locationLon: userInfo.location?.coordinates?.[0] || 77.5946,
  });

  const [suggestions, setSuggestions] = useState([]);

  // Fetch address suggestions for autocomplete
  const fetchSuggestions = async (query) => {
    if (!query) return setSuggestions([]);
    try {
      const response = await axios.get(
        "https://api.geoapify.com/v1/geocode/autocomplete",
        {
          params: {
            text: query,
            apiKey: GEOAPIFY_API_KEY,
            limit: 5,
          },
        }
      );
      setSuggestions(response.data.features);
    } catch (err) {
      console.error(err);
    }
  };

  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (name === "address") {
      fetchSuggestions(value);
    }
  };

  // When user selects a suggestion
  const selectSuggestion = (place) => {
    setFormData({
      ...formData,
      address: place.properties.formatted,
      locationLat: place.properties.lat,
      locationLon: place.properties.lon,
    });
    setSuggestions([]);
  };

  const handleSave = () => {
    onSave({
      ...formData,
      location: {
        type: "Point",
        coordinates: [formData.locationLon, formData.locationLat],
      },
    });
  };

  return (
    <div className="max-w-lg mx-auto p-4 space-y-4 bg-white shadow-lg rounded-xl">
      {/* Username */}
      <div>
        <label className="block font-semibold mb-1">Username</label>
        <input
          type="text"
          name="username"
          value={formData.username}
          onChange={handleChange}
          className="w-full border p-2 rounded"
          placeholder="Enter your username"
        />
      </div>

      {/* Phone */}
      <div>
        <label className="block font-semibold mb-1">Phone</label>
        <input
          type="text"
          name="phone"
          value={formData.phone}
          onChange={handleChange}
          className="w-full border p-2 rounded"
          placeholder="Enter your phone number"
        />
      </div>

      {/* Address */}
      <div className="relative">
        <label className="block font-semibold mb-1">Address</label>
        <input
          type="text"
          name="address"
          value={formData.address}
          onChange={handleChange}
          className="w-full border p-2 rounded"
          placeholder="Enter your address"
        />
        {suggestions.length > 0 && (
          <ul className="absolute top-full left-0 right-0 bg-white border rounded max-h-40 overflow-y-auto z-10">
            {suggestions.map((s) => (
              <li
                key={s.properties.place_id}
                className="p-2 cursor-pointer hover:bg-gray-200"
                onClick={() => selectSuggestion(s)}
              >
                {s.properties.formatted}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Map */}
      <div className="h-64 w-full rounded-xl overflow-hidden border border-gray-300 shadow-sm">
        <MapContainer
  center={[formData.locationLat, formData.locationLon]}
  zoom={16}
  scrollWheelZoom={true}
  style={{ height: "100%", width: "100%" }}
>
  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

  
  {/* Draggable marker */}
  <DraggableMarker
    position={[formData.locationLat, formData.locationLon]}
    setPosition={(pos) =>
      setFormData((prev) => ({
        ...prev,
        locationLat: pos[0],
        locationLon: pos[1],
      }))
    }
  />

  {/* Recenter map when lat/lon change */}
  <MapRecenter lat={formData.locationLat} lon={formData.locationLon} />
</MapContainer>

      </div>

      {/* Coordinates */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block font-semibold mb-1">Latitude</label>
          <input
            type="number"
            value={formData.locationLat}
            readOnly
            className="w-full border p-2 rounded bg-gray-100 cursor-not-allowed"
          />
        </div>
        <div>
          <label className="block font-semibold mb-1">Longitude</label>
          <input
            type="number"
            value={formData.locationLon}
            readOnly
            className="w-full border p-2 rounded bg-gray-100 cursor-not-allowed"
          />
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition"
      >
        Save
      </button>
    </div>
  );
}
function UserHomepage() {
  const [activeTab, setActiveTab] = useState("home");
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [bookingWorker, setBookingWorker] = useState(null);
  const [allWorkers, setAllWorkers] = useState([]);
  const [loadingAll, setLoadingAll] = useState(false);
  const [recommendedWorkers, setRecommendedWorkers] = useState([]);
  const [userInfo, setUserInfo] = useState({
    username: "",
    email: "",
    id: null,
    phone: "",
    address: "",
    location: null,
  });
  const [selectedBookingId, setSelectedBookingId] = useState(null);

  const onToggleAvailability = async (workerId, newAvailability) => {
    try {
      const csrftoken = getCookie("csrftoken");
      await axios.post(
        "http://localhost:8000/api/worker/availability/",
        { available: newAvailability, workerId },
        { withCredentials: true, headers: { "X-CSRFToken": csrftoken } }
      );

      setRecommendedWorkers((prev) =>
        prev.map((w) => (w.id === workerId ? { ...w, available: newAvailability } : w))
      );
      toast.success("Availability updated successfully!");
    } catch (error) {
      toast.error("Failed to update availability");
    }
  };

  useEffect(() => {
    async function fetchCSRF() {
      try {
        await axios.get("http://localhost:8000/api/csrf/", { withCredentials: true });
      } catch (err) {
        console.error("Failed to fetch CSRF cookie:", err);
      }
    }
    fetchCSRF();
  }, []);

  useEffect(() => {
    async function fetchUserProfile() {
      try {
        const response = await axios.get("http://localhost:8000/api/user-profile/", {
          withCredentials: true,
        });
        const data = response.data;
        setUserInfo({
          username: data.username || (data.email ? data.email.split("@")[0] : "User"),
          email: data.email || "",
          id: data.id || null,
          phone: data.phone || "",
          address: data.address || "",
          location: data.location || null,
        });
      } catch (error) {
        console.error("Failed to fetch user profile:", error);
        setUserInfo({
          username: "Guest",
          email: "",
          id: null,
          phone: "",
          address: "",
          location: null,
        });
        toast.error("Failed to fetch user profile");
      }
    }
    fetchUserProfile();
  }, []);

  useEffect(() => {
    if (!userInfo.id) return;

    const fetchData = async () => {
      setLoadingRecs(true);
      setLoadingAll(true);
      try {
        const [recsResponse, allResponse] = await Promise.all([
          axios.get(`http://localhost:8000/api/recommend/${userInfo.id}/`, { withCredentials: true }),
          axios.get(`http://localhost:8000/api/workers/`, { withCredentials: true }),
        ]);

        const recs = recsResponse.data.recommendations || [];
        const mappedRecs = recs.map((w) => ({
  id: w.worker_id,
  name: w.worker_name || `Worker ${w.worker_id}`,
  service: { service_type: w.service_type || w.service_name || "Service" },
  avatar: w.avatar || `https://i.pravatar.cc/80?u=${w.worker_id}`, // use backend-provided avatar
  rating: w.total_rating || 0,
  costPerHour: w.charge || 0,
  address: w.address || w.user?.address || "Not provided",

  available: w.is_available !== false,
}));

setRecommendedWorkers(mappedRecs);


        const all = allResponse.data || [];
        const mappedAll = all.map((w) => ({
          id: w.id,
          name: w.name || `Worker ${w.id}`,
          service: { service_type: w.service_type || w.service?.service_type || "Service" },
          avatar: w.avatar || `https://i.pravatar.cc/80?u=${w.id}`,
          rating: w.rating || 0,
          costPerHour: w.costPerHour || w.cost_per_hour || 0,
          address: w.address || w.user?.address || "Not provided",

          available: w.available !== false && w.is_available !== false,
        }));
        setAllWorkers(mappedAll);
      } catch (error) {
        console.error("Error fetching workers data:", error);
        setRecommendedWorkers([]);
        setAllWorkers([]);
        toast.error("Failed to fetch workers data");
      } finally {
        setLoadingRecs(false);
        setLoadingAll(false);
      }
    };

    fetchData();
    const intervalId = setInterval(fetchData, 300000);
    return () => clearInterval(intervalId);
  }, [userInfo.id]);

  async function encryptProfileData(formData) {
    const aesKeyBytes = forge.random.getBytesSync(32);
    const locationJSON = JSON.stringify({
      type: "Point",
      coordinates: [
        parseFloat(formData.locationLon) || 0,
        parseFloat(formData.locationLat) || 0,
      ],
    });

    const encryptedData = {
      name: aesEncrypt(formData.username || "", aesKeyBytes),
      phone: aesEncrypt(formData.phone || "", aesKeyBytes),
      address: aesEncrypt(formData.address || "", aesKeyBytes),
      location: aesEncrypt(locationJSON, aesKeyBytes),
    };

    const encryptedKey = encryptAESKeyWithRSA(aesKeyBytes);
    return { key: encryptedKey, data: encryptedData };
  }

  async function handleSaveUserProfile(newData) {
    try {
      const encryptedPayload = await encryptProfileData(newData);
      const csrfToken = getCookie("csrftoken");
      await axios.post(
        "http://localhost:8000/api/user-profile/",
        encryptedPayload,
        { withCredentials: true, headers: { "X-CSRFToken": csrfToken } }
      );
      setUserInfo((prev) => ({ ...prev, ...newData }));
      toast.success("Profile updated successfully!");
    } catch (error) {
      console.error(error);
      toast.error("Failed to update profile");
    }
  }

return (
  <div className="min-h-screen bg-white text-gray-800 font-sans">
    <Toaster position="top-right" />

    {/* 🌟 Header Section */}
    <header className="bg-[#0A2342] text-white shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center px-6 py-5">
        {/* Title and Description */}
        <div className="text-center md:text-left">
          <h1 className="text-3xl font-bold tracking-tight">
            AI Powered Local Service Finder
          </h1>
          <p className="text-blue-200 text-sm mt-1">
            Find trusted local professionals near you effortlessly.
          </p>
        </div>

        {/* User Info */}
        <div className="flex items-center space-x-3 mt-3 md:mt-0">
          <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center font-semibold text-[#0A2342] uppercase text-sm shadow-sm">
            {userInfo.username ? userInfo.username[0] : "G"}
          </div>
          <span className="font-medium text-base tracking-wide">
            {userInfo.username ? userInfo.username : "Guest"}
          </span>
        </div>
      </div>

      {/* 🌐 Navigation Bar */}
      <nav className="flex justify-center space-x-8 bg-[#0A2342] py-3 border-t border-blue-900 shadow-sm">
        {[
          { name: "Home", tab: "home" },
          { name: "Booking History", tab: "bookingHistory" },
          { name: "Settings", tab: "settings" },
        ].map((item) => (
          <button
            key={item.tab}
            className={`transition-all duration-300 px-2 md:px-3 pb-1 font-semibold ${
              activeTab === item.tab
                ? "text-blue-300 border-b-2 border-blue-300"
                : "text-white hover:text-blue-200 hover:border-b-2 hover:border-blue-200"
            }`}
            onClick={() => setActiveTab(item.tab)}
            type="button"
          >
            {item.name}
          </button>
        ))}
      </nav>
    </header>

    {/* 💬 Floating Chat Section */}
    
  

      {activeTab === "home" && (
        <HomeTab
          onBook={setBookingWorker}
          recommendedWorkers={recommendedWorkers}
          allWorkers={allWorkers}
          loading={loadingRecs || loadingAll}
          onToggleAvailability={onToggleAvailability}
        />
      )}

      {activeTab === "bookingHistory" && (
        <>
          <BookingHistory onShowDetails={(id) => setSelectedBookingId(id)} />
          {selectedBookingId && (
            <BookingDetails bookingId={selectedBookingId} onClose={() => setSelectedBookingId(null)} />
          )}
        </>
      )}

      {activeTab === "settings" && (
        <SettingsTab userInfo={userInfo} onSave={handleSaveUserProfile} />
      )}

      {bookingWorker && (
        <UserBooking worker={bookingWorker} userId={userInfo.id} onClose={() => setBookingWorker(null)} />
      )}

      <ChatbotModal />
      
    </div>
  );
}

export default UserHomepage;
