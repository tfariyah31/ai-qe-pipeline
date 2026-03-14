const rateLimit = require('express-rate-limit');

// ============================================================================
// INJECTION DETECTION HELPER
// ============================================================================
const detectInjection = (value) => {
  // Check if value is an object (NoSQL injection attempt)
  if (typeof value === 'object' && value !== null) {
    return true;
  }
  
  // Check for injection patterns in strings
  if (typeof value === 'string') {
    const injectionPatterns = [
      /\$ne/i, /\$gt/i, /\$lt/i, /\$or/i, /\$and/i,
      /\$where/i, /\$regex/i, /<script/i, /javascript:/i,
      /union.*select/i, /drop.*table/i
    ];
    return injectionPatterns.some(pattern => pattern.test(value));
  }
  
  return false;
};

// ============================================================================
// MIDDLEWARE: Block Injection Attempts BEFORE Rate Limiter
// ============================================================================
const blockInjectionAttempts = (req, res, next) => {
  try {
    // Check if request body exists and is an object
    if (req.body && typeof req.body === 'object' && !Array.isArray(req.body)) {
      // Check all values in the body for injection attempts
      const bodyValues = Object.values(req.body);
      const hasInjection = bodyValues.some(detectInjection);
      
      if (hasInjection) {
        console.warn('🚫 Injection attempt blocked:', {
          ip: req.ip,
          body: req.body
        });
        
        // Return 400 immediately, don't continue to rate limiter or controller
        return res.status(400).json({
          success: false,
          message: 'Invalid input format'
        });
      }
    }
    
    // No injection detected, continue
    next();
    
  } catch (error) {
    console.error('❌ Injection detection error:', error);
    // On error, block the request to be safe
    return res.status(400).json({
      success: false,
      message: 'Invalid request format'
    });
  }
};

// ============================================================================
// AUTH RATE LIMITER
// ============================================================================
const authLimiter = rateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 3,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: "Too many failed login attempts. Try again later."
  },
  skipSuccessfulRequests: true,
  
  keyGenerator: (req) => {
    try {
      // At this point, injection attempts are already blocked
      // So we can safely process the email
      
      if (req.body && req.body.email && typeof req.body.email === 'string') {
        return req.body.email.toLowerCase().trim();
      }

      return req.ip;

    } catch (error) {
      console.error('❌ Rate limit key generator error:', error);
      return req.ip;
    }
  },

  handler: (req, res) => {
    const identifier = req.body?.email 
      ? (typeof req.body.email === 'string' ? req.body.email : 'invalid-input')
      : req.ip;
    
    console.warn(`⚠️ Rate limit exceeded for: ${identifier}`);
    
    res.status(429).json({
      success: false,
      message: "Too many failed login attempts. Try again later.",
      error: "RATE_LIMIT_EXCEEDED"
    });
  }
});

// ============================================================================
// EXPORTS
// ============================================================================
module.exports = {
  authLimiter,
  blockInjectionAttempts
};

/*const rateLimit = require('express-rate-limit');

const authLimiter = rateLimit({
  windowMs: 5 * 60 * 1000, // 5 minutes
  max: 3,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    error: "Too many failed login attempts. Try again later."
  },
  skipSuccessfulRequests: true,

  keyGenerator: (req) => {
    if (req.body && req.body.email) {
      return req.body.email.toLowerCase();
    }
    return req.ip;
  }
});

module.exports = authLimiter; */
