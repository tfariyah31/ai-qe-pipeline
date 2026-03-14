import { test, expect } from '@playwright/test';
import { getSession, authHeader, TEST_USERS } from '../fixtures/auth.fixture';
import { TEST_PRODUCTS, API_URL } from '../fixtures/test-data';

/**
 * Products API Tests
 * GET    /api/products/     — All roles: get all products
 * GET    /api/products/:id  — All roles: get single product
 * POST   /api/products/     — Merchant, Super Admin: create product
 * PUT    /api/products/:id  — Merchant, Super Admin: update product
 * DELETE /api/products/:id  — Merchant, Super Admin: delete product
 */

const BASE_URL = `${API_URL}/products`;

// ---------------------------------------------------------------------------
// Helper — asserts the shape of a single product object
// ---------------------------------------------------------------------------

function expectProductShape(product: any) {
  expect(product).toHaveProperty('id');
  expect(product).toHaveProperty('name');
  expect(product).toHaveProperty('description');
  expect(product).toHaveProperty('image');
  expect(product).toHaveProperty('price');
  expect(product).toHaveProperty('rating');
  // Model strips _id and __v via toJSON transform
  expect(product._id).toBeUndefined();
  expect(product.__v).toBeUndefined();
}

// ---------------------------------------------------------------------------
// Unique product factory — avoids test pollution across runs
// ---------------------------------------------------------------------------

const newProduct = (overrides = {}) => ({
  ...TEST_PRODUCTS.valid,
  name: `${TEST_PRODUCTS.valid.name} ${Date.now()}`,
  ...overrides,
});

// ---------------------------------------------------------------------------
// GET /api/products  — Get all products
// ---------------------------------------------------------------------------

test.describe('GET /api/products', () => {
  test('[PRD-001] Superadmin can fetch all products', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);

    const body = await res.json();
    expect(body.success).toBe(true);
    expect(Array.isArray(body.products)).toBe(true);
  });

  test('[PRD-002] Merchant can fetch all products', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('merchant'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-003] Customer can fetch all products', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('customer'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-004] Each product in the list has the correct shape', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
    });

    const { products } = await res.json();
    products.forEach(expectProductShape);
  });

  test('[PRD-005] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`);
    expect([401, 403]).toContain(res.status());
  });

  test('[PRD-006] Returns 401 with an invalid token', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/`, {
      headers: { Authorization: 'Bearer invalid.token.here' },
    });
    expect([401, 403]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// GET /api/products/:id  — Get single product
// ---------------------------------------------------------------------------

test.describe('GET /api/products/:id', () => {
  let createdProductId: string;

  // Create a product once to use across this describe block
  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });
    const body = await res.json();
    createdProductId = body.product.id;
  });

  test.afterAll(async ({ request }) => {
    if (createdProductId) {
      await request.delete(`${BASE_URL}/${createdProductId}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[PRD-010] Superadmin can fetch a single product by ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/${createdProductId}`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);
    const { product } = await res.json();
    expectProductShape(product);
    expect(product.id).toBe(createdProductId);
  });

  test('[PRD-011] Merchant can fetch a single product by ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/${createdProductId}`, {
      headers: authHeader('merchant'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-012] Customer can fetch a single product by ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/${createdProductId}`, {
      headers: authHeader('customer'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-013] Returns 404 for a non-existent product ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/000000000000000000000000`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(404);
  });

  test('[PRD-014] Returns 400 for a malformed product ID', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/not-a-valid-id`, {
      headers: authHeader('superadmin'),
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-015] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.get(`${BASE_URL}/${createdProductId}`);
    expect([401, 403]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// POST /api/products  — Create product
// ---------------------------------------------------------------------------

test.describe('POST /api/products', () => {
  // Track created IDs to clean up after each test
  const createdIds: string[] = [];

  test.afterAll(async ({ request }) => {
    for (const id of createdIds) {
      await request.delete(`${BASE_URL}/${id}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[PRD-020] Superadmin can create a product', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });

    expect(res.status()).toBe(201);
    const { success, product } = await res.json();
    expect(success).toBe(true);
    expectProductShape(product);
    createdIds.push(product.id);
  });

  test('[PRD-021] Merchant can create a product', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('merchant'),
      data: newProduct(),
    });

    expect(res.status()).toBe(201);
    const { product } = await res.json();
    expectProductShape(product);
    createdIds.push(product.id);
  });

  test('[PRD-022] Created product has correct field values', async ({ request }) => {
    const payload = newProduct();

    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: payload,
    });

    expect(res.status()).toBe(201);
    const { product } = await res.json();
    expect(product.name).toBe(payload.name);
    expect(product.description).toBe(payload.description);
    expect(product.image).toBe(payload.image);
    expect(product.price).toBe(payload.price);
    expect(product.rating).toBe(payload.rating);
    createdIds.push(product.id);
  });

  test('[PRD-023] Returns 400 when required field "name" is missing', async ({ request }) => {
    const { name, ...withoutName } = newProduct();

    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: withoutName,
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-024] Returns 400 when required field "description" is missing', async ({
    request,
  }) => {
    const { description, ...withoutDescription } = newProduct();

    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: withoutDescription,
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-025] Returns 400 when required field "image" is missing', async ({ request }) => {
    const { image, ...withoutImage } = newProduct();

    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: withoutImage,
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-026] Returns 400 when required field "rating" is missing', async ({ request }) => {
    const { rating, ...withoutRating } = newProduct();

    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: withoutRating,
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-027] Returns 403 when a customer attempts to create a product', async ({
    request,
  }) => {
    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('customer'),
      data: newProduct(),
    });

    expect([401, 403]).toContain(res.status());
  });

  test('[PRD-028] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.post(`${BASE_URL}/`, {
      data: newProduct(),
    });

    expect([401, 403]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// PUT /api/products/:id  — Update product
// ---------------------------------------------------------------------------

test.describe('PUT /api/products/:id', () => {
  let productId: string;

  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });
    productId = (await res.json()).product.id;
  });

  test.afterAll(async ({ request }) => {
    if (productId) {
      await request.delete(`${BASE_URL}/${productId}`, {
        headers: authHeader('superadmin'),
      });
    }
  });

  test('[PRD-030] Superadmin can update a product name', async ({ request }) => {
    const updatedName = `Updated Product ${Date.now()}`;

    const res = await request.put(`${BASE_URL}/${productId}`, {
      headers: authHeader('superadmin'),
      data: { name: updatedName },
    });

    expect(res.status()).toBe(200);
    const { product } = await res.json();
    expect(product.name).toBe(updatedName);
  });

  test('[PRD-031] Merchant can update a product price', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${productId}`, {
      headers: authHeader('merchant'),
      data: { price: 99.99 },
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).product.price).toBe(99.99);
  });

  test('[PRD-032] Updated product has correct shape', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${productId}`, {
      headers: authHeader('superadmin'),
      data: { description: 'Updated description' },
    });

    expect(res.status()).toBe(200);
    expectProductShape((await res.json()).product);
  });

  test('[PRD-033] Returns 404 when updating a non-existent product', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/000000000000000000000000`, {
      headers: authHeader('superadmin'),
      data: { name: 'Ghost' },
    });

    expect(res.status()).toBe(404);
  });

  test('[PRD-034] Returns 400 for a malformed product ID', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/not-a-valid-id`, {
      headers: authHeader('superadmin'),
      data: { name: 'Ghost' },
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-035] Returns 403 when a customer attempts to update a product', async ({
    request,
  }) => {
    const res = await request.put(`${BASE_URL}/${productId}`, {
      headers: authHeader('customer'),
      data: { name: 'Sneaky Customer' },
    });

    expect([401, 403]).toContain(res.status());
  });

  test('[PRD-036] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.put(`${BASE_URL}/${productId}`, {
      data: { name: 'Ghost' },
    });

    expect([401, 403]).toContain(res.status());
  });
});

