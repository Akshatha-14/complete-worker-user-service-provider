// src/components/Verifier3/ApplicationDetail3.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';
import Zoom from 'react-medium-image-zoom';
import 'react-medium-image-zoom/dist/styles.css';

const BASE_URL = process.env.REACT_APP_BACKEND_ORIGIN || 'http://localhost:8000';

export default function ApplicationDetail3() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [application, setApplication] = useState(null);
  const [review, setReview] = useState(null);
  const [localReview, setLocalReview] = useState({
    location_verified: false,
    skill_verified: false,
    comments: '',
    status: 'pending'
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(()=>{ fetchAll(); /*eslint-disable-next-line*/ }, [id]);

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [appRes, reviewRes] = await Promise.all([
        api.get(`/verifier3/applications/${id}/`),
        api.get(`/verifier3/applications/${id}/review_status/`).catch(()=>({data:{exists:false}}))
      ]);
      setApplication(appRes.data);
      if (reviewRes.data && reviewRes.data.exists === false) {
        setReview(null);
      } else {
        setReview(reviewRes.data);
        setLocalReview({
          location_verified: reviewRes.data.location_verified || false,
          skill_verified: reviewRes.data.skill_verified || false,
          comments: reviewRes.data.comments || '',
          status: reviewRes.data.status || 'pending'
        });
      }
    } catch (err) {
      console.error(err);
      alert('Failed to load application');
    } finally {
      setLoading(false);
    }
  };

  const ensureReviewExists = async () => {
    if (review && review.id) return review.id;
    try {
      const res = await api.post('/verifier3/reviews/', { application: parseInt(id) });
      setReview(res.data);
      return res.data.id;
    } catch (err) {
      console.error('create verifier3 review', err);
      alert('Cannot create review record');
      return null;
    }
  };

  const toggleField = (field) => setLocalReview(prev => ({ ...prev, [field]: !prev[field] }));

  const handleSubmit = async () => {
    const reviewId = await ensureReviewExists();
    if (!reviewId) return;
    setSubmitting(true);
    try {
      const payload = {
        location_verified: localReview.location_verified,
        skill_verified: localReview.skill_verified,
        comments: localReview.comments,
        status: localReview.status,
        is_submitted: true,
        submitted_at: new Date().toISOString(),
      };

      if (review && review.id) {
        await api.patch(`/verifier3/reviews/${reviewId}/`, payload);
      } else {
        await api.post('/verifier3/reviews/', { application: parseInt(id), ...payload });
      }

      alert(`Verification submitted as ${payload.status.toUpperCase()}`);
      navigate('/verifier3');
    } catch (err) {
      console.error('submit verifier3', err);
      alert('Failed to submit verification');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-center">Loading...</div>;
  if (!application) return <div className="p-8 text-center text-red-600">Application not found</div>;

  const unionCard = application.union_card_path;
  const unionUrl = unionCard ? (unionCard.startsWith('http') ? unionCard : `${BASE_URL}${unionCard}`) : null;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <button onClick={() => navigate('/verifier3')} className="text-blue-600 hover:underline">&larr; Back to Applications</button>

        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-bold">Worker Information</h2>
          <p><b>Name:</b> {application.name}</p>
          <p><b>Email:</b> {application.email}</p>
          <p><b>Address:</b> {application.address}</p>
          <p><b>Skills:</b> {application.skills}</p>
        </div>

        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold">Union Card</h3>
          <div className="border p-2 rounded text-center mt-3">
            {unionUrl ? (
              <Zoom>
                <img src={unionUrl} alt="Union Card" className="h-48 w-full object-contain mx-auto" onError={(e)=>{e.target.src='/placeholder.png'}} />
              </Zoom>
            ) : <p className="italic text-gray-400">No union card uploaded</p>}
            <p className="mt-2">Union Card</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded shadow">
          <h3 className="text-lg font-semibold">On-site Verification</h3>
          <div className="space-y-2 mt-3">
            {['location_verified','skill_verified'].map(f => (
              <label key={f} className="flex items-center gap-3">
                <input type="checkbox" checked={!!localReview[f]} onChange={() => toggleField(f)} />
                <span className="capitalize">{f.replace(/_/g,' ')}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded shadow max-w-xl">
          <h3 className="text-lg font-semibold">Final Decision</h3>
          <div className="mt-3 space-y-3">
            <select className="w-full border p-2 rounded" value={localReview.status} onChange={(e)=>setLocalReview({...localReview, status: e.target.value})}>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>

            <textarea placeholder="Comments" value={localReview.comments} onChange={(e)=>setLocalReview({...localReview, comments: e.target.value})} className="w-full border p-2 rounded" rows={3} />

            <button disabled={submitting} onClick={handleSubmit} className={`w-full py-3 rounded text-white ${submitting ? 'bg-gray-400' : 'bg-blue-600 hover:bg-blue-700'}`}>
              {submitting ? 'Submitting...' : 'Submit Verification'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
