import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import forge from "node-forge";
import {
  GeoapifyGeocoderAutocomplete,
  GeoapifyContext,
} from "@geoapify/react-geocoder-autocomplete";
import "@geoapify/geocoder-autocomplete/styles/minimal.css";

// Utility: Get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Leaflet icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// RSA Public Key PEM (Replace with your backend key)
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

// AES encryption helper
function aesEncrypt(data, aesKeyBytes) {
  const iv = forge.random.getBytesSync(16);
  const buffer = forge.util.createBuffer(data, "utf8");
  const cipher = forge.cipher.createCipher("AES-CBC", aesKeyBytes);
  cipher.start({ iv: iv });
  cipher.update(buffer);
  cipher.finish();
  const encrypted = iv + cipher.output.getBytes();
  return forge.util.encode64(encrypted);
}

// RSA encrypt key helper
function encryptAESKeyWithRSA(aesKeyBytes) {
  const publicKey = forge.pki.publicKeyFromPem(RSA_PUBLIC_KEY_PEM);
  const encryptedKey = publicKey.encrypt(aesKeyBytes, "RSA-OAEP");
  return forge.util.encode64(encryptedKey);
}

// Map view updater component
function ChangeView({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom(), { animate: true });
    }
  }, [center, map]);
  return null;
}

