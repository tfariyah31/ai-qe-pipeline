// Decode JWT payload without a library
export const decodeToken = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

export const getRole = () => {
  const token = localStorage.getItem('accessToken');
  if (!token) return null;
  // First try localStorage directly (your current setup stores it there)
  const storedRole = localStorage.getItem('userRole');
  if (storedRole) return storedRole;
  // Fallback: decode from JWT
  const decoded = decodeToken(token);
  return decoded?.role || null;
};

export const isAuthenticated = () => !!localStorage.getItem('accessToken');

export const logout = (navigate) => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('userRole');
  navigate('/');
};