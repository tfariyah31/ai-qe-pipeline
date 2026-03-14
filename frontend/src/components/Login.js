import React, { useState } from 'react';
//import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { 
  Container, 
  Typography, 
  TextField, 
  Button, 
  Box, 
  Paper, 
  Alert 
} from '@mui/material'; // Correct package name

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [attemptsLeft, setAttemptsLeft] = useState(3);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:5001/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json(); // Parse the response body as JSON
      
      if (!response.ok) {
        // Handle rate limit error or other errors
        //console.log('Error from backend:', data.error);
        if (data.error) {
          //setError(data.error); // Display the error message from the backend
          if (data.error === "Too many attempts. Try again later.") {
            setAttemptsLeft(0); // Disable the login button
          }
        } 
        else if (!data.success) {
          setError(data.message); // Display the error message from the backend
        }
        else {
          setError('Login failed. Please try again.');
        }
        return;
      }

      // Save authentication info
      localStorage.setItem('accessToken', data.accessToken);
      if (data.user && data.user.role) {
        localStorage.setItem('userRole', data.user.role);
      }
      navigate('/dashboard'); // Redirect to the dashboard page
    } catch (err) {
      setError(
        err.res?.data?.message ||
        err.message ||
        'Login failed'
      );
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: '100%', maxWidth: 400 }}>
          <Typography variant="h4" align="center" gutterBottom>
            Login
          </Typography>
          {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

          <form onSubmit={handleSubmit}>
            <TextField
              label="Email"
              type="email"
              fullWidth
              margin="normal"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <TextField
              label="Password"
              type="password"
              fullWidth
              margin="normal"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              sx={{ mt: 2 }}
              disabled={attemptsLeft === 0}
            >
              {attemptsLeft === 0 ? 'Try again later' : 'Login'}
            </Button>

            
          </form>
        </Paper>
      </Box>
    </Container>
  );
};

export default Login;
