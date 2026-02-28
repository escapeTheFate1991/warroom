"use client";

import { useState, useEffect } from "react";
import { Package, Plus, Edit, Trash2, X, Save, Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Product {
  id: number;
  name: string;
  sku: string;
  description: string | null;
  price: number;
  quantity: number;
  created_at: string;
  updated_at: string;
}

interface ProductFormData {
  name: string;
  sku: string;
  description: string;
  price: string;
  quantity: string;
}

export default function ProductsPanel() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<ProductFormData>({
    name: "",
    sku: "",
    description: "",
    price: "",
    quantity: "",
  });

  const loadProducts = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/api/crm/products`);
      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      }
    } catch (error) {
      console.error("Failed to load products:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  const handleAddProduct = () => {
    setEditingProduct(null);
    setFormData({
      name: "",
      sku: "",
      description: "",
      price: "",
      quantity: "",
    });
    setShowModal(true);
  };

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      sku: product.sku,
      description: product.description || "",
      price: product.price.toString(),
      quantity: product.quantity.toString(),
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const productData = {
        name: formData.name,
        sku: formData.sku,
        description: formData.description || null,
        price: parseFloat(formData.price),
        quantity: parseInt(formData.quantity),
      };

      const url = editingProduct
        ? `${API}/api/crm/products/${editingProduct.id}`
        : `${API}/api/crm/products`;

      const method = editingProduct ? "PUT" : "POST";

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(productData),
      });

      if (response.ok) {
        setShowModal(false);
        loadProducts(); // Reload the products list
      } else {
        console.error("Failed to save product");
      }
    } catch (error) {
      console.error("Failed to save product:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteProduct = async (product: Product) => {
    if (!confirm(`Are you sure you want to delete "${product.name}"?`)) {
      return;
    }

    try {
      const response = await fetch(`${API}/api/crm/products/${product.id}`, {
        method: "DELETE",
      });

      if (response.ok) {
        loadProducts(); // Reload the products list
      } else {
        console.error("Failed to delete product");
      }
    } catch (error) {
      console.error("Failed to delete product:", error);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingProduct(null);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(price);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Package size={16} />
          Products
        </h2>
        <button
          onClick={handleAddProduct}
          className="flex items-center gap-2 px-3 py-1.5 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition"
        >
          <Plus size={14} />
          Add Product
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {/* Products Table */}
        {!loading && products.length > 0 && (
          <div className="bg-warroom-surface border border-warroom-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-warroom-border bg-warroom-bg">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">SKU</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Price</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Quantity</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-warroom-muted uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id} className="border-b border-warroom-border/50 hover:bg-warroom-border/20">
                    <td className="px-4 py-3">
                      <p className="font-medium text-warroom-text">{product.name}</p>
                      {product.description && (
                        <p className="text-xs text-warroom-muted mt-1 max-w-xs truncate">
                          {product.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-warroom-text font-mono text-xs">{product.sku}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-warroom-text font-medium">{formatPrice(product.price)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        product.quantity > 10 
                          ? "bg-green-500/20 text-green-400"
                          : product.quantity > 0
                          ? "bg-yellow-500/20 text-yellow-400"
                          : "bg-red-500/20 text-red-400"
                      }`}>
                        {product.quantity} in stock
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEditProduct(product)}
                          className="p-1.5 text-warroom-muted hover:text-warroom-accent transition rounded"
                          title="Edit product"
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          onClick={() => handleDeleteProduct(product)}
                          className="p-1.5 text-warroom-muted hover:text-red-400 transition rounded"
                          title="Delete product"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20 text-warroom-muted">
            <Loader2 size={24} className="animate-spin mr-3" />
            <span className="text-sm">Loading products...</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && products.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-warroom-muted">
            <Package size={48} className="mb-4 opacity-20" />
            <p className="text-sm">No products found</p>
            <p className="text-xs mt-1">Add your first product or service</p>
          </div>
        )}
      </div>

      {/* Add/Edit Product Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity">
              <div className="absolute inset-0 bg-black/50" onClick={handleCloseModal} />
            </div>

            <div className="inline-block align-bottom bg-warroom-surface rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full border border-warroom-border">
              <form onSubmit={handleSubmit}>
                <div className="px-6 py-4 border-b border-warroom-border">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium text-warroom-text">
                      {editingProduct ? "Edit Product" : "Add Product"}
                    </h3>
                    <button
                      type="button"
                      onClick={handleCloseModal}
                      className="text-warroom-muted hover:text-warroom-text transition"
                    >
                      <X size={20} />
                    </button>
                  </div>
                </div>

                <div className="px-6 py-4 space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">
                      Product Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      placeholder="Enter product name"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">
                      SKU *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.sku}
                      onChange={(e) => setFormData(prev => ({ ...prev, sku: e.target.value }))}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent font-mono"
                      placeholder="Enter SKU"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-warroom-muted mb-1">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      rows={3}
                      className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                      placeholder="Enter product description (optional)"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">
                        Price *
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        required
                        value={formData.price}
                        onChange={(e) => setFormData(prev => ({ ...prev, price: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        placeholder="0.00"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-warroom-muted mb-1">
                        Quantity *
                      </label>
                      <input
                        type="number"
                        min="0"
                        required
                        value={formData.quantity}
                        onChange={(e) => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
                        className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        placeholder="0"
                      />
                    </div>
                  </div>
                </div>

                <div className="px-6 py-4 border-t border-warroom-border flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={handleCloseModal}
                    className="px-4 py-2 text-sm border border-warroom-border text-warroom-text hover:bg-warroom-border/20 rounded-lg transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 text-sm bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 text-white rounded-lg transition flex items-center gap-2"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    {saving ? "Saving..." : editingProduct ? "Update Product" : "Add Product"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}