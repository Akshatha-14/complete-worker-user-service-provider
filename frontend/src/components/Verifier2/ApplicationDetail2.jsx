// src/components/Verifier2/ApplicationDetail2.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';
import Zoom from 'react-medium-image-zoom';
import 'react-medium-image-zoom/dist/styles.css';

const BASE_URL = process.env.REACT_APP_BACKEND_ORIGIN || 'http://localhost:8000';

export default function ApplicationDetail2() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [application, setApplication] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [review, setReview] = useState(null);
  const [localReview, setLocalReview] = useState({
    photo_matches_id: false,
    aadhaar_verified: false,
    union_membership_verified: false,
    address_verified: false,
    otp_sent: false,
    otp_verified: false,
    status: 'pending',
    comments: '',
    discrepancies_found: ''
  });
  const [otpInput, setOtpInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [appRes, docsRes, reviewRes] = await Promise.all([
        api.get(`/verifier2/applications/${id}/`),
        api.get(`/verifier2/applications/${id}/documents/`),
        api.get(`/verifier2/applications/${id}/review_status/`).catch(() => ({ data: { exists: false } })),
      ]);

      setApplication(appRes.data);
      setDocuments(docsRes.data || []);

      if (reviewRes.data && reviewRes.data.exists === false) {
        setReview(null);
        setLocalReview(prev => ({ ...prev }));
      } else {
        setReview(reviewRes.data);
        setLocalReview(prev => ({
          ...prev,
          photo_matches_id: reviewRes.data.photo_matches_id || false,
          aadhaar_verified: reviewRes.data.aadhaar_verified || false,
          union_membership_verified: reviewRes.data.union_membership_verified || false,
          address_verified: reviewRes.data.address_verified || false,
          otp_sent: reviewRes.data.otp_sent || false,
          otp_verified: reviewRes.data.otp_verified || false,
          status: reviewRes.data.status || 'pending',
          comments: reviewRes.data.comments || '',
          discrepancies_found: reviewRes.data.discrepancies_found || ''
        }));
      }
    } catch (err) {
      console.error('Fetch error', err);
      alert('Failed to load application data');
    } finally {
      setLoading(false);
    }
  };

  const ensureReviewExistsAndReturnId = async () => {
    if (review && review.id) return review.id;
    // create empty review
    try {
      const res = await api.post('/verifier2/reviews/', { application: parseInt(id) });
      setReview(res.data);
      return res.data.id;
    } catch (err) {
      console.error('Failed create review', err);
      alert('Failed to create review record');
      return null;
    }
  };

  const handleToggle = (field) => {
    setLocalReview(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const sendOtp = async () => {
    const reviewId = await ensureReviewExistsAndReturnId();
    if (!reviewId) return;
    try {
      const res = await api.post(`/verifier2/reviews/${reviewId}/send_otp/`);
      setLocalReview(prev => ({ ...prev, otp_sent: true }));
      alert(res.data.message || 'OTP sent');
    } catch (err) {
      console.error('send otp error', err);
      alert('Failed to send OTP');
    }
  };

  const verifyOtp = async () => {
    const reviewId = await ensureReviewExistsAndReturnId();
    if (!reviewId) return;
    try {
      const res = await api.post(`/verifier2/reviews/${reviewId}/verify_otp/`, { otp_code: otpInput });
      if (res.data.verified) {
        setLocalReview(prev => ({ ...prev, otp_verified: true }));
        alert('OTP verified');
      } else {
        alert('Invalid OTP');
      }
    } catch (err) {
      console.error('verify otp', err);
      alert('OTP verification failed');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const reviewId = await ensureReviewExistsAndReturnId();
    if (!reviewId) return;
    setSubmitting(true);
    try {
      const payload = {
        photo_matches_id: localReview.photo_matches_id,
        aadhaar_verified: localReview.aadhaar_verified,
        union_membership_verified: localReview.union_membership_verified,
        address_verified: localReview.address_verified,
        otp_sent: localReview.otp_sent,
        otp_verified: localReview.otp_verified,
        status: localReview.status,
        comments: localReview.comments,
        discrepancies_found: localReview.discrepancies_found,
        is_submitted: true,
        submitted_at: new Date().toISOString()
      };

      await api.patch(`/verifier2/reviews/${reviewId}/`, payload);
      alert(`Review ${payload.status.toUpperCase()} submitted`);
      navigate('/verifier2');
    } catch (err) {
      console.error('submit review', err);
      alert('Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center p-8">Loading...</div>;
  if (!application) return <div className="p-8 text-center text-red-600">Application not found</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <button onClick={() => navigate('/verifier2')} className="text-blue-600 hover:underline">&larr; Back to Applications</button>
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-bold">Worker Information</h2>
          <p><b>Name:</b> {application.name}</p>
          <p><b>Email:</b> {application.email}</p>
          <p><b>Address:</b> {application.address}</p>
        </div>

        <div className="bg-blue-50 p-6 rounded shadow">
  <h3 className="text-lg font-semibold text-blue-700">Verifier 1 Summary</h3>
  <p><b>Status:</b> {application.verifier1_summary?.status || 'Not reviewed'}</p>
  <p><b>Comments:</b> {application.verifier1_summary?.comments || '—'}</p>
</div>


        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold">Documents</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4">
            {['photo_id_path','aadhaar_card','union_card_path','certifications','signature_copy'].map(key => {
              const file = application[key];
              let url = null;
              if (file) {
                if (typeof file === 'string' && file.startsWith('http')) url = file;
                else if (typeof file === 'string' && file.startsWith('/')) url = `${BASE_URL}${file}`;
              }
              return (
                <div key={key} className="border p-2 rounded text-center">
                  {url ? (
                    <Zoom>
                      <img src={url} alt={key} className="h-40 w-full object-contain mx-auto" onError={(e)=>{e.target.src='/placeholder.png'}}/>
                    </Zoom>
                  ) : <p className="italic text-gray-400">No {key.replace(/_/g,' ')} uploaded</p>}
                  <p className="mt-2">{key.replace(/_/g,' ')}</p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold">Verification Checklist</h3>
          <div className="space-y-2 mt-4">
            {['photo_matches_id','aadhaar_verified','union_membership_verified','address_verified'].map(f => (
              <label key={f} className="flex items-center gap-3">
                <input type="checkbox" checked={!!localReview[f]} onChange={() => handleToggle(f)} />
                <span className="capitalize">{f.replace(/_/g,' ')}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded shadow max-w-md">
          <h3 className="text-lg font-semibold">OTP Verification</h3>
          <p>Email: {application.email}</p>
          <div className="mt-3 flex flex-col gap-2">
            <button onClick={sendOtp} className="py-2 px-3 bg-blue-600 text-white rounded">Send OTP</button>

            {localReview.otp_sent && !localReview.otp_verified && (
              <div className="flex gap-2">
                <input value={otpInput} onChange={(e)=>setOtpInput(e.target.value)} className="border p-2 rounded flex-1" placeholder="Enter OTP"/>
                <button onClick={verifyOtp} className="py-2 px-3 bg-green-600 text-white rounded">Verify</button>
              </div>
            )}

            {localReview.otp_verified && <div className="text-green-600 font-semibold">✅ Verified</div>}
          </div>
        </div>

        <div className="bg-white p-6 rounded shadow max-w-xl">
          <h3 className="text-lg font-semibold">Final Decision</h3>
          <div className="mt-3 space-y-3">
            <select className="w-full border p-2 rounded" value={localReview.status} onChange={(e)=>setLocalReview({...localReview, status: e.target.value})}>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="correction_required">Correction Required</option>
            </select>
            <textarea placeholder="Comments" value={localReview.comments} onChange={(e)=>setLocalReview({...localReview, comments: e.target.value})} className="w-full border p-2 rounded" rows={3} />
            <textarea placeholder="Discrepancies Found" value={localReview.discrepancies_found} onChange={(e)=>setLocalReview({...localReview, discrepancies_found: e.target.value})} className="w-full border p-2 rounded" rows={2} />
            <button disabled={submitting} onClick={handleSubmit} className={`w-full py-3 rounded text-white ${submitting ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}>
              {submitting ? 'Submitting...' : 'Submit Review'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
