const CART_KEY = 'cart_items';

export const getCart = () => {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || [];
  } catch {
    return [];
  }
};

export const addToCart = (product) => {
  const cart = getCart();
  const existing = cart.find((item) => item._id === product._id);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ ...product, quantity: 1, price: product.price || 29.99 });
  }
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
};

export const removeFromCart = (productId) => {
  const cart = getCart().filter((item) => item._id !== productId);
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
};

export const updateQuantity = (productId, quantity) => {
  const cart = getCart().map((item) =>
    item._id === productId ? { ...item, quantity } : item
  );
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
};

export const clearCart = () => {
  localStorage.removeItem(CART_KEY);
};

export const getCartCount = () => {
  return getCart().reduce((sum, item) => sum + item.quantity, 0);
};