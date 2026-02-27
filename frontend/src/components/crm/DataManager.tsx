"use client";

import { useState, useRef } from "react";
import { Upload, Download, Search, ArrowRight, FileText, AlertCircle, Check } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface ImportMapping {
  csvColumn: string;
  crmField: string;
}

interface DuplicatePair {
  id1: number;
  id2: number;
  entity1: any;
  entity2: any;
  similarity: number;
}

const ENTITY_TYPES = [
  { value: 'person', label: 'Persons' },
  { value: 'organization', label: 'Organizations' },
  { value: 'deal', label: 'Deals' },
  { value: 'product', label: 'Products' }
];

const CRM_FIELDS = {
  person: ['name', 'email', 'phone', 'job_title', 'organization_name'],
  organization: ['name', 'address', 'phone', 'website'],
  deal: ['title', 'description', 'deal_value', 'expected_close_date'],
  product: ['name', 'sku', 'description', 'price', 'quantity']
};

const TABS = [
  { id: 'import', label: 'Import', icon: Upload },
  { id: 'export', label: 'Export', icon: Download },
  { id: 'dedupe', label: 'Deduplication', icon: Search }
] as const;

type Tab = typeof TABS[number]['id'];

export default function DataManager() {
  const [activeTab, setActiveTab] = useState<Tab>('import');
  const [selectedEntityType, setSelectedEntityType] = useState('person');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [fieldMappings, setFieldMappings] = useState<ImportMapping[]>([]);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  
  // Export state
  const [exportFormat, setExportFormat] = useState('csv');
  const [exportDateFrom, setExportDateFrom] = useState('');
  const [exportDateTo, setExportDateTo] = useState('');
  const [exporting, setExporting] = useState(false);
  
  // Deduplication state
  const [duplicatePairs, setDuplicatePairs] = useState<DuplicatePair[]>([]);
  const [findingDuplicates, setFindingDuplicates] = useState(false);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportFile(file);
    
    // Parse CSV headers
    const text = await file.text();
    const lines = text.split('\n');
    if (lines.length > 0) {
      const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
      setCsvHeaders(headers);
      
      // Initialize field mappings
      const mappings: ImportMapping[] = headers.map(header => ({
        csvColumn: header,
        crmField: ''
      }));
      setFieldMappings(mappings);
    }
  };

  const updateFieldMapping = (index: number, crmField: string) => {
    const newMappings = [...fieldMappings];
    newMappings[index].crmField = crmField;
    setFieldMappings(newMappings);
  };

  const importData = async () => {
    if (!importFile) return;

    setImporting(true);
    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('entity_type', selectedEntityType);
    formData.append('mappings', JSON.stringify(fieldMappings));

    try {
      const resp = await fetch(`${API}/api/crm/import`, {
        method: 'POST',
        body: formData
      });
      
      if (resp.ok) {
        const result = await resp.json();
        setImportResult(result);
      } else {
        alert('Import failed');
      }
    } catch (error) {
      alert('Import error: ' + error);
    } finally {
      setImporting(false);
    }
  };

  const exportData = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams({
        format: exportFormat,
        ...(exportDateFrom && { from_date: exportDateFrom }),
        ...(exportDateTo && { to_date: exportDateTo })
      });
      
      const resp = await fetch(`${API}/api/crm/export/${selectedEntityType}?${params}`);
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedEntityType}_export.${exportFormat}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      alert('Export failed');
    } finally {
      setExporting(false);
    }
  };

  const findDuplicates = async () => {
    setFindingDuplicates(true);
    try {
      const resp = await fetch(`${API}/api/crm/deduplicate/${selectedEntityType}`, {
        method: 'POST'
      });
      
      if (resp.ok) {
        const pairs = await resp.json();
        setDuplicatePairs(pairs);
      }
    } catch (error) {
      alert('Failed to find duplicates');
    } finally {
      setFindingDuplicates(false);
    }
  };

  const mergeDuplicates = async (id1: number, id2: number, keepId: number) => {
    try {
      const resp = await fetch(`${API}/api/crm/merge/${selectedEntityType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          primary_id: keepId,
          duplicate_id: keepId === id1 ? id2 : id1
        })
      });
      
      if (resp.ok) {
        // Remove merged pair from list
        setDuplicatePairs(pairs => 
          pairs.filter(pair => !(pair.id1 === id1 && pair.id2 === id2))
        );
      }
    } catch (error) {
      alert('Failed to merge duplicates');
    }
  };

  const renderImportTab = () => (
    <div className="space-y-6">
      <div>
        <label className="text-sm text-warroom-text block mb-2">Entity Type</label>
        <select
          value={selectedEntityType}
          onChange={(e) => setSelectedEntityType(e.target.value)}
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
        >
          {ENTITY_TYPES.map(type => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-sm text-warroom-text block mb-2">CSV File</label>
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-warroom-border rounded-lg p-8 text-center cursor-pointer hover:border-warroom-accent transition"
        >
          {importFile ? (
            <div className="flex items-center justify-center gap-2 text-warroom-accent">
              <FileText size={20} />
              <span className="text-sm">{importFile.name}</span>
            </div>
          ) : (
            <div className="text-warroom-muted">
              <Upload size={32} className="mx-auto mb-2" />
              <p className="text-sm">Click to upload CSV file</p>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {csvHeaders.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-warroom-text mb-4">Field Mapping</h4>
          <div className="space-y-3">
            {fieldMappings.map((mapping, index) => (
              <div key={index} className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="bg-warroom-surface border border-warroom-border rounded px-3 py-2 text-sm">
                    {mapping.csvColumn}
                  </div>
                </div>
                <ArrowRight size={16} className="text-warroom-muted" />
                <div className="flex-1">
                  <select
                    value={mapping.crmField}
                    onChange={(e) => updateFieldMapping(index, e.target.value)}
                    className="w-full bg-warroom-bg border border-warroom-border rounded px-3 py-2 text-sm"
                  >
                    <option value="">Skip this field</option>
                    {CRM_FIELDS[selectedEntityType as keyof typeof CRM_FIELDS]?.map(field => (
                      <option key={field} value={field}>{field}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {importFile && (
        <button
          onClick={importData}
          disabled={importing}
          className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition"
        >
          <Upload size={16} />
          {importing ? 'Importing...' : 'Import Data'}
        </button>
      )}

      {importResult && (
        <div className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-400 mb-2">
            <Check size={16} />
            <span className="text-sm font-medium">Import Complete</span>
          </div>
          <div className="text-xs text-warroom-muted space-y-1">
            <div>Total rows: {importResult.total_rows}</div>
            <div>Successfully imported: {importResult.successful}</div>
            <div>Errors: {importResult.errors?.length || 0}</div>
          </div>
          {importResult.errors?.length > 0 && (
            <details className="mt-2">
              <summary className="text-xs text-warroom-muted cursor-pointer">View errors</summary>
              <div className="mt-2 text-xs text-red-400 space-y-1">
                {importResult.errors.map((error: string, i: number) => (
                  <div key={i}>{error}</div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );

  const renderExportTab = () => (
    <div className="space-y-6">
      <div>
        <label className="text-sm text-warroom-text block mb-2">Entity Type</label>
        <select
          value={selectedEntityType}
          onChange={(e) => setSelectedEntityType(e.target.value)}
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
        >
          {ENTITY_TYPES.map(type => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-sm text-warroom-text block mb-2">Format</label>
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
        >
          <option value="csv">CSV</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm text-warroom-text block mb-2">From Date</label>
          <input
            type="date"
            value={exportDateFrom}
            onChange={(e) => setExportDateFrom(e.target.value)}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="text-sm text-warroom-text block mb-2">To Date</label>
          <input
            type="date"
            value={exportDateTo}
            onChange={(e) => setExportDateTo(e.target.value)}
            className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      <button
        onClick={exportData}
        disabled={exporting}
        className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition"
      >
        <Download size={16} />
        {exporting ? 'Exporting...' : 'Export Data'}
      </button>
    </div>
  );

  const renderDedupeTab = () => (
    <div className="space-y-6">
      <div>
        <label className="text-sm text-warroom-text block mb-2">Entity Type</label>
        <select
          value={selectedEntityType}
          onChange={(e) => setSelectedEntityType(e.target.value)}
          className="w-full bg-warroom-bg border border-warroom-border rounded-lg px-3 py-2 text-sm"
        >
          {ENTITY_TYPES.map(type => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
      </div>

      <button
        onClick={findDuplicates}
        disabled={findingDuplicates}
        className="flex items-center gap-2 px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition"
      >
        <Search size={16} />
        {findingDuplicates ? 'Finding Duplicates...' : 'Find Duplicates'}
      </button>

      {duplicatePairs.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-warroom-text">
            Found {duplicatePairs.length} potential duplicate pairs
          </h4>
          {duplicatePairs.map((pair, index) => (
            <div key={index} className="bg-warroom-surface border border-warroom-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-warroom-muted">
                  {Math.round(pair.similarity * 100)}% similarity
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="bg-warroom-bg rounded p-3">
                  <div className="text-sm font-medium text-warroom-text mb-1">
                    {pair.entity1.name || pair.entity1.title}
                  </div>
                  <div className="text-xs text-warroom-muted space-y-1">
                    {Object.entries(pair.entity1).slice(1, 4).map(([key, value]) => (
                      <div key={key}>{key}: {String(value)}</div>
                    ))}
                  </div>
                </div>
                <div className="bg-warroom-bg rounded p-3">
                  <div className="text-sm font-medium text-warroom-text mb-1">
                    {pair.entity2.name || pair.entity2.title}
                  </div>
                  <div className="text-xs text-warroom-muted space-y-1">
                    {Object.entries(pair.entity2).slice(1, 4).map(([key, value]) => (
                      <div key={key}>{key}: {String(value)}</div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => mergeDuplicates(pair.id1, pair.id2, pair.id1)}
                  className="px-3 py-1 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded text-xs font-medium transition"
                >
                  Keep Left
                </button>
                <button
                  onClick={() => mergeDuplicates(pair.id1, pair.id2, pair.id2)}
                  className="px-3 py-1 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded text-xs font-medium transition"
                >
                  Keep Right
                </button>
                <button className="px-3 py-1 bg-warroom-bg hover:bg-warroom-surface border border-warroom-border rounded text-xs font-medium transition">
                  Skip
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {duplicatePairs.length === 0 && !findingDuplicates && (
        <div className="text-center py-12 text-warroom-muted">
          <Search size={32} className="mx-auto mb-4 opacity-50" />
          <p className="text-sm">No duplicate search performed yet</p>
          <p className="text-xs mt-1">Click "Find Duplicates" to scan for similar records</p>
        </div>
      )}
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 gap-3">
        <FileText size={18} className="text-warroom-accent" />
        <h2 className="text-sm font-semibold">Data Management</h2>
      </div>

      {/* Tabs */}
      <div className="border-b border-warroom-border bg-warroom-surface">
        <div className="flex">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition ${
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
        <div className="max-w-2xl mx-auto">
          {activeTab === 'import' && renderImportTab()}
          {activeTab === 'export' && renderExportTab()}
          {activeTab === 'dedupe' && renderDedupeTab()}
        </div>
      </div>
    </div>
  );
}