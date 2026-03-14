const { body, validationResult } = require('express-validator');

// Custom error formatter to remove sensitive data
const formatValidationErrors = (errors) => {
    return errors.array().map(err => {
        // Clean error object without sensitive data
        const cleanError = {
            type: err.type,
            msg: err.msg,
            path: err.path,
            location: err.location
        };
        
        
        if (err.path !== 'password' && err.path !== 'confirmPassword' && err.value) {
            cleanError.value = err.value;
        }
        
        return cleanError;
    });
};

// Validation rules for registration
exports.validateRegister = [
    body('name')
        .trim()
        .escape()
        .notEmpty().withMessage('Name is required')
        .isLength({ min: 2, max: 50 }).withMessage('Name must be 2-50 characters')
        .matches(/^[a-zA-Z\s]+$/).withMessage('Name can only contain letters and spaces'),
    
    body('email')
        .trim()
        .escape()
        .normalizeEmail()
        .isEmail().withMessage('Valid email is required')
        .isLength({ max: 100 }).withMessage('Email too long'),
    
    body('password')
        .isLength({ min: 8 }).withMessage('Password must be at least 8 characters')
        .isLength({ max: 32 }).withMessage('Password must not exceed 32 characters')
        .matches(/[A-Z]/).withMessage('Password must contain an uppercase letter')
        .matches(/[a-z]/).withMessage('Password must contain a lowercase letter')
        .matches(/[0-9]/).withMessage('Password must contain a number')
        .matches(/[!@#$%^&*]/).withMessage('Password must contain a special character')
        // Custom validator to prevent common passwords
        .custom((value) => {
            const commonPasswords = [
                'password', 'password123', '12345678', 'qwerty123', 
                'admin123', 'letmein', 'welcome', 'monkey123'
            ];
            if (commonPasswords.includes(value.toLowerCase())) {
                throw new Error('Password is too common and easily guessable');
            }
            return true;
        }),
    
    // Custom validator for password strength (optional)
    body('confirmPassword')
        .optional()
        .custom((value, { req }) => {
            if (value && value !== req.body.password) {
                throw new Error('Passwords do not match');
            }
            return true;
        }),
    
    // Error handler middleware with password protection
    (req, res, next) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) {
            return res.status(400).json({ 
                success: false, 
                errors: formatValidationErrors(errors) // Use formatter to remove password
            });
        }
        next();
    }
];

// Validation rules for login
exports.validateLogin = [
    body('email')
        .trim()
        .escape()
        .normalizeEmail()
        .isEmail().withMessage('Valid email is required'),
    
    body('password')
        .notEmpty().withMessage('Password is required'),
    
    // Error handler middleware with password protection
    (req, res, next) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) {
            return res.status(400).json({ 
                success: false, 
                errors: formatValidationErrors(errors) // Use formatter to remove password
            });
        }
        next();
    }
];

// Password strength validator function
exports.validatePasswordStrength = (password) => {
    const errors = [];
    
    if (password.length < 8) {
        errors.push('Password must be at least 8 characters long');
    }
    
    if (password.length > 32) {
        errors.push('Password must not exceed 32 characters');
    }
    
    if (!/[A-Z]/.test(password)) {
        errors.push('Password must contain an uppercase letter');
    }
    
    if (!/[a-z]/.test(password)) {
        errors.push('Password must contain a lowercase letter');
    }
    
    if (!/[0-9]/.test(password)) {
        errors.push('Password must contain a number');
    }
    
    if (!/[!@#$%^&*]/.test(password)) {
        errors.push('Password must contain a special character');
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
};