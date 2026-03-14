const express = require('express');
const mongoose = require('mongoose');
const dotenv = require('dotenv');
dotenv.config();
const cors = require('cors');
const mongoSanitize = require('express-mongo-sanitize');
const helmet = require('helmet');
const xss = require('xss-clean');
const sanitize = require('./middleware/sanitize');
const userRoutes = require('./routes/users');
const paymentRoutes = require('./routes/payments');



const app = express();
const PORT = process.env.PORT || 5001;

const swaggerUi = require('swagger-ui-express');
const swaggerSpec = require('./config/swagger');

app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

//const cleanupBlockedUsers = require('./utils/cleanupBlockedUsers');

// Run cleanup every minute
//setInterval(cleanupBlockedUsers, 60 * 1000);

app.get('/', (req, res) => {
  res.send('Welcome to the backend server!');
});

app.get('/api/health', (req, res) => {
  res.json({ ok: true });
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(mongoSanitize({
    replaceWith: '_', // Replace $ with _
    onSanitize: ({ req, key }) => {
        console.warn('Attempted injection detected:', key);
    }
}));

// Add security headers
app.use(helmet());

// Sanitize user input to prevent XSS
app.use(xss());
app.use(sanitize);

console.log('MongoDB URI:', process.env.MONGO_URI); 

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI, { useNewUrlParser: true, useUnifiedTopology: true })
  .then(() => console.log('MongoDB connected'))
  .catch(err => console.log(err));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/products', require('./routes/products'));

app.use('/api/users', userRoutes);
app.use('/api/payments', paymentRoutes);


app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Auth routes: http://localhost:${PORT}/api/auth`);
  console.log(`Product routes: http://localhost:${PORT}/api/products`);
});
