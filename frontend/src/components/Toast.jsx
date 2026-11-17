import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import './Toast.css';

export default function Toast({ message, type = 'error', link, onClose, duration = 4000 }) {
  const [visible, setVisible] = useState(true);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => {
      setFadeOut(true);
    }, duration - 300);

    const closeTimer = setTimeout(() => {
      setVisible(false);
      onClose?.();
    }, duration);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(closeTimer);
    };
  }, [duration, onClose]);

  if (!visible) return null;

  return (
    <div className={`toast toast--${type} ${fadeOut ? 'toast--fade-out' : ''}`} role="alert">
      <div className="toast__content">
        {link ? (
          <>
            <Link to={link.to} className="toast__link">{link.text}</Link> {message}
          </>
        ) : (
          message
        )}
      </div>
      <button
        type="button"
        className="toast__close"
        onClick={() => {
          setFadeOut(true);
          setTimeout(() => {
            setVisible(false);
            onClose?.();
          }, 300);
        }}
        aria-label="Close notification"
      >
        ×
      </button>
    </div>
  );
}
