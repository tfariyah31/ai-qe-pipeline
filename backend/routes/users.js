const express = require('express');
const router = express.Router();
const User = require('../models/User');
const authMiddleware = require('../middleware/auth');
const { requireRole } = authMiddleware;

function isInvalidObjectId(err) {
  return err.name === 'CastError' && err.path === '_id';
}

/**
 * @swagger
 * tags:
 *   name: Users
 *   description: User management APIs (Super Admin only)
 */

/**
 * @swagger
 * /api/users:
 *   get:
 *     summary: Get all users
 *     description: Retrieve a list of all users. Only accessible by Super Admin.
 *     tags: [Users]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: List of users retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 users:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/User'
 *       403:
 *         description: Forbidden (requires superadmin role)
 *       500:
 *         description: Server error
 */
router.get('/', authMiddleware, requireRole('superadmin'), async (req, res) => {
  try {
    const users = await User.find().select('-password -tokens -refreshTokens');
    res.json({ success: true, users });
  } catch (err) {
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * @swagger
 * /api/users/{id}:
 *   get:
 *     summary: Get single user
 *     description: Retrieve details of a specific user by ID. Super Admin only.
 *     tags: [Users]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         description: User ID
 *         schema:
 *           type: string
 *           example: 65e9c2b3a1b2c3d4e5f67890
 *     responses:
 *       200:
 *         description: User retrieved successfully
 *       400:
 *         description: Invalid user ID format
 *       404:
 *         description: User not found
 *       403:
 *         description: Forbidden (requires superadmin role)
 *       500:
 *         description: Server error
 */
router.get('/:id', authMiddleware, requireRole('superadmin'), async (req, res) => {
  try {
    const user = await User.findById(req.params.id).select('-password -tokens -refreshTokens');
    if (!user) return res.status(404).json({ success: false, message: 'User not found' });
    res.json({ success: true, user });
  } catch (err) {
    if (isInvalidObjectId(err)) {
      return res.status(400).json({ success: false, message: 'Invalid user ID format' });
    }
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * @swagger
 * /api/users/{id}:
 *   put:
 *     summary: Update a user
 *     description: Update user details (name, email, role, block/unblock). Super Admin only.
 *     tags: [Users]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - name: id
 *         in: path
 *         required: true
 *         description: User ID
 *         schema:
 *           type: string
 *           example: 65e9c2b3a1b2c3d4e5f67890
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               name:
 *                 type: string
 *                 example: John Doe
 *               email:
 *                 type: string
 *                 example: john@example.com
 *               role:
 *                 type: string
 *                 enum: [customer, merchant, superadmin]
 *                 example: merchant
 *               isBlocked:
 *                 type: boolean
 *                 example: false
 *     responses:
 *       200:
 *         description: User updated successfully
 *       400:
 *         description: Validation error or invalid ID
 *       403:
 *         description: Forbidden (requires superadmin role)
 *       404:
 *         description: User not found
 *       409:
 *         description: Email already exists
 *       500:
 *         description: Server error
 */
router.put('/:id', authMiddleware, requireRole('superadmin'), async (req, res) => {
  try {
    const { name, email, role, isBlocked } = req.body;

    // Only allow updating these fields
    const updates = {};
    if (name !== undefined) updates.name = name;
    if (email !== undefined) updates.email = email;
    if (role !== undefined) updates.role = role;
    if (isBlocked !== undefined) {
      updates.isBlocked = isBlocked;
      // If unblocking, also reset failed attempts and lock
      if (!isBlocked) {
        updates.failedLoginAttempts = 0;
        updates.lockUntil = null;
      }
    }

    const user = await User.findByIdAndUpdate(
      req.params.id,
      updates,
      { new: true, runValidators: true }
    ).select('-password -tokens -refreshTokens');

    if (!user) return res.status(404).json({ success: false, message: 'User not found' });

    res.json({ success: true, user });
  } catch (err) {
    if (isInvalidObjectId(err)) {
      return res.status(400).json({ success: false, message: 'Invalid user ID format' });
    }
    if (err.name === 'ValidationError') {
      const messages = Object.values(err.errors).map((e) => e.message);
      return res.status(400).json({ success: false, message: messages.join(', ') });
    }
    if (err.code === 11000) {
      return res.status(409).json({ success: false, message: 'Email already in use by another account' });
    }
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

module.exports = router;