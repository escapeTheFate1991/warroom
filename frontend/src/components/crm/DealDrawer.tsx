"use client";

import { useState, useEffect } from "react";
import { 
  X, 
  DollarSign, 
  Calendar, 
  User, 
  Building2, 
  Edit,
  Save,
  Loader2,
  Plus,
  Clock,
  AlertTriangle,
  CheckCircle,
  Mail,
  Phone as PhoneIcon,
  FileText,
  Package,
  MessageSquare
} from "lucide-react";
import { DealFull, Activity, Product, Email } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface DealDrawerProps {
  deal: DealFull | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdate?: (deal: DealFull) => void;
  onEdit?: (deal: DealFull) => void;
}

const STAGE_COLORS: Record<number, string> = {
  0: "bg-red-500/20 text-red-400 border-red-500/30",
  10: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  20: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  40: "bg-blue-600/20 text-blue-300 border-blue-600/30",
  60: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  80: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  100: "bg-green-500/20 text-green-400 border-green-500/30",
};

const ACTIVITY_TYPES = [
  { value: "call", label: "Call", icon: PhoneIcon },
  { value: "meeting", label: "Meeting", icon: User },
  { value: "email", label: "Email", icon: Mail },
  { value: "note", label: "Note", icon: FileText },
  { value: "task", label: "Task", icon: CheckCircle },
];

