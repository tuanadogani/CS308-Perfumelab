# Products Module

Product management system for PerfumeLab online store.

## Features

### Product Manager (Requirement 12)
- **Product Management**: Add, edit, remove products and categories
- **Stock Management**: Update and monitor product inventory
- **Delivery Management**: View orders, delivery addresses, and update order status
- **Comment Approval**: Approve or reject customer product reviews

### Customer Features (Requirement 5, 7, 9)
- **Product Browsing**: Search and filter products by name, category, brand, scent family
- **Product Reviews**: Rate and comment on delivered products
- **Sorting**: Sort products by price or popularity

## API Endpoints

### Categories
- `GET /api/categories/` - List all categories
- `POST /api/categories/` - Create category (PM only)
- `PUT/PATCH /api/categories/{id}/` - Update category (PM only)
- `DELETE /api/categories/{id}/` - Delete category (PM only)

### Products
- `GET /api/products/` - List products (with search, filter, sort)
- `GET /api/products/{id}/` - Get product details
- `POST /api/products/` - Create product (PM only)
- `PUT/PATCH /api/products/{id}/` - Update product (PM only)
- `DELETE /api/products/{id}/` - Delete product (PM only)
- `PATCH /api/products/{id}/update-stock/` - Update stock (PM only)

### Orders
- `GET /api/orders/` - List orders
- `GET /api/orders/{id}/` - Get order details
- `POST /api/orders/` - Create order
- `PATCH /api/orders/{id}/update-status/` - Update order status (PM only)

### Deliveries
- `GET /api/deliveries/` - List delivery queue (PM only)

### Comments
- `GET /api/comments/` - List comments (approved only for public)
- `POST /api/comments/` - Create comment (requires delivered order)
- `PATCH /api/comments/{id}/approve/` - Approve comment (PM only)
- `PATCH /api/comments/{id}/reject/` - Reject comment (PM only)

### Ratings
- `GET /api/ratings/` - List ratings
- `POST /api/ratings/` - Create rating (requires delivered order)

## Models

### Product (Requirement 9)
Required fields: ID, name, model, serial_number, description, stock, price, warranty_status, distributor

Additional fields: category, brand, scent_family, notes (top, heart, base), size_ml, image_url, discount_rate, cost_price

### Order (Requirement 3)
Status flow: processing → in_transit → delivered

### Comment (Requirement 5, 12)
Status: pending (default) → approved/rejected (PM decision)

### Rating (Requirement 5)
Direct submission without approval (1-5 stars)

## Permissions

- **Public**: Browse products, view approved comments and ratings
- **Authenticated Users**: Create orders, rate and comment on delivered products
- **Product Managers**: Full access to products, categories, stock, deliveries, and comment approval
