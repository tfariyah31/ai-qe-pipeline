import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from './Navbar';
import {
  Box, Container, Typography, Card, CardContent, TextField,
  Button, Avatar, Alert, Snackbar, Grid, InputAdornment,
  LinearProgress, Divider
} from '@mui/material';
import InventoryIcon from '@mui/icons-material/Inventory';
import ImageIcon from '@mui/icons-material/Image';
import axios from 'axios';

const initialForm = {
  name: '',
  description: '',
  image: '',
  price: '',
  rating: '',
};

const AddProduct = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [apiError, setApiError] = useState('');

  const validate = () => {
    const newErrors = {};
    if (!form.name.trim()) newErrors.name = 'Product name is required';
    if (!form.description.trim()) newErrors.description = 'Description is required';
    if (!form.image.trim()) newErrors.image = 'Image URL is required';
    else if (!/^https?:\/\/.+/.test(form.image.trim())) newErrors.image = 'Must be a valid URL (http/https)';
    if (!form.price) newErrors.price = 'Price is required';
    else if (isNaN(form.price) || Number(form.price) < 0) newErrors.price = 'Enter a valid price';
    if (!form.rating) newErrors.rating = 'Rating is required';
    else if (isNaN(form.rating) || Number(form.rating) < 0 || Number(form.rating) > 5) newErrors.rating = 'Rating must be between 0 and 5';
    return newErrors;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear error on change
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async () => {
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);
    setApiError('');

    try {
      const token = localStorage.getItem('accessToken');
      await axios.post(
        'http://127.0.0.1:5001/api/products',
        {
          name: form.name.trim(),
          description: form.description.trim(),
          image: form.image.trim(),
          price: Number(form.price),
          rating: Number(form.rating),
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(true);
      setForm(initialForm);
      setTimeout(() => navigate('/products'), 2000);
    } catch (err) {
      setApiError(err.response?.data?.message || 'Failed to add product. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setForm(initialForm);
    setErrors({});
    setApiError('');
  };

  return (
    <Box sx={{ minHeight: '100vh', background: '#f8fafc' }}>
      <Navbar />
      {loading && <LinearProgress sx={{ '& .MuiLinearProgress-bar': { background: '#0369a1' } }} />}

      <Container maxWidth="md" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#0369a1', width: 52, height: 52 }}>
            <InventoryIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              Add New Product
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Fill in the details below to list a new product
            </Typography>
          </Box>
          <Button
            variant="outlined"
            onClick={() => navigate('/products')}
            sx={{ ml: 'auto', borderColor: '#e2e8f0', color: '#64748b', textTransform: 'none' }}
          >
            ← Back to Products
          </Button>
        </Box>

        <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3 }}>
          <CardContent sx={{ p: 4 }}>

            {apiError && (
              <Alert severity="error" sx={{ mb: 3 }}>{apiError}</Alert>
            )}

            <Grid container spacing={3}>

              {/* Product Name */}
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: '#0f172a' }}>
                  Product Name *
                </Typography>
                <TextField
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="e.g. Wireless Bluetooth Headphones"
                  fullWidth
                  error={!!errors.name}
                  helperText={errors.name}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
              </Grid>

              {/* Description */}
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: '#0f172a' }}>
                  Description *
                </Typography>
                <TextField
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Describe your product in detail..."
                  fullWidth
                  multiline
                  rows={4}
                  error={!!errors.description}
                  helperText={errors.description}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
              </Grid>

              {/* Image URL */}
              <Grid item xs={12}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: '#0f172a' }}>
                  Image URL *
                </Typography>
                <TextField
                  name="image"
                  value={form.image}
                  onChange={handleChange}
                  placeholder="https://example.com/product-image.jpg"
                  fullWidth
                  error={!!errors.image}
                  helperText={errors.image}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <ImageIcon sx={{ color: '#94a3b8' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
                {/* Image preview */}
                {form.image && /^https?:\/\/.+/.test(form.image) && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary">Preview:</Typography>
                    <Box
                      component="img"
                      src={form.image}
                      alt="preview"
                      onError={(e) => { e.target.style.display = 'none'; }}
                      sx={{ display: 'block', mt: 1, height: 140, width: 'auto', maxWidth: '100%', borderRadius: 2, border: '1px solid #e2e8f0', objectFit: 'cover' }}
                    />
                  </Box>
                )}
              </Grid>

              {/* Price and Rating side by side */}
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: '#0f172a' }}>
                  Price *
                </Typography>
                <TextField
                  name="price"
                  value={form.price}
                  onChange={handleChange}
                  placeholder="0.00"
                  fullWidth
                  type="number"
                  inputProps={{ min: 0, step: '0.01' }}
                  error={!!errors.price}
                  helperText={errors.price}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1, color: '#0f172a' }}>
                  Rating * <Typography component="span" variant="caption" color="text.secondary">(0 – 5)</Typography>
                </Typography>
                <TextField
                  name="rating"
                  value={form.rating}
                  onChange={handleChange}
                  placeholder="e.g. 4.5"
                  fullWidth
                  type="number"
                  inputProps={{ min: 0, max: 5, step: '0.1' }}
                  error={!!errors.rating}
                  helperText={errors.rating}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">⭐</InputAdornment>,
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 4 }} />

            {/* Actions */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={handleReset}
                disabled={loading}
                sx={{ borderColor: '#e2e8f0', color: '#64748b', textTransform: 'none', px: 3 }}
              >
                Reset
              </Button>
              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={loading}
                sx={{
                  background: '#0369a1', textTransform: 'none', fontWeight: 600, px: 4,
                  '&:hover': { background: '#0284c7' }
                }}
              >
                {loading ? 'Adding Product...' : 'Add Product'}
              </Button>
            </Box>

          </CardContent>
        </Card>
      </Container>

      {/* Success Snackbar */}
      <Snackbar
        open={success}
        autoHideDuration={3000}
        onClose={() => setSuccess(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          ✅ Product added successfully! Redirecting to products...
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AddProduct;