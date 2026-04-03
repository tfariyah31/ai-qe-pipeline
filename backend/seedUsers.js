const mongoose = require('mongoose');
const User = require('./models/User');
const dotenv = require('dotenv');
const bcrypt = require('bcryptjs');

//dotenv.config();
dotenv.config({ path: require('path').resolve(__dirname, '.env') });

const seed = async () => {
  try {
    await mongoose.connect(process.env.MONGO_URI);
    console.log('✅ Connected to MongoDB');

    // OPTION 1: Delete ALL users (clean slate)
    const deleteAllResult = await User.deleteMany({});
    console.log(`🗑️ Deleted ${deleteAllResult.deletedCount} existing users`);


    // Create all users
    const users = [
      {
        name: 'Super Admin',
        email: 'superadmin@test.com',
        password: 'Str0ng!Pass#2024',
        role: 'superadmin'
      },
      {
        name: 'Merchant User',
        email: 'merchant@test.com',
        password: 'MerchantPass123!',
        role: 'merchant'
      },
      {
        name: 'Customer User',
        email: 'customer@test.com',
        password: 'CustomerPass123!',
        role: 'customer'
      },
      {
        name: 'Validation User',
        email: 'validation@test.com',
        password: 'ValidationPass123!',
        role: 'customer'
      },
      {
        name: 'Blocked Customer',
        email: 'blocked@test.com',
        password: 'BlockedPass123!',
        role: 'customer',
        isBlocked: true
      }
    ];

    for (const userData of users) {
      const user = new User(userData);
      await user.save(); // This triggers the pre-save hashing
      console.log(` User created: ${userData.email}`);
    }

    // Verify users were created
    const dbUsers = await User.find({}).lean();
    console.log('\n All Users in Database:');
    
    for (const dbUser of dbUsers) {
      console.log('\n-------------------');
      console.log('Email:', dbUser.email);
      console.log('Name:', dbUser.name);
      console.log('Role:', dbUser.role);
      console.log('isBlocked:', dbUser.isBlocked);
      console.log('Password (hashed):', dbUser.password.substring(0, 20) + '...');
      
      // Test password verification for each user
      let testPassword;
      if (dbUser.email === 'superadmin@test.com') testPassword = 'Str0ng!Pass#2024';
      else if (dbUser.email === 'merchant@test.com') testPassword = 'MerchantPass123!';
      else if (dbUser.email === 'customer@test.com') testPassword = 'CustomerPass123!';
      else if (dbUser.email === 'validation@test.com') testPassword = 'ValidationPass123!';
      else if (dbUser.email === 'blocked@test.com') testPassword = 'BlockedPass123!';
      
      const isMatch = await bcrypt.compare(testPassword, dbUser.password);
      console.log('Password verification:', isMatch ? '✅ PASS' : '❌ FAIL');
    }

    await mongoose.disconnect();
    console.log('\n Database connection closed');
    
  } catch (error) {
    console.error(' Seeding failed:', error);
    process.exit(1);
  }
};

seed();