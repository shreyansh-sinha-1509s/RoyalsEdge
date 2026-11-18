import bcrypt from 'bcryptjs';
import readline from 'node:readline';
import { Writable } from 'node:stream';
import { loadEnv } from '../src/config/env.js';
import { disconnectPrisma, getPrismaClient } from '../src/config/prisma.js';

function promptHidden(promptText) {
  return new Promise((resolve) => {
    let muted = false;
    const mutableStdout = new Writable({
      write(chunk, encoding, callback) {
        if (!muted) process.stdout.write(chunk, encoding);
        callback();
      },
    });

    const rl = readline.createInterface({
      input: process.stdin,
      output: mutableStdout,
      terminal: true,
    });

    process.stdout.write(promptText);
    muted = true;
    rl.question('', (answer) => {
      muted = false;
      process.stdout.write('\n');
      rl.close();
      resolve(answer);
    });
  });
}

async function main() {
  const env = loadEnv({ requireDatabase: true, requireJwt: false });
  const email = (env.ADMIN_BOOTSTRAP_EMAIL || '').trim().toLowerCase();

  if (!email || email === 'admin@example.com') {
    throw new Error(
      'Set a valid ADMIN_BOOTSTRAP_EMAIL in webapp/backend/.env before running bootstrap:admin.'
    );
  }

  console.log('=== RoyalsEdge — Secure Admin Bootstrap ===');
  console.log(`Target admin email from .env: ${email}`);
  console.log('Password input is hidden and will NEVER be logged or stored in plaintext.\n');

  const password = await promptHidden('Enter strong admin password (min 12 chars): ');
  if (password.length < 12) {
    throw new Error('Admin password must be at least 12 characters long.');
  }

  const confirm = await promptHidden('Confirm admin password: ');
  if (password !== confirm) {
    throw new Error('Passwords do not match. Aborting without changes.');
  }

  const passwordHash = await bcrypt.hash(password, 12);
  const prisma = getPrismaClient();

  const admin = await prisma.adminUser.upsert({
    where: { email },
    update: { passwordHash, isActive: true, role: 'ADMIN' },
    create: { email, passwordHash, isActive: true, role: 'ADMIN' },
    select: { id: true, email: true, role: true, isActive: true, updatedAt: true },
  });

  await prisma.adminAuditLog.create({
    data: {
      adminUserId: admin.id,
      actorEmail: admin.email,
      action: 'ADMIN_BOOTSTRAP',
      status: 'SUCCESS',
      detailsJson: { source: 'CLI' },
    },
  });

  console.log(`\nAdmin account ready: id=${admin.id}, email=${admin.email}, role=${admin.role}`);
}

main()
  .catch((err) => {
    console.error('\n[BOOTSTRAP FAILED]', err.message);
    process.exitCode = 1;
  })
  .finally(async () => {
    await disconnectPrisma();
  });

