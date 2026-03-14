import React, { useEffect, useState } from 'react';
import Navbar from './Navbar';
import axios from 'axios';
import {
  Box, Container, Typography, Avatar, Card, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  TextField, MenuItem, Alert, Snackbar, CircularProgress,
  InputAdornment, Tooltip
} from '@mui/material';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const roleColors = {
  superadmin: { bg: '#ede9fe', color: '#7c3aed' },
  merchant:   { bg: '#e0f2fe', color: '#0369a1' },
  customer:   { bg: '#d1fae5', color: '#047857' },
};

const ManageUsers = () => {
  const [users, setUsers] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [apiError, setApiError] = useState('');
  const [success, setSuccess] = useState('');

  // Edit dialog state
  const [editOpen, setEditOpen] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', email: '', role: '', isBlocked: false });
  const [editErrors, setEditErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const token = localStorage.getItem('accessToken');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await axios.get('http://127.0.0.1:5001/api/users', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = Array.isArray(res.data) ? res.data : res.data.users || [];
      setUsers(data);
      setFiltered(data);
    } catch (err) {
      setApiError(err.response?.data?.message || 'Failed to fetch users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  // Search filter
  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(users.filter(u =>
      u.name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.role?.toLowerCase().includes(q)
    ));
  }, [search, users]);

  const openEdit = (user) => {
    setEditUser(user);
    setEditForm({ name: user.name, email: user.email, role: user.role, isBlocked: user.isBlocked });
    setEditErrors({});
    setEditOpen(true);
  };

  const closeEdit = () => {
    setEditOpen(false);
    setEditUser(null);
  };

  const validate = () => {
    const errs = {};
    if (!editForm.name.trim()) errs.name = 'Name is required';
    if (!editForm.email.trim()) errs.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(editForm.email)) errs.email = 'Invalid email address';
    return errs;
  };

  const handleSave = async () => {
    const errs = validate();
    if (Object.keys(errs).length > 0) { setEditErrors(errs); return; }
    setSaving(true);
    try {
      await axios.put(
        `http://127.0.0.1:5001/api/users/${editUser._id || editUser.id}`,
        { name: editForm.name.trim(), email: editForm.email.trim(), role: editForm.role, isBlocked: editForm.isBlocked },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(`"${editForm.name}" updated successfully!`);
      closeEdit();
      fetchUsers();
    } catch (err) {
      setEditErrors({ api: err.response?.data?.message || 'Failed to update user.' });
    } finally {
      setSaving(false);
    }
  };

  // Quick toggle block/unblock
  const handleToggleBlock = async (user) => {
    try {
      await axios.put(
        `http://127.0.0.1:5001/api/users/${user._id || user.id}`,
        { isBlocked: !user.isBlocked },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(`User "${user.name}" ${!user.isBlocked ? 'blocked' : 'unblocked'} successfully!`);
      fetchUsers();
    } catch (err) {
      setApiError(err.response?.data?.message || 'Failed to update user.');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', background: '#f8fafc' }}>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>

        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 4 }}>
          <Avatar sx={{ background: '#7c3aed', width: 52, height: 52 }}>
            <PeopleAltIcon />
          </Avatar>
          <Box>
            <Typography variant="h5" sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, color: '#0f172a' }}>
              Manage Users
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {users.length} total users
            </Typography>
          </Box>
          {/* Search */}
          <TextField
            size="small"
            placeholder="Search by name, email or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ ml: 'auto', width: 280, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            InputProps={{
              startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#94a3b8' }} /></InputAdornment>
            }}
          />
        </Box>

        {apiError && <Alert severity="error" sx={{ mb: 3 }}>{apiError}</Alert>}

        {/* Table */}
        <Card elevation={0} sx={{ border: '1px solid #e2e8f0', borderRadius: 3 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress sx={{ color: '#7c3aed' }} />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ background: '#f8fafc' }}>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>User</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>Email</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>Role</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>Failed Logins</TableCell>
                    <TableCell sx={{ fontWeight: 700, color: '#0f172a' }} align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filtered.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 6, color: '#94a3b8' }}>
                        No users found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((user) => (
                      <TableRow key={user._id || user.id} hover sx={{ '&:last-child td': { border: 0 } }}>
                        {/* Avatar + Name */}
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <Avatar sx={{ width: 36, height: 36, background: roleColors[user.role]?.color || '#475569', fontSize: '0.85rem' }}>
                              {user.name?.charAt(0).toUpperCase()}
                            </Avatar>
                            <Typography variant="body2" fontWeight={600}>{user.name}</Typography>
                          </Box>
                        </TableCell>

                        {/* Email */}
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">{user.email}</Typography>
                        </TableCell>

                        {/* Role */}
                        <TableCell>
                          <Chip
                            label={user.role}
                            size="small"
                            sx={{
                              background: roleColors[user.role]?.bg || '#f1f5f9',
                              color: roleColors[user.role]?.color || '#475569',
                              fontWeight: 600, fontSize: '0.7rem'
                            }}
                          />
                        </TableCell>

                        {/* Status */}
                        <TableCell>
                          <Chip
                            label={user.isBlocked ? 'Blocked' : user.lockUntil && new Date(user.lockUntil) > new Date() ? 'Locked' : 'Active'}
                            size="small"
                            sx={{
                              background: user.isBlocked ? '#fee2e2' : user.lockUntil && new Date(user.lockUntil) > new Date() ? '#fef3c7' : '#d1fae5',
                              color: user.isBlocked ? '#dc2626' : user.lockUntil && new Date(user.lockUntil) > new Date() ? '#b45309' : '#047857',
                              fontWeight: 600, fontSize: '0.7rem'
                            }}
                          />
                        </TableCell>

                        {/* Failed Logins */}
                        <TableCell>
                          <Typography variant="body2" color={user.failedLoginAttempts > 0 ? '#dc2626' : 'text.secondary'} fontWeight={user.failedLoginAttempts > 0 ? 700 : 400}>
                            {user.failedLoginAttempts}
                          </Typography>
                        </TableCell>

                        {/* Actions */}
                        <TableCell align="right">
                          <Tooltip title="Edit user">
                            <IconButton size="small" onClick={() => openEdit(user)} sx={{ color: '#7c3aed', mr: 0.5 }}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={user.isBlocked ? 'Unblock user' : 'Block user'}>
                            <IconButton size="small" onClick={() => handleToggleBlock(user)}
                              sx={{ color: user.isBlocked ? '#047857' : '#dc2626' }}>
                              {user.isBlocked ? <CheckCircleIcon fontSize="small" /> : <BlockIcon fontSize="small" />}
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Card>
      </Container>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={closeEdit} maxWidth="sm" fullWidth
        PaperProps={{ sx: { borderRadius: 3 } }}>
        <DialogTitle sx={{ fontFamily: "'Syne', sans-serif", fontWeight: 700, pb: 1 }}>
          Edit User
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {editErrors.api && <Alert severity="error" sx={{ mb: 2 }}>{editErrors.api}</Alert>}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1 }}>
            <TextField
              label="Full Name"
              value={editForm.name}
              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
              fullWidth
              error={!!editErrors.name}
              helperText={editErrors.name}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <TextField
              label="Email"
              value={editForm.email}
              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              fullWidth
              error={!!editErrors.email}
              helperText={editErrors.email}
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <TextField
              label="Role"
              value={editForm.role}
              onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
              select
              fullWidth
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            >
              <MenuItem value="customer">Customer</MenuItem>
              <MenuItem value="merchant">Merchant</MenuItem>
              <MenuItem value="superadmin">Super Admin</MenuItem>
            </TextField>
            <TextField
              label="Account Status"
              value={editForm.isBlocked ? 'blocked' : 'active'}
              onChange={(e) => setEditForm({ ...editForm, isBlocked: e.target.value === 'blocked' })}
              select
              fullWidth
              sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            >
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="blocked">Blocked</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, gap: 1 }}>
          <Button onClick={closeEdit} disabled={saving}
            sx={{ borderColor: '#e2e8f0', color: '#64748b', textTransform: 'none' }} variant="outlined">
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving} variant="contained"
            sx={{ background: '#7c3aed', textTransform: 'none', fontWeight: 600, px: 3, '&:hover': { background: '#6d28d9' } }}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar open={!!success} autoHideDuration={3000} onClose={() => setSuccess('')}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <Alert severity="success" sx={{ width: '100%' }}>{success}</Alert>
      </Snackbar>
    </Box>
  );
};

export default ManageUsers;