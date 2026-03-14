// frontend/src/components/CheckoutPayment.jsx
// Requires: npm install @stripe/react-stripe-js @stripe/stripe-js
//
// Usage in your Cart / Order Summary page:
//   import CheckoutPayment from './CheckoutPayment';
//   <CheckoutPayment cartTotal={subtotal + tax} onSuccess={handleOrderPlaced} />

import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Paper,
  Divider,
  Chip,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import CreditCardIcon from '@mui/icons-material/CreditCard';

// ── Stripe publishable key ────────────────────────────────────────────────────
// Add REACT_APP_STRIPE_PUBLISHABLE_KEY to your frontend .env
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY);

// ── Card Element styling to match MUI theme ───────────────────────────────────
const CARD_ELEMENT_OPTIONS = {
  style: {
    base: {
      fontSize: '16px',
      color: '#1a1a2e',
      fontFamily: '"Roboto", sans-serif',
      '::placeholder': { color: '#9e9e9e' },
      iconColor: '#1976d2',
    },
    invalid: { color: '#d32f2f', iconColor: '#d32f2f' },
  },
};

// ── Inner form (must be inside <Elements>) ────────────────────────────────────
function PaymentForm({ cartTotal, onSuccess, onError }) {
  const stripe = useStripe();
  const elements = useElements();

  const [loading, setLoading] = useState(false);
  const [clientSecret, setClientSecret] = useState('');
  const [message, setMessage] = useState('');
  const [severity, setSeverity] = useState('info');

  // Step 1 — fetch a PaymentIntent from your backend when the component mounts
  useEffect(() => {
    const createIntent = async () => {
      try {
        const token = localStorage.getItem('accessToken'); // adjust to your auth storage key
        const res = await fetch('/api/payments/create-intent', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ amount: cartTotal }),
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.message || 'Failed to initialise payment');

        setClientSecret(data.clientSecret);
      } catch (err) {
        setSeverity('error');
        setMessage(err.message);
        if (onError) onError(err.message);
      }
    };

    if (cartTotal > 0) createIntent();
  }, [cartTotal]);

  // Step 2 — confirm payment on form submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements || !clientSecret) return;

    setLoading(true);
    setMessage('');

    const cardElement = elements.getElement(CardElement);

    const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
      payment_method: { card: cardElement },
    });

    setLoading(false);

    if (error) {
      setSeverity('error');
      setMessage(error.message);
      if (onError) onError(error.message);
    } else if (paymentIntent.status === 'succeeded') {
      setSeverity('success');
      setMessage('Payment successful! 🎉');
      if (onSuccess) onSuccess(paymentIntent);
    } else {
      setSeverity('warning');
      setMessage(`Payment status: ${paymentIntent.status}. Please wait…`);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} data-testid="payment-form">
      {/* Test card hint — remove in production */}
      <Alert severity="info" sx={{ mb: 2 }} data-testid="test-card-hint">
        <strong>Test mode:</strong> Use card <code>4242 4242 4242 4242</code>, any future
        expiry, any CVC.
      </Alert>

      {/* Card input */}
      <Paper
        variant="outlined"
        sx={{ p: 2, mb: 2, borderRadius: 2 }}
        data-testid="card-element-wrapper"
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <CreditCardIcon color="primary" fontSize="small" />
          <Typography variant="caption" color="text.secondary">
            Card details
          </Typography>
        </Box>
        <CardElement options={CARD_ELEMENT_OPTIONS} />
      </Paper>

      {/* Order summary */}
      <Divider sx={{ my: 2 }} />
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="body1" fontWeight={600}>
          Total charged
        </Typography>
        <Chip
          label={`$${Number(cartTotal).toFixed(2)}`}
          color="primary"
          data-testid="charge-amount"
        />
      </Box>

      {/* Status message */}
      {message && (
        <Alert severity={severity} sx={{ mb: 2 }} data-testid="payment-message">
          {message}
        </Alert>
      )}

      {/* Submit */}
      <Button
        type="submit"
        variant="contained"
        fullWidth
        size="large"
        disabled={!stripe || !clientSecret || loading}
        startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <LockIcon />}
        data-testid="pay-button"
        sx={{ borderRadius: 2, py: 1.5 }}
      >
        {loading ? 'Processing…' : `Pay $${Number(cartTotal).toFixed(2)}`}
      </Button>
    </Box>
  );
}

// ── Public wrapper — wraps form in Stripe Elements provider ──────────────────
export default function CheckoutPayment({ cartTotal = 0, onSuccess, onError }) {
  return (
    <Paper elevation={3} sx={{ p: 3, maxWidth: 480, mx: 'auto', borderRadius: 3 }}>
      <Typography variant="h6" fontWeight={700} gutterBottom>
        Secure Checkout
      </Typography>
      <Elements stripe={stripePromise}>
        <PaymentForm cartTotal={cartTotal} onSuccess={onSuccess} onError={onError} />
      </Elements>
    </Paper>
  );
}