import React, { useState, useEffect } from "react";
import axios from "axios";

function WorkerApplicationPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    address: "",
    skills: "",
    experience: "",
    service_categories: [],
    
    // Document uploads (address_proof removed)
    photo_id_path: null,
    aadhaar_card: null,
    union_card_path: null,
    certifications: null,
    signature_copy: null,
    
    coinsPaid: false,
  });

  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applicationId, setApplicationId] = useState(null);
  
  // Geoapify address autocomplete states
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);

  const GEOAPIFY_API_KEY = "1dec767eff4b49419346e6adb2815a1d";

  // Available service categories
  const serviceOptions = [
    "Plumbing",
    "Electrical",
    "Cleaning",
    "Carpentry",
    "Painting",
    "Gardening",
    "Appliance Repair",
    "AC Repair",
    "Other"
  ];

  // Debounced address search
  useEffect(() => {
    if (formData.address.length > 3) {
      const timeoutId = setTimeout(() => {
        searchAddress(formData.address);
      }, 500);
      return () => clearTimeout(timeoutId);
    } else {
      setAddressSuggestions([]);
      setShowSuggestions(false);
    }
  }, [formData.address]);

  const searchAddress = async (query) => {
    try {
      const response = await axios.get(
        `https://api.geoapify.com/v1/geocode/autocomplete?text=${encodeURIComponent(query)}&format=json&apiKey=${GEOAPIFY_API_KEY}`
      );
      
      if (response.data && response.data.results) {
        setAddressSuggestions(response.data.results);
        setShowSuggestions(true);
      }
    } catch (error) {
      console.error("Address search error:", error);
    }
  };

  const selectAddress = (suggestion) => {
    setFormData({
      ...formData,
      address: suggestion.formatted
    });
    setSelectedLocation({
      lat: suggestion.lat,
      lon: suggestion.lon,
      formatted: suggestion.formatted
    });
    setShowSuggestions(false);
    setAddressSuggestions([]);
  };

  const handleChange = (e) => {
    const { name, value, type, checked, files } = e.target;
    if (type === "checkbox") {
      if (name === "coinsPaid") {
        setFormData({ ...formData, [name]: checked });
      } else {
        // Handle service categories checkboxes
        const currentCategories = [...formData.service_categories];
        if (checked) {
          currentCategories.push(value);
        } else {
          const index = currentCategories.indexOf(value);
          if (index > -1) currentCategories.splice(index, 1);
        }
        setFormData({ ...formData, service_categories: currentCategories });
      }
    } else if (type === "file") {
      setFormData({ ...formData, [name]: files[0] });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const validate = () => {
    const errs = {};
    
    // Basic Information
    if (!formData.name.trim()) errs.name = "Full name is required";
    if (!formData.email.trim()) errs.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(formData.email)) errs.email = "Invalid email address";
    if (!formData.phone.trim()) errs.phone = "Phone number is required";
    if (!formData.address.trim()) errs.address = "Complete address is required";
    if (!formData.skills.trim()) errs.skills = "Please list your skills";
    if (!formData.experience.trim()) errs.experience = "Please describe your experience";
    if (formData.service_categories.length === 0) 
      errs.service_categories = "Select at least one service category";
    
    // Required Documents (address_proof removed)
    if (!formData.photo_id_path) errs.photo_id_path = "Photo ID is required";
    if (!formData.aadhaar_card) errs.aadhaar_card = "Aadhaar card is required";
    
    // Payment
    if (!formData.coinsPaid) errs.coinsPaid = "You must pay 150 coins before submitting";
    
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // Load Razorpay script dynamically
  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if (window.Razorpay) {
        resolve(true);
        return;
      }
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handlePayment = async () => {
    if (!formData.name || !formData.email) {
      alert("Please fill in your full name and email before payment.");
      return;
    }
    
    setLoading(true);
    const scriptLoaded = await loadRazorpayScript();
    if (!scriptLoaded) {
      alert("Razorpay SDK failed to load. Check your internet connection.");
      setLoading(false);
      return;
    }

    try {
      const tempFormData = new FormData();
      tempFormData.append("name", formData.name);
      tempFormData.append("email", formData.email);
      tempFormData.append("phone", formData.phone);
      tempFormData.append("address", formData.address);
      tempFormData.append("skills", formData.skills);
      tempFormData.append("experience", formData.experience);
      
      // Append service categories as JSON array
      tempFormData.append("service_categories", JSON.stringify(formData.service_categories));
      
      // Append documents (address_proof removed)
      if (formData.photo_id_path) tempFormData.append("photo_id_path", formData.photo_id_path);
      if (formData.aadhaar_card) tempFormData.append("aadhaar_card", formData.aadhaar_card);
      if (formData.union_card_path) tempFormData.append("union_card_path", formData.union_card_path);
      if (formData.certifications) tempFormData.append("certifications", formData.certifications);
      if (formData.signature_copy) tempFormData.append("signature_copy", formData.signature_copy);

      // Create application
      const createAppResp = await axios.post(
        "http://localhost:8000/api/worker-application/",
        tempFormData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      const appId = createAppResp.data.id;
      setApplicationId(appId);

      // Create payment order
      const orderResp = await axios.post(
        "http://localhost:8000/api/payments/create-order1/",
        { worker_application_id: appId }
      );

      const orderData = orderResp.data;

      const options = {
        key: "rzp_test_R6KHQL3uufbASp",
        amount: orderData.amount,
        currency: orderData.currency,
        order_id: orderData.order_id,
        name: "Worker Application Payment",
        description: "Pay 150 coins to submit application",
        handler: async function (response) {
          try {
            const verifyResp = await axios.post(
              "http://localhost:8000/api/payments/verify1/",
              response
            );
            if (verifyResp.status === 200) {
              setPaymentSuccess(true);
              setFormData((prev) => ({ ...prev, coinsPaid: true }));
              setErrors((prev) => {
                const newErrors = { ...prev };
                delete newErrors.coinsPaid;
                return newErrors;
              });
              alert("Payment successful! You can now submit your application.");
            }
          } catch (error) {
            alert(
              "Payment verification failed: " +
                (error.response?.data?.error || error.message)
            );
          } finally {
            setLoading(false);
          }
        },
        prefill: {
          name: formData.name,
          email: formData.email,
          contact: formData.phone,
        },
        theme: {
          color: "#0366d6",
        },
        modal: {
          ondismiss: function() {
            setLoading(false);
          }
        }
      };
      
      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (error) {
      alert(
        "Payment initiation failed: " + (error.response?.data?.error || error.message)
      );
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-[#0a174e] via-[#161f39] to-[#1a213a] p-6">
        <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-8 text-center">
          <div className="mb-4">
            <svg className="mx-auto h-16 w-16 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-blue-900 mb-4">Application Submitted Successfully!</h2>
          <p className="text-gray-700 mb-2">
            Thank you for applying! Your application ID is: <strong>#{applicationId}</strong>
          </p>
          <p className="text-gray-600 mb-6 text-sm">
            We will review your submission through our 3-stage verification process and get back to you via email within 3-5 business days.
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-left">
            <h3 className="font-semibold text-blue-900 mb-2">Next Steps:</h3>
            <ol className="list-decimal list-inside space-y-1 text-gray-700">
              <li>Stage 1: Document verification (1-2 days)</li>
              <li>Stage 2: Identity & union verification (1-2 days)</li>
              <li>Stage 3: Admin approval & account creation (1 day)</li>
            </ol>
            <p className="mt-3 text-gray-600">
              If approved, you'll receive your login credentials via email.
            </p>
          </div>
          <button
            onClick={() => {
              setFormData({
                name: "",
                email: "",
                phone: "",
                address: "",
                skills: "",
                experience: "",
                service_categories: [],
                photo_id_path: null,
                aadhaar_card: null,
                union_card_path: null,
                certifications: null,
                signature_copy: null,
                coinsPaid: false,
              });
              setErrors({});
              setSubmitted(false);
              setPaymentSuccess(false);
              setApplicationId(null);
              setSelectedLocation(null);
            }}
            className="bg-blue-700 text-white px-6 py-2 rounded-lg hover:bg-blue-800 transition"
          >
            Submit Another Application
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-r from-[#0a174e] via-[#161f39] to-[#1a213a] flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-8 overflow-auto max-h-screen">
        <h2 className="text-3xl font-extrabold text-blue-900 mb-6 text-center">
          Worker Application Form
        </h2>

        {/* Information Banner */}
        <div className="bg-blue-100 border border-blue-300 rounded-lg p-4 mb-6 text-blue-900 text-sm leading-relaxed">
          <h3 className="font-bold mb-2">📋 Application Guidelines:</h3>
          <ul className="list-disc list-inside space-y-1">
            <li>Your application will go through <strong>3 verification stages</strong></li>
            <li>If approved, you'll receive login credentials via email</li>
            <li>Application fee: <strong>150 coins</strong> (payment required before submission)</li>
            <li>Ensure all documents are clear and readable</li>
            <li>Review time: <strong>3-5 business days</strong></li>
          </ul>
        </div>

        {/* Payment Section */}
        <div className="mb-6 text-center bg-yellow-50 border border-yellow-300 rounded-lg p-4">
          {!paymentSuccess ? (
            <>
              <p className="text-gray-700 mb-3 text-sm">
                Complete payment before filling the form (your data will be saved)
              </p>
              <button
                onClick={handlePayment}
                disabled={loading}
                className={`bg-yellow-500 text-blue-900 font-extrabold rounded-md px-6 py-3 shadow-md hover:bg-yellow-600 transition transform hover:scale-105 ${
                  loading ? "opacity-50 cursor-not-allowed" : ""
                }`}
              >
                {loading ? "Processing..." : "💰 Pay 150 Coins"}
              </button>
            </>
          ) : (
            <div className="text-green-700 font-semibold flex items-center justify-center">
              <svg className="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              ✅ Payment Successful! Complete the form below.
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Basic Information Section */}
          <div className="border-b pb-4">
            <h3 className="text-xl font-bold text-blue-900 mb-4">📝 Basic Information</h3>
            
            {/* Full Name */}
            <div className="mb-4">
              <label htmlFor="name" className="block text-blue-900 font-semibold mb-1">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                id="name"
                name="name"
                type="text"
                value={formData.name}
                onChange={handleChange}
                className={`w-full px-4 py-2 border rounded-md outline-none transition ${
                  errors.name ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="John Doe"
              />
              {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
            </div>

            {/* Email */}
            <div className="mb-4">
              <label htmlFor="email" className="block text-blue-900 font-semibold mb-1">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                className={`w-full px-4 py-2 border rounded-md outline-none transition ${
                  errors.email ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="you@example.com"
              />
              {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
            </div>

            {/* Phone */}
            <div className="mb-4">
              <label htmlFor="phone" className="block text-blue-900 font-semibold mb-1">
                Phone Number <span className="text-red-500">*</span>
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                value={formData.phone}
                onChange={handleChange}
                className={`w-full px-4 py-2 border rounded-md outline-none transition ${
                  errors.phone ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="+91 98765 43210"
              />
              {errors.phone && <p className="text-red-500 text-sm mt-1">{errors.phone}</p>}
            </div>

            {/* Address with Geoapify Autocomplete */}
            <div className="mb-4 relative">
              <label htmlFor="address" className="block text-blue-900 font-semibold mb-1">
                Complete Address <span className="text-red-500">*</span>
              </label>
              <textarea
                id="address"
                name="address"
                rows={3}
                value={formData.address}
                onChange={handleChange}
                onFocus={() => formData.address.length > 3 && setShowSuggestions(true)}
                className={`w-full px-4 py-2 border rounded-md outline-none resize-none transition ${
                  errors.address ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="Start typing your address..."
              />
              
              {/* Address Suggestions Dropdown */}
              {showSuggestions && addressSuggestions.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                  {addressSuggestions.map((suggestion, index) => (
                    <div
                      key={index}
                      onClick={() => selectAddress(suggestion)}
                      className="px-4 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                    >
                      <p className="text-sm font-medium text-gray-900">{suggestion.formatted}</p>
                      {suggestion.city && (
                        <p className="text-xs text-gray-500">
                          {suggestion.city}, {suggestion.state || suggestion.country}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              {errors.address && <p className="text-red-500 text-sm mt-1">{errors.address}</p>}
              
              <div className="flex items-center mt-2">
                <svg className="h-4 w-4 text-green-600 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <p className="text-xs text-gray-600">
                  {selectedLocation 
                    ? `📍 Location verified: ${selectedLocation.lat.toFixed(4)}, ${selectedLocation.lon.toFixed(4)}`
                    : "Type your address to see suggestions and verify location"
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Professional Details Section */}
          <div className="border-b pb-4">
            <h3 className="text-xl font-bold text-blue-900 mb-4">💼 Professional Details</h3>
            
            {/* Service Categories */}
            <div className="mb-4">
              <label className="block text-blue-900 font-semibold mb-2">
                Service Categories <span className="text-red-500">*</span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {serviceOptions.map((service) => (
                  <label key={service} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      value={service}
                      checked={formData.service_categories.includes(service)}
                      onChange={handleChange}
                      className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                    />
                    <span className="text-gray-700 text-sm">{service}</span>
                  </label>
                ))}
              </div>
              {errors.service_categories && (
                <p className="text-red-500 text-sm mt-1">{errors.service_categories}</p>
              )}
            </div>

            {/* Skills */}
            <div className="mb-4">
              <label htmlFor="skills" className="block text-blue-900 font-semibold mb-1">
                Skills & Expertise <span className="text-red-500">*</span>
              </label>
              <textarea
                id="skills"
                name="skills"
                rows={3}
                value={formData.skills}
                onChange={handleChange}
                className={`w-full px-4 py-2 border rounded-md outline-none resize-none transition ${
                  errors.skills ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="E.g., Expert in residential plumbing, pipe fitting, leak detection..."
              />
              {errors.skills && <p className="text-red-500 text-sm mt-1">{errors.skills}</p>}
            </div>

            {/* Experience */}
            <div className="mb-4">
              <label htmlFor="experience" className="block text-blue-900 font-semibold mb-1">
                Work Experience <span className="text-red-500">*</span>
              </label>
              <textarea
                id="experience"
                name="experience"
                rows={4}
                value={formData.experience}
                onChange={handleChange}
                className={`w-full px-4 py-2 border rounded-md outline-none resize-none transition ${
                  errors.experience ? "border-red-500" : "border-gray-300"
                } focus:ring-2 focus:ring-blue-400`}
                placeholder="Describe your work history, years of experience, notable projects..."
              />
              {errors.experience && <p className="text-red-500 text-sm mt-1">{errors.experience}</p>}
            </div>
          </div>

          {/* Documents Section (address_proof removed) */}
          <div className="border-b pb-4">
            <h3 className="text-xl font-bold text-blue-900 mb-4">📄 Required Documents</h3>
            
            {/* Photo ID */}
            <div className="mb-4">
              <label htmlFor="photo_id_path" className="block text-blue-900 font-semibold mb-1">
                Photo ID <span className="text-red-500">*</span>
              </label>
              <input
                id="photo_id_path"
                name="photo_id_path"
                type="file"
                accept="image/*,.pdf"
                onChange={handleChange}
                className={`w-full ${errors.photo_id_path ? "border-red-500" : "border-gray-300"} rounded-md outline-none transition`}
              />
              <p className="text-xs text-gray-500 mt-1">Upload passport-size photograph</p>
              {errors.photo_id_path && <p className="text-red-500 text-sm mt-1">{errors.photo_id_path}</p>}
            </div>

            {/* Aadhaar Card */}
            <div className="mb-4">
              <label htmlFor="aadhaar_card" className="block text-blue-900 font-semibold mb-1">
                Aadhaar Card <span className="text-red-500">*</span>
              </label>
              <input
                id="aadhaar_card"
                name="aadhaar_card"
                type="file"
                accept="image/*,.pdf"
                onChange={handleChange}
                className={`w-full ${errors.aadhaar_card ? "border-red-500" : "border-gray-300"} rounded-md outline-none transition`}
              />
              <p className="text-xs text-gray-500 mt-1">Front and back (single file or combined PDF) - serves as address proof</p>
              {errors.aadhaar_card && <p className="text-red-500 text-sm mt-1">{errors.aadhaar_card}</p>}
            </div>

            {/* Union Card (Optional) */}
            <div className="mb-4">
              <label htmlFor="union_card_path" className="block text-blue-900 font-semibold mb-1">
                Labor Union Card <span className="text-gray-400 text-sm">(Optional)</span>
              </label>
              <input
                id="union_card_path"
                name="union_card_path"
                type="file"
                accept="image/*,.pdf"
                onChange={handleChange}
                className="w-full border-gray-300 rounded-md outline-none transition"
              />
              <p className="text-xs text-gray-500 mt-1">If you're a member of any labor union</p>
            </div>

            {/* Certifications (Optional) */}
            <div className="mb-4">
              <label htmlFor="certifications" className="block text-blue-900 font-semibold mb-1">
                Professional Certifications <span className="text-gray-400 text-sm">(Optional)</span>
              </label>
              <input
                id="certifications"
                name="certifications"
                type="file"
                accept="image/*,.pdf"
                onChange={handleChange}
                className="w-full border-gray-300 rounded-md outline-none transition"
              />
              <p className="text-xs text-gray-500 mt-1">Trade certificates, training completion documents</p>
            </div>

            {/* Signature (Optional) */}
            <div className="mb-4">
              <label htmlFor="signature_copy" className="block text-blue-900 font-semibold mb-1">
                Signature Specimen <span className="text-gray-400 text-sm">(Optional)</span>
              </label>
              <input
                id="signature_copy"
                name="signature_copy"
                type="file"
                accept="image/*"
                onChange={handleChange}
                className="w-full border-gray-300 rounded-md outline-none transition"
              />
              <p className="text-xs text-gray-500 mt-1">Clear image of your signature</p>
            </div>
          </div>

          {/* Payment Confirmation */}
          <div className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg">
            <input
              id="coinsPaid"
              name="coinsPaid"
              type="checkbox"
              checked={formData.coinsPaid}
              readOnly
              className="h-5 w-5 text-blue-600 border-gray-300 rounded"
            />
            <label htmlFor="coinsPaid" className="block text-blue-900 font-semibold">
              {formData.coinsPaid ? "✅ 150 coins payment received" : "⚠️ Payment pending"}
            </label>
          </div>
          {errors.coinsPaid && <p className="text-red-500 text-sm">{errors.coinsPaid}</p>}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!formData.coinsPaid || loading}
            className={`w-full text-white font-bold py-3 rounded-lg transition ${
              formData.coinsPaid && !loading
                ? "bg-blue-700 hover:bg-blue-800"
                : "bg-gray-400 cursor-not-allowed"
            }`}
          >
            {loading ? "Processing..." : "Submit Application"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default WorkerApplicationPage;
