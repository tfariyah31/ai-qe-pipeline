import React from 'react';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, requiredRoles = [] }) => {
  // Check for auth token
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  const role = localStorage.getItem('userRole');

  // If no token, redirect to login
  if (!token) {
    console.log('No token found - redirecting to login');
    return <Navigate to="/login" replace />;
  }

  // If roles are specified, ensure user has one of them
  if (requiredRoles.length > 0) {
    if (!role || !requiredRoles.includes(role)) {
      console.log('User role insufficient, redirecting to home');
      return <Navigate to="/" replace />;
    }
  }

  // Token and/or role checks passed
  return children;
};

export default ProtectedRoute;