const mongoose = require('mongoose');

const failedLoginSchema = new mongoose.Schema({
  email: { type: String, required: true, index: true },
  attempts: { type: Number, default: 1 },
  firstAttempt: { type: Date, default: Date.now },
  lastAttempt: { type: Date, default: Date.now }
});

// Auto-expire documents after 5 minutes
failedLoginSchema.index({ lastAttempt: 1 }, { expireAfterSeconds: 300 });

module.exports = mongoose.model('FailedLogin', failedLoginSchema);