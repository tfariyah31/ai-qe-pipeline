import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Container, Typography, Grid, Card, CardContent, CardMedia,
  CircularProgress, Alert, Button, Snackbar, Box, Chip
} from '@mui/material';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import AddBoxIcon from '@mui/icons-material/AddBox';
import Navbar from './Navbar';
import { getRole } from '../utils/auth';
import { addToCart } from '../utils/cart';

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cartSnack, setCartSnack] = useState('');
  const navigate = useNavigate();
  const role = getRole();

  useEffect(() => {
    const fetchProducts = async () => {
      const token = localStorage.getItem('accessToken');
      try {
        const res = await axios.get('http://127.0.0.1:5001/api/products', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const productsData = Array.isArray(res.data) ? res.data : res.data.products || [];
        setProducts(productsData);
      } catch (err) {
        setError('Failed to fetch products. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    fetchProducts();
  }, []);

  const handleAddToCart = (product) => {
    addToCart(product);
    setCartSnack(`"${product.name}" added to cart!`);
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', background: '#f8fafc' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ mt: 4 }}>

        {/* Header row */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700 }}>
              Products
            </Typography>
            <Typography variant="body2" color="text.secondary">{products.length} items available</Typography>
          </Box>
          {/* Super admin or Merchant can add products from here too */}
          {(role === 'super_admin' || role === 'merchant') && (
            <Button
              variant="contained"
              startIcon={<AddBoxIcon />}
              onClick={() => navigate('/add-product')}
              sx={{ background: role === 'super_admin' ? '#7c3aed' : '#0369a1', textTransform: 'none', fontWeight: 600 }}
            >
              Add Product
            </Button>
          )}
        </Box>

        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

        <Grid container spacing={3}>
          {products.map((product) => (
            <Grid item key={product._id} xs={12} sm={6} md={4}>
              <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
                <CardMedia
                  component="img"
                  height="160"
                  image={product.image}
                  alt={product.name}
                  sx={{ objectFit: 'cover' }}
                />
                <CardContent sx={{ flexGrow: 1 }}>
                  <Typography variant="h6" component="div" sx={{ fontWeight: 600, fontSize: '1rem' }}>
                    {product.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1 }}>
                    {product.description}
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Chip label={`⭐ ${product.rating}`} size="small" sx={{ background: '#fef3c7', color: '#b45309' }} />
                    {product.price && (
                      <Typography variant="body2" fontWeight={700} color="primary">
                        ${product.price}
                      </Typography>
                    )}
                  </Box>
                </CardContent>

                {/* Role-based action buttons */}
                <Box sx={{ px: 2, pb: 2 }}>
                  {/* Customer: Add to Cart */}
                  {(role === 'customer') && (
                    <Button
                      fullWidth
                      variant="contained"
                      startIcon={<AddShoppingCartIcon />}
                      onClick={() => handleAddToCart(product)}
                      sx={{ background: '#047857', textTransform: 'none', fontWeight: 600, '&:hover': { background: '#065f46' } }}
                    >
                      Add to Cart
                    </Button>
                  )}

                  {/* Merchant: Edit own products */}
                  {role === 'merchant' && (
                    <Button
                      fullWidth
                      variant="outlined"
                      onClick={() => navigate(`/edit-product/${product._id}`)}
                      sx={{ borderColor: '#0369a1', color: '#0369a1', textTransform: 'none', fontWeight: 600 }}
                    >
                      Edit Product
                    </Button>
                  )}

                  {/* Super Admin: All actions */}
                  {role === 'super_admin' && (
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        fullWidth
                        variant="contained"
                        startIcon={<AddShoppingCartIcon />}
                        onClick={() => handleAddToCart(product)}
                        sx={{ background: '#047857', textTransform: 'none', fontSize: '0.75rem', '&:hover': { background: '#065f46' } }}
                      >
                        Add to Cart
                      </Button>
                      <Button
                        fullWidth
                        variant="outlined"
                        onClick={() => navigate(`/edit-product/${product._id}`)}
                        sx={{ borderColor: '#7c3aed', color: '#7c3aed', textTransform: 'none', fontSize: '0.75rem' }}
                      >
                        Edit
                      </Button>
                    </Box>
                  )}
                </Box>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Cart Snackbar */}
      <Snackbar
        open={!!cartSnack}
        autoHideDuration={2500}
        onClose={() => setCartSnack('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setCartSnack('')} severity="success" sx={{ width: '100%' }}>
          {cartSnack}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ProductList;