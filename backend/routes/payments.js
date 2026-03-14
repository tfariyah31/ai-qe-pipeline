const express = require('express');
const router = express.Router();
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const protect = require('../middleware/auth'); 

/**
 * @swagger
 * tags:
 *   name: Payments
 *   description: Stripe payment processing APIs
 */

/**
 * @swagger
 * /api/payments/create-intent:
 *   post:
 *     summary: Create a Stripe PaymentIntent
 *     description: Creates a Stripe PaymentIntent for the cart total and returns a client secret for frontend payment confirmation.
 *     tags: [Payments]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - amount
 *             properties:
 *               amount:
 *                 type: number
 *                 example: 29.99
 *                 description: Cart total in dollars (converted to cents internally)
 *               currency:
 *                 type: string
 *                 example: usd
 *                 description: Currency code (defaults to usd)
 *     responses:
 *       200:
 *         description: PaymentIntent successfully created
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 clientSecret:
 *                   type: string
 *                   example: pi_3Pxxxx_secret_xxxx
 *                 paymentIntentId:
 *                   type: string
 *                   example: pi_3Pxxxx
 *       400:
 *         description: Invalid request input
 *       402:
 *         description: Stripe payment error
 *       500:
 *         description: Server error creating payment intent
 */
router.post('/create-intent', protect, async (req, res) => {
  try {
    const { amount, currency = 'usd' } = req.body;

    // ── Validation ────────────────────────────────────────────────────────────
    if (amount === undefined || amount === null) {
      return res.status(400).json({ message: 'amount is required' });
    }

    if (Array.isArray(amount) || typeof amount === 'object') {
      return res.status(400).json({ message: 'amount must be a number' });
    }

    if (typeof amount !== 'number' || !isFinite(amount)) {
      return res.status(400).json({ message: 'amount must be a valid number' });
    }

    const parsedAmount = parseFloat(amount);

    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      return res.status(400).json({ message: 'amount must be a positive number' });
    }

    // Stripe minimum charge is $0.50 USD
    if (parsedAmount < 0.5) {
      return res.status(400).json({ message: 'amount must be at least $0.50' });
    }

    // Convert dollars → cents (Stripe works in smallest currency unit)
    const amountInCents = Math.round(parsedAmount * 100);

    // ── Create PaymentIntent ──────────────────────────────────────────────────
    const paymentIntent = await stripe.paymentIntents.create({
      amount: amountInCents,
      currency: currency.toLowerCase(),
      metadata: {
        userId: req.userId,
        userRole: req.userRole || 'unknown',
      },
      automatic_payment_methods: { enabled: true },
  });
    return res.status(200).json({
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id, // useful for logging / test assertions
    });
  } catch (error) {
    // Stripe errors have a 'type' field
    if (error.type && error.type.startsWith('Stripe')) {
      return res.status(402).json({
        message: error.message,
        stripeCode: error.code,
      });
    }
    console.error('PaymentIntent creation error:', error);
    return res.status(500).json({ message: 'Server error creating payment intent' });
  }
});

/**
 * @swagger
 * /api/payments/confirm:
 *   post:
 *     summary: Confirm a Stripe PaymentIntent
 *     description: Confirms a PaymentIntent server-side after a payment method has been attached. Useful for testing payment confirmation flows.
 *     tags: [Payments]
 *     security:
 *       - bearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - paymentIntentId
 *               - paymentMethodId
 *             properties:
 *               paymentIntentId:
 *                 type: string
 *                 example: pi_3Pxxxx
 *               paymentMethodId:
 *                 type: string
 *                 example: pm_card_visa
 *     responses:
 *       200:
 *         description: PaymentIntent confirmed
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 status:
 *                   type: string
 *                   example: succeeded
 *                 paymentIntentId:
 *                   type: string
 *                   example: pi_3Pxxxx
 *       400:
 *         description: Missing required parameters
 *       402:
 *         description: Stripe payment error
 *       500:
 *         description: Server error confirming payment
 */

router.post('/confirm', protect, async (req, res) => {
  try {
    const { paymentIntentId, paymentMethodId } = req.body;

    if (!paymentIntentId || !paymentMethodId) {
      return res.status(400).json({ message: 'paymentIntentId and paymentMethodId are required' });
    }

    const paymentIntent = await stripe.paymentIntents.confirm(paymentIntentId, {
      payment_method: paymentMethodId,
    });

    return res.status(200).json({
      status: paymentIntent.status,
      paymentIntentId: paymentIntent.id,
    });
  } catch (error) {
    if (error.type && error.type.startsWith('Stripe')) {
      return res.status(402).json({ message: error.message, stripeCode: error.code });
    }
    return res.status(500).json({ message: 'Server error confirming payment' });
  }
});

module.exports = router;