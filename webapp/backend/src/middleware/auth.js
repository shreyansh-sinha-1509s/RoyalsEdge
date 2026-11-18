import jwt from 'jsonwebtoken';
import { AppError } from '../utils/response.js';

export const ADMIN_COOKIE_NAME = 'rr_admin_session';

export function signAdminToken(adminUser, env) {
  return jwt.sign(
    {
      sub: String(adminUser.id),
      email: adminUser.email,
      role: adminUser.role,
    },
    env.JWT_SECRET,
    { expiresIn: env.JWT_EXPIRES_IN || '8h' }
  );
}

export function getAdminCookieOptions(env) {
  const isProd = env.NODE_ENV === 'production';
  return {
    httpOnly: true,
    secure: isProd,
    sameSite: isProd ? 'strict' : 'lax',
    path: '/',
    maxAge: 8 * 60 * 60 * 1000,
  };
}

export function createRequireAdmin(prisma, env) {
  return async function requireAdmin(req, _res, next) {
    try {
      const token = req.cookies?.[ADMIN_COOKIE_NAME];
      if (!token) {
        return next(new AppError(401, 'UNAUTHORIZED', 'Administrator authentication required.'));
      }

      let payload;
      try {
        payload = jwt.verify(token, env.JWT_SECRET);
      } catch {
        return next(new AppError(401, 'INVALID_SESSION', 'Session expired or invalid. Please log in again.'));
      }

      const adminId = Number(payload.sub);
      if (!Number.isInteger(adminId)) {
        return next(new AppError(401, 'INVALID_SESSION', 'Invalid administrator session payload.'));
      }

      const admin = await prisma.adminUser.findUnique({
        where: { id: adminId },
        select: { id: true, email: true, role: true, isActive: true, lastLoginAt: true },
      });

      if (!admin || !admin.isActive || admin.role !== 'ADMIN') {
        return next(new AppError(403, 'FORBIDDEN', 'Administrator account is inactive or unauthorized.'));
      }

      req.admin = admin;
      return next();
    } catch (err) {
      return next(err);
    }
  };
}

