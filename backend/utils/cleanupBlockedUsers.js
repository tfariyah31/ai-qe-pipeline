const User = require('../models/User');
const FailedLogin = require('../models/FailedLogin');

// Run this periodically (e.g., every minute)
const cleanupBlockedUsers = async () => {
  try {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    
    // Find expired failed login attempts
    const expiredAttempts = await FailedLogin.find({
      firstAttempt: { $lt: fiveMinutesAgo }
    });

    for (const attempt of expiredAttempts) {
      // Unblock users
      await User.updateOne(
        { email: attempt.email, isBlocked: true },
        { isBlocked: false }
      );
      
      // Delete expired records
      await FailedLogin.deleteOne({ _id: attempt._id });
    }
    
    console.log(`Cleaned up ${expiredAttempts.length} expired blocks`);
  } catch (error) {
    console.error('Cleanup error:', error);
  }
};

module.exports = cleanupBlockedUsers;