// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import ProductReviews, { RatingSummary } from '../components/ProductReviews';

// Requirement 5: approved reviews are public; the form only appears after delivery;
// a rating can be sent without a comment; comments can be posted repeatedly and edited
// by their author until a product manager reviews them.

const auth = vi.hoisted(() => ({ user: null }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }));

const CUSTOMER = { id: 1, name: 'Ross Customer', role: 'customer' };
const json = (data, status = 200) => ({ ok: status < 400, status, json: async () => data });
const APPROVED = [
  { id: 1, customerName: 'Ada', rating: 4, text: 'Lovely scent', approved: true, createdAt: '2026-11-20T10:00:00Z' },
  { id: 2, customerName: 'Grace', rating: null, text: 'No stars from me', approved: true, createdAt: '2026-11-21T10:00:00Z' },
];
const NOT_ELIGIBLE = { score: null, canReview: false, pendingComments: [] };
const ELIGIBLE = { score: null, canReview: true, pendingComments: [] };

function server({ comments = APPROVED, mine = NOT_ELIGIBLE, fail } = {}) {
  const calls = [];
  let nextId = 50;
  vi.stubGlobal('fetch', vi.fn(async (url, init = {}) => {
    const method = init.method ?? 'GET';
    const body = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ method, url, body });
    const forced = fail?.(method, url);
    if (forced) return forced;
    if (url.endsWith('/comments/') && method === 'GET') return json(comments);
    if (url.endsWith('/comments/') && method === 'POST') {
      return json({ id: nextId++, text: body.text, approved: false, createdAt: '2026-11-28T10:00:00Z' }, 201);
    }
    if (url.endsWith('/rating/') && method === 'GET') return json(mine);
    if (url.endsWith('/rating/') && method === 'PUT') return json({ score: body.score });
    if (url.startsWith('/api/comments/') && method === 'PATCH') {
      return json({ id: Number(url.split('/')[3]), text: body.text.trim(), createdAt: '2026-11-27T10:00:00Z' });
    }
    return json({}, 404);
  }));
  return calls;
}

const renderReviews = (props = {}) => render(<ProductReviews productId={7} rating={4.5} ratingCount={2} {...props} />);
const star = async (n) => (await screen.findAllByRole('button', { name: `${n} star${n > 1 ? 's' : ''}` }))[0];

afterEach(() => { cleanup(); vi.unstubAllGlobals(); auth.user = null; });

describe('ProductReviews visibility', () => {
  it('shows approved reviews to guests but no form and no eligibility call', async () => {
    const calls = server();
    renderReviews();
    expect(await screen.findByText('Lovely scent')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Submit review/ })).toBeNull();
    expect(screen.queryByText(/Log in/)).toBeNull();
    expect(calls.some((c) => c.url.endsWith('/rating/'))).toBe(false);
  });

  it('hides the form from a customer who has not received the product', async () => {
    server();
    auth.user = CUSTOMER;
    renderReviews();
    expect(await screen.findByText('Lovely scent')).toBeTruthy();
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('button', { name: /Submit review/ })).toBeNull();
  });

  it('never asks staff for eligibility and shows them no form', async () => {
    const calls = server();
    auth.user = { id: 3, name: 'Phoebe', role: 'product_manager' };
    renderReviews();
    await screen.findByText('Lovely scent');
    expect(calls.some((c) => c.url.endsWith('/rating/'))).toBe(false);
    expect(screen.queryByRole('button', { name: /review|comment/i })).toBeNull();
  });

  it('shows the form once the product was delivered', async () => {
    server({ mine: ELIGIBLE });
    auth.user = CUSTOMER;
    renderReviews();
    expect(await screen.findByRole('button', { name: 'Submit review' })).toBeTruthy();
    expect(screen.getByText(/optional/)).toBeTruthy();
  });

  it('shows "No reviews yet." without inviting non-buyers', async () => {
    server({ comments: [] });
    renderReviews();
    expect(await screen.findByText('No reviews yet.')).toBeTruthy();
  });

  it("shows each author's stars next to their name", async () => {
    server();
    renderReviews();
    const ada = (await screen.findByText('Lovely scent')).closest('.comment-card');
    expect(within(ada).getByLabelText('Rated 4 out of 5')).toBeTruthy();
    const grace = screen.getByText('No stars from me').closest('.comment-card');
    expect(within(grace).queryByLabelText(/Rated/)).toBeNull();
  });
});

