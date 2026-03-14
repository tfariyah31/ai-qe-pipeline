import { test, expect } from '@playwright/test';
import { getSession, authHeader, TEST_USERS } from '../fixtures/auth.fixture';

/**
 * Users API Tests
 * GET  /api/users/     — Super Admin: get all users
 * GET  /api/users/:id  — Super Admin: get single user
 * PUT  /api/users/:id  — Super Admin: update user name or email
 *
 * NOTE: PUT tests never touch seeded users (customer@test.com etc.).
 * Each PUT describe block registers a fresh disposable user in beforeAll
 * and deletes them in afterAll.
 */

const BASE_URL = 'http://127.0.0.1:5001/api/users';
const AUTH_URL = 'http://127.0.0.1:5001/api/auth';

// ---------------------------------------------------------------------------
// Helper — asserts the shape of a user object and that password is never leaked
// ---------------------------------------------------------------------------

function expectUserShape(user: any) {
  expect(user).toHaveProperty('_id');
  expect(user).toHaveProperty('name');
  expect(user).toHaveProperty('email');
  expect(user).toHaveProperty('role');
  expect(user).toHaveProperty('isBlocked');
  expect(user.password).toBeUndefined();
}

// ---------------------------------------------------------------------------
// Disposable user factory — unique timestamp per call, never conflicts with seed data
// ---------------------------------------------------------------------------

const disposableUser = () => ({
  name: 'Disposable Test User',
  email: `disposable_${Date.now()}@testmart.com`,
  password: 'Disposable@1234',
});

// ---------------------------------------------------------------------------
// GET /api/users  — Get all users
// ---------------------------------------------------------------------------

test.describe('GET /api/users', () => {
  test('[USR-001] Super admin can fetch all users and receives a non-empty list', async ({
    request,
  }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);

    const body = await res.json();
    const users: any[] = body.users ?? body;

    expect(Array.isArray(users)).toBe(true);
    expect(users.length).toBeGreaterThan(0);
    users.forEach(expectUserShape);
  });

  test('[USR-002] Every user in the list has a valid role (superadmin | merchant | customer)', async ({
    request,
  }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    const users: any[] = body.users ?? body;
    users.forEach((u) =>
      expect(['superadmin', 'merchant', 'customer']).toContain(u.role)
    );
  });

  test('[USR-003] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`);
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-004] Returns 401 with an invalid or malformed token', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: { Authorization: 'Bearer invalid.token.here' },
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-005] Returns 403 when accessed by a merchant', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('merchant'),
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-006] Returns 403 when accessed by a customer', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('customer'),
    });
    expect([401, 403]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// GET /api/users/:id  — Get single user
// ---------------------------------------------------------------------------

test.describe('GET /api/users/:id', () => {
  test('[USR-010] Super admin can fetch a customer user by ID', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);

    const body = await res.json();
    const user = body.user ?? body;
    expectUserShape(user);
    expect(user._id).toBe(session.user.id);
    expect(user.email).toBe(TEST_USERS.customer.email);
  });

  test('[USR-011] Super admin can fetch a merchant user by ID', async ({ request }) => {
    const session = getSession('merchant');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);

    const body = await res.json();
    const user = body.user ?? body;
    expectUserShape(user);
    expect(user.role).toBe('merchant');
  });

  test('[USR-012] Fetched user has a valid role value', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('superadmin'),
    });

    const body = await res.json();
    const user = body.user ?? body;
    expect(['superadmin', 'merchant', 'customer']).toContain(user.role);
  });

  test('[USR-013] Returns 404 for a non-existent user ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/000000000000000000000000`, {
      headers: authHeader('superadmin'),
    });
    expect(res.status()).toBe(404);
  });

  test('[USR-014] Returns 400 for a malformed user ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/not-a-valid-id`, {
      headers: authHeader('superadmin'),
    });
    expect([400, 404, 422]).toContain(res.status());
  });

  test('[USR-015] Returns 401 when no token is provided', async ({ request }) => {
    const session = getSession('customer');
    const res = await request.get(`${BASE_URL}/${session.user.id}`);
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-016] Returns 403 when accessed by a merchant', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('merchant'),
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-017] Returns 403 when accessed by a customer', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('customer'),
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-018] Single user response does not expose password', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.get(`${BASE_URL}/${session.user.id}`, {
      headers: authHeader('superadmin'),
    });

    const body = await res.json();
    const user = body.user ?? body;
    expect(user.password).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// PUT /api/users/:id — Update name
// Uses a fresh disposable user. Seed data is never touched.
// ---------------------------------------------------------------------------