// ---------------------------------------------------------------------------
// DELETE /api/products/:id  — Delete product
// ---------------------------------------------------------------------------

test.describe('DELETE /api/products/:id', () => {
  test('[PRD-040] Superadmin can delete a product', async ({ request }) => {
    // Create a dedicated product to delete
    const created = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });
    const { id } = (await created.json()).product;

    const res = await request.delete(`${BASE_URL}/${id}`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-041] Merchant can delete a product', async ({ request }) => {
    const created = await request.post(`${BASE_URL}/`, {
      headers: authHeader('merchant'),
      data: newProduct(),
    });
    const { id } = (await created.json()).product;

    const res = await request.delete(`${BASE_URL}/${id}`, {
      headers: authHeader('merchant'),
    });

    expect(res.status()).toBe(200);
    expect((await res.json()).success).toBe(true);
  });

  test('[PRD-042] Deleted product is no longer retrievable', async ({ request }) => {
    const created = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });
    const { id } = (await created.json()).product;

    await request.delete(`${BASE_URL}/${id}`, {
      headers: authHeader('superadmin'),
    });

    const res = await request.get(`${BASE_URL}/${id}`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(404);
  });

  test('[PRD-043] Returns 404 when deleting a non-existent product', async ({ request }) => {
    const res = await request.delete(`${BASE_URL}/000000000000000000000000`, {
      headers: authHeader('superadmin'),
    });

    expect(res.status()).toBe(404);
  });

  test('[PRD-044] Returns 400 for a malformed product ID', async ({ request }) => {
    const res = await request.delete(`${BASE_URL}/not-a-valid-id`, {
      headers: authHeader('superadmin'),
    });

    expect([400, 422]).toContain(res.status());
  });

  test('[PRD-045] Returns 403 when a customer attempts to delete a product', async ({
    request,
  }) => {
    const created = await request.post(`${BASE_URL}/`, {
      headers: authHeader('superadmin'),
      data: newProduct(),
    });
    const { id } = (await created.json()).product;

    const res = await request.delete(`${BASE_URL}/${id}`, {
      headers: authHeader('customer'),
    });

    expect([401, 403]).toContain(res.status());

    // Cleanup
    await request.delete(`${BASE_URL}/${id}`, {
      headers: authHeader('superadmin'),
    });
  });

  test('[PRD-046] Returns 401 when no token is provided', async ({ request }) => {
    const res = await request.delete(`${BASE_URL}/000000000000000000000000`);
    expect([401, 403]).toContain(res.status());
  });
});