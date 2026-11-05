import { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from './AuthContext';
import { USE_MOCK } from '../api/client';
import * as api from '../api/wishlistApi';

const WishlistContext = createContext(null);

function loadLocal(key) {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || '[]');
    return Array.isArray(saved) ? saved.filter((p) => p && p.id != null && p.notes) : [];
  } catch { return []; }
}

export function WishlistProvider({ children }) {
  const { user } = useAuth();
  const remote = !!user && !USE_MOCK;
  const scope = `${USE_MOCK ? 'mock' : 'real'}:${user?.id ?? 'guest'}`;
  const storageKey = `ml_wishlist:${scope}`;
  const currentScope = useRef(scope);
  currentScope.current = scope;
  const [state, setState] = useState({ scope: null, items: [], loading: true, error: '' });
  const [version, setVersion] = useState(0);
  const [pending, setPending] = useState(new Set());
  const inFlight = useRef(new Set());

  useEffect(() => {
    let active = true;
    setState({ scope, items: [], loading: true, error: '' });
    const load = remote ? api.getWishlist() : Promise.resolve(loadLocal(storageKey));
    load.then((items) => {
      if (active) setState({ scope, items, loading: false, error: '' });
    }).catch((error) => {
      if (active) setState({ scope, items: [], loading: false, error: error.message });
    });
    return () => { active = false; };
  }, [scope, remote, storageKey, version]);

  const items = state.scope === scope ? state.items : [];
  const loading = state.scope !== scope || state.loading;
  const toggle = async (product) => {
    const key = `${scope}:${product.id}`;
    if (loading || state.error || inFlight.current.has(key)) return;
    inFlight.current.add(key);
    setPending(new Set(inFlight.current));
    const exists = items.some((p) => p.id === product.id);
    try {
      const saved = remote && !exists ? await api.addToWishlist(product.id) : product;
      if (remote && exists) await api.removeFromWishlist(product.id);
      if (currentScope.current !== scope) return;
      setState((previous) => {
        if (previous.scope !== scope) return previous;
        const next = exists ? previous.items.filter((p) => p.id !== product.id) : [saved, ...previous.items];
        if (!remote) {
          try { localStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* session still works */ }
        }
        return { ...previous, items: next };
      });
    } finally {
      inFlight.current.delete(key);
      setPending(new Set(inFlight.current));
    }
  };

  return <WishlistContext.Provider value={{
    items, loading, error: state.scope === scope ? state.error : '', toggle,
    isWishlisted: (id) => items.some((p) => p.id === id),
    isPending: (id) => pending.has(`${scope}:${id}`),
    reload: () => setVersion((value) => value + 1),
  }}>{children}</WishlistContext.Provider>;
}

export const useWishlist = () => useContext(WishlistContext);
