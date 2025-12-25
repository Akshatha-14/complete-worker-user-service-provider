import { useState } from "react";

export default function DemoWorkCompletion() {
  const [assignmentId, setAssignmentId] = useState("");
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [result, setResult] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const res = await fetch(
      `http://localhost:8000/api/workers/demo/${assignmentId}/complete/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, feedback }),
      }
    );
    const data = await res.json();
    setResult(data);
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>Demo Work Completion (Step 3)</h2>
      <form onSubmit={submit}>
        <input
          placeholder="Assignment ID"
          value={assignmentId}
          onChange={(e) => setAssignmentId(e.target.value)}
          required
        /><br />

        <label>
          Rating (1–5):{" "}
          <input
            type="number"
            min="1"
            max="5"
            value={rating}
            onChange={(e) => setRating(e.target.value)}
            required
          />
        </label><br />

        <textarea
          placeholder="Feedback"
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        /><br />

        <button type="submit">Submit Completion</button>
      </form>

      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>✅ Submission Saved</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
