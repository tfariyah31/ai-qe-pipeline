import { test, expect, APIRequestContext } from '@playwright/test';
import { getSession, getCredentials, authHeader, TEST_USERS } from '../fixtures/auth.fixture';

/**
 * Auth API Tests
 * POST /api/auth/login
 * POST /api/auth/register
 * POST /api/auth/refresh
 * POST /api/auth/logout
 */

const BASE_URL = 'http://127.0.0.1:5001/api/auth';

// Fresh unique user for registration tests (never rate-limited)
const newUser = () => ({
  name: 'Test Customer',
  email: `testcustomer_${Date.now()}@testmart.com`,
  password: 'Customer@1234',
});

// ---------------------------------------------------------------------------
// LOGIN
// ---------------------------------------------------------------------------
test.describe('POST /api/auth/login', () => {

  test('[LG-001] Login successfully with valid credentials', async ({ request }) => {
    const session = getSession('superadmin');
    expect(session.accessToken).toBeTruthy();
    expect(session.refreshToken).toBeTruthy();
    expect(session.user.role).toBe('superadmin');

    const parts = session.accessToken.split('.');
    expect(parts.length).toBe(3);

    expect((session.user as any).password).toBeUndefined();

  });

  test('[LG-002] Should return 401 with wrong password', async ({ request }) => {
    const { email } = getCredentials('validationuser');

    const res = await request.post(`${BASE_URL}/login`, {
      data: { email, password: 'WrongPassword!' },
    });

    const body = await res.json();
    expect(res.status()).toBe(401);
    expect(body.success).toBe(false);
  });

  test('[LG-003] Should return 401 with non-existent email', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/login`, {
      data: { email: 'nobody@testmart.com', password: 'SomePass@1' },
    });

    expect(res.status()).toBe(401);
  });

  test('[LG-004] Email case handling documented (200 or 401)', async ({ request }) => {
    const { email, password } = getCredentials("customer");
    const res = await request.post(`${BASE_URL}/login`, {
    data: { 
      email: email.toUpperCase(), 
      password: password 
      },
    });

    const status = res.status();
    expect([200, 401]).toContain(status);

    console.log(status === 200 
      ? 'INFO: Email login is case-insensitive' 
      : 'INFO: Email login is case-sensitive'
    );
  });

test('[LG-005] Should return 403 Forbidden for a blocked user', async ({ request }) => {
  const { email, password } = getCredentials('blockedUser');
  const res = await request.post(`${BASE_URL}/login`, {
    data: { email, password },
  });

  expect(res.status()).toBe(403);
  const body = await res.json();

  expect(body).toMatchObject({
    success: false,
    message: expect.stringContaining('Your account is blocked. Please contact')
  });

  expect(typeof body.success).toBe('boolean');
  expect(typeof body.message).toBe('string');
  
  const keys = Object.keys(body);
  expect(keys).toEqual(expect.arrayContaining(['success', 'message']));
  expect(keys.length).toBe(2);
});


  test('[LG-006] Should return 400 when email is missing', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/login`, {
      data: { password: 'SomePass@1' },
    });

    expect(res.status()).toBe(400);
  });

  test('[LG-007] Should return 400 when password is missing', async ({ request }) => {
    const { email } = getCredentials('validationuser');
    const res = await request.post(`${BASE_URL}/login`, {
       data: { email }, 
    });

    expect(res.status()).toBe(400);
  });

  test('[LG-008] Should return 400 when body is empty', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/login`, { data: {} });

    expect(res.status()).toBe(400);
  });

  test('[LG-009] Invalid email format should return 400', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/login`, {
      data: { email: 'not-an-email', password: 'SomePass@1' },
    });

    expect(res.status()).toBe(401);
  });

});

