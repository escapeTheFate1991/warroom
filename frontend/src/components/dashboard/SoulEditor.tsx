"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Save, History, FileText, User, Settings, Brain, Clock,
  Loader2, AlertCircle, CheckCircle2, RotateCcw
} from "lucide-react";
import { API, authFetch } from "@/lib/api";


const SOUL_FILES = [
  { key: "SOUL.md", label: "SOUL", icon: Brain, description: "Core personality & behavior" },
  { key: "IDENTITY.md", label: "IDENTITY", icon: User, description: "Name, avatar, basic info" },
  { key: "USER.md", label: "USER", icon: User, description: "About the human you're helping" },
  { key: "AGENTS.md", label: "AGENTS", icon: Settings, description: "Operating instructions & rules" },
  { key: "MEMORY.md", label: "MEMORY", icon: Brain, description: "Long-term curated memories" }
];

interface SoulData {
  [key: string]: string;
}

interface VersionHistory {
  path: string;
  timestamp: string;
  size: number;
}

export default function SoulEditor() {
  const [activeTab, setActiveTab] = useState("SOUL.md");
  const [soulData, setSoulData] = useState<SoulData>({});
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");
  
  // Version history
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<VersionHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [previewContent, setPreviewContent] = useState("");
  const [selectedVersion, setSelectedVersion] = useState("");

  // Load all soul files
  const loadSoulData = useCallback(async () => {
    try {
      setLoading(true);
      const response = await authFetch(`${API}/api/soul`);
      if (!response.ok) throw new Error("Failed to load soul data");
      const data = await response.json();
      setSoulData(data);
      setContent(data[activeTab] || "");
      setError("");
    } catch (err) {
      console.error("Error loading soul data:", err);
      setError("Failed to load soul files");
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  // Load version history for active file
  const loadHistory = useCallback(async () => {
    if (!showHistory) return;
    
    try {
      setHistoryLoading(true);
      const response = await authFetch(`${API}/api/soul/history/${activeTab}`);
      if (!response.ok) throw new Error("Failed to load history");
      const data = await response.json();
      setHistory(data);
    } catch (err) {
      console.error("Error loading history:", err);
    } finally {
      setHistoryLoading(false);
    }
  }, [activeTab, showHistory]);

  // Save current file
  const saveFile = async () => {
    try {
      setSaving(true);
      setSaveSuccess(false);
      setError("");
      
      const response = await authFetch(`${API}/api/soul`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: activeTab,
          content: content
        })
      });
      
      if (!response.ok) throw new Error("Failed to save file");
      
      // Update local data
      setSoulData(prev => ({ ...prev, [activeTab]: content }));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
      
    } catch (err) {
      console.error("Error saving file:", err);
      setError("Failed to save file");
    } finally {
      setSaving(false);
    }
  };

  // Revert to selected version
  const revertToVersion = async () => {
    if (!selectedVersion) return;
    
    try {
      setSaving(true);
      const response = await authFetch(`${API}/api/soul/revert/${activeTab}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: selectedVersion })
      });
      
      if (!response.ok) throw new Error("Failed to revert");
      
      // Reload data
      await loadSoulData();
      setShowHistory(false);
      setSelectedVersion("");
      setPreviewContent("");
      
    } catch (err) {
      console.error("Error reverting:", err);
      setError("Failed to revert to selected version");
    } finally {
      setSaving(false);
    }
  };

  // Preview version content
  const previewVersion = async (version: string) => {
    try {
      const response = await authFetch(`${API}/soul/history/${version}`);
      if (response.ok) {
        const data = await response.text();
        setPreviewContent(data);
        setSelectedVersion(version);
      }
    } catch (err) {
      console.error("Error previewing version:", err);
    }
  };

  // Handle tab change
  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setContent(soulData[tab] || "");
    setShowHistory(false);
    setSelectedVersion("");
    setPreviewContent("");
  };

  // Load data on mount and tab change
  useEffect(() => {
    loadSoulData();
  }, [loadSoulData]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const activeFile = SOUL_FILES.find(f => f.key === activeTab);
  const hasUnsavedChanges = content !== (soulData[activeTab] || "");

  return (
    <div className="bg-warroom-surface border border-warroom-border rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="border-b border-warroom-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-warroom-text flex items-center gap-2">
              <FileText size={20} className="text-warroom-accent" />
              Soul Editor
            </h2>
            <p className="text-sm text-warroom-muted mt-1">
              Edit your core personality and configuration files
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                showHistory 
                  ? "bg-warroom-accent text-white" 
                  : "bg-warroom-bg border border-warroom-border hover:bg-warroom-surface"
              }`}
            >
              <History size={14} />
              History
            </button>
            
            <button
              onClick={saveFile}
              disabled={saving || !hasUnsavedChanges}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                hasUnsavedChanges
                  ? "bg-warroom-accent hover:bg-warroom-accent/90 text-white"
                  : "bg-warroom-bg border border-warroom-border text-warroom-muted cursor-not-allowed"
              }`}
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
          </div>
        </div>
        
        {/* Status Messages */}
        {error && (
          <div className="flex items-center gap-2 mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <AlertCircle size={16} className="text-red-400" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
        
        {saveSuccess && (
          <div className="flex items-center gap-2 mt-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <CheckCircle2 size={16} className="text-green-400" />
            <p className="text-sm text-green-400">File saved successfully!</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-warroom-border overflow-x-auto">
        {SOUL_FILES.map((file) => {
          const IconComponent = file.icon;
          const isActive = activeTab === file.key;
          const hasChanges = content !== (soulData[file.key] || "") && isActive;
          
          return (
            <button
              key={file.key}
              onClick={() => handleTabChange(file.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? "border-warroom-accent text-warroom-accent bg-warroom-accent/5"
                  : "border-transparent text-warroom-muted hover:text-warroom-text hover:bg-warroom-bg"
              }`}
            >
              <IconComponent size={14} />
              {file.label}
              {hasChanges && <div className="w-2 h-2 bg-warroom-accent rounded-full" />}
            </button>
          );
        })}
      </div>

      <div className="flex h-[600px]">
        {/* Editor */}
        <div className={`flex-1 flex flex-col ${showHistory ? "border-r border-warroom-border" : ""}`}>
          {activeFile && (
            <div className="p-4 border-b border-warroom-border">
              <p className="text-sm text-warroom-text font-medium">{activeFile.label}</p>
              <p className="text-xs text-warroom-muted mt-1">{activeFile.description}</p>
            </div>
          )}
          
          <div className="flex-1 p-4">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 size={24} className="animate-spin text-warroom-accent" />
              </div>
            ) : (
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full h-full bg-warroom-bg border border-warroom-border rounded-lg p-4 font-mono text-sm text-warroom-text placeholder-warroom-muted resize-none focus:outline-none focus:ring-2 focus:ring-warroom-accent"
                placeholder={`Edit ${activeTab} content...`}
              />
            )}
          </div>
        </div>

        {/* History Panel */}
        {showHistory && (
          <div className="w-80 flex flex-col bg-warroom-bg">
            <div className="p-4 border-b border-warroom-border">
              <h3 className="font-medium text-warroom-text">Version History</h3>
              <p className="text-xs text-warroom-muted mt-1">{activeTab}</p>
            </div>
            
            <div className="flex-1 overflow-auto">
              {historyLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 size={20} className="animate-spin text-warroom-accent" />
                </div>
              ) : history.length === 0 ? (
                <div className="p-4 text-center text-warroom-muted">
                  <Clock size={24} className="mx-auto mb-2 opacity-20" />
                  <p className="text-sm">No version history</p>
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {history.map((version, i) => (
                    <div
                      key={version.path}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedVersion === version.path
                          ? "bg-warroom-accent/10 border-warroom-accent"
                          : "border-warroom-border hover:bg-warroom-surface"
                      }`}
                      onClick={() => previewVersion(version.path)}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-medium text-warroom-text">
                          Version {history.length - i}
                        </p>
                        <p className="text-xs text-warroom-muted">
                          {(version.size / 1024).toFixed(1)}KB
                        </p>
                      </div>
                      <p className="text-xs text-warroom-muted mt-1">
                        {new Date(version.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {selectedVersion && (
              <div className="p-4 border-t border-warroom-border">
                <button
                  onClick={revertToVersion}
                  disabled={saving}
                  className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-red-500 hover:bg-red-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
                  Revert to This Version
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}