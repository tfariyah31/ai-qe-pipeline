/**
 * Central test data for TestMart test suite.
 * These users must exist in the DB before running tests.
 * Seed them via: npm run seed:test (or create manually in MongoDB)
 */

export const TEST_USERS = {
  superadmin: {
    email: 'superadmin@test.com',
    password: 'Str0ng!Pass#2024',
    role: 'superadmin',
    name: 'Super Admin',
  },
  merchant: {
    email: 'merchant@test.com',
    password: 'MerchantPass123!',
    role: 'merchant',
    name: 'Test Merchant',
  },
  validationuser:{
    email: 'validation@test.com',
    password: 'ValidationPass123!',
    role: 'customer',
    name: 'Validation User',
  },
  customer: {
    email: 'customer@test.com',
    password: 'CustomerPass123!',
    role: 'customer',
    name: 'Test Customer',
  },
  // Fixed users for specific test scenarios
  blockedUser: {
    email: 'blocked@test.com',
    password: 'BlockedPass123!',
    role: 'customer',
    name: 'Blocked User',
  },
  lockedUser: {
    email: 'locked@test.com',
    password: 'Locked@1234',
    role: 'customer',
    name: 'Locked User',
  },
} as const;

export const TEST_PRODUCTS = {
  valid: {
    name: 'Playwright Test Product',
    description: 'Created by automated test suite',
    image: 'https://picsum.photos/200',
    price: 49.99,
    rating: 4.5,
  },
  invalidMissingName: {
    description: 'No name product',
    image: 'https://picsum.photos/200',
    price: 10,
    rating: 3,
  },
} as const;

export const API_URL = 'http://127.0.0.1:5001/api';
export const APP_URL = 'http://localhost:3000';