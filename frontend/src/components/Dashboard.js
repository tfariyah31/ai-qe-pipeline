import React from 'react';
import { getRole } from '../utils/auth';
import SuperAdminDashboard from './dashboards/SuperAdminDashboard';
import MerchantDashboard from './dashboards/MerchantDashboard';
import CustomerDashboard from './dashboards/CustomerDashboard';

const Dashboard = () => {
  const role = getRole();

  if (role === 'superadmin') return <SuperAdminDashboard />;
  if (role === 'merchant') return <MerchantDashboard />;
  if (role === 'customer') return <CustomerDashboard />;

  return <div>Unknown role. Please log in again.</div>;
};

export default Dashboard;