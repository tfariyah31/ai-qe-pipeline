# FEATURES

TestMart is a **full-stack e-commerce demo application** designed to demonstrate secure authentication, role-based access control, product management, and a complete customer purchase flow including **Stripe sandbox payment integration**.

The application supports **three user roles**:

* Super Admin
* Merchant
* Customer

Each role has different capabilities and access levels.

---

# 1. Authentication & Login Flow

The application uses **JWT-based authentication** with security best practices.

### Login Flow

1. User enters email and password.
2. Credentials are verified against the database.
3. If valid:

   * A **short-lived access token** is issued.
   * A **long-lived refresh token** is issued.
4. The frontend stores the access token for authenticated requests.
5. Protected routes validate tokens through backend middleware.

### Security Features

* Password hashing using **bcryptjs**
* **Account lockout** after 3 failed login attempts (5 minute lock)
* **JWT access + refresh token mechanism**
* **Rate limiting** to prevent brute-force attacks
* **Helmet** for HTTP security headers
* **XSS protection**
* **NoSQL injection prevention**

---

# 2. Role-Based Access Control

The system enforces role permissions using backend middleware.

| Role        | Access                                 |
| ----------- | -------------------------------------- |
| Super Admin | Full system access                     |
| Merchant    | Product management and store dashboard |
| Customer    | Shopping and checkout                  |

Unauthorized users are automatically **redirected from protected routes**.

---

# 3. Super Admin Features

The **Super Admin** manages the overall platform.

### User Management

Super Admin can:

* View all registered users
* Update user details
* Change user roles
* Block or unblock users

### Product Oversight

Super Admin can:

* View all products
* Add new products
* Monitor merchant products

### Admin Dashboard

Provides an overview of:

* User activity
* Total products
* Platform statistics

---

# 4. Merchant Features

Merchants manage their store inventory.

### Product Management

Merchants can:

* Add new products
* Edit existing products
* View all available products

Each product includes:

* Product name
* Description
* Image
* Price
* Rating

### Merchant Dashboard

Displays store insights such as:

* Total products
* Top performing products
* Basic store metrics

---

# 5. Customer Features

Customers interact with the store to browse products and place orders.

### Product Browsing

Customers can:

* View all available products
* View product details
* Browse through the product catalog

### Add to Cart Flow

1. Customer selects a product.
2. Clicks **Add to Cart**.
3. Product is added to the cart.
4. Cart icon updates with a **live item count**.

Customers can also:

* Adjust quantities
* Remove items from cart

---

# 6. Cart & Order Summary

The cart page provides a complete purchase overview.

Displayed values include:

* Product list
* Quantity per item
* Subtotal
* Estimated tax
* Final order total

Customers can proceed to checkout from the cart page.

---

# 7. Stripe Payment Checkout

The application integrates **Stripe Sandbox** to simulate a real-world payment flow.

### Checkout Flow

1. Customer reviews cart.
2. Clicks **Checkout**.
3. Backend creates a **Stripe payment session**.
4. Customer is redirected to the **Stripe payment page**.
5. Customer enters test card details.
6. Stripe processes the payment.
7. After successful payment:

   * User is redirected back to the application.
   * Order is confirmed.

### Stripe Testing

The integration uses **Stripe test mode**, allowing developers and testers to simulate payments safely using Stripe test cards.

This allows validation of:

* Payment success flow
* Payment failure scenarios
* Secure checkout integration

---

# 8. Frontend UI Features

The application uses **React with Material UI** to provide a responsive interface.

Key UI features include:

* Role-based dashboards
* Responsive design
* Smart navigation bar
* Role badge display
* Context-aware menu options
* Live cart item counter
* Protected routes for restricted pages

---