export default function ProfileCompletionPage() {
  const [formData, setFormData] = useState({
    address: "",
    city: "",
    phone: "",
    location: null,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    axios.get("http://localhost:8000/api/csrf/", { withCredentials: true }).catch(() => {});
  }, []);

  useEffect(() => {
    async function fetchProfile() {
      setLoading(true);
      try {
        const res = await axios.get("http://localhost:8000/api/user-profile/", { withCredentials: true });
        const data = res.data;
        setFormData({
          address: data.address || "",
          city: data.city || "",
          phone: data.phone || "",
          location:
            data.location && data.location.coordinates
              ? [data.location.coordinates[1], data.location.coordinates[0]]
              : null,
        });
        setError("");
      } catch {
        setError("Failed to load profile info.");
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, []);

  useEffect(() => {
    if (!formData.location && !loading && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData(f => ({ ...f, location: [position.coords.latitude, position.coords.longitude] }));
          setError("");
        },
        () => setError("Could not fetch location. Please enable GPS or enter manually."),
        { enableHighAccuracy: true }
      );
    }
  }, [formData.location, loading]);

  // Auto update location when city changes (geocode city)
  useEffect(() => {
    async function fetchCityCoords() {
      if (!formData.city || formData.city.trim() === "") return;
      try {
        const response = await axios.get("https://api.geoapify.com/v1/geocode/search", {
          params: {
            text: formData.city,
            apiKey: "1dec767eff4b49419346e6adb2815a1d",
            limit: 1,
          },
        });
        const features = response.data.features;
        if (features.length > 0) {
          const { lat, lon } = features[0].properties;
          setFormData(f => ({ ...f, location: [lat, lon] }));
        }
      } catch (e) {
        console.error("Error fetching city coordinates:", e);
      }
    }
    fetchCityCoords();
  }, [formData.city]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const validate = () => {
    if (!formData.address.trim()) {
      setError("Address is required");
      return false;
    }
    if (!formData.city.trim()) {
      setError("City or Village is required");
      return false;
    }
    if (!formData.phone.trim()) {
      setError("Phone number is required");
      return false;
    }
    if (!formData.location) {
      setError("Location must be set or allowed on the map");
      return false;
    }
    setError("");
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setError("");
    setSubmitting(true);
    try {
      const aesKeyBytes = forge.random.getBytesSync(32);
      const encryptedAddress = aesEncrypt(formData.address, aesKeyBytes);
      const encryptedCity = aesEncrypt(formData.city, aesKeyBytes);
      const encryptedPhone = aesEncrypt(formData.phone, aesKeyBytes);
      const encryptedLocation = aesEncrypt(
        JSON.stringify({
          type: "Point",
          coordinates: [formData.location[1], formData.location[0]], // [lng, lat]
        }),
        aesKeyBytes
      );
      const encryptedAESKey = encryptAESKeyWithRSA(aesKeyBytes);

      await axios.post(
        "http://localhost:8000/api/user-profile/",
        {
          key: encryptedAESKey,
          data: {
            address: encryptedAddress,
            city: encryptedCity,
            phone: encryptedPhone,
            location: encryptedLocation,
          },
        },
        {
          withCredentials: true,
          headers: { "X-CSRFToken": getCookie("csrftoken") },
        }
      );

      navigate("/userhome");
    } catch (error) {
      if (error.response && error.response.data) {
        setError(error.response.data.error || JSON.stringify(error.response.data));
      } else {
        setError("Failed to update profile. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="w-full flex justify-center py-8">Loading profile...</div>;
  }

  return (
    <div className="max-w-xl mx-auto mt-10 px-4 py-7 border rounded-lg shadow-lg bg-white">
      <h2 className="text-xl font-semibold mb-4">Complete Your Profile</h2>
      {error && (
        <div className="text-red-700 bg-red-100 p-2 rounded mb-3">{error}</div>
      )}
      <form onSubmit={handleSubmit} className="space-y-5">
        <label className="block">
          <span className="font-semibold text-gray-700">Full Address</span>
          <input
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            className="w-full mt-2 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:ring-blue-500"
            placeholder="Type your full address"
            required
          />
        </label>

        <label className="block">
          <span className="font-semibold text-gray-700">City / Village</span>
          <GeoapifyContext apiKey="1dec767eff4b49419346e6adb2815a1d">
            <GeoapifyGeocoderAutocomplete
              placeholder="Start typing your city or village…"
              placeSelect={(place) => {
                if (place?.properties) {
                  setFormData((f) => ({
                    ...f,
                    city:
                      place.properties.city ||
                      place.properties.town ||
                      place.properties.village ||
                      place.properties.county ||
                      "",
                  }));
                  setError("");
                }
              }}
              options={{ types: ["city", "town", "village", "locality"] }}
              className="mt-1"
            />
          </GeoapifyContext>
          <input
            type="text"
            name="city"
            value={formData.city || ""}
            onChange={(e) =>
              setFormData((f) => ({ ...f, city: e.target.value }))
            }
            className="w-full mt-2 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:ring-blue-500"
            placeholder="Or enter city/village manually"
            required
          />
        </label>

        <label className="block">
          <span className="font-semibold text-gray-700">Phone Number</span>
          <input
            type="text"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            className="w-full mt-2 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring focus:ring-blue-500"
            placeholder="Enter phone number"
            required
          />
        </label>

        <div>
          <span className="block font-semibold text-gray-700 mb-1">
            Set Location on Map
          </span>
          <div style={{ height: "250px", width: "100%" }}>
            {formData.location && (
              <MapContainer
                center={formData.location}
                zoom={15}
                scrollWheelZoom={false}
                style={{ height: "100%", width: "100%" }}
                whenCreated={(map) => {
                  map.on("click", (e) => {
                    const { lat, lng } = e.latlng;
                    setFormData((f) => ({ ...f, location: [lat, lng] }));
                    setError("");
                  });
                }}
              >
                <ChangeView center={formData.location} />
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <Marker
                  position={formData.location}
                  draggable={true}
                  eventHandlers={{
                    dragend: (e) => {
                      const marker = e.target;
                      const position = marker.getLatLng();
                      setFormData((f) => ({ ...f, location: [position.lat, position.lng] }));
                      setError("");
                    },
                  }}
                >
                  <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent>
                    Drag to reposition or click map to move marker
                  </Tooltip>
                </Marker>
              </MapContainer>
            )}
          </div>
          <button
            type="button"
            onClick={() => setFormData((f) => ({ ...f, location: null }))}
            className="mt-2 px-4 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 focus:outline-none focus:ring focus:ring-red-300"
          >
            Clear Location
          </button>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full mt-6 bg-blue-600 text-white py-2 rounded shadow"
        >
          {submitting ? "Submitting..." : "Save Profile"}
        </button>
      </form>
    </div>
  );
}
