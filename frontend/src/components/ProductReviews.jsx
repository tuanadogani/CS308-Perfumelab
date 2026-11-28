import { useEffect, useState } from 'react';
import StarRating from './StarRating';
import {
  getProductComments, getUserRating, submitComment, submitRating, updateComment,
} from '../api/reviewApi';
import { useAuth } from '../context/AuthContext';
import { ROLES } from '../constants/roles';

/**
 * Requirement 5: everyone can read approved reviews; only a customer who has received the
 * product sees the form. A star rating is required the first time and goes live at once;
 * comments are optional, can be posted more than once, and wait for a product manager.
 * The author sees their own waiting comments (faded) and can edit them until they are reviewed.
 */
export default function ProductReviews({ productId, rating, ratingCount = 0, onRated }) {
  const { user } = useAuth();
  const isCustomer = user?.role === ROLES.CUSTOMER;
  const [comments, setComments] = useState([]);
  const [mine, setMine] = useState(null); // { score, canReview, pendingComments: [{id, text, createdAt}] }

  const loadComments = () => getProductComments(productId).then(setComments).catch(() => {});
  const loadMine = () => (isCustomer
    ? getUserRating(productId).then(setMine).catch(() => {}) // no form when eligibility is unknown
    : Promise.resolve());

  useEffect(() => {
    setComments([]); setMine(null);
    loadComments();
    loadMine();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, isCustomer]);

  const pending = mine?.pendingComments ?? [];
  const setPending = (update) => setMine((m) => ({ ...m, pendingComments: update(m.pendingComments ?? []) }));

  return (
    <section className="reviews-section" id="reviews">
      <div className="reviews-section__head">
        <h2>Reviews &amp; Ratings</h2>
        <RatingSummary rating={rating} count={ratingCount} />
      </div>

      {mine?.canReview && (
        <ReviewForm
          productId={productId}
          savedScore={mine.score}
          onSaved={({ score, comment }) => {
            setMine((m) => ({
              ...m,
              score,
              pendingComments: comment ? [comment, ...(m.pendingComments ?? [])] : m.pendingComments,
            }));
            if (score !== mine.score) onRated?.();
          }}
        />
      )}

      <div className="comments-list">
        <h3>Customer Reviews ({comments.length})</h3>
        {pending.length === 0 && comments.length === 0 && <p className="muted">No reviews yet.</p>}
        <div className="comments">
          {pending.map((comment) => (
            <PendingComment
              key={comment.id}
              comment={comment}
              authorName={user?.name}
              score={mine?.score}
              onChange={(updated) => setPending((list) => list.map((c) => (c.id === updated.id ? updated : c)))}
              onLocked={() => { loadMine(); loadComments(); }}
            />
          ))}
          {comments.map((comment) => (
            <div key={comment.id} className="comment-card">
              <CommentHeader name={comment.customerName} score={comment.rating} date={comment.createdAt} />
              <p>{comment.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CommentHeader({ name, score, date, children }) {
  return (
    <div className="comment-header">
      <div className="comment-header__author">
        <strong>{name}</strong>
        {score ? (
          <span className="comment-header__rating" aria-label={`Rated ${score} out of 5`}>
            <StarRating rating={score} readonly size={14} />
          </span>
        ) : null}
        {children}
      </div>
      <span className="muted small">{new Date(date).toLocaleDateString()}</span>
    </div>
  );
}

export function RatingSummary({ rating, count }) {
  if (!count) return <p className="muted rating-summary">No ratings yet</p>;
  return (
    <div className="rating-summary" aria-label={`Rated ${rating} out of 5 by ${count} customer${count === 1 ? '' : 's'}`}>
      <StarRating rating={Math.round(rating)} readonly size={18} />
      <strong>{rating.toFixed(1)}</strong>
      <span className="muted small">({count} rating{count === 1 ? '' : 's'})</span>
    </div>
  );
}

/** The author's own comment while it waits for approval: faded, click to edit. */
function PendingComment({ comment, authorName, score, onChange, onLocked }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(comment.text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const startEditing = () => { setText(comment.text); setError(''); setEditing(true); };

  const save = async (e) => {
    e.preventDefault();
    if (!text.trim() || saving) return;
    setSaving(true); setError('');
    try {
      onChange(await updateComment(comment.id, text));
      setEditing(false);
    } catch (err) {
      setError(err.message || 'Could not save your changes.');
      if (err.status === 400 || err.status === 404) setTimeout(onLocked, 2500); // it was reviewed meanwhile
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="comment-card comment-card--pending">
      <CommentHeader name={authorName} score={score} date={comment.createdAt}>
        <span className="comment-card__badge">Awaiting approval</span>
      </CommentHeader>
      {editing ? (
        <form className="comment-edit" onSubmit={save}>
          <label className="sr-only" htmlFor={`edit-comment-${comment.id}`}>Edit your comment</label>
          <textarea id={`edit-comment-${comment.id}`} value={text} rows={3} maxLength={2000}
            onChange={(e) => setText(e.target.value)} autoFocus />
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="comment-edit__actions">
            <button type="submit" className="btn btn-dark" disabled={!text.trim() || saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button type="button" className="link-btn" disabled={saving} onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button type="button" className="comment-card__edit" onClick={startEditing}
          title="Only visible to you until approved. Click to edit.">
          <p>{comment.text}</p>
          <span className="muted small">Only you can see this until it is approved · Click to edit</span>
        </button>
      )}
    </div>
  );
}

function ReviewForm({ productId, savedScore, onSaved }) {
  const [score, setScore] = useState(savedScore ?? 0);
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const rated = savedScore != null;
  const comment = text.trim();
  const scoreChanged = !!score && score !== savedScore;
  const canSend = !!score && (scoreChanged || !!comment);
  const label = !rated ? 'Submit review'
    : scoreChanged && comment ? 'Save rating & post comment'
      : scoreChanged ? 'Update rating' : 'Post comment';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSend || saving) return;
    setSaving(true); setError(''); setSuccess('');
    try {
      if (scoreChanged) await submitRating(productId, score);
      const posted = comment ? await submitComment(productId, comment) : null;
      setText('');
      setSuccess([
        scoreChanged && 'Your rating is live.',
        posted && 'Your comment will appear for everyone after our team approves it.',
      ].filter(Boolean).join(' '));
      onSaved({ score, comment: posted && { id: posted.id, text: posted.text, createdAt: posted.createdAt } });
    } catch (err) {
      setError(err.message || 'Could not save your review.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="review-submit" onSubmit={handleSubmit}>
      <div className="rating-submit">
        <h3>{rated ? 'Your rating' : 'Rate this perfume'}</h3>
        <div className="rating-submit__stars">
          <StarRating rating={score} onRate={setScore} />
          <span className="muted small">
            {score ? `${score}/5` : 'Choose 1–5 stars'}
            {rated && !scoreChanged && ' · click a star to change it'}
          </span>
        </div>
      </div>

      <div className="comment-submit">
        <label htmlFor="review-comment">
          <h3>{rated ? 'Add a comment' : 'Comment'} <span className="muted small">(optional)</span></h3>
        </label>
        <textarea
          id="review-comment"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Share your experience with this perfume…"
          rows={4}
          maxLength={2000}
        />
        <p className="muted small">
          You can post more than one comment. Comments are shown after approval; ratings count right away.
        </p>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      {success && <p className="form-success" role="status">Thank you! {success}</p>}

      <div>
        <button type="submit" className="btn btn-dark" disabled={!canSend || saving}>
          {saving ? 'Saving…' : label}
        </button>
      </div>
    </form>
  );
}
