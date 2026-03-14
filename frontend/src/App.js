import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Login from './components/Login';
import ProductList from './components/ProductList';
import Cart from './components/Cart';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './components/Dashboard';
import AddProduct from './components/AddProduct';
import ManageUsers from './components/ManageUsers';


function App() {
  return (
    <Router>
      <Routes>
        {/* Public */}
        <Route path="/" element={<Login />} />

        {/* Any authenticated user */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/products"
          element={
            <ProtectedRoute>
              <ProductList />
            </ProtectedRoute>
          }
        />
        {/* Customer + Super Admin only */}
        <Route path="/cart" element={<ProtectedRoute requiredRoles={['customer', 'superadmin']}><Cart /></ProtectedRoute>} />


        {/* Merchant + Super Admin only */}
       <Route path="/add-product" element={<ProtectedRoute requiredRoles={['merchant', 'superadmin']}><AddProduct /></ProtectedRoute>} />

        {/* Super Admin only */}
31        <Route path="/admin" element={<ProtectedRoute requiredRoles={['superadmin']}><ManageUsers /></ProtectedRoute>} />
32

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;

