import { createApp } from './app.js';
import { loadEnv } from './config/env.js';
import { disconnectPrisma, getPrismaClient } from './config/prisma.js';

async function startServer() {
  let env;
  try {
    env = loadEnv();
  } catch (err) {
    console.error('[STARTUP CONFIG ERROR]', err.message);
    process.exit(1);
  }

  const prisma = getPrismaClient();
  const app = createApp({ prismaClient: prisma, envOverride: env });

  const server = app.listen(env.PORT, () => {
    console.log(`RoyalsEdge API listening on port ${env.PORT} (${env.NODE_ENV})`);
  });

  const shutdown = async (signal) => {
    console.log(`\nReceived ${signal}. Closing HTTP server and database connections...`);
    server.close(async () => {
      await disconnectPrisma();
      process.exit(0);
    });
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

startServer();

