# Bug Reports - CS308 Perfumelab Project

**Team:** Perfumelab
**Demo:** Week 11 Progress Demo
**Reported by:** Zeynep (QA Lead)

---

## Bug #1: Guests Can Add Items to Wishlist (Requirements Violation)

**Priority:** High
**Status:** Fixed
**Date Reported:** 2026-11-17
**Date Fixed:** 2026-11-17
**Fixed By:** Tuana

### Description
Unauthenticated users (guests) were able to add products to their wishlist using localStorage, which violates project requirements 11 and 14. The requirements explicitly state that only logged-in customers should be able to use the wishlist feature.

### Requirements Violated
- **Requirement 11** (Page 2): "notifies the users whose wish list includes the discounted product" - implies wishlist is tied to user accounts
- **Requirement 14** (Page 2): "The **customers** shall... include products in their wish lists" - "customers" means authenticated users

### Steps to Reproduce
1. Open the application without logging in (as a guest)
2. Navigate to any product page or shop page
3. Click the heart icon (wishlist button) on any product
4. **Actual Result:** Product is added to wishlist and stored in localStorage
5. **Expected Result:** Should show error message requiring login

### Expected Behavior
- Guests should NOT be able to add items to wishlist
- Clicking wishlist button should prompt user to log in
- Wishlist should require authentication to function

### Actual Behavior (Before Fix)
- Guests could add items to wishlist
- Wishlist data stored in browser localStorage
- No authentication check performed
- Wishlist functioned the same for guests and logged-in users

### Environment
- **Browser:** Chrome 120, Safari 17
- **OS:** macOS 14.6
- **Frontend:** React 18 + Vite
- **Backend:** Django 5.2 + PostgreSQL
- **Files Affected:**
  - `frontend/src/context/WishlistContext.jsx` (line 41-68)
  - `frontend/src/components/WishlistButton.jsx`

### Root Cause
The `WishlistContext` component allowed toggle operations for both authenticated users (via API) and guests (via localStorage). The code had a `remote` flag that switched between backend API and localStorage based on user authentication status, but did not block the operation for guests.

**Problematic Code (Line 17, 48, 54-55):**
```javascript
const remote = !!user && !USE_MOCK;
// ...
const saved = remote && !exists ? await api.addToWishlist(product.id) : product;
// ...
if (!remote) {
  localStorage.setItem(storageKey, JSON.stringify(next));
}
```

### Fix Applied
Added authentication check at the beginning of `toggle()` function in `WishlistContext.jsx`:

```javascript
const toggle = async (product) => {
  // Requirement 11, 14: Wishlist requires login
  if (!user) {
    throw new Error('Please log in to add items to your wishlist');
  }
  // ... rest of function
};
```

Also updated `WishlistButton.jsx` to display user-friendly toast notification with link to login page when guests attempt to use wishlist.

### Verification
1. ✅ Logged-out users cannot add items to wishlist
2. ✅ Clicking wishlist button shows "Log in to add items to your wishlist" message
3. ✅ Message includes clickable link to login page
4. ✅ Toast notification appears centered and auto-dismisses after 4 seconds
5. ✅ Logged-in users can still use wishlist normally
6. ✅ Backend API already had authentication requirement (uses `request.user`)

### Test Cases Added
- [ ] Manual test: Guest attempts to wishlist → should see error
- [ ] Manual test: Logged-in user wishlists → should succeed
- [ ] Manual test: Toast notification appears and disappears smoothly
- [ ] Manual test: "Log in" link in toast navigates to login page

### Impact
- **Security:** Medium - No security breach, but requirements violation
- **Functionality:** High - Core feature not following specification
- **User Experience:** Improved - Now enforces proper authentication flow

---

## Bug Template for Future Reports

**Priority:** Critical / High / Medium / Low
**Status:** Open / In Progress / Fixed / Verified
**Date Reported:** YYYY-MM-DD
**Date Fixed:** YYYY-MM-DD
**Fixed By:** Team Member Name

### Description
Brief description of the bug.

### Steps to Reproduce
1. Step one
2. Step two
3. ...

### Expected Behavior
What should happen.

### Actual Behavior
What actually happens.

### Environment
- Browser:
- OS:
- Files affected:

### Screenshots
[Attach if applicable]

### Root Cause
Technical explanation.

### Fix Applied
How it was fixed.

### Verification
How to verify the fix works.

---

**Total Bug Reports:** 1 / 5 (minimum required for demo)
