import { createApp } from '../webapp/backend/src/app.js';

let cachedApp = null;
let initError = null;

function getApp() {
  if (cachedApp) return cachedApp;
  try {
    cachedApp = createApp();
    return cachedApp;
  } catch (err) {
    initError = err;
    return null;
  }
}

/**
 * Vercel Serverless Function entrypoint wrapping the existing Express app.
 * Never calls app.listen() and never runs Prisma migrations on cold start.
 */
export default function handler(req, res) {
  const app = getApp();
  if (!app) {
    return res.status(503).json({
      success: false,
      error: {
        code: 'SERVICE_CONFIGURATION_ERROR',
        message: 'Backend environment configuration is incomplete on this deployment.',
      },
    });
  }
  return app(req, res);
}
