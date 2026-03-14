const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({

  name: { type: String, required: true },
  email: { type: String, unique: true, required: true, lowercase: true, trim: true, match: [/^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Please provide a valid email address'], },
  password: { type: String, required: true },

  // role-based access control: default to customer
  role: { 
    type: String, 
    enum: ['superadmin', 'merchant', 'customer'], 
    default: 'customer' 
  },

  isBlocked: { type: Boolean, default: false },

  failedLoginAttempts: { type: Number, default: 0 },
  lockUntil: { type: Date, default: null },

  tokens: [{
        token: String,
        createdAt: { type: Date, default: Date.now }
    }],

  refreshTokens: [{
        token: String,
        expiresAt: Date,
        device: String
    }]

});

// Virtual to check if account is currently locked
userSchema.virtual('isLocked').get(function () {
  return this.lockUntil && this.lockUntil > Date.now();
});

userSchema.pre('save', async function (next) {
  if (this.isModified('password')) {
    this.password = await bcrypt.hash(this.password, 8);
  }
  next();
});

module.exports = mongoose.model('User', userSchema);