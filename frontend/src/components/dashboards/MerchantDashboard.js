import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../Navbar';
import {
  Box, Container, Typography, Grid, Card, CardContent,
  Button, Avatar, Divider, LinearProgress, Chip
} from '@mui/material';
import InventoryIcon from '@mui/icons-material/Inventory';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AddBoxIcon from '@mui/icons-material/AddBox';
import StorefrontIcon from '@mui/icons-material/Storefront';
import ReceiptIcon from '@mui/icons-material/Receipt';

const stats = [
  { label: 'My Products', value: '34', icon: <InventoryIcon />, color: '#0369a1', bg: '#e0f2fe' },
  { label: 'Orders Today', value: '12', icon: <ReceiptIcon />, color: '#047857', bg: '#d1fae5' },
  { label: 'Monthly Revenue', value: '$4,820', icon: <TrendingUpIcon />, color: '#b45309', bg: '#fef3c7' },
  { label: 'Store Views', value: '981', icon: <StorefrontIcon />, color: '#7c3aed', bg: '#ede9fe' },
];

const topProducts = [
  { name: 'Wireless Headphones', sales: 87, stock: 40 },
  { name: 'USB-C Hub 7-in-1', sales: 65, stock: 20 },
  { name: 'Mechanical Keyboard', sales: 54, stock: 8 },
  { name: 'Phone Stand Aluminum', sales: 42, stock: 55 },
];

const MerchantDashboard = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: '100vh', background: '#f0f9ff' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#0369a1', width: 52, height: 52 }}>
            <StorefrontIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              Merchant Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary">Manage your store and products</Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddBoxIcon />}
            onClick={() => navigate('/add-product')}
            sx={{ ml: 'auto', background: '#0369a1', textTransform: 'none', fontWeight: 600, '&:hover': { background: '#0284c7' } }}
          >
            Add Product
          </Button>
        </Box>

        {/* Stats */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {stats.map((s) => (
            <Grid item xs={12} sm={6} md={3} key={s.label}>
              <Card elevation={0} sx={{ border: '1px solid #bae6fd', borderRadius: 3 }}>
                <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Avatar sx={{ background: s.bg, color: s.color, width: 48, height: 48 }}>
                    {s.icon}
                  </Avatar>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>{s.value}</Typography>
                    <Typography variant="caption" color="text.secondary">{s.label}</Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Grid container spacing={3}>
          {/* Top Products */}
          <Grid item xs={12} md={7}>
            <Card elevation={0} sx={{ border: '1px solid #bae6fd', borderRadius: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, fontFamily: "'Syne', sans-serif" }}>
                    Top Products
                  </Typography>
                  <Button size="small" onClick={() => navigate('/products')} sx={{ textTransform: 'none', color: '#0369a1' }}>
                    View All
                  </Button>
                </Box>
                <Divider sx={{ mb: 2 }} />
                {topProducts.map((p) => (
                  <Box key={p.name} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="body2" fontWeight={600}>{p.name}</Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Chip label={`${p.sales} sold`} size="small" sx={{ background: '#d1fae5', color: '#047857', fontSize: '0.65rem' }} />
                        <Chip label={`${p.stock} left`} size="small" sx={{ background: p.stock < 15 ? '#fee2e2' : '#f1f5f9', color: p.stock < 15 ? '#dc2626' : '#475569', fontSize: '0.65rem' }} />
                      </Box>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={(p.sales / 100) * 100}
                      sx={{ height: 6, borderRadius: 3, background: '#e0f2fe', '& .MuiLinearProgress-bar': { background: '#0369a1' } }}
                    />
                  </Box>
                ))}
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} md={5}>
            <Card elevation={0} sx={{ border: '1px solid #bae6fd', borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                  Quick Actions
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {[
                  { label: '+ Add New Product', path: '/add-product', color: '#0369a1', variant: 'contained' },
                  { label: 'View My Products', path: '/products', color: '#0369a1', variant: 'outlined' },
                  { label: 'View Orders', path: '/orders', color: '#047857', variant: 'outlined' },
                ].map((action) => (
                  <Button
                    key={action.label}
                    fullWidth
                    variant={action.variant}
                    onClick={() => navigate(action.path)}
                    sx={{
                      mb: 1.5, textTransform: 'none', fontWeight: 600,
                      ...(action.variant === 'contained'
                        ? { background: action.color, '&:hover': { background: '#0284c7' } }
                        : { borderColor: '#bae6fd', color: action.color, '&:hover': { borderColor: action.color } })
                    }}
                  >
                    {action.label}
                  </Button>
                ))}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
};

export default MerchantDashboard;