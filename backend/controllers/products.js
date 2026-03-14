const Product = require('../models/Product');

const getProducts = async (req, res) => {
    try {
        const products = await Product.find();
        // No transformation needed! The model handles it automatically
        res.json(products);
    } catch (error) {
        console.error('Error fetching products:', error);
        res.status(500).json({ 
            success: false, 
            message: 'Server error while fetching products' 
        });
    }
};

module.exports = {
    getProducts
};