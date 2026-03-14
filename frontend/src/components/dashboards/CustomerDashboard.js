import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../Navbar';
import {
  Box, Container, Typography, Grid, Card, CardContent,
  Button, Avatar, Divider, List, ListItem, ListItemText, Chip
} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import FavoriteIcon from '@mui/icons-material/Favorite';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import PersonIcon from '@mui/icons-material/Person';
import StorefrontIcon from '@mui/icons-material/Storefront';

const stats = [
  { label: 'Items in Cart', value: '3', icon: <ShoppingCartIcon />, color: '#047857', bg: '#d1fae5' },
  { label: 'Wishlist', value: '7', icon: <FavoriteIcon />, color: '#be185d', bg: '#fce7f3' },
  { label: 'Active Orders', value: '2', icon: <LocalShippingIcon />, color: '#0369a1', bg: '#e0f2fe' },
  { label: 'Total Orders', value: '21', icon: <PersonIcon />, color: '#7c3aed', bg: '#ede9fe' },
];

const recentOrders = [
  { id: '#4821', product: 'Wireless Headphones', status: 'Delivered', date: 'Feb 24' },
  { id: '#4756', product: 'USB-C Hub 7-in-1', status: 'Shipped', date: 'Feb 28' },
  { id: '#4800', product: 'Phone Stand', status: 'Processing', date: 'Mar 1' },
];

const statusColor = {
  Delivered: { bg: '#d1fae5', color: '#047857' },
  Shipped: { bg: '#e0f2fe', color: '#0369a1' },
  Processing: { bg: '#fef3c7', color: '#b45309' },
};

const CustomerDashboard = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: '100vh', background: '#f0fdf4' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#047857', width: 52, height: 52 }}>
            <PersonIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              My Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary">Welcome back! Here's your shopping overview.</Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<StorefrontIcon />}
            onClick={() => navigate('/products')}
            sx={{ ml: 'auto', background: '#047857', textTransform: 'none', fontWeight: 600, '&:hover': { background: '#065f46' } }}
          >
            Shop Now
          </Button>
        </Box>

        {/* Stats */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {stats.map((s) => (
            <Grid item xs={12} sm={6} md={3} key={s.label}>
              <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3 }}>
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
          {/* Recent Orders */}
          <Grid item xs={12} md={7}>
            <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                  Recent Orders
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <List dense>
                  {recentOrders.map((order) => (
                    <ListItem key={order.id} sx={{ px: 0 }}>
                      <ListItemText
                        primary={<><strong>{order.id}</strong> — {order.product}</>}
                        secondary={order.date}
                      />
                      <Chip
                        label={order.status}
                        size="small"
                        sx={{ background: statusColor[order.status].bg, color: statusColor[order.status].color, fontWeight: 600, fontSize: '0.7rem' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} md={5}>
            <Card elevation={0} sx={{ border: '1px solid #bbf7d0', borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                  Quick Actions
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {[
                  { label: '🛒 View Cart', path: '/cart', color: '#047857', variant: 'contained' },
                  { label: '🛍️ Browse Products', path: '/products', color: '#047857', variant: 'outlined' },
                  { label: '❤️ My Wishlist', path: '/wishlist', color: '#be185d', variant: 'outlined' },
                  { label: '📦 Track Orders', path: '/orders', color: '#0369a1', variant: 'outlined' },
                ].map((action) => (
                  <Button
                    key={action.label}
                    fullWidth
                    variant={action.variant}
                    onClick={() => navigate(action.path)}
                    sx={{
                      mb: 1.5, textTransform: 'none', fontWeight: 600,
                      ...(action.variant === 'contained'
                        ? { background: action.color, '&:hover': { background: '#065f46' } }
                        : { borderColor: '#bbf7d0', color: action.color, '&:hover': { borderColor: action.color } })
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

export default CustomerDashboard;