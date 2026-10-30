// Requirement 10: the system has four basic roles. The backend must return these exact strings.
export const ROLES = Object.freeze({
  CUSTOMER: 'customer',
  SALES_MANAGER: 'sales_manager',
  PRODUCT_MANAGER: 'product_manager',
  SUPPORT_AGENT: 'support_agent',
});

export const ROLE_LABELS = {
  [ROLES.CUSTOMER]: 'Customer',
  [ROLES.SALES_MANAGER]: 'Sales Manager',
  [ROLES.PRODUCT_MANAGER]: 'Product Manager',
  [ROLES.SUPPORT_AGENT]: 'Support Agent',
};

export const STAFF_ROLES = [ROLES.SALES_MANAGER, ROLES.PRODUCT_MANAGER, ROLES.SUPPORT_AGENT];
