import { useState } from 'react';
import './StarRating.css';

/**
 * StarRating component for displaying and optionally submitting ratings
 * @param {number} rating - Current rating (0-5)
 * @param {function} onRate - Optional callback when user clicks a star
 * @param {boolean} readonly - If true, stars are not clickable
 * @param {number} size - Star size in pixels (default: 24)
 */
export default function StarRating({ rating = 0, onRate, readonly = false, size = 24 }) {
  const [hoverRating, setHoverRating] = useState(0);

  const displayRating = hoverRating || rating;

  const handleClick = (score) => {
    if (!readonly && onRate) {
      onRate(score);
    }
  };

  return (
    <div
      className={`star-rating ${readonly ? 'star-rating--readonly' : 'star-rating--interactive'}`}
      onMouseLeave={() => setHoverRating(0)}
      style={{ fontSize: `${size}px` }}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          className={`star ${displayRating >= star ? 'star--filled' : 'star--empty'}`}
          onMouseEnter={() => !readonly && setHoverRating(star)}
          onClick={() => handleClick(star)}
          role={readonly ? 'img' : 'button'}
          aria-label={`${star} star${star > 1 ? 's' : ''}`}
        >
          ★
        </span>
      ))}
    </div>
  );
}
