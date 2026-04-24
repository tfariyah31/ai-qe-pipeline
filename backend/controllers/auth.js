const User = require('../models/User');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// embed role in the token so middleware can authorize without extra DB lookup
const generateTokens = (userId, role) => {
    const accessToken = jwt.sign(
        { userId, role },
        process.env.JWT_SECRET,
        { expiresIn: '1d' } // Short-lived
    );
    
    const refreshToken = jwt.sign(
        { userId, role },
        process.env.REFRESH_SECRET,
        { expiresIn: '7d' } // Long-lived
    );
    
    return { accessToken, refreshToken };
};

exports.register = async (req, res) => {
  const { name, email, password } = req.body;
  try {
    let user = await User.findOne({ email });
    if (user) return res.status(400).json({ message: 'User already exists' });

    // always default to 'customer' on registration; role assignment is done by admins
    user = new User({ name, email, password, role: 'customer' });
    await user.save();

    const payload = { userId: user.id, role: user.role };
    const token = jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: '1h' });

    res.status(201).json({ token, user: { id: user._id, email: user.email, name: user.name, role: user.role } });
  } catch (err) {
    res.status(500).json({ message: 'Server error' });
  }
};

exports.login = async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({
      success: false,
      message: 'Email and password required'
    });
  }
  try {
    const user = await User.findOne({ email });

    if (!user) return res.status(401).json({ success: false, error: 'INVALID_CREDENTIALS', message: 'Invalid credentials', attemptsLeft: req.rateLimit?.remaining ?? null });

    // 1. Check if account is admin-blocked
    if (user.isBlocked) {
      return res.status(403).json({ success: false, message: 'Your account is blocked. Please contact support.' });
    }

    // 2. Check if account is temporarily locked
    if (user.lockUntil && user.lockUntil > Date.now()) {
      const minutesLeft = Math.ceil((user.lockUntil - Date.now()) / 60000);
      return res.status(423).json({
        success: false,
        message: `Account locked due to too many failed attempts. Try again in ${minutesLeft} minute(s).`
      });
    }

    // 3. Check password
    const isMatch = await bcrypt.compare(password, user.password);

    if (!isMatch) {
      user.failedLoginAttempts += 1;

      // Lock account on 3rd failed attempt (so 4th request hits the lock above)
      if (user.failedLoginAttempts >= 3) {
        user.lockUntil = new Date(Date.now() + 5 * 60 * 1000); // 5 min lock
      }

      await user.save();

      const attemptsLeft = Math.max(0, 3 - user.failedLoginAttempts);

      return res.status(401).json({
        success: false,
        error: 'INVALID_CREDENTIALS',
        message: 'Invalid credentials',
        attemptsLeft,
        ...(user.lockUntil && { locked: true, message: 'Account locked due to too many failed attempts. Try again in 5 minutes.' })
      });
    }

// 4. Successful login — reset lock state
    user.failedLoginAttempts = 0;
    user.lockUntil = null;

    const { accessToken, refreshToken } = generateTokens(user._id, user.role);

    user.refreshTokens = user.refreshTokens || [];
    user.refreshTokens.push({
      token: refreshToken,
      expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
      device: req.headers['user-agent'] || 'unknown'
    });

    await user.save();

    return res.json({
      success: true,
      accessToken,
      refreshToken,
      user: { id: user._id, email: user.email, name: user.name, role: user.role }
    });

  } catch (err) {
    res.status(500).json({ success: false, message: 'Server error' });
  }
};


exports.refreshToken = async (req, res) => {
    try {
        const { refreshToken } = req.body;
        
        if (!refreshToken) {
            return res.status(401).json({ success: false, message: 'Refresh token required' });
        }
        
        // Verify refresh token
        const decoded = jwt.verify(refreshToken, process.env.REFRESH_SECRET);
        
        // Find user with this refresh token
        const user = await User.findOne({
            _id: decoded.userId,
            'refreshTokens.token': refreshToken
        });
        
        if (!user) {
            return res.status(403).json({ success: false, message: 'Invalid refresh token' });
        }
        
        // Generate new tokens
        const { accessToken, refreshToken: newRefreshToken } = generateTokens(user._id, user.role);
        
        // Remove old refresh token and add new one
        user.refreshTokens = user.refreshTokens.filter(t => t.token !== refreshToken);
        user.refreshTokens.push({
            token: newRefreshToken,
            expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
            device: req.headers['user-agent'] || 'unknown'
        });
        await user.save();
        
        res.json({
            success: true,
            accessToken,
            refreshToken: newRefreshToken
        });
        
    } catch (error) {
        if (error.name === 'TokenExpiredError') {
        return res.status(401).json({
            success: false,
            message: 'Refresh token expired'
        });
    }

    if (error.name === 'JsonWebTokenError') {
        return res.status(401).json({
            success: false,
            message: 'Invalid refresh token'
        });
    }

    return res.status(500).json({
        success: false,
        message: 'Server error'
    });    
  }
};


exports.logout = async (req, res) => {
    try {
        const { refreshToken } = req.body;
        const userId = req.userId; // From auth middleware
        
        if (refreshToken) {
            await User.updateOne(
                { _id: userId },
                { $pull: { refreshTokens: { token: refreshToken } } }
            );
        }
        
        res.json({ success: true, message: 'Logged out successfully' });
    } catch (error) {
        res.status(500).json({ success: false, message: 'Server error' });
    }
};