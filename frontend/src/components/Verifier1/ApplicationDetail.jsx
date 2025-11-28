import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

// Get CSRF token from cookie
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

// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add CSRF token to requests
api.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  
  const authToken = localStorage.getItem('authToken');
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  
  return config;
});

// API Methods
const getApplicationDetail = (id) => api.get(`/verifier1/applications/${id}/`);
const getApplicationDocuments = (id) => api.get(`/verifier1/applications/${id}/documents/`);
const getReviewStatus = (id) => api.get(`/verifier1/applications/${id}/review_status/`);
const getApplicationLogs = (id) => api.get(`/verifier1/applications/${id}/logs/`);
const createReview = (data) => api.post('/verifier1/reviews/', data);
const updateReview = (id, data) => api.patch(`/verifier1/reviews/${id}/`, data);
const getCsrf = () => api.get('/csrf/');

// Component
function ApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [application, setApplication] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [existingReview, setExistingReview] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  
  const [reviewData, setReviewData] = useState({
    all_documents_uploaded: false,
    documents_legible: false,
    correct_format: false,
    no_missing_fields: false,
    files_not_corrupted: false,
    expiry_dates_valid: false,
    status: 'pending',
    comments: '',
    issues_found: '',
  });

  useEffect(() => {
    fetchCsrf();
    fetchData();
  }, [id]);

  const fetchCsrf = async () => {
    try {
      await getCsrf();
    } catch (err) {
      console.error('Failed to fetch CSRF token:', err);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      
      const appRes = await getApplicationDetail(id);
      setApplication(appRes.data);
      
      const docsRes = await getApplicationDocuments(id);
      setDocuments(docsRes.data);
      
      const logsRes = await getApplicationLogs(id);
      setLogs(logsRes.data);
      
      try {
        const reviewRes = await getReviewStatus(id);
        if (reviewRes.data && reviewRes.data.exists !== false) {
          setExistingReview(reviewRes.data);
          setReviewData({
            all_documents_uploaded: reviewRes.data.all_documents_uploaded,
            documents_legible: reviewRes.data.documents_legible,
            correct_format: reviewRes.data.correct_format,
            no_missing_fields: reviewRes.data.no_missing_fields,
            files_not_corrupted: reviewRes.data.files_not_corrupted,
            expiry_dates_valid: reviewRes.data.expiry_dates_valid,
            status: reviewRes.data.status,
            comments: reviewRes.data.comments || '',
            issues_found: reviewRes.data.issues_found || '',
          });
        }
      } catch (err) {
        console.log('No existing review');
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
      alert('Failed to load application details');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckboxChange = (field) => {
    setReviewData({ ...reviewData, [field]: !reviewData[field] });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (reviewData.status === 'pending') {
      alert('Please select a review status');
      return;
    }
    
    try {
      setSubmitting(true);
      
      const payload = {
        application: parseInt(id),
        ...reviewData,
      };
      
      if (existingReview) {
        await updateReview(existingReview.id, payload);
        alert('Review updated successfully!');
      } else {
        await createReview(payload);
        alert('Review submitted successfully!');
      }
      
      navigate('/verifier1');
    } catch (err) {
      console.error('Failed to submit review:', err);
      const errorMsg = err.response?.data?.error || err.response?.data?.detail || err.message;
      alert('Failed to submit review: ' + errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!application) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-600">Application not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate('/verifier1')}
              className="text-blue-600 hover:text-blue-800 mb-2"
            >
              ← Back to Applications
            </button>
            <h1 className="text-3xl font-bold text-gray-900">Review Application</h1>
            <p className="text-gray-600 mt-1">ID: #{application.id}</p>
            {application.stage1_completed && (
              <p className="text-orange-600 text-sm mt-1">⚠️ This review is editable for 2 days after submission</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-bold mb-4">Applicant Information</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Name</p>
                  <p className="font-medium">{application.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Email</p>
                  <p className="font-medium">{application.email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Phone</p>
                  <p className="font-medium">{application.phone}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Applied</p>
                  <p className="font-medium">{new Date(application.applied_at).toLocaleDateString()}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-gray-600">Address</p>
                  <p className="font-medium">{application.address || 'Not provided'}</p>
                </div>
                {application.latitude && application.longitude && (
                  <div className="col-span-2">
                    <p className="text-sm text-gray-600">Location Coordinates</p>
                    <p className="font-medium">
                      📍 Latitude: {application.latitude}, Longitude: {application.longitude}
                    </p>
                    <a 
                      href={`https://www.google.com/maps?q=${application.latitude},${application.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 text-sm hover:underline"
                    >
                      View on Google Maps →
                    </a>
                  </div>
                )}
                <div className="col-span-2">
                  <p className="text-sm text-gray-600">Skills</p>
                  <p className="font-medium">{application.skills}</p>
                </div>
                <div className="col-span-2">
                  <p className="text-sm text-gray-600">Experience</p>
                  <p className="font-medium">{application.experience}</p>
                </div>
              </div>
            </div>

            {documents && (
              <div className="bg-white p-6 rounded-lg shadow">
                <h2 className="text-xl font-bold mb-4">Documents</h2>
                {Object.entries(documents).map(([key, url]) => url && (
                  <div key={key} className="mb-4 p-3 border rounded">
                    <p className="font-medium mb-2">{key.replace('_', ' ').toUpperCase()}</p>
                    <a href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      View Document →
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <div className="bg-white p-6 rounded-lg shadow sticky top-6">
              <h2 className="text-xl font-bold mb-4">
                {existingReview ? 'Update Review' : 'Submit Review'}
              </h2>
              
              <form onSubmit={handleSubmit} className="space-y-4">
                {[
                  { field: 'all_documents_uploaded', label: 'All documents uploaded' },
                  { field: 'documents_legible', label: 'Documents legible' },
                  { field: 'correct_format', label: 'Correct format' },
                  { field: 'no_missing_fields', label: 'No missing fields' },
                  { field: 'files_not_corrupted', label: 'Files not corrupted' },
                  { field: 'expiry_dates_valid', label: 'Expiry dates valid' },
                ].map(({ field, label }) => (
                  <label key={field} className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={reviewData[field]}
                      onChange={() => handleCheckboxChange(field)}
                      className="h-5 w-5 text-blue-600 rounded"
                    />
                    <span className="ml-3">{label}</span>
                  </label>
                ))}

                <div className="pt-4 border-t">
                  <label className="block mb-2 font-medium">Status</label>
                  <select
                    value={reviewData.status}
                    onChange={(e) => setReviewData({ ...reviewData, status: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md"
                  >
                    <option value="pending">Select...</option>
                    <option value="approved">✅ Approved</option>
                    <option value="rejected">❌ Rejected</option>
                    <option value="resubmission_required">🔄 Resubmission Required</option>
                  </select>
                </div>

                <div>
                  <label className="block mb-2 font-medium">Comments</label>
                  <textarea
                    value={reviewData.comments}
                    onChange={(e) => setReviewData({ ...reviewData, comments: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-md"
                    placeholder="Add your comments here..."
                  />
                </div>

                <div>
                  <label className="block mb-2 font-medium">Issues Found</label>
                  <textarea
                    value={reviewData.issues_found}
                    onChange={(e) => setReviewData({ ...reviewData, issues_found: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 border rounded-md"
                    placeholder="List any issues found..."
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className={`w-full py-3 rounded-md font-semibold text-white ${
                    submitting ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {submitting ? 'Submitting...' : existingReview ? 'Update Review' : 'Submit Review'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ApplicationDetail;
