"use client";

import { useState, useEffect } from "react";
import { Eye, Filter, Calendar, User, FileText } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface AuditLogEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  user_id: number;
  user_name?: string;
  old_values: any;
  new_values: any;
  created_at: string;
  entity_name?: string;
}

interface Filters {
  entity_type: string;
  action: string;
  user_id: string;
  date_from: string;
  date_to: string;
}

const ENTITY_TYPES = [
  { value: '', label: 'All Entity Types' },
  { value: 'deal', label: 'Deals' },
  { value: 'person', label: 'Persons' },
  { value: 'organization', label: 'Organizations' },
  { value: 'activity', label: 'Activities' },
  { value: 'email', label: 'Emails' },
  { value: 'product', label: 'Products' }
];

const ACTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'created', label: 'Created' },
  { value: 'updated', label: 'Updated' },
  { value: 'deleted', label: 'Deleted' },
  { value: 'stage_changed', label: 'Stage Changed' }
];

const ACTION_COLORS = {
  created: 'text-green-400 bg-green-500/20',
  updated: 'text-blue-400 bg-blue-500/20',
  deleted: 'text-red-400 bg-red-500/20',
  stage_changed: 'text-yellow-400 bg-yellow-500/20'
};

export default function AuditTrail() {
  const [auditEntries, setAuditEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<{ id: number; name: string }[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    entity_type: '',
    action: '',
    user_id: '',
    date_from: '',
    date_to: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const loadAuditLog = async (page = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: '50',
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v))
      });
      
      const resp = await fetch(`${API}/api/crm/audit-log?${params}`);
      if (resp.ok) {
        const data = await resp.json();
        setAuditEntries(data.entries || []);
        setTotalPages(data.total_pages || 1);
        setCurrentPage(page);
      }
    } catch (error) {
      console.error('Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const resp = await fetch(`${API}/api/crm/users`);
      if (resp.ok) {
        const data = await resp.json();
        setUsers(data);
      }
    } catch (error) {
      console.error('Failed to load users');
    }
  };

  useEffect(() => {
    loadAuditLog();
    loadUsers();
  }, []);

  useEffect(() => {
    loadAuditLog(1);
  }, [filters]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatChanges = (oldValues: any, newValues: any) => {
    if (!oldValues && newValues) {
      return Object.entries(newValues).map(([key, value]) => (
        <div key={key} className="text-xs">
          <span className="text-warroom-muted">{key}:</span>
          <span className="text-green-400 ml-1">{String(value)}</span>
        </div>
      ));
    }

    if (oldValues && !newValues) {
      return (
        <div className="text-xs text-red-400">
          Record deleted
        </div>
      );
    }

    if (oldValues && newValues) {
      const changes = Object.entries(newValues).filter(([key, value]) => 
        oldValues[key] !== value
      );

      return changes.map(([key, newValue]) => (
        <div key={key} className="text-xs">
          <span className="text-warroom-muted">{key}:</span>
          <span className="text-red-400 ml-1">{String(oldValues[key] || 'null')}</span>
          <span className="text-warroom-muted mx-1">→</span>
          <span className="text-green-400">{String(newValue)}</span>
        </div>
      ));
    }

    return null;
  };

  const renderFilters = () => (
    <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4 mb-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="text-xs text-warroom-text block mb-1">Entity Type</label>
          <select
            value={filters.entity_type}
            onChange={(e) => setFilters(prev => ({ ...prev, entity_type: e.target.value }))}
            className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs"
          >
            {ENTITY_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-warroom-text block mb-1">Action</label>
          <select
            value={filters.action}
            onChange={(e) => setFilters(prev => ({ ...prev, action: e.target.value }))}
            className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs"
          >
            {ACTIONS.map(action => (
              <option key={action.value} value={action.value}>{action.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-warroom-text block mb-1">User</label>
          <select
            value={filters.user_id}
            onChange={(e) => setFilters(prev => ({ ...prev, user_id: e.target.value }))}
            className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs"
          >
            <option value="">All Users</option>
            {users.map(user => (
              <option key={user.id} value={user.id.toString()}>{user.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-warroom-text block mb-1">From Date</label>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => setFilters(prev => ({ ...prev, date_from: e.target.value }))}
            className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs"
          />
        </div>

        <div>
          <label className="text-xs text-warroom-text block mb-1">To Date</label>
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => setFilters(prev => ({ ...prev, date_to: e.target.value }))}
            className="w-full bg-warroom-bg border border-warroom-border rounded px-2 py-1 text-xs"
          />
        </div>

        <div className="flex items-end">
          <button
            onClick={() => setFilters({
              entity_type: '',
              action: '',
              user_id: '',
              date_from: '',
              date_to: ''
            })}
            className="px-3 py-1 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded text-xs font-medium transition"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );

  const renderDetailModal = () => {
    if (!selectedEntry) return null;

    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-semibold text-warroom-text">
              Audit Log Details
            </h4>
            <button
              onClick={() => setSelectedEntry(null)}
              className="text-warroom-muted hover:text-warroom-text"
            >
              ✕
            </button>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Entity</label>
                <div className="text-sm text-warroom-text">
                  {selectedEntry.entity_type} #{selectedEntry.entity_id}
                </div>
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Action</label>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  ACTION_COLORS[selectedEntry.action as keyof typeof ACTION_COLORS] || 
                  'text-warroom-text bg-warroom-bg'
                }`}>
                  {selectedEntry.action}
                </span>
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">User</label>
                <div className="text-sm text-warroom-text">
                  {selectedEntry.user_name || `User #${selectedEntry.user_id}`}
                </div>
              </div>
              <div>
                <label className="text-xs text-warroom-muted block mb-1">Date</label>
                <div className="text-sm text-warroom-text">
                  {formatDate(selectedEntry.created_at)}
                </div>
              </div>
            </div>

            {selectedEntry.old_values && (
              <div>
                <label className="text-xs text-warroom-muted block mb-2">Previous Values</label>
                <div className="bg-warroom-bg rounded p-3">
                  <pre className="text-xs text-warroom-text whitespace-pre-wrap">
                    {JSON.stringify(selectedEntry.old_values, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {selectedEntry.new_values && (
              <div>
                <label className="text-xs text-warroom-muted block mb-2">New Values</label>
                <div className="bg-warroom-bg rounded p-3">
                  <pre className="text-xs text-warroom-text whitespace-pre-wrap">
                    {JSON.stringify(selectedEntry.new_values, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <FileText size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Audit Trail</h2>
        <div className="ml-auto">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium transition ${
              showFilters 
                ? 'bg-warroom-accent text-white' 
                : 'bg-warroom-surface hover:bg-warroom-bg border border-warroom-border'
            }`}
          >
            <Filter size={14} />
            Filters
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-6xl mx-auto">
          {showFilters && renderFilters()}

          {loading ? (
            <div className="flex items-center justify-center py-12 text-warroom-muted">
              <FileText size={24} className="animate-spin mr-3" />
              Loading audit trail...
            </div>
          ) : auditEntries.length === 0 ? (
            <div className="text-center py-12 text-warroom-muted">
              <FileText size={32} className="mx-auto mb-4 opacity-50" />
              <p className="text-sm">No audit log entries found</p>
              <p className="text-xs mt-1">Try adjusting your filters</p>
            </div>
          ) : (
            <div className="space-y-3">
              {auditEntries.map((entry) => (
                <div 
                  key={entry.id} 
                  className="bg-warroom-surface border border-warroom-border rounded-lg p-4 hover:bg-warroom-surface/80 cursor-pointer transition"
                  onClick={() => setSelectedEntry(entry)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          ACTION_COLORS[entry.action as keyof typeof ACTION_COLORS] || 
                          'text-warroom-text bg-warroom-bg'
                        }`}>
                          {entry.action}
                        </span>
                        <span className="text-sm text-warroom-text font-medium">
                          {entry.entity_type} #{entry.entity_id}
                          {entry.entity_name && ` - ${entry.entity_name}`}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-xs text-warroom-muted mb-2">
                        <div className="flex items-center gap-1">
                          <User size={12} />
                          {entry.user_name || `User #${entry.user_id}`}
                        </div>
                        <div className="flex items-center gap-1">
                          <Calendar size={12} />
                          {formatDate(entry.created_at)}
                        </div>
                      </div>

                      {/* Changes Summary */}
                      <div className="space-y-1 max-w-2xl">
                        {formatChanges(entry.old_values, entry.new_values)}
                      </div>
                    </div>
                    
                    <button className="p-1 hover:bg-warroom-bg rounded transition">
                      <Eye size={14} className="text-warroom-muted" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => loadAuditLog(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1 bg-warroom-bg hover:bg-warroom-surface disabled:opacity-50 border border-warroom-border rounded text-xs font-medium transition"
              >
                Previous
              </button>
              
              <span className="px-3 py-1 bg-warroom-accent rounded text-xs font-medium">
                {currentPage} of {totalPages}
              </span>
              
              <button
                onClick={() => loadAuditLog(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 bg-warroom-bg hover:bg-warroom-surface disabled:opacity-50 border border-warroom-border rounded text-xs font-medium transition"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {renderDetailModal()}
    </div>
  );
}