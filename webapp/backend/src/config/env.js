import dotenv from 'dotenv';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BACKEND_ROOT = path.resolve(__dirname, '..', '..');

// Load local .env if present (silently skipped if env vars are injected by host)
dotenv.config({ path: path.join(BACKEND_ROOT, '.env') });

const PLACEHOLDER_PATTERNS = [
  /^YOUR_/i,
  /^REPLACE_WITH_/i,
  /^CHANGEME/i,
  /^example$/i,
];

function isPlaceholder(val) {
  if (!val) return true;
  return PLACEHOLDER_PATTERNS.some((re) => re.test(val.trim()));
}

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().min(1).max(65535).default(5000),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),
  DIRECT_URL: z.string().optional(),
  JWT_SECRET: z.string().min(32, 'JWT_SECRET must be at least 32 characters'),
  JWT_EXPIRES_IN: z.string().default('8h'),
  FRONTEND_ORIGIN: z.string().default('http://localhost:5173'),
  ADMIN_BOOTSTRAP_EMAIL: z.string().email().optional(),
});

let cachedEnv = null;

/**
 * Validates and returns sanitized runtime environment configuration.
 * Never logs or exposes secret values in error messages.
 */
export function loadEnv({ requireDatabase = true, requireJwt = true } = {}) {
  const nodeEnv = process.env.NODE_ENV || 'development';

  if (nodeEnv === 'test') {
    return {
      NODE_ENV: 'test',
      PORT: Number(process.env.PORT || 5000),
      DATABASE_URL: process.env.DATABASE_URL || 'postgresql://test:test@localhost:5432/rr_test',
      DIRECT_URL: process.env.DIRECT_URL || 'postgresql://test:test@localhost:5432/rr_test',
      JWT_SECRET:
        process.env.JWT_SECRET && process.env.JWT_SECRET.length >= 32
          ? process.env.JWT_SECRET
          : 'test-only-ephemeral-jwt-signing-key-not-for-production-use',
      JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '1h',
      FRONTEND_ORIGIN: process.env.FRONTEND_ORIGIN || 'http://localhost:5173',
      ALLOWED_ORIGINS: (process.env.FRONTEND_ORIGIN || 'http://localhost:5173')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      ADMIN_BOOTSTRAP_EMAIL: process.env.ADMIN_BOOTSTRAP_EMAIL || 'admin@example.com',
    };
  }

  if (cachedEnv) return cachedEnv;

  const missingOrInvalid = [];
  if (requireDatabase && isPlaceholder(process.env.DATABASE_URL)) {
    missingOrInvalid.push('DATABASE_URL (set your Neon pooled PostgreSQL connection string in webapp/backend/.env)');
  }
  if (requireJwt && (isPlaceholder(process.env.JWT_SECRET) || (process.env.JWT_SECRET || '').length < 32)) {
    missingOrInvalid.push('JWT_SECRET (generate a random 32+ character secret in webapp/backend/.env)');
  }

  if (missingOrInvalid.length > 0) {
    throw new Error(
      `Missing or placeholder environment configuration:\n  - ${missingOrInvalid.join('\n  - ')}\n` +
        'Copy webapp/backend/.env.example to webapp/backend/.env and configure real values locally.'
    );
  }

  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    const keys = parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`);
    throw new Error(`Invalid environment configuration:\n  - ${keys.join('\n  - ')}`);
  }

  const data = parsed.data;
  const originSet = new Set(
    data.FRONTEND_ORIGIN.split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  );
  if (process.env.VERCEL_URL) {
    originSet.add(`https://${process.env.VERCEL_URL}`);
  }
  if (process.env.VERCEL_PROJECT_PRODUCTION_URL) {
    originSet.add(`https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`);
  }
  cachedEnv = {
    ...data,
    ALLOWED_ORIGINS: Array.from(originSet),
  };
  return cachedEnv;
}

export function resetEnvCache() {
  cachedEnv = null;
}

