const swaggerJsdoc = require('swagger-jsdoc');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'TestMart API',
      version: '1.0.0',
      description: 'TestMart e-commerce API documentation',
    },
    servers: [{ url: 'http://localhost:5001' }],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
        },
      },
    },
  },
  apis: ['./routes/*.js'],   // points to all your route files
};

module.exports = swaggerJsdoc(options);