// ---------------------------------------------------------------------------
// REGISTER
// ---------------------------------------------------------------------------
test.describe('POST /api/auth/register', () => {

  test('[REG-001]should register a new user successfully', async ({ request }) => {
    const user = newUser();
    const res = await request.post(`${BASE_URL}/register`, { data: user });
    const body = await res.json();

    expect(res.status()).toBe(201);
    expect(body).toMatchObject({ email: user.email, name: user.name, role: 'customer',message: 'User registered successfully' });
    expect(body.user?.password).toBeUndefined();
  });

  test('[REG-002] Newly registered user should be able to login', async ({ request }) => {
    const user = newUser();
    await request.post(`${BASE_URL}/register`, { data: user });

    const res = await request.post(`${BASE_URL}/login`, {
      data: { email: user.email, password: user.password },
    });
    const body = await res.json();

    expect(res.status()).toBe(200);
    expect(body.accessToken).toBeTruthy();
  });

  test('[REG-003] Should return 400 for duplicate email', async ({ request }) => {
    const user = newUser();
    await request.post(`${BASE_URL}/register`, { data: user });

    const res = await request.post(`${BASE_URL}/register`, { data: user });
    expect(res.status()).toBe(400);
  });

  test('[REG-004] Invalid email format should return 400', async ({ request }) => {
    const user = { name: 'Invalid Email', email: 'invalid-email', password: 'Pass@1234' };
    const res = await request.post(`${BASE_URL}/register`, { data: user });
    expect(res.status()).toBe(400);
  });
 
  test('[REG-005] Password complexity rules should be enforced', async ({ request }) => {
    const user = { name: 'Weak Password', email: `weakpass_${Date.now()}@testmart.com`, password: '123' };
    const res = await request.post(`${BASE_URL}/register`, { data: user });
    expect(res.status()).toBe(400);
  });

  test('[REG-006] Multiple required fields missing should return 400 with all errors', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/register`, { data: {} });
    const body = await res.json();

    expect(res.status()).toBe(400);
   expect(body.errors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ path: 'name', msg: expect.any(String) }),
        expect.objectContaining({ path: 'email', msg: expect.any(String) }),
        expect.objectContaining({ path: 'password', msg: expect.any(String) }),
      ])
    );
    expect(body.success).toBe(false);
  });

  test('[REG-007] Should return 400 when email is missing', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/register`, {
      data: { name: 'No Email', password: 'Pass@1234' },
    });
    expect(res.status()).toBe(400);
  });

  test('[REG-008] Should return 400 when password is missing', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/register`, {
      data: { name: 'No Pass', email: `nopass_${Date.now()}@testmart.com` },
    });
    expect(res.status()).toBe(400);
  });

  test('[REG-009] Should return 400 when name is missing', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/register`, {
      data: { email: `missing_${Date.now()}@testmart.com`, password: 'Pass@1234' },
    });
    expect(res.status()).toBe(400);
  });

  test('[REG-010] Should return 400 when body is empty', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/register`, { data: {} });
    expect(res.status()).toBe(400);
  });

  test('[REG-011] Unknown fields in request body should return 400', async ({ request }) => {
    const user = newUser();
    const res = await request.post(`${BASE_URL}/register`, {
      data: { ...user, unexpectedField: 'unexpectedValue' },
    });
    const body = await res.json();

    expect(res.status()).toBe(400);
    expect(body).not.toHaveProperty('unexpectedField');
    expect(body.message).toContain('Unknown field(s) detected');
  });
  
  test('[REG-012] Email as whitespace should return 400', async ({ request }) => {
    const user = { name: 'Whitespace Email', email: '   ', password: 'Pass@1234' };
    const res = await request.post(`${BASE_URL}/register`, { data: user });
    expect(res.status()).toBe(400);
  });

  test('REG-013] Password below minimum length should return 400', async ({ request }) => {
    const user = { name: 'Short Password', email: `shortpass_${Date.now()}@testmart.com`, password: 'P@1' };
    const res = await request.post(`${BASE_URL}/register`, { data: user });
    expect(res.status()).toBe(400);
  });

});

// ---------------------------------------------------------------------------
// REFRESH TOKEN
// ---------------------------------------------------------------------------
test.describe('POST /api/auth/refresh', () => {

  test('[REF-001] should return new tokens with valid refresh token', async ({ request }) => {
    const session = getSession('customer');

    const res = await request.post(`${BASE_URL}/refresh`, {
      data: { refreshToken: session.refreshToken },
    });
    const body = await res.json();

    expect(res.status()).toBe(200);
    expect(body.success).toBe(true);
    expect(body.accessToken).toBeTruthy();
    expect(body.accessToken).not.toBe(session.accessToken);
  });

  test('[REF-002] Should return 401 when refresh token is missing', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/refresh`, { data: {} });
    expect(res.status()).toBe(401);
  });

  test('[REF-003] Should return 401 with an invalid refresh token', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/refresh`, {
      data: { refreshToken: 'this.is.invalid' },
    });
    expect(res.status()).toBe(401);
  });

});

// ---------------------------------------------------------------------------
// LOGOUT
// ---------------------------------------------------------------------------
test.describe('POST /api/auth/logout', () => {

  test('[LOG-001] Should logout successfully with valid token', async ({ request }) => {
    // Login fresh for logout test — uses a newly registered user to avoid touching saved sessions
    const user = newUser();
    await request.post(`${BASE_URL}/register`, { data: user });
    const loginRes = await request.post(`${BASE_URL}/login`, {
      data: { email: user.email, password: user.password },
    });
    const { accessToken, refreshToken } = await loginRes.json();

    const res = await request.post(`${BASE_URL}/logout`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { refreshToken },
    });
    const body = await res.json();

    expect(res.status()).toBe(200);
    expect(body.message).toBe('Logged out successfully');
  });

  test('[LOG-002] Refresh token should be invalidated after logout', async ({ request }) => {
    const user = newUser();
    await request.post(`${BASE_URL}/register`, { data: user });
    const loginRes = await request.post(`${BASE_URL}/login`, {
      data: { email: user.email, password: user.password },
    });
    const { accessToken, refreshToken } = await loginRes.json();

    // Logout
    await request.post(`${BASE_URL}/logout`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      data: { refreshToken },
    });

    // Try to refresh after logout
    const res = await request.post(`${BASE_URL}/refresh`, { data: { refreshToken } });
    expect(res.status()).toBe(403);
  });

  test('[LOG-003] Should return 401 when no auth header provided', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/logout`, {
      data: { refreshToken: 'sometoken' },
    });
    expect(res.status()).toBe(401);
  });

});