describe('ReviewForm', () => {
  const eligible = (extra = {}) => {
    auth.user = CUSTOMER;
    return server({ mine: ELIGIBLE, ...extra });
  };

  it('needs a star before it can be sent', async () => {
    eligible();
    renderReviews();
    const submit = await screen.findByRole('button', { name: 'Submit review' });
    expect(submit.disabled).toBe(true);
    fireEvent.click(await star(4));
    expect(submit.disabled).toBe(false);
  });

  it('sends a rating alone, without a comment', async () => {
    const calls = eligible();
    const onRated = vi.fn();
    renderReviews({ onRated });
    fireEvent.click(await star(5));
    fireEvent.click(screen.getByRole('button', { name: 'Submit review' }));
    expect(await screen.findByText('Thank you! Your rating is live.')).toBeTruthy();
    expect(calls.filter((c) => c.method === 'PUT')).toEqual([{ method: 'PUT', url: '/api/products/7/rating/', body: { score: 5 } }]);
    expect(calls.some((c) => c.method === 'POST')).toBe(false);
    expect(onRated).toHaveBeenCalledTimes(1);
  });

  it('sends rating and comment together and shows the comment as waiting', async () => {
    const calls = eligible();
    renderReviews();
    fireEvent.click(await star(3));
    fireEvent.change(screen.getByLabelText(/Comment/), { target: { value: '  Lasts all day  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit review' }));
    expect(await screen.findByText(/after our team approves it/)).toBeTruthy();
    expect(calls.find((c) => c.method === 'POST').body).toEqual({ text: 'Lasts all day' });
    const card = screen.getByText('Lasts all day').closest('.comment-card');
    expect(card.className).toContain('comment-card--pending');
    expect(within(card).getByText('Awaiting approval')).toBeTruthy();
  });

  it('lets a customer who already rated post another comment without re-rating', async () => {
    const calls = eligible({ mine: { score: 4, canReview: true, pendingComments: [] } });
    const onRated = vi.fn();
    renderReviews({ onRated });
    const button = await screen.findByRole('button', { name: 'Post comment' });
    expect(button.disabled).toBe(true); // nothing new yet
    fireEvent.change(screen.getByLabelText(/Add a comment/), { target: { value: 'One more thing' } });
    fireEvent.click(button);
    await screen.findByText('One more thing');
    fireEvent.change(screen.getByLabelText(/Add a comment/), { target: { value: 'And another' } });
    fireEvent.click(screen.getByRole('button', { name: 'Post comment' }));
    await screen.findByText('And another');
    expect(calls.filter((c) => c.method === 'POST')).toHaveLength(2);
    expect(calls.some((c) => c.method === 'PUT')).toBe(false);
    expect(onRated).not.toHaveBeenCalled();
  });

  it('names the action after what changed', async () => {
    eligible({ mine: { score: 4, canReview: true, pendingComments: [] } });
    renderReviews();
    await screen.findByRole('button', { name: 'Post comment' });
    fireEvent.click(await star(2));
    expect(screen.getByRole('button', { name: 'Update rating' })).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Add a comment/), { target: { value: 'Changed my mind' } });
    expect(screen.getByRole('button', { name: 'Save rating & post comment' })).toBeTruthy();
  });

  it('shows the server message when saving fails', async () => {
    eligible({ fail: (method) => (method === 'PUT' ? json({ message: 'You can only rate products that were delivered to you.' }, 400) : null) });
    const onRated = vi.fn();
    renderReviews({ onRated });
    fireEvent.click(await star(2));
    fireEvent.click(screen.getByRole('button', { name: 'Submit review' }));
    expect(await screen.findByText(/only rate products that were delivered/)).toBeTruthy();
    expect(onRated).not.toHaveBeenCalled();
  });
});

describe('Pending comments', () => {
  const WAITING = { id: 9, text: 'Draft opinion', createdAt: '2026-11-27T10:00:00Z' };
  const withPending = (extra = {}) => {
    auth.user = CUSTOMER;
    return server({ mine: { score: 5, canReview: true, pendingComments: [WAITING] }, ...extra });
  };

  it('shows the author their waiting comment, faded, with their stars', async () => {
    withPending();
    renderReviews();
    const card = (await screen.findByText('Draft opinion')).closest('.comment-card');
    expect(card.className).toContain('comment-card--pending');
    expect(within(card).getByText('Ross Customer')).toBeTruthy();
    expect(within(card).getByLabelText('Rated 5 out of 5')).toBeTruthy();
    expect(within(card).getByText(/Only you can see this/)).toBeTruthy();
  });

  it('is not shown to other visitors', async () => {
    server();
    renderReviews();
    await screen.findByText('Lovely scent');
    expect(screen.queryByText('Draft opinion')).toBeNull();
  });

  it('can be edited by clicking it', async () => {
    const calls = withPending();
    renderReviews();
    fireEvent.click(await screen.findByText('Draft opinion'));
    const box = screen.getByLabelText('Edit your comment');
    expect(box.value).toBe('Draft opinion');
    fireEvent.change(box, { target: { value: 'Final opinion' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Final opinion')).toBeTruthy();
    expect(calls.find((c) => c.method === 'PATCH')).toEqual({ method: 'PATCH', url: '/api/comments/9/', body: { text: 'Final opinion' } });
    expect(screen.queryByLabelText('Edit your comment')).toBeNull();
  });

  it('can cancel an edit without saving', async () => {
    const calls = withPending();
    renderReviews();
    fireEvent.click(await screen.findByText('Draft opinion'));
    fireEvent.change(screen.getByLabelText('Edit your comment'), { target: { value: 'Never mind' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByText('Draft opinion')).toBeTruthy();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
  });

  it('explains when the comment was reviewed in the meantime', async () => {
    withPending({
      fail: (method) => (method === 'PATCH'
        ? json({ message: 'This comment was already reviewed and can no longer be edited.' }, 400) : null),
    });
    renderReviews();
    fireEvent.click(await screen.findByText('Draft opinion'));
    fireEvent.change(screen.getByLabelText('Edit your comment'), { target: { value: 'Too late' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText(/already reviewed/)).toBeTruthy();
  });
});

describe('RatingSummary', () => {
  it('shows the average and how many customers rated', () => {
    render(<RatingSummary rating={4.25} count={3} />);
    expect(screen.getByText('4.3')).toBeTruthy();
    expect(screen.getByText('(3 ratings)')).toBeTruthy();
  });

  it('says when nobody has rated yet', () => {
    render(<RatingSummary rating={null} count={0} />);
    expect(screen.getByText('No ratings yet')).toBeTruthy();
  });
});
