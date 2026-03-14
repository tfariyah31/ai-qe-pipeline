import { request } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { TEST_USERS, API_URL } from './fixtures/test-data';

const SESSION_DIR = path.join(__dirname, '.sessions');

// Only session-based roles need pre-login (not blocked/locked users)
const SESSION_ROLES = [
  TEST_USERS.superadmin,
  TEST_USERS.merchant,
  TEST_USERS.customer,
] as const;

async function globalSetup() {
  if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  }

  console.log(`📁 Sessions directory: ${SESSION_DIR}`);
  const context = await request.newContext();

  for (const user of SESSION_ROLES) {
    const sessionFile = path.join(SESSION_DIR, `${user.role}.json`);

    // Reuse session if under 20 minutes old
    if (fs.existsSync(sessionFile)) {
      const ageMinutes = (Date.now() - fs.statSync(sessionFile).mtimeMs) / 1000 / 60;
      if (ageMinutes < 20) {
        console.log(`✅ Reusing session for ${user.role} (${Math.round(ageMinutes)}m old)`);
        continue;
      }
    }

    try {
      console.log(`🔐 Logging in as ${user.role}...`);
      const res = await context.post(`${API_URL}/auth/login`, {
        data: { email: user.email, password: user.password },
      });

      if (!res.ok()) {
        console.warn(`⚠️  Could not login as ${user.role}: ${res.status()}`);
        continue;
      }

      const body = await res.json();
      fs.writeFileSync(sessionFile, JSON.stringify({
        accessToken: body.accessToken,
        refreshToken: body.refreshToken,
        user: body.user,
        savedAt: Date.now(),
      }, null, 2));

      console.log(`✅ Session saved for ${user.role}`);
    } catch (err) {
      console.warn(`⚠️  Failed to create session for ${user.role}:`, err);
    }
  }

  await context.dispose();
}

export default globalSetup;