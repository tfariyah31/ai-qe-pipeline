import fs from 'fs';
import path from 'path';
import { TEST_USERS } from './test-data';

const SESSION_DIR = path.join(__dirname, '..', '.sessions');

export type AuthRole = keyof typeof TEST_USERS;

export interface SessionData {
  accessToken: string;
  refreshToken: string;
  user: { id: string; email: string; name: string; role: string };
  savedAt: number;
}

/**
 * Returns saved session tokens for a role.
 * Only works for superadmin, merchant, customer (session roles).
 * For blocked/locked users, use TEST_USERS directly in tests.
 */
export function getSession(role: 'superadmin' | 'merchant' | 'customer'): SessionData {
  const sessionFile = path.join(SESSION_DIR, `${role}.json`);

  if (!fs.existsSync(sessionFile)) {
    throw new Error(
      `No session found for "${role}" at ${sessionFile}.\n` +
      `Run global setup first or check credentials in fixtures/test-data.ts`
    );
  }

  return JSON.parse(fs.readFileSync(sessionFile, 'utf-8')) as SessionData;
}

/**
 * Returns Authorization header for a role.
 * Usage: headers: authHeader('superadmin')
 */
export function authHeader(role: 'superadmin' | 'merchant' | 'customer') {
  const session = getSession(role);
  return { Authorization: `Bearer ${session.accessToken}` };
}

/**
 * Returns credentials for any user type including blocked/locked.
 * Usage: const { email, password } = getCredentials('blockedUser')
 */
export function getCredentials(user: AuthRole) {
  return {
    email: TEST_USERS[user].email,
    password: TEST_USERS[user].password,
  };
}

// Re-export TEST_USERS for convenience
export { TEST_USERS };