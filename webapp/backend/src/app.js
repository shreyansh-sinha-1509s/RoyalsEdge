import compression from 'compression';
import cookieParser from 'cookie-parser';
import cors from 'cors';
import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import { loadEnv } from './config/env.js';
import { getPrismaClient } from './config/prisma.js';
import { errorHandler, notFoundHandler } from './middleware/errorHandler.js';
import { createPublicRateLimiter } from './middleware/rateLimiter.js';
import { createApiRouter } from './routes/index.js';

export function createApp({ prismaClient = null, envOverride = null } = {}) {
  const env = envOverride || loadEnv();
  const prisma = prismaClient || getPrismaClient();

  const app = express();
  app.set('trust proxy', 1);

  // Security headers
  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: 'cross-origin' },
    })
  );

  // Strict CORS allowlist
  app.use(
    cors({
      origin(origin, callback) {
        if (!origin || env.ALLOWED_ORIGINS.includes(origin)) {
          return callback(null, true);
        }
        return callback(new Error('CORS origin not allowed'));
      },
      credentials: true,
    })
  );

  app.use(compression());
  app.use(cookieParser());
  app.use(express.json({ limit: '1mb' }));
  app.use(express.urlencoded({ extended: false, limit: '1mb' }));

  if (env.NODE_ENV !== 'test') {
    app.use(morgan('[:date[iso]] :method :url :status :response-time ms'));
  }

  app.use('/api', createPublicRateLimiter());
  app.use('/api', createApiRouter(prisma, env));

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
}