test.describe('PUT /api/users/:id — Update name', () => {
  let testUserId: string;

  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${AUTH_URL}/register`, {
      data: disposableUser(),
    });
    expect(res.status(), 'disposable user registration failed').toBe(201);
    const body = await res.json();
    
    testUserId = body.id || body._id || body.user?.id || body.user?._id;
    expect(testUserId, 'could not read created user ID from register response').toBeTruthy();
  });

  test.afterAll(async ({ request }) => {
    if (testUserId) {
      await request.delete(`${BASE_URL}/${testUserId}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[USR-020] Super admin can update a user name', async ({ request }) => {
    const updatedName = `Updated Name ${Date.now()}`;

    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { name: updatedName },
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    const user = body.user ?? body;
    expect(user.name).toBe(updatedName);
  });

  test('[USR-021] Updated user response has correct shape and no password', async ({
    request,
  }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { name: `Shape Check ${Date.now()}` },
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    const user = body.user ?? body;
    expectUserShape(user);
  });

  test('[USR-022] Returns 400 when name is an empty string', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { name: '' },
    });
    expect([400, 422]).toContain(res.status());
  });

  test('[USR-023] Returns 400 when name is only whitespace', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { name: '   ' },
    });
    expect([400, 422]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// PUT /api/users/:id — Update email
// Uses a fresh disposable user. Seed data is never touched.
// ---------------------------------------------------------------------------

test.describe('PUT /api/users/:id — Update email', () => {
  let testUserId: string;

  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${AUTH_URL}/register`, {
      data: disposableUser(),
    });
    expect(res.status(), 'disposable user registration failed').toBe(201);
    const body = await res.json();
    
    testUserId = body.id || body._id || body.user?.id || body.user?._id;
    expect(testUserId, 'could not read created user ID from register response').toBeTruthy();
  });

  test.afterAll(async ({ request }) => {
    if (testUserId) {
      await request.delete(`${BASE_URL}/${testUserId}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[USR-030] Super admin can update a user email', async ({ request }) => {
    const updatedEmail = `updated_${Date.now()}@testmart.com`;

    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { email: updatedEmail },
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    const user = body.user ?? body;
    expect(user.email).toBe(updatedEmail);
  });

  test('[USR-031] Returns 400 when email has an invalid format', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { email: 'not-an-email' },
    });
    expect([400, 422]).toContain(res.status());
  });

  test('[USR-032] Returns 400 when email is an empty string', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { email: '' },
    });
    expect([400, 422]).toContain(res.status());
  });

  test('[USR-033] Returns 409 when email is already taken by another user', async ({
    request,
  }) => {
    // Attempts to assign an existing seeded email — read-only reference, no seed mutation
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { email: TEST_USERS.merchant.email },
    });
    expect([400, 409, 422]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// PUT /api/users/:id — Auth & not-found guards
// Uses a fresh disposable user. Seed data is never touched.
// ---------------------------------------------------------------------------

test.describe('PUT /api/users/:id — Auth & not-found guards', () => {
  let testUserId: string;

  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${AUTH_URL}/register`, {
      data: disposableUser(),
    });
    expect(res.status(), 'disposable user registration failed').toBe(201);
    const body = await res.json();
    
    testUserId = body.id || body._id || body.user?.id || body.user?._id;
    expect(testUserId, 'could not read created user ID from register response').toBeTruthy();
  });

  test.afterAll(async ({ request }) => {
    if (testUserId) {
      await request.delete(`${BASE_URL}/${testUserId}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[USR-040] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      data: { name: 'Ghost User' },
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-041] Returns 401 with an invalid token', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: { Authorization: 'Bearer badtoken' },
      data: { name: 'Ghost User' },
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-042] Returns 403 when a merchant attempts to update a user', async ({
    request,
  }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('merchant'),
      data: { name: 'Sneaky Merchant' },
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-043] Returns 403 when a customer attempts to update another user', async ({
    request,
  }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('customer'),
      data: { name: 'Sneaky Customer' },
    });
    expect([401, 403]).toContain(res.status());
  });

  test('[USR-044] Returns 404 when updating a non-existent user', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/000000000000000000000000`, {
      headers: authHeader('superadmin'),
      data: { name: 'Nobody' },
    });
    expect(res.status()).toBe(404);
  });

  test('[USR-045] Returns 400 for a malformed user ID on update', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/not-a-valid-id`, {
      headers: authHeader('superadmin'),
      data: { name: 'Nobody' },
    });
    expect([400, 404, 422]).toContain(res.status());
  });

  test('[USR-046] Update response never exposes the user password', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${testUserId}`, {
      headers: authHeader('superadmin'),
      data: { name: `Safe Name ${Date.now()}` },
    });

    expect(res.status()).toBe(200);
    const body = await res.json();
    const user = body.user ?? body;
    expect(user.password).toBeUndefined();
  });
});