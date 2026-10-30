// Requirement 14: customer fields → ID (backend), name, taxID, e-mail, home address, password
// Note: frontend validation is only for UX; the backend must re-check the same rules.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateRegister(f) {
  const e = {};
  if (f.name.trim().length < 2) e.name = 'Full name must be at least 2 characters.';
  if (!EMAIL_RE.test(f.email)) e.email = 'Please enter a valid email address.';
  if (!/^\d{10,11}$/.test(f.taxId)) e.taxId = 'Tax ID must be 10–11 digits.';
  if (f.homeAddress.trim().length < 10) e.homeAddress = 'Please enter your full address.';
  if (f.password.length < 8 || !/[A-Z]/.test(f.password) || !/\d/.test(f.password))
    e.password = 'Password must be at least 8 characters with 1 uppercase letter and 1 digit.';
  if (f.password !== f.confirm) e.confirm = 'Passwords do not match.';
  return e;
}
