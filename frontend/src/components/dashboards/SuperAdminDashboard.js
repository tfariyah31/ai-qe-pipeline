import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../Navbar';
import {
  Box, Container, Typography, Grid, Card, CardContent,
  Button, Avatar, Divider, List, ListItem, ListItemText, Chip
} from '@mui/material';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import StorefrontIcon from '@mui/icons-material/Storefront';
import InventoryIcon from '@mui/icons-material/Inventory';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AddBoxIcon from '@mui/icons-material/AddBox';
import ShieldIcon from '@mui/icons-material/Shield';

const stats = [
  { label: 'Total Users', value: '1,284', icon: <PeopleAltIcon />, color: '#7c3aed', bg: '#ede9fe' },
  { label: 'Merchants', value: '48', icon: <StorefrontIcon />, color: '#0369a1', bg: '#e0f2fe' },
  { label: 'Products', value: '3,921', icon: <InventoryIcon />, color: '#047857', bg: '#d1fae5' },
  { label: 'Revenue', value: '$84,200', icon: <TrendingUpIcon />, color: '#b45309', bg: '#fef3c7' },
];

const recentActivity = [
  { text: 'Merchant "TechHub" added 12 new products', time: '2m ago', role: 'merchant' },
  { text: 'Customer "John D." placed order #4821', time: '15m ago', role: 'customer' },
  { text: 'New merchant application from "GadgetZone"', time: '1h ago', role: 'merchant' },
  { text: 'User "alice@mail.com" registered', time: '3h ago', role: 'customer' },
];

const roleColor = { merchant: '#0369a1', customer: '#047857' };

const SuperAdminDashboard = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ minHeight: '100vh', background: '#f8fafc' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#7c3aed', width: 52, height: 52 }}>
            <ShieldIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              Super Admin Dashboard
            </Typography>
            <Typography variant="body2" color="text.secondary">Full system access — manage everything</Typography>
          </Box>
          <Box sx={{ ml: 'auto', display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              startIcon={<AddBoxIcon />}
              onClick={() => navigate('/add-product')}
              sx={{ background: '#7c3aed', textTransform: 'none', '&:hover': { background: '#6d28d9' } }}
            >
              Add Product
            </Button>
            <Button
              variant="outlined"
              startIcon={<PeopleAltIcon />}
              onClick={() => navigate('/admin')}
              sx={{ borderColor: '#7c3aed', color: '#7c3aed', textTransform: 'none' }}
            >
              Manage Users
            </Button>
          </Box>
        </Box>

        {/* Stats */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {stats.map((s) => (
            <Grid item xs={12} sm={6} md={3} key={s.label}>
              <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3 }}>
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
          {/* Recent Activity */}
          <Grid item xs={12} md={7}>
            <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3, height: '100%' }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                  Recent Activity
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <List dense>
                  {recentActivity.map((item, i) => (
                    <ListItem key={i} sx={{ px: 0, alignItems: 'flex-start' }}>
                      <ListItemText
                        primary={item.text}
                        secondary={item.time}
                      />
                      <Chip
                        label={item.role}
                        size="small"
                        sx={{ ml: 1, mt: 0.5, background: roleColor[item.role], color: '#fff', fontSize: '0.65rem' }}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} md={5}>
            <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2, fontFamily: "'Syne', sans-serif" }}>
                  Quick Actions
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {[
                  { label: 'View All Products', path: '/products', color: '#0f172a' },
                  { label: 'Add New Product', path: '/add-product', color: '#7c3aed' },
                  { label: 'Manage Users', path: '/admin', color: '#0369a1' },
                  { label: 'View Orders', path: '/orders', color: '#047857' },
                ].map((action) => (
                  <Button
                    key={action.label}
                    fullWidth
                    variant="outlined"
                    onClick={() => navigate(action.path)}
                    sx={{
                      mb: 1.5, justifyContent: 'flex-start', textTransform: 'none',
                      borderColor: '#e2e8f0', color: action.color, fontWeight: 600,
                      '&:hover': { borderColor: action.color, background: `${action.color}08` }
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

export default SuperAdminDashboard;