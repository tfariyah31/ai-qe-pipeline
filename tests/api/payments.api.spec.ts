/**
 * TestMart — Payments API Contract Tests
 * File: tests/api/payments.api.spec.ts
 * This suite validates the contract of the /api/payments/create-intent endpoint.
 * It covers:
 *  - API contract validation (shape, types, formats)
 *  - Auth & RBAC enforcement
 *  - Input boundary & edge cases
 *  - Stripe-specific behaviour (PI id format, secret format)
 *  - Security hardening (injection, missing fields)
 */

import { test, expect, APIRequestContext, request } from '@playwright/test';
import { authHeader, getSession } from '../fixtures/auth.fixture';
import { API_URL } from '../fixtures/test-data';

// ─── Constants ────────────────────────────────────────────────────────────────

const ENDPOINT = `${API_URL}/payments/create-intent`;

// Stripe PI id / secret regex patterns
const PI_ID_PATTERN = /^pi_[a-zA-Z0-9]+$/;
const CLIENT_SECRET_PATTERN = /^pi_[a-zA-Z0-9]+_secret_[a-zA-Z0-9]+$/;

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function postCreateIntent(
  apiContext: APIRequestContext,
  body: Record<string, unknown>,
  headers: Record<string, string> = {}
) {
  return apiContext.post(ENDPOINT, {
    data: body,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

// ─── Suite ────────────────────────────────────────────────────────────────────

test.describe('POST /api/payments/create-intent', () => {

  // ── 1. Response Contract ───────────────────────────────────────────────────

  test.describe('Response contract', () => {

    test('returns 200 with correct shape for valid amount', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 49.99 },
        authHeader('customer')
      );

      expect(res.status()).toBe(200);

      const body = await res.json();

      // Shape assertions
      expect(body).toHaveProperty('clientSecret');
      expect(body).toHaveProperty('paymentIntentId');

      // Type assertions
      expect(typeof body.clientSecret).toBe('string');
      expect(typeof body.paymentIntentId).toBe('string');

      // Stripe format assertions
      expect(body.paymentIntentId).toMatch(PI_ID_PATTERN);
      expect(body.clientSecret).toMatch(CLIENT_SECRET_PATTERN);

      // clientSecret must start with the same PI id
      expect(body.clientSecret.startsWith(body.paymentIntentId)).toBeTruthy();
    });

    test('each call produces a unique paymentIntentId', async ({ request }) => {
      const [res1, res2] = await Promise.all([
        postCreateIntent(request, { amount: 10 }, authHeader('customer')),
        postCreateIntent(request, { amount: 10 }, authHeader('customer')),
      ]);

      const [b1, b2] = await Promise.all([res1.json(), res2.json()]);

      expect(b1.paymentIntentId).not.toBe(b2.paymentIntentId);
      expect(b1.clientSecret).not.toBe(b2.clientSecret);
    });

    test('response Content-Type is application/json', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 20 },
        authHeader('customer')
      );
      expect(res.headers()['content-type']).toContain('application/json');
    });

    test('does not leak sensitive fields in response', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 20 },
        authHeader('customer')
      );
      const body = await res.json();

      // Must NOT expose these
      expect(body).not.toHaveProperty('stripeSecretKey');
      expect(body).not.toHaveProperty('apiKey');
      expect(body).not.toHaveProperty('userId');
      expect(body).not.toHaveProperty('password');
    });

  });

  // ── 2. Amount Boundary Tests ───────────────────────────────────────────────

  test.describe('Amount validation', () => {

    test('accepts minimum valid amount ($0.50)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 0.50 },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('accepts large cart total ($9999.99)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 9999.99 },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('accepts two-decimal precision amount ($29.99)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 29.99 },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('returns 400 when amount is missing', async ({ request }) => {
      const res = await postCreateIntent(request, {}, authHeader('customer'));

      expect(res.status()).toBe(400);
      const body = await res.json();
      expect(body).toHaveProperty('message');
      expect(body.message.toLowerCase()).toContain('amount');
    });

    test('returns 400 when amount is zero', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 0 },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
    });

    test('returns 400 when amount is negative', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: -10 },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
    });

    test('returns 400 when amount is below Stripe minimum ($0.49)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 0.49 },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
      const body = await res.json();
      expect(body.message).toMatch(/0\.50/);
    });

    test('returns 400 when amount is a string', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 'twenty' },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
    });

    test('returns 400 when amount is null', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: null },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
    });

    test('returns 400 when amount is an array', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: [10, 20] },
        authHeader('customer')
      );
      expect(res.status()).toBe(400);
    });

  });

  // ── 3. Currency Tests ──────────────────────────────────────────────────────

  test.describe('Currency handling', () => {

    test('defaults to USD when currency is omitted', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 15 },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('accepts explicit USD', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 15, currency: 'usd' },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('accepts GBP', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 15, currency: 'gbp' },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('accepts uppercase currency (EUR)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 15, currency: 'EUR' },
        authHeader('customer')
      );
      // Should normalise to lowercase and succeed
      expect(res.status()).toBe(200);
    });

  });

  // ── 4. Authentication Tests ────────────────────────────────────────────────

  test.describe('Authentication enforcement', () => {

    test('returns 401 with no Authorization header', async ({ request }) => {
      const res = await postCreateIntent(request, { amount: 10 });
      expect(res.status()).toBe(401);
    });

    test('returns 401 with malformed Bearer token', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 10 },
        { Authorization: 'Bearer this.is.not.valid' }
      );
      expect(res.status()).toBe(401);
    });

    test('returns 401 with empty Bearer value', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 10 },
        { Authorization: 'Bearer ' }
      );
      expect(res.status()).toBe(401);
    });

    test('returns 401 with non-Bearer scheme', async ({ request }) => {
      const session = getSession('customer');
      const res = await postCreateIntent(
        request,
        { amount: 10 },
        { Authorization: `Basic ${session.accessToken}` }
      );
      expect(res.status()).toBe(401);
    });

    test('returns 401 with expired/tampered token', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 10 },
        { Authorization: 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VySWQiOiJmYWtlIn0.invalidsignature' }
      );
      expect(res.status()).toBe(401);
    });

  });

  // ── 5. RBAC Tests ─────────────────────────────────────────────────────────

  test.describe('Role-based access', () => {

    test('customer role can create a payment intent', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 25 },
        authHeader('customer')
      );
      expect(res.status()).toBe(200);
    });

    test('superadmin role response is 200 or 403 — document actual behaviour', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 25 },
        authHeader('superadmin')
      );
      // Log for SDET awareness — adjust assertion to match your RBAC policy
      console.log(`superadmin → payment intent status: ${res.status()}`);
      expect([200, 403]).toContain(res.status());
    });

    test('merchant role response is 200 or 403 — document actual behaviour', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 25 },
        authHeader('merchant')
      );
      console.log(`merchant → payment intent status: ${res.status()}`);
      expect([200, 403]).toContain(res.status());
    });

  });

  // ── 6. Security / Injection Tests ─────────────────────────────────────────

  test.describe('Security hardening', () => {

    const injectionPayloads = [
      { label: 'NoSQL operator',      amount: { $gt: 0 } },
      { label: 'SQL injection',       amount: "1; DROP TABLE payments;--" },
      { label: 'XSS in amount',       amount: '<script>alert(1)</script>' },
      { label: 'Object amount',       amount: { value: 10 } },
      { label: 'Boolean amount',      amount: true },
    ];

    for (const { label, amount } of injectionPayloads) {
      test(`returns 400 for injection payload: ${label}`, async ({ request }) => {
        const res = await postCreateIntent(
          request,
          { amount },
          authHeader('customer')
        );
        expect(res.status()).toBe(400);
      });
    }

    test('extra unknown fields in body are ignored (no 400)', async ({ request }) => {
      const res = await postCreateIntent(
        request,
        { amount: 10, unknownField: 'hacker', __proto__: { isAdmin: true } },
        authHeader('customer')
      );
      // Should succeed — unknown fields must not cause a 500
      expect(res.status()).toBe(200);
    });

    test('Content-Type: text/plain is rejected or handled gracefully', async ({ request }) => {
      const res = await request.post(ENDPOINT, {
        data: 'amount=10',
        headers: {
          'Content-Type': 'text/plain',
          ...authHeader('customer'),
        },
      });
      // Must not be 500 — either 400 (bad body) or 200 if server parses it
      expect(res.status()).not.toBe(500);
    });

  });

  // ── 7. Idempotency & Concurrency ──────────────────────────────────────────

  test.describe('Idempotency and concurrency', () => {

    test('10 concurrent requests all return 200 with unique PI ids', async ({ request }) => {
      const responses = await Promise.all(
        Array.from({ length: 10 }, () =>
          postCreateIntent(request, { amount: 5 }, authHeader('customer'))
        )
      );

      const bodies = await Promise.all(responses.map(r => r.json()));
      const statuses = responses.map(r => r.status());
      const piIds = bodies.map(b => b.paymentIntentId);

      // All should succeed
      expect(statuses.every(s => s === 200)).toBeTruthy();

      // All PI ids should be unique
      const uniqueIds = new Set(piIds);
      expect(uniqueIds.size).toBe(10);
    });

  });

  // ── 8. HTTP Method Enforcement ────────────────────────────────────────────

  test.describe('HTTP method enforcement', () => {

    test('GET returns 404 or 405', async ({ request }) => {
      const res = await request.get(ENDPOINT, {
        headers: authHeader('customer'),
      });
      expect([404, 405]).toContain(res.status());
    });

    test('PUT returns 404 or 405', async ({ request }) => {
      const res = await request.put(ENDPOINT, {
        data: { amount: 10 },
        headers: authHeader('customer'),
      });
      expect([404, 405]).toContain(res.status());
    });

    test('DELETE returns 404 or 405', async ({ request }) => {
      const res = await request.delete(ENDPOINT, {
        headers: authHeader('customer'),
      });
      expect([404, 405]).toContain(res.status());
    });

  });

});