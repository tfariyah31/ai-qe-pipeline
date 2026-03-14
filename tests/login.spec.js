// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Login Flow', () => {
  test('should log in with valid credentials', async ({ page }) => {
    await page.goto('http://127.0.0.1:3000'); // Change if login page is under a different path

    //await page.getByLabel('Username').fill('usera');
   // await page.getByLabel('Password').fill('password');
   // await page.getByRole('button', { name: /login/i }).click();

    await page.fill('input[type="text"]', 'usera');
    await page.fill('input[type="password"]', 'password');

    await page.click('button[type="submit"]');

  // Verify navigation to the product list page
    //await expect(page).toHaveURL('http://127.0.0.1:3000/products');

    console.log('Current URL:', await page.url());
  
  // Increase timeout to 15 seconds and verify navigation
  await expect(page).toHaveURL('http://127.0.0.1:3000/products', { timeout: 15000 });

      });

  test('login response contains role and products endpoint respects role', async ({ request }) => {
    // perform login via API rather than UI
    const loginRes = await request.post('http://localhost:5001/api/auth/login', {
      data: { email: 'merchant@test.com', password: 'MerchantPass123!' }
    });
    expect(loginRes.ok()).toBeTruthy();
    const loginData = await loginRes.json();
    expect(loginData.user).toBeDefined();
    expect(loginData.user.role).toBe('merchant');

    // merchant should be allowed to create a product
    const createRes = await request.post('http://localhost:5001/api/products', {
      data: { name: 'TestProd', description: 'desc', image: '', price: 1 },
      headers: { Authorization: `Bearer ${loginData.accessToken}` }
    });
    expect(createRes.status()).not.toBe(403);

    // now try as customer and ensure forbidden
    const customerLogin = await request.post('http://localhost:5001/api/auth/login', {
      data: { email: 'customer@test.com', password: 'CustomerPass123!' }
    });
    const customerData = await customerLogin.json();
    const custCreate = await request.post('http://localhost:5001/api/products', {
      data: { name: 'Nope', description: '', image: '', price: 0 },
      headers: { Authorization: `Bearer ${customerData.accessToken}` }
    });
    expect(custCreate.status()).toBe(403);
  });

/*  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('http://127.0.0.1:3000');

    await page.fill('input[type="text"]', 'testuser');
    await page.fill('input[type="password"]', 'testpassword');

    await page.click('button[type="submit"]');

    const errorMessage = page.locator('.MuiAlert-message'); 
  await expect(errorMessage).toHaveText('Invalid credentials');
  });*/
});
