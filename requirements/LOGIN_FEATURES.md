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
* View user details Page

### Product Oversight

Super Admin can:

* View all products
* View Add product button

---

# 4. Merchant Features

Merchants manage their store inventory.

### Product Management

Merchants can:

* Add new products button visible
* View all available products


### Merchant Dashboard

Displays store insights such as:

* Total products
* Top performing products
* Basic store metrics

---

# 5. Customer Features

Customers interact with the store to browse products and view.

### Product Browsing

Customers can:

* View all available products
* View Cart Icon

# 6. Frontend UI Features

The application uses **React with Material UI** to provide a responsive interface.

Key UI features include:

* Role-based dashboards
* Responsive design
* Smart navigation bar
* Role badge display

---
