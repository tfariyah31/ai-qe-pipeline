const jwt = require('jsonwebtoken');

// primary auth middleware
const authMiddleware = (req, res, next) => {
  try {
    const authHeader = req.header('Authorization');
    if (!authHeader) {
      return res.status(401).json({ message: 'Authorization header missing' });
    }

    const token = authHeader.replace('Bearer ', '');
    if (!token || token === authHeader) {
      return res.status(401).json({ message: 'Token missing from Authorization header' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.userId = decoded.userId;
    req.userRole = decoded.role; // may be undefined if old tokens still exist
    next();

  } catch (err) {
    res.status(401).json({ message: 'Invalid token' });
  }
};

// helper factory to restrict routes to one or more roles
const requireRole = (...allowedRoles) => {
  return (req, res, next) => {
    if (!req.userRole) {
      return res.status(403).json({ message: 'Role information missing' });
    }
    if (!allowedRoles.includes(req.userRole)) {
      return res.status(403).json({ message: 'Forbidden: insufficient privileges' });
    }
    next();
  };
};

// export both the middleware and the requireRole helper
module.exports = authMiddleware;
module.exports.requireRole = requireRole;