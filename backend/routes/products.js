const express = require('express');
const router = express.Router();
const Product = require('../models/Product');
const { getProducts } = require('../controllers/products');
const authMiddleware = require('../middleware/auth');
const { requireRole } = authMiddleware; 

function isInvalidObjectId(err) {
  return err.name === 'CastError' && err.path === '_id';
}
/**
 * @swagger
 * tags:
 *   name: Products
 *   description: Product management APIs
 */

/**
 * @swagger
 * /api/products:
 *   get:
 *     summary: Get all products
 *     description: Returns a list of all available products.
 *     tags: [Products]
 *     security:
 *       - bearerAuth: []
 *     responses:
 *       200:
 *         description: Product list retrieved successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 products:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/Product'
 *       500:
 *         description: Server error
 */


router.get('/', authMiddleware, async (req, res) => {
    try {
        const products = await Product.find();
        res.json({ success: true, products });
    } catch (error) {
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

/**
 * @swagger
 * /api/products/{id}:
 *   get:
 *     summary: Get a single product
 *     description: Retrieve a product by its ID.
 *     tags: [Products]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         description: Product ID
 *         schema:
 *           type: string
 *           example: 65e9b9a9c12b3c45ab12de34
 *     responses:
 *       200:
 *         description: Product retrieved successfully
 *       400:
 *         description: Invalid product ID format
 *       404:
 *         description: Product not found
 *       500:
 *         description: Server error
 */

router.get('/:id', authMiddleware, async (req, res) => {
  try {
    const product = await Product.findById(req.params.id);
    if (!product) {
      return res.status(404).json({ success: false, message: 'Product not found' });
    }
    res.json({ success: true, product });
  } catch (err) {               // ← must be `err`, not `error`
    if (isInvalidObjectId(err)) { // ← must match the catch parameter
      return res.status(400).json({ success: false, message: 'Invalid product ID format' });
    }
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * @swagger
 * /api/products:
 *   post:
 *     summary: Create a new product
 *     description: Create a product. Only merchants or superadmins are allowed.
 *     tags: [Products]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *               - price
 *             properties:
 *               name:
 *                 type: string
 *                 example: Wireless Mouse
 *               description:
 *                 type: string
 *                 example: Ergonomic wireless mouse
 *               image:
 *                 type: string
 *                 example: https://example.com/product.jpg
 *               price:
 *                 type: number
 *                 example: 19.99
 *               rating:
 *                 type: number
 *                 example: 4.5
 *     responses:
 *       201:
 *         description: Product created successfully
 *       400:
 *         description: Validation error
 *       403:
 *         description: Forbidden (role restriction)
 *       500:
 *         description: Server error
 */

router.post('/', authMiddleware, requireRole('merchant', 'superadmin'), async (req, res) => {
  try {
    const product = new Product(req.body);
    await product.save();
    res.status(201).json({ success: true, product });
  } catch (err) {                          
    if (err.name === 'ValidationError') {
      const messages = Object.values(err.errors).map((e) => e.message);
      return res.status(400).json({ success: false, message: messages.join(', ') });
    }
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * @swagger
 * /api/products/{id}:
 *   put:
 *     summary: Update a product
 *     description: Update product details. Only merchants or superadmins are allowed.
 *     tags: [Products]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - name: id
 *         in: path
 *         required: true
 *         description: Product ID
 *         schema:
 *           type: string
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/Product'
 *     responses:
 *       200:
 *         description: Product updated successfully
 *       400:
 *         description: Invalid product ID
 *       404:
 *         description: Product not found
 *       403:
 *         description: Forbidden
 *       500:
 *         description: Server error
 */
router.put('/:id', authMiddleware, requireRole('merchant','superadmin'), async (req, res) => {
    try {
        const product = await Product.findByIdAndUpdate(
            req.params.id, 
            req.body, 
            { new: true }
        );
        if (!product) {
            return res.status(404).json({ success: false, message: 'Product not found' });
        }
        res.json({ success: true, product });
    } catch (error) {
        if (isInvalidObjectId(error)) {
            return res.status(400).json({ success: false, message: 'Invalid user ID format' });
        }
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

/**
 * @swagger
 * /api/products/{id}:
 *   delete:
 *     summary: Delete a product
 *     description: Delete a product. Only merchants or superadmins are allowed.
 *     tags: [Products]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - name: id
 *         in: path
 *         required: true
 *         description: Product ID
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Product deleted
 *       400:
 *         description: Invalid product ID
 *       404:
 *         description: Product not found
 *       403:
 *         description: Forbidden
 *       500:
 *         description: Server error
 */

router.delete('/:id', authMiddleware, requireRole('merchant','superadmin'), async (req, res) => {
    try {
        const product = await Product.findByIdAndDelete(req.params.id);
        if (!product) {
            return res.status(404).json({ success: false, message: 'Product not found' });
        }
        res.json({ success: true, message: 'Product deleted' });
    } catch (error) {
        if (isInvalidObjectId(error)) {
      return res.status(400).json({ success: false, message: 'Invalid user ID format' });
    }
        res.status(500).json({ success: false, message: 'Server error' });
    }
});

router.all('/', (req, res) => {
  res.status(405).json({
    success: false,
    message: `Method ${req.method} not allowed`,
    allowedMethods: ['GET', 'POST']
  });
});



module.exports = router;