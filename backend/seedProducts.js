const mongoose = require('mongoose');
const Product = require('./models/Product');
const dotenv = require('dotenv');

//dotenv.config();
dotenv.config({ path: require('path').resolve(__dirname, '.env') });

// Sample product data
const products = [
  {
    name: "iPhone 15 Pro Max",
    description: "Apple's latest flagship with A17 Pro chip, titanium design, and advanced camera system",
    image: "https://www.apple.com/newsroom/images/2023/09/apple-unveils-iphone-15-pro-and-iphone-15-pro-max/article/Apple-iPhone-15-Pro-lineup-hero-230912_Full-Bleed-Image.jpg.medium_2x.jpg",
    rating: 4.8,
    price: 999.99
  },
  {
    name: "MacBook Pro 16-inch",
    description: "M3 Pro chip, 18GB RAM, 512GB SSD - Space Black",
    image: "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/mbp16-spaceblack-select-202310?wid=904&hei=840&fmt=jpeg&qlt=90&.v=1697311054771",
    rating: 4.9,
    price: 1999.99
  },
  {
    name: "iPad Pro 12.9-inch",
    description: "M2 chip, Liquid Retina XDR display, 5G capable",
    image: "https://cdsassets.apple.com/live/SZLF0YNV/images/sp/111979_ipad-pro-12-2018.png",
    rating: 4.7,
    price: 1299.99
  },
  {
    name: "AirPods Pro (2nd Gen)",
    description: "Active Noise Cancellation, Adaptive Audio, MagSafe Charging Case",
    image: "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/MQD83?wid=1144&hei=1144&fmt=jpeg&qlt=90&.v=1660803972361",
    rating: 4.8,
    price: 249.99
  },
  {
    name: "Apple Watch Series 9",
    description: "Double tap gesture, S9 chip, brighter display",
    image: "https://www.apple.com/newsroom/images/2023/09/apple-introduces-the-advanced-new-apple-watch-series-9/article/Apple-Watch-S9-pink-aluminum-Sport-Band-pink-230912_inline.jpg.medium_2x.jpg",
    rating: 4.6,
    price: 399.99
  },
  {
    name: "Samsung Galaxy S24 Ultra",
    description: "AI-powered phone with 200MP camera and S Pen",
    image: "https://images.samsung.com/is/image/samsung/assets/us/2501/pcd/smartphones/galaxy-s24-ultra/galaxy-S24-ultra-ft02-kv_MO.jpg?$720_N_JPG$",
    rating: 4.7,
    price: 1199.99
  },
  {
    name: "Dell XPS 15",
    description: "Intel Core i9, 32GB RAM, 1TB SSD, RTX 4060",
    image: "https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/xps-notebooks/xps-16-da16260/media-gallery/touch/notebook-da16260-t-gray-copilot-gallery-1.psd?fmt=png-alpha&pscan=auto&scl=1&hei=476&wid=593&qlt=100,1&resMode=sharp2&size=593,476&chrss=full",
    rating: 4.5,
    price: 2499.99
  }
];

// Connect to MongoDB
mongoose.connect(process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/simplewebapp')
    .then(() => console.log('✅ MongoDB connected'))
    .catch(err => {
        console.error('❌ MongoDB connection error:', err);
        process.exit(1);
    });

// Function to seed products
const seedProducts = async () => {
    try {
        // Clear existing products 
        console.log('🗑️  Clearing existing products...');
        await Product.deleteMany({});
        console.log('✅ Existing products cleared');

        // Insert new products
        console.log('📦 Inserting new products...');
        const insertedProducts = await Product.insertMany(products);
        console.log(`✅ Successfully added ${insertedProducts.length} products!`);

        // Show the inserted products
        console.log('\n📋 Products added:');
        insertedProducts.forEach((product, index) => {
            console.log(`${index + 1}. ${product.name} - Rating: ${product.rating}⭐`);
        });

    } catch (error) {
        console.error('❌ Error seeding products:', error);
    } finally {
        // Close the database connection
        await mongoose.connection.close();
        console.log('\n🔌 Database connection closed');
    }
};

// Run the seed function
seedProducts();