export default function DealDrawer({ deal, isOpen, onClose, onUpdate, onEdit }: DealDrawerProps) {
  const [activeTab, setActiveTab] = useState<"details" | "activities" | "products" | "emails" | "notes">("details");
  const [activities, setActivities] = useState<Activity[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [emails, setEmails] = useState<Email[]>([]);
  const [notes, setNotes] = useState("");
  const [newActivity, setNewActivity] = useState({
    title: "",
    type: "note",
    comment: "",
    schedule_from: "",
    schedule_to: "",
  });
  const [saving, setSaving] = useState(false);
  const [loadingActivities, setLoadingActivities] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [loadingEmails, setLoadingEmails] = useState(false);

  // Load data when drawer opens or deal changes
  useEffect(() => {
    if (isOpen && deal) {
      setNotes(deal.description || "");
      
      // Set default tab based on deal completeness
      if (deal.status === null) {
        setActiveTab("activities");
      } else {
        setActiveTab("details");
      }
      
      // Load activities by default
      loadActivities();
    }
  }, [isOpen, deal]);

  const loadActivities = async () => {
    if (!deal) return;
    
    setLoadingActivities(true);
    try {
      const response = await fetch(`${API}/api/crm/activities?deal_id=${deal.id}`);
      if (response.ok) {
        const data = await response.json();
        setActivities(data);
      }
    } catch (error) {
      console.error("Failed to load activities:", error);
    } finally {
      setLoadingActivities(false);
    }
  };

  const loadProducts = async () => {
    if (!deal) return;
    
    setLoadingProducts(true);
    try {
      const response = await fetch(`${API}/api/crm/deals/${deal.id}/products`);
      if (response.ok) {
        const data = await response.json();
        setProducts(data);
      }
    } catch (error) {
      console.error("Failed to load products:", error);
    } finally {
      setLoadingProducts(false);
    }
  };

  const loadEmails = async () => {
    if (!deal) return;
    
    setLoadingEmails(true);
    try {
      const response = await fetch(`${API}/api/crm/emails?deal_id=${deal.id}`);
      if (response.ok) {
        const data = await response.json();
        setEmails(data);
      }
    } catch (error) {
      console.error("Failed to load emails:", error);
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleTabChange = (tab: typeof activeTab) => {
    setActiveTab(tab);
    
    // Lazy load data when tab is first accessed
    if (tab === "products" && products.length === 0) {
      loadProducts();
    } else if (tab === "emails" && emails.length === 0) {
      loadEmails();
    }
  };

  const handleSaveNotes = async () => {
    if (!deal) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API}/api/crm/deals/${deal.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: notes }),
      });
      
      if (response.ok) {
        const updatedDeal = await response.json();
        onUpdate?.(updatedDeal);
      }
    } catch (error) {
      console.error("Failed to save notes:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleAddActivity = async () => {
    if (!deal || !newActivity.title) return;
    
    setSaving(true);
    try {
      const activityData = {
        ...newActivity,
        schedule_from: newActivity.schedule_from || null,
        schedule_to: newActivity.schedule_to || null,
      };
      
      const response = await fetch(`${API}/api/crm/activities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(activityData),
      });
      
      if (response.ok) {
        // Link activity to deal
        const activity = await response.json();
        await fetch(`${API}/api/crm/deals/${deal.id}/activities`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ activity_id: activity.id }),
        });
        
        // Reset form and reload activities
        setNewActivity({
          title: "",
          type: "note",
          comment: "",
          schedule_from: "",
          schedule_to: "",
        });
        loadActivities();
      }
    } catch (error) {
      console.error("Failed to add activity:", error);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActivity = async (activity: Activity) => {
    setSaving(true);
    try {
      const response = await fetch(`${API}/api/crm/activities/${activity.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_done: !activity.is_done }),
      });
      
      if (response.ok) {
        loadActivities();
      }
    } catch (error) {
      console.error("Failed to toggle activity:", error);
    } finally {
      setSaving(false);
    }
  };

  const formatCurrency = (amount: number | null) => {
    if (!amount) return "$0";
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Not set";
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return "Not set";
    return new Date(dateString).toLocaleString();
  };

  if (!isOpen || !deal) return null;

  const stageColor = STAGE_COLORS[deal.stage_probability] || STAGE_COLORS[0];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-[700px] bg-warroom-surface border-l border-warroom-border shadow-2xl">
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex-shrink-0 p-6 border-b border-warroom-border">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-start gap-3 mb-4">
                  <div className="flex-1">
                    <h2 className="text-xl font-semibold text-warroom-text mb-2">
                      {deal.title}
                    </h2>
                    
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full border ${stageColor}`}>
                        {deal.stage_name}
                      </span>
                      {deal.deal_value && (
                        <span className="text-lg font-bold text-green-400">
                          {formatCurrency(deal.deal_value)}
                        </span>
                      )}
                      {deal.is_rotten && (
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 flex items-center gap-1">
                          <AlertTriangle size={10} />
                          Rotten
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onEdit?.(deal)}
                      className="text-warroom-muted hover:text-warroom-accent transition p-2"
                      title="Edit Deal"
                    >
                      <Edit size={16} />
                    </button>
                    <button
                      onClick={onClose}
                      className="text-warroom-muted hover:text-warroom-text transition p-2"
                    >
                      <X size={20} />
                    </button>
                  </div>
                </div>

                {/* Contact Info */}
                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  {deal.person_name && (
                    <div className="flex items-center gap-2 text-warroom-muted">
                      <User size={14} />
                      <span>{deal.person_name}</span>
                    </div>
                  )}
                  {deal.organization_name && (
                    <div className="flex items-center gap-2 text-warroom-muted">
                      <Building2 size={14} />
                      <span>{deal.organization_name}</span>
                    </div>
                  )}
                  {deal.expected_close_date && (
                    <div className="flex items-center gap-2 text-warroom-muted">
                      <Calendar size={14} />
                      <span>Expected close: {formatDate(deal.expected_close_date)}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-warroom-muted">
                    <Clock size={14} />
                    <span>{deal.days_in_stage} {deal.days_in_stage === 1 ? "day" : "days"} in stage</span>
                  </div>
                </div>

                {/* Additional Info */}
                <div className="grid grid-cols-3 gap-4 text-xs text-warroom-muted">
                  <div>
                    <span className="font-medium">Pipeline:</span> {deal.pipeline_name}
                  </div>
                  {deal.source_name && (
                    <div>
                      <span className="font-medium">Source:</span> {deal.source_name}
                    </div>
                  )}
                  {deal.type_name && (
                    <div>
                      <span className="font-medium">Type:</span> {deal.type_name}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-warroom-border">
            <div className="flex">
              {[
                { id: "details", label: "Details", icon: FileText },
                { id: "activities", label: "Activities", icon: CheckCircle },
                { id: "products", label: "Products", icon: Package },
                { id: "emails", label: "Emails", icon: Mail },
                { id: "notes", label: "Notes", icon: MessageSquare },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => handleTabChange(id as any)}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition border-b-2 ${
                    activeTab === id
                      ? "text-warroom-accent border-warroom-accent bg-warroom-accent/5"
                      : "text-warroom-muted border-transparent hover:text-warroom-text"
                  }`}
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "details" && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-warroom-text mb-2">Deal Information</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Value:</span>
                          <span className="text-warroom-text font-medium">
                            {formatCurrency(deal.deal_value)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Stage:</span>
                          <span className="text-warroom-text">{deal.stage_name} ({deal.stage_probability}%)</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Expected Close:</span>
                          <span className="text-warroom-text">{formatDate(deal.expected_close_date)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Days in Stage:</span>
                          <span className="text-warroom-text">{deal.days_in_stage}</span>
                        </div>
                      </div>
                    </div>

                    {deal.status !== null && (
                      <div>
                        <h4 className="text-sm font-medium text-warroom-text mb-2">Status</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-warroom-muted">Status:</span>
                            <span className={`font-medium ${
                              deal.status === true 
                                ? "text-green-400" 
                                : deal.status === false 
                                  ? "text-red-400" 
                                  : "text-warroom-text"
                            }`}>
                              {deal.status === true ? "Won" : deal.status === false ? "Lost" : "Open"}
                            </span>
                          </div>
                          {deal.closed_at && (
                            <div className="flex justify-between">
                              <span className="text-warroom-muted">Closed:</span>
                              <span className="text-warroom-text">{formatDateTime(deal.closed_at)}</span>
                            </div>
                          )}
                          {deal.lost_reason && (
                            <div className="flex justify-between">
                              <span className="text-warroom-muted">Reason:</span>
                              <span className="text-warroom-text">{deal.lost_reason}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium text-warroom-text mb-2">Contact Information</h4>
                      <div className="space-y-2 text-sm">
                        {deal.person_name && (
                          <div className="flex justify-between">
                            <span className="text-warroom-muted">Person:</span>
                            <span className="text-warroom-text">{deal.person_name}</span>
                          </div>
                        )}
                        {deal.organization_name && (
                          <div className="flex justify-between">
                            <span className="text-warroom-muted">Organization:</span>
                            <span className="text-warroom-text">{deal.organization_name}</span>
                          </div>
                        )}
                        {deal.user_name && (
                          <div className="flex justify-between">
                            <span className="text-warroom-muted">Owner:</span>
                            <span className="text-warroom-text">{deal.user_name}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-warroom-text mb-2">Dates</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Created:</span>
                          <span className="text-warroom-text">{formatDateTime(deal.created_at)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-warroom-muted">Updated:</span>
                          <span className="text-warroom-text">{formatDateTime(deal.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {deal.description && (
                  <div>
                    <h4 className="text-sm font-medium text-warroom-text mb-2">Description</h4>
                    <div className="p-3 bg-warroom-bg rounded-lg text-sm text-warroom-text">
                      {deal.description}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "activities" && (
              <div className="space-y-4">
                {/* Add Activity Form */}
                <div className="p-4 bg-warroom-bg rounded-lg border border-warroom-border">
                  <h4 className="text-sm font-medium text-warroom-text mb-3">Add Activity</h4>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <input
                        type="text"
                        value={newActivity.title}
                        onChange={(e) => setNewActivity(prev => ({ ...prev, title: e.target.value }))}
                        placeholder="Activity title"
                        className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                      />
                      <select
                        value={newActivity.type}
                        onChange={(e) => setNewActivity(prev => ({ ...prev, type: e.target.value }))}
                        className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
                        style={{ colorScheme: "dark" }}
                      >
                        {ACTIVITY_TYPES.map((type) => (
                          <option key={type.value} value={type.value}>
                            {type.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <textarea
                      value={newActivity.comment}
                      onChange={(e) => setNewActivity(prev => ({ ...prev, comment: e.target.value }))}
                      placeholder="Activity notes..."
                      rows={2}
                      className="w-full bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                    />
                    <div className="flex justify-end">
                      <button
                        onClick={handleAddActivity}
                        disabled={saving || !newActivity.title}
                        className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded text-sm font-medium transition flex items-center gap-2"
                      >
                        {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                        Add
                      </button>
                    </div>
                  </div>
                </div>

                {/* Activities List */}
                <div>
                  <h4 className="text-sm font-medium text-warroom-text mb-3">Recent Activities</h4>
                  {loadingActivities ? (
                    <div className="flex items-center justify-center py-8 text-warroom-muted">
                      <Loader2 size={16} className="animate-spin mr-2" />
                      Loading activities...
                    </div>
                  ) : activities.length > 0 ? (
                    <div className="space-y-3">
                      {activities.map((activity) => {
                        const ActivityIcon = ACTIVITY_TYPES.find(t => t.value === activity.type)?.icon || FileText;
                        return (
                          <div
                            key={activity.id}
                            className={`p-3 rounded-lg border transition ${
                              activity.is_done 
                                ? "bg-green-500/10 border-green-500/30" 
                                : "bg-warroom-bg border-warroom-border"
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-3 flex-1">
                                <ActivityIcon size={16} className="text-warroom-muted mt-0.5" />
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="text-sm font-medium text-warroom-text">
                                      {activity.title}
                                    </span>
                                    <span className="text-xs px-2 py-0.5 bg-warroom-border/50 rounded-full text-warroom-muted">
                                      {activity.type}
                                    </span>
                                  </div>
                                  {activity.comment && (
                                    <p className="text-xs text-warroom-muted mb-2">{activity.comment}</p>
                                  )}
                                  <div className="flex items-center gap-3 text-xs text-warroom-muted">
                                    <span>{activity.user_name}</span>
                                    <span>•</span>
                                    <span>{formatDateTime(activity.created_at)}</span>
                                    {activity.schedule_from && (
                                      <>
                                        <span>•</span>
                                        <span>Scheduled: {formatDateTime(activity.schedule_from)}</span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                              {activity.type === "task" && (
                                <button
                                  onClick={() => handleToggleActivity(activity)}
                                  className={`ml-3 p-1 rounded transition ${
                                    activity.is_done
                                      ? "text-green-400 hover:text-green-300"
                                      : "text-warroom-muted hover:text-warroom-text"
                                  }`}
                                >
                                  <CheckCircle size={16} />
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-warroom-muted">
                      <CheckCircle size={32} className="mx-auto mb-2 opacity-20" />
                      <p className="text-sm">No activities yet</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "products" && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-warroom-text">Products</h4>
                  <button
                    onClick={loadProducts}
                    className="text-warroom-muted hover:text-warroom-text transition"
                  >
                    <Plus size={16} />
                  </button>
                </div>

                {loadingProducts ? (
                  <div className="flex items-center justify-center py-8 text-warroom-muted">
                    <Loader2 size={16} className="animate-spin mr-2" />
                    Loading products...
                  </div>
                ) : products.length > 0 ? (
                  <div className="space-y-3">
                    {products.map((product) => (
                      <div key={product.id} className="p-3 bg-warroom-bg rounded-lg border border-warroom-border">
                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-medium text-warroom-text">{product.name}</h5>
                            {product.sku && (
                              <p className="text-xs text-warroom-muted">SKU: {product.sku}</p>
                            )}
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium text-warroom-text">
                              {formatCurrency(product.amount)}
                            </div>
                            <div className="text-xs text-warroom-muted">
                              {product.quantity} × {formatCurrency(product.price)}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-warroom-muted">
                    <Package size={32} className="mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No products attached</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "emails" && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-warroom-text">Emails</h4>

                {loadingEmails ? (
                  <div className="flex items-center justify-center py-8 text-warroom-muted">
                    <Loader2 size={16} className="animate-spin mr-2" />
                    Loading emails...
                  </div>
                ) : emails.length > 0 ? (
                  <div className="space-y-3">
                    {emails.map((email) => (
                      <div key={email.id} className="p-3 bg-warroom-bg rounded-lg border border-warroom-border">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h5 className="font-medium text-warroom-text mb-1">{email.subject}</h5>
                            <div className="flex items-center gap-2 text-xs text-warroom-muted">
                              <span>From: {email.from_addr?.email || "Unknown"}</span>
                              <span>•</span>
                              <span>{formatDateTime(email.created_at)}</span>
                            </div>
                          </div>
                          {!email.is_read && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0"></div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-warroom-muted">
                    <Mail size={32} className="mx-auto mb-2 opacity-20" />
                    <p className="text-sm">No emails found</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "notes" && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-warroom-text">Notes</h4>
                
                <div>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={10}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent resize-none"
                    placeholder="Add your notes about this deal..."
                  />
                </div>

                <button
                  onClick={handleSaveNotes}
                  disabled={saving}
                  className="w-full px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition flex items-center justify-center gap-2"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? "Saving..." : "Save Notes"}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}