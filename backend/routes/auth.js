const express = require('express');
const router = express.Router();
const { register, login } = require('../controllers/auth');
const User = require('../models/User');
const authMiddleware = require('../middleware/auth'); 
const {authLimiter, blockInjectionAttempts} = require('../middleware/rateLimit');
const { validateRegister, validateLogin } = require('../middleware/validation');
const authController = require('../controllers/auth');

/**
 * @swagger
 * /api/auth/login:
 *   post:
 *     summary: Login user
 *     tags: [Auth]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               email:
 *                 type: string
 *               password:
 *                 type: string
 *     responses:
 *       200:
 *         description: Returns JWT token
 *       401:
 *         description: Invalid credentials
 *       429:
 *         description: Too many requests
 */
router.post('/login', blockInjectionAttempts,authLimiter, login);


/**
 * @swagger
 * /api/auth/register:
 *   post:
 *     summary: Register a new user
 *     tags: [Auth]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *               - email
 *               - password
 *             properties:
 *               name:
 *                 type: string
 *               email:
 *                 type: string
 *               password:
 *                 type: string
 *     responses:
 *       201:
 *         description: User registered successfully
 *       400:
 *         description: Email already exists or invalid input
 *       500:
 *         description: Server error
 */
router.post('/register', validateRegister, async (req, res) => {
    try {

        // Check for unknown fields
        const allowedFields = ['name', 'email', 'password'];
        const receivedFields = Object.keys(req.body);
        const unknownFields = receivedFields.filter(field => !allowedFields.includes(field));
        
        if (unknownFields.length > 0) {
            return res.status(400).json({ 
                success: false, 
                message: `Unknown field(s) detected: ${unknownFields.join(', ')}. Allowed fields: name, email, password` 
            });
        }
        
        const { name, email, password } = req.body;

       
        // Check if user already exists by email
        const existingUser = await User.findOne({ email });
        
        if (existingUser) {
            return res.status(400).json({ 
                success: false, 
                message: 'Email already exists' 
            });
        }

        // Create new user 
        const user = new User({
            name,
            email,
            password,
            role: 'customer', // new role-based default
            isBlocked: false // default value
        });

        await user.save();

        // Remove password from response
        const userResponse = user.toObject();
        delete userResponse.password;

        res.status(201).json({
            success: true,
            message: 'User registered successfully',
            id: user._id.toString(),
            email: user.email,
            emailVerified: false,
            name: user.name,
            role: user.role,
            isBlocked: user.isBlocked
        });

    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ 
            success: false, 
            message: 'Server error during registration',
        });
    }
});


/**
 * @swagger
 * /api/auth/logout:
 *   post:
 *     summary: Logout user
 *     tags: [Auth]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Successfully logged out
 *       401:
 *         description: Unauthorized
 */
router.post('/logout' , authMiddleware,authController.logout);


/**
 * @swagger
 * /api/auth/refresh:
 *   post:
 *     summary: Refresh access token
 *     tags: [Auth]
 *     responses:
 *       200:
 *         description: New access token returned
 *       403:
 *         description: Invalid refresh token
 */
router.post('/refresh', authController.refreshToken);

module.exports = router;