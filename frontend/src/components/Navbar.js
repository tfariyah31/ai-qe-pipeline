import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { getRole, logout } from '../utils/auth';
import { getCartCount } from '../utils/cart';
import {
  AppBar, Toolbar, Typography, Button, Box, Chip, Badge, IconButton
} from '@mui/material';
import StorefrontIcon from '@mui/icons-material/Storefront';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';

const roleColors = {
  superadmin: '#7c3aed',
  merchant: '#0369a1',
  customer: '#047857',
};

const roleLabels = {
  superadmin: 'Super Admin',
  merchant: 'Merchant',
  customer: 'Customer',
};

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const role = getRole();
  const [cartCount, setCartCount] = useState(0);

  // Refresh cart count on every route change
  useEffect(() => {
    if (role === 'customer') {
      setCartCount(getCartCount());
    }
  }, [location, role]);

  // Poll every second to catch same-tab cart updates
  useEffect(() => {
    const interval = setInterval(() => {
      if (role === 'customer') {
        setCartCount(getCartCount());
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [role]);

  return (
    <AppBar position="sticky" sx={{ background: '#0f172a', boxShadow: '0 1px 0 rgba(255,255,255,0.08)' }}>
      <Toolbar sx={{ gap: 1 }}>
        <StorefrontIcon sx={{ color: '#f59e0b', mr: 1 }} />
        <Typography
          variant="h6"
          sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#fff', flexGrow: 0, mr: 3 }}
        >
          TestMart
        </Typography>

        {/* Nav Links */}
        <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
          <Button component={Link} to="/dashboard" sx={{ color: '#94a3b8', textTransform: 'none', '&:hover': { color: '#fff' } }}>
            Dashboard
          </Button>
          <Button component={Link} to="/products" sx={{ color: '#94a3b8', textTransform: 'none', '&:hover': { color: '#fff' } }}>
            Products
          </Button>
          {(role === 'superadmin' || role === 'merchant') && (
            <Button component={Link} to="/add-product" sx={{ color: '#f59e0b', textTransform: 'none', fontWeight: 600, '&:hover': { color: '#fbbf24' } }}>
              + Add Product
            </Button>
          )}
          {role === 'superadmin' && (
            <Button component={Link} to="/admin" sx={{ color: '#a78bfa', textTransform: 'none', '&:hover': { color: '#c4b5fd' } }}>
              Admin Panel
            </Button>
          )}
        </Box>

        {/* Cart Icon — customers and superadmin only */}
        {(role === 'customer') && (
          <IconButton
            onClick={() => navigate('/cart')}
            sx={{ color: '#fff', mr: 1, '&:hover': { background: 'rgba(255,255,255,0.08)' } }}
          >
            <Badge
              badgeContent={cartCount}
              sx={{
                '& .MuiBadge-badge': {
                  background: '#f59e0b',
                  color: '#0f172a',
                  fontWeight: 700,
                  fontSize: '0.65rem',
                }
              }}
            >
              <ShoppingCartIcon />
            </Badge>
          </IconButton>
        )}

        {/* Role Badge */}
        {role && (
          <Chip
            label={roleLabels[role] || role}
            size="small"
            sx={{
              background: roleColors[role] || '#475569',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.7rem',
              mr: 2,
            }}
          />
        )}

        <Button
          variant="outlined"
          size="small"
          onClick={() => logout(navigate)}
          sx={{ color: '#f87171', borderColor: '#f87171', textTransform: 'none', '&:hover': { background: '#f871711a' } }}
        >
          Logout
        </Button>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;