const sanitize = (req, res, next) => {
    try {
        // Remove any $ or . from query parameters
        if (req.query) {
            Object.keys(req.query).forEach(key => {
                if (typeof req.query[key] === 'string') {
                    req.query[key] = req.query[key].replace(/[$.]/g, '');
                }
            });
        }
        
        // Sanitize body
        if (req.body) {
            Object.keys(req.body).forEach(key => {
                if (typeof req.body[key] === 'string') {
                    // Remove any potential MongoDB operators
                    req.body[key] = req.body[key].replace(/\$/g, '');
                    // Trim whitespace (but NOT for passwords if spaces are allowed)
                    if (key !== 'password') {
                        req.body[key] = req.body[key].trim();
                    }
                }
            });
        }
        
        next();
    } catch (error) {
        console.error('Sanitization error:', error);
        next(error); // Pass error to Express error handler
    }
};

module.exports = sanitize; 