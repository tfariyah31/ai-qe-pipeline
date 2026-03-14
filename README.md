# TestMart

A full-stack web application with a React frontend and Node.js backend, featuring role-based user authentication, product management, shopping cart, and user administration.

---

## Tech Stack

- **Frontend:** React, Material-UI (MUI), React Router
- **Backend:** Node.js, Express, MongoDB (Mongoose)
- **Auth:** JWT (access + refresh tokens), bcryptjs
- **Testing:** Playwright (end-to-end)
- **CI/CD:** GitHub Actions

---

## Features

### Security & Authentication
- JWT-based login with short-lived access tokens and long-lived refresh tokens
- `bcryptjs` password hashing
- Role-based access control with middleware enforcement (`superadmin`, `merchant`, `customer`)
- Account lockout after 3 failed login attempts (5-minute lock)
- HTTP header protection via `Helmet`
- XSS prevention via `xss-clean`
- NoSQL injection prevention with `express-mongo-sanitize`
- Rate limiting to guard against brute-force attacks

### Role-Based Access

#### Super Admin (`superadmin`)
- Access to all pages and features
- View all products
- Add new products
- Manage all user accounts (update name, email, role, block/unblock)

#### Merchant (`merchant`)
- View all products
- Add new products (name, description, image, price, rating)
- Edit existing products
- Access merchant dashboard with store stats and top products

#### Customer (`customer`)
- Browse all products
- Add products to cart
- View and manage cart (adjust quantities, remove items)
- View order summary with subtotal, tax, and total
- Secure checkout with Stripe Sandbox payment integration
- Place orders after successful payment
- Access customer dashboard with order history and wishlist overview


#### Payment Integration
- Integrated Stripe Sandbox for secure test payments
- Customers can complete checkout using Stripe’s payment flow
- Payment confirmation before order creation
- Simulated real-world e-commerce payment processing
- Supports testing with Stripe test cards
- Designed to enable automated payment flow testing
  
### Frontend & UI
- Role-specific dashboards rendered automatically on login
- Smart navbar with role badge and context-aware links
- Cart icon with live item count badge (customers only)
- Fully responsive UI built with Material-UI (MUI)
- Protected routes — unauthorized roles are redirected automatically

### DevOps & Quality Assurance
- End-to-end test suite powered by Playwright
- CI/CD pipeline via GitHub Actions for automated testing and deployment

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) v16 or higher
- [MongoDB](https://www.mongodb.com/try/download/community) (local) or a [MongoDB Atlas](https://www.mongodb.com/atlas) cloud URI
- [Git](https://git-scm.com/)

---


### 1. Clone the Repository

```bash
git clone https://github.com/tfariyah31/TestMart-ReactNode_Playwright_CI.git
cd TestMart
```

### 2. Set Up the Backend

```bash
cd backend
npm install
```

Create a `.env` file in the `backend` folder:

```env
PORT=5001
MONGO_URI=mongodb://localhost:27017/mywebapp
JWT_SECRET=your_secret_key_here
REFRESH_SECRET=your_refresh_secret
```
> Replace `MONGO_URI` with your MongoDB Atlas connection string if using a cloud database.

Start the backend server:

```bash
node server.js
```

The backend will be available at `http://localhost:5001`.

### 3. Set Up the Frontend

```bash
cd ../frontend
npm install
npm start
```

The frontend will be available at `http://localhost:3000`.

---
## **Project Structure**
```
TestMart/
├── backend/
│   ├── config/          
│   ├── controllers/     
│   ├── middleware/      
│   ├── models/          
│   ├── routes/          
│   ├── server.js        
│   └── .env             
├── frontend/
│   ├── src/             
│   ├── utils/             
│   ├── App.js     
│   └── ...              
├── tests/
│   ├── login.spec.js    
├── package.json         
├── playwright.config.js
└── README.md            
```

---
## API Endpoints

### Auth — `/api/auth`

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | `/login` | Public | Login and receive JWT tokens |
| POST | `/register` | Public | Register a new customer account |
| POST | `/refresh` | Public | Refresh access token |
| POST | `/logout` | Authenticated | Logout and invalidate refresh token |

### Products — `/api/products`

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/` | All roles | Get all products |
| GET | `/:id` | All roles | Get single product |
| POST | `/` | Merchant, Super Admin | Add a new product |
| PUT | `/:id` | Merchant, Super Admin | Update a product |
| DELETE | `/:id` | Merchant, Super Admin | Delete a product |

### Users — `/api/users`

| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | `/` | Super Admin | Get all users |
| GET | `/:id` | Super Admin | Get single user |
| PUT | `/:id` | Super Admin | Update user info, role, or block status |

---

## Playwright Tests

### API Tests Prerequisites

- Backend server running at `http://127.0.0.1:5001`
- Test users seeded in MongoDB — run `npm run seed:test` if not done yet

## Running the Tests

Global setup (`tests/global.setup.ts`) runs **automatically** before the tests. It logs in as each role (`superadmin`, `merchant`, `customer`) and saves session tokens to `.sessions/` for reuse across all tests.

```bash
npm run test:api
```
Re-run this any time your tokens expire or you reseed the database.


## Test Coverage

| Spec file | Endpoints |
|---|---|
| `auth.api.spec.ts` | `POST /api/auth/login`, `/register`, `/refresh`, `/logout` |
| `users.api.spec.ts` | `GET /api/users`, `GET /api/users/:id`, `PUT /api/users/:id` |
| `products.api.spec.ts` | `GET /api/products`, `GET /api/products/:id`, `POST`, `PUT`, `DELETE` |

## Notes

- Tests are **read-only safe** — any products created during testing are cleaned up via `afterAll`
- Blocked/locked user credentials are available via `getCredentials('blockedUser')` in `fixtures/auth.fixture.ts` for scenario-specific tests

---

## Author
**Tasnim Fariyah**

[![GitHub](https://img.shields.io/badge/GitHub-tfariyah31-181717?logo=github)](https://github.com/tfariyah31)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-tasnim--fariyah-0A66C2?logo=linkedin)](https://www.linkedin.com/in/tasnim-fariyah/)

---

