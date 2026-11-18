import { ZodError } from 'zod';
import { AppError } from '../utils/response.js';

/**
 * Central Express error handler.
 * Never exposes stack traces, SQL strings, or environment secrets to clients.
 */
export function notFoundHandler(req, res) {
  res.status(404).json({
    success: false,
    error: {
      code: 'NOT_FOUND',
      message: `Route not found: ${req.method} ${req.originalUrl}`,
    },
  });
}

export function errorHandler(err, _req, res, _next) {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message,
        ...(err.details ? { details: err.details } : {}),
      },
    });
  }

  if (err instanceof ZodError) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid request parameters.',
        details: err.issues.map((i) => ({
          field: i.path.join('.'),
          message: i.message,
        })),
      },
    });
  }

  if (err?.code === 'P1001' || err?.code === 'P1002' || err?.name === 'PrismaClientInitializationError') {
    return res.status(503).json({
      success: false,
      error: {
        code: 'DATABASE_UNAVAILABLE',
        message: 'Database service is currently unreachable.',
      },
    });
  }

  if (err?.code === 'P2025') {
    return res.status(404).json({
      success: false,
      error: {
        code: 'RECORD_NOT_FOUND',
        message: 'Requested record was not found.',
      },
    });
  }

  if (err?.type === 'entity.too.large') {
    return res.status(413).json({
      success: false,
      error: {
        code: 'PAYLOAD_TOO_LARGE',
        message: 'Request payload exceeds allowed size limit.',
      },
    });
  }

  // Log error code/message safely without leaking secrets
  if (process.env.NODE_ENV !== 'test') {
    console.error('[API ERROR]', err?.name || 'Error', err?.code || '', err?.message || 'Unexpected error');
  }

  return res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected server error occurred.',
    },
  });
}

