import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import {
  Box, Container, Typography, Grid, Card, CardMedia, CardContent,
  Button, Divider, IconButton, Alert, Snackbar, Avatar
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import ShoppingBagIcon from '@mui/icons-material/ShoppingBag';
import { getCart, removeFromCart, updateQuantity, clearCart } from '../utils/cart';
import CheckoutPayment from './CheckoutPayment';


const Cart = () => {
  const [cartItems, setCartItems] = useState([]);
  const [orderPlaced, setOrderPlaced] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setCartItems(getCart());
  }, []);

  const refresh = () => setCartItems(getCart());

  const handleRemove = (id) => {
    removeFromCart(id);
    refresh();
  };

  const handleQuantity = (id, qty) => {
    if (qty < 1) {
      removeFromCart(id);
    } else {
      updateQuantity(id, qty);
    }
    refresh();
  };

  const handleCheckout = () => {
    clearCart();
    setOrderPlaced(true);
    refresh();
    setTimeout(() => navigate('/products'), 2500);
  };

  const subtotal = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  return (
    <Box sx={{ minHeight: '100vh', background: '#f0fdf4' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#047857', width: 48, height: 48 }}>
            <ShoppingCartIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              My Cart
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {cartItems.length === 0 ? 'Your cart is empty' : `${cartItems.reduce((s, i) => s + i.quantity, 0)} items`}
            </Typography>
          </Box>
          <Button
            variant="outlined"
            onClick={() => navigate('/products')}
            sx={{ ml: 'auto', borderColor: '#bbf7d0', color: '#047857', textTransform: 'none' }}
          >
            ← Continue Shopping
          </Button>
        </Box>

        {/* Empty state */}
        {cartItems.length === 0 && !orderPlaced && (
          <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3, textAlign: 'center', py: 8 }}>
            <ShoppingBagIcon sx={{ fontSize: 64, color: '#bbf7d0', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>Your cart is empty</Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/products')}
              sx={{ mt: 2, background: '#047857', textTransform: 'none', '&:hover': { background: '#065f46' } }}
            >
              Browse Products
            </Button>
          </Card>
        )}

        {cartItems.length > 0 && (
          <Grid container spacing={3}>

            {/* Cart Items */}
            <Grid item xs={12} md={8}>
              <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3 }}>
                {cartItems.map((item, index) => (
                  <Box key={item._id}>
                    <Box sx={{ display: 'flex', gap: 2, p: 2, alignItems: 'center' }}>
                      {/* Product Image */}
                      <CardMedia
                        component="img"
                        image={item.image || 'https://via.placeholder.com/80'}
                        alt={item.name}
                        sx={{ width: 80, height: 80, borderRadius: 2, objectFit: 'cover', flexShrink: 0 }}
                      />

                      {/* Product Info */}
                      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                        <Typography variant="body1" fontWeight={600} noWrap>{item.name}</Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>{item.description}</Typography>
                        <Typography variant="body2" fontWeight={700} color="#047857" sx={{ mt: 0.5 }}>
                          ${item.price.toFixed(2)} each
                        </Typography>
                      </Box>

                      {/* Quantity Controls */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                        <IconButton
                          size="small"
                          onClick={() => handleQuantity(item._id, item.quantity - 1)}
                          sx={{ border: '1px solid #bbf7d0', width: 28, height: 28 }}
                        >
                          <RemoveIcon fontSize="small" />
                        </IconButton>
                        <Typography variant="body1" fontWeight={700} sx={{ minWidth: 24, textAlign: 'center' }}>
                          {item.quantity}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => handleQuantity(item._id, item.quantity + 1)}
                          sx={{ border: '1px solid #bbf7d0', width: 28, height: 28 }}
                        >
                          <AddIcon fontSize="small" />
                        </IconButton>
                      </Box>

                      {/* Line total */}
                      <Typography variant="body1" fontWeight={700} sx={{ minWidth: 64, textAlign: 'right', flexShrink: 0 }}>
                        ${(item.price * item.quantity).toFixed(2)}
                      </Typography>

                      {/* Remove */}
                      <IconButton
                        size="small"
                        onClick={() => handleRemove(item._id)}
                        sx={{ color: '#f87171', flexShrink: 0 }}
                      >
                        <DeleteOutlineIcon />
                      </IconButton>
                    </Box>
                    {index < cartItems.length - 1 && <Divider />}
                  </Box>
                ))}
              </Card>
            </Grid>

            {/* Order Summary */}
            <Grid item xs={12} md={4}>
              <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3, position: 'sticky', top: 80 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                    Order Summary
                  </Typography>
                  <Divider sx={{ mb: 2 }} />

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Subtotal</Typography>
                    <Typography variant="body2" fontWeight={600}>${subtotal.toFixed(2)}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Tax (8%)</Typography>
                    <Typography variant="body2" fontWeight={600}>${tax.toFixed(2)}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Shipping</Typography>
                    <Typography variant="body2" fontWeight={600} color="#047857">Free</Typography>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
                    <Typography variant="body1" fontWeight={700}>Total</Typography>
                    <Typography variant="body1" fontWeight={700} color="#047857">${total.toFixed(2)}</Typography>
                  </Box>

                  <CheckoutPayment
                    cartTotal={total}
                    onSuccess={(paymentIntent) => {
                    handleCheckout();
                    }}
                    onError={(msg) => console.error('Payment failed:', msg)}
                  />
                  <Button
                    fullWidth
                    variant="text"
                    onClick={() => { clearCart(); refresh(); }}
                    sx={{ mt: 1, color: '#f87171', textTransform: 'none', fontSize: '0.8rem' }}
                  >
                    Clear Cart
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}
      </Container>

      {/* Order placed snackbar */}
      <Snackbar
        open={orderPlaced}
        autoHideDuration={3000}
        onClose={() => setOrderPlaced(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          🎉 Order placed successfully! Redirecting to products...
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Cart;