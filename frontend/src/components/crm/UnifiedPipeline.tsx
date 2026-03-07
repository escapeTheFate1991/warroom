"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Briefcase, DollarSign, Calendar, User, AlertTriangle, Clock,
  ChevronRight, GripVertical, X, Loader2, ArrowRight, RefreshCw, Building2,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import LoadingState from "@/components/ui/LoadingState";
import EmptyState from "@/components/ui/EmptyState";
import StageGateModal from "./StageGateModal";
import DealDetailDrawer from "./DealDetailDrawer";
import { Pipeline, PipelineStage, Deal } from "./types";

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_PIPELINES: Pipeline[] = [{ id: 1, name: "Sales Pipeline", is_default: true, rotten_days: 30 }];

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_STAGES: PipelineStage[] = [
  { id: 1, code: "discovery", name: "Lead Discovery", probability: 10, sort_order: 0, pipeline_id: 1 },
  { id: 2, code: "contact", name: "Initial Contact", probability: 20, sort_order: 1, pipeline_id: 1 },
  { id: 3, code: "qualified", name: "Qualified", probability: 40, sort_order: 2, pipeline_id: 1 },
  { id: 4, code: "meeting", name: "Meeting / Demo", probability: 60, sort_order: 3, pipeline_id: 1 },
  { id: 5, code: "proposal", name: "Proposal Sent", probability: 80, sort_order: 4, pipeline_id: 1 },
  { id: 6, code: "negotiation", name: "Negotiation", probability: 90, sort_order: 5, pipeline_id: 1 },
  { id: 7, code: "closed", name: "Closed Won", probability: 100, sort_order: 6, pipeline_id: 1 },
];

// TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
const MOCK_DEALS: Deal[] = [
  { id: 1, title: "Acme Corp Website Redesign", description: null, deal_value: 15000, status: null, expected_close_date: "2026-04-15", person_name: "John Smith", organization_name: "Acme Corp", stage_id: 1, pipeline_id: 1, created_at: "2026-02-20", updated_at: "2026-03-01", days_in_stage: 14, is_rotten: false },
  { id: 2, title: "TechStart SaaS Integration", description: null, deal_value: 8500, status: null, expected_close_date: "2026-03-30", person_name: "Sarah Chen", organization_name: "TechStart Inc", stage_id: 2, pipeline_id: 1, created_at: "2026-02-15", updated_at: "2026-03-03", days_in_stage: 7, is_rotten: false },
  { id: 3, title: "BlueSky Marketing Retainer", description: null, deal_value: 4500, status: null, expected_close_date: "2026-03-20", person_name: "Mike Johnson", organization_name: "BlueSky Media", stage_id: 3, pipeline_id: 1, created_at: "2026-01-10", updated_at: "2026-02-28", days_in_stage: 21, is_rotten: false },
  { id: 4, title: "GreenLeaf E-commerce Build", description: null, deal_value: 22000, status: null, expected_close_date: "2026-05-01", person_name: "Lisa Park", organization_name: "GreenLeaf Organics", stage_id: 3, pipeline_id: 1, created_at: "2026-02-01", updated_at: "2026-03-05", days_in_stage: 5, is_rotten: false },
  { id: 5, title: "Nova Finance Dashboard", description: null, deal_value: 35000, status: null, expected_close_date: "2026-04-10", person_name: "David Wilson", organization_name: "Nova Financial", stage_id: 4, pipeline_id: 1, created_at: "2026-01-15", updated_at: "2026-03-02", days_in_stage: 10, is_rotten: false },
  { id: 6, title: "Meridian Brand Strategy", description: null, deal_value: 12000, status: null, expected_close_date: "2026-03-25", person_name: "Emma Davis", organization_name: "Meridian Group", stage_id: 5, pipeline_id: 1, created_at: "2026-01-05", updated_at: "2026-03-04", days_in_stage: 3, is_rotten: false },
  { id: 7, title: "Apex Consulting Portal", description: null, deal_value: 18500, status: null, expected_close_date: "2026-03-15", person_name: "Tom Brown", organization_name: "Apex Consulting", stage_id: 6, pipeline_id: 1, created_at: "2025-12-20", updated_at: "2026-03-06", days_in_stage: 15, is_rotten: true },
  { id: 8, title: "Stellar App Redesign", description: null, deal_value: 9800, status: null, expected_close_date: "2026-04-20", person_name: "Amy Taylor", organization_name: "Stellar Apps", stage_id: 1, pipeline_id: 1, created_at: "2026-03-01", updated_at: "2026-03-06", days_in_stage: 5, is_rotten: false },
];

const STAGE_COLORS: Record<number, string> = {
  0: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  10: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  20: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  40: "bg-blue-600/20 text-blue-300 border-blue-600/30",
  60: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  80: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  100: "bg-green-500/20 text-green-400 border-green-500/30",
};

const COLUMN_BORDER: Record<number, string> = {
  0: "border-t-gray-500",
  10: "border-t-gray-400",
  20: "border-t-blue-500",
  40: "border-t-blue-400",
  60: "border-t-yellow-500",
  80: "border-t-orange-500",
  100: "border-t-green-500",
};

type QuarterFilter = "all" | "Q1" | "Q2" | "Q3" | "Q4" | "custom";

export default function UnifiedPipeline() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [dealsByStage, setDealsByStage] = useState<Record<number, Deal[]>>({});
  const [loading, setLoading] = useState(true);

  // Quarter filter state
  const [quarterFilter, setQuarterFilter] = useState<QuarterFilter>("all");
  const [customDateRange, setCustomDateRange] = useState<{ start: string; end: string }>({ start: "", end: "" });

  // Drag state
  const [draggedDeal, setDraggedDeal] = useState<Deal | null>(null);
  const [dragOverStage, setDragOverStage] = useState<number | null>(null);

  // Gate modal state
  const [gateModal, setGateModal] = useState<{
    deal: Deal; fromStage: PipelineStage; toStage: PipelineStage;
  } | null>(null);

  // Demote confirm
  const [demoteConfirm, setDemoteConfirm] = useState<{
    deal: Deal; toStage: PipelineStage;
  } | null>(null);

  // Deal detail drawer
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);

  // Toast
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => { loadPipelines(); }, []);
  useEffect(() => { if (selectedPipeline) loadStagesAndDeals(); }, [selectedPipeline]);

  const loadPipelines = async () => {
    try {
      const res = await authFetch(`${API}/api/crm/pipelines`);
      if (res.ok) {
        const data = await res.json();
        setPipelines(data);
        const def = data.find((p: Pipeline) => p.is_default) || data[0];
        if (def) setSelectedPipeline(def);
      } else {
        // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
        console.error("Failed to load pipelines:", res.status);
        setPipelines(MOCK_PIPELINES);
        setSelectedPipeline(MOCK_PIPELINES[0]);
      }
    } catch (e) {
      // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
      console.error("Failed to load pipelines:", e);
      setPipelines(MOCK_PIPELINES);
      setSelectedPipeline(MOCK_PIPELINES[0]);
    }
  };

  const loadStagesAndDeals = async () => {
    if (!selectedPipeline) return;
    setLoading(true);
    try {
      const [stagesRes, dealsRes] = await Promise.all([
        authFetch(`${API}/api/crm/pipelines/${selectedPipeline.id}/stages`),
        authFetch(`${API}/api/crm/deals?pipeline_id=${selectedPipeline.id}`),
      ]);
      if (stagesRes.ok && dealsRes.ok) {
        const stagesData: PipelineStage[] = await stagesRes.json();
        const dealsData: Deal[] = await dealsRes.json();
        setStages(stagesData);
        const grouped: Record<number, Deal[]> = {};
        stagesData.forEach((s) => { grouped[s.id] = dealsData.filter((d) => d.stage_id === s.id); });
        setDealsByStage(grouped);
      } else {
        // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
        console.error("Failed to load stages/deals:", stagesRes.status, dealsRes.status);
        setStages(MOCK_STAGES);
        const grouped: Record<number, Deal[]> = {};
        MOCK_STAGES.forEach((s) => { grouped[s.id] = MOCK_DEALS.filter((d) => d.stage_id === s.id); });
        setDealsByStage(grouped);
      }
    } catch (e) {
      // TEMP: Mock data for UI preview - REMOVE BEFORE COMMIT
      console.error(e);
      setStages(MOCK_STAGES);
      const grouped: Record<number, Deal[]> = {};
      MOCK_STAGES.forEach((s) => { grouped[s.id] = MOCK_DEALS.filter((d) => d.stage_id === s.id); });
      setDealsByStage(grouped);
    } finally { setLoading(false); }
  };

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000); };

  const findStage = (stageId: number) => stages.find((s) => s.id === stageId);

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, deal: Deal) => {
    setDraggedDeal(deal);
    e.dataTransfer.effectAllowed = "move";
  };
  const handleDragOver = (e: React.DragEvent, stageId: number) => {
    e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverStage(stageId);
  };
  const handleDragLeave = () => setDragOverStage(null);

  const handleDrop = (e: React.DragEvent, targetStageId: number) => {
    e.preventDefault(); setDragOverStage(null);
    if (!draggedDeal || draggedDeal.stage_id === targetStageId) { setDraggedDeal(null); return; }

    const fromStage = findStage(draggedDeal.stage_id);
    const toStage = findStage(targetStageId);
    if (!fromStage || !toStage) { setDraggedDeal(null); return; }

    // Moving to Lost — always allowed via gate
    if (toStage.probability === 0) {
      setGateModal({ deal: draggedDeal, fromStage, toStage });
      setDraggedDeal(null);
      return;
    }

    // Forward move
    if (toStage.sort_order > fromStage.sort_order) {
      if (toStage.sort_order !== fromStage.sort_order + 1) {
        showToast("Can only advance one stage at a time");
        setDraggedDeal(null); return;
      }
      setGateModal({ deal: draggedDeal, fromStage, toStage });
    } else {
      // Backward — demote confirm
      setDemoteConfirm({ deal: draggedDeal, toStage });
    }
    setDraggedDeal(null);
  };

  // Advance via API
  const handleAdvance = async (data: Record<string, unknown>) => {
    if (!gateModal) return;
    const res = await authFetch(`${API}/api/crm/deals/${gateModal.deal.id}/advance`, {
      method: "PUT", body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to advance deal");
    }
    setGateModal(null);
    await loadStagesAndDeals();
  };

  // Demote via existing stage move API
  const handleDemote = async () => {
    if (!demoteConfirm) return;
    const res = await authFetch(`${API}/api/crm/deals/${demoteConfirm.deal.id}/stage`, {
      method: "PUT", body: JSON.stringify({ stage_id: demoteConfirm.toStage.id }),
    });
    if (res.ok) await loadStagesAndDeals();
    setDemoteConfirm(null);
  };

  // Quarter filter logic
  const currentYear = new Date().getFullYear();
  const QUARTER_RANGES: Record<string, [string, string]> = {
    Q1: [`${currentYear}-01-01`, `${currentYear}-03-31`],
    Q2: [`${currentYear}-04-01`, `${currentYear}-06-30`],
    Q3: [`${currentYear}-07-01`, `${currentYear}-09-30`],
    Q4: [`${currentYear}-10-01`, `${currentYear}-12-31`],
  };

  const filterDealsByQuarter = (deals: Deal[]) => {
    if (quarterFilter === "all") return deals;
    if (quarterFilter === "custom") {
      if (!customDateRange.start || !customDateRange.end) return deals;
      return deals.filter(d => d.expected_close_date && d.expected_close_date >= customDateRange.start && d.expected_close_date <= customDateRange.end);
    }
    const [start, end] = QUARTER_RANGES[quarterFilter];
    return deals.filter(d => d.expected_close_date && d.expected_close_date >= start && d.expected_close_date <= end);
  };

  const fmt = (n: number | null) => {
    if (!n) return "$0";
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
  };

  if (loading) return <LoadingState message="Loading pipeline…" />;
  if (!stages.length) return <EmptyState icon={<Briefcase className="w-10 h-10" />} title="No pipeline stages" description="Set up a sales pipeline first." />;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-warroom-border flex items-center px-6 py-2 justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-4">
          <h2 className="text-sm font-semibold flex items-center gap-2"><Briefcase size={16} /> Pipeline Board</h2>
          <select value={selectedPipeline?.id || ""} onChange={(e) => { const p = pipelines.find((pp) => pp.id === parseInt(e.target.value)); setSelectedPipeline(p || null); }}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }}>
            {pipelines.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            {(["all", "Q1", "Q2", "Q3", "Q4", "custom"] as QuarterFilter[]).map((q) => (
              <button key={q} onClick={() => setQuarterFilter(q)}
                className={`px-2.5 py-1 text-xs rounded-full border transition ${quarterFilter === q ? "bg-warroom-accent text-white border-warroom-accent" : "bg-warroom-surface border-warroom-border text-warroom-muted hover:text-warroom-text"}`}>
                {q === "all" ? "All" : q === "custom" ? (
                  <span className="flex items-center gap-1"><Calendar size={10} />Custom</span>
                ) : `${q} ${currentYear}`}
              </button>
            ))}
          </div>
          {quarterFilter === "custom" && (
            <div className="flex items-center gap-1.5">
              <input type="date" value={customDateRange.start} onChange={(e) => setCustomDateRange(prev => ({ ...prev, start: e.target.value }))}
                className="bg-warroom-surface border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }} />
              <span className="text-xs text-warroom-muted">to</span>
              <input type="date" value={customDateRange.end} onChange={(e) => setCustomDateRange(prev => ({ ...prev, end: e.target.value }))}
                className="bg-warroom-surface border border-warroom-border rounded px-2 py-1 text-xs text-warroom-text focus:outline-none focus:border-warroom-accent" style={{ colorScheme: "dark" }} />
            </div>
          )}
          <button onClick={loadStagesAndDeals} className="text-warroom-muted hover:text-warroom-text transition p-2" title="Refresh"><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 p-4 overflow-x-auto">
        <div className="flex gap-4 h-full min-w-fit">
          {stages.map((stage) => {
            const stageDeals = filterDealsByQuarter(dealsByStage[stage.id] || []);
            const stageValue = stageDeals.reduce((s, d) => s + (d.deal_value || 0), 0);
            const color = STAGE_COLORS[stage.probability] || STAGE_COLORS[0];
            const borderColor = COLUMN_BORDER[stage.probability] || "border-t-gray-500";
            const isDragOver = dragOverStage === stage.id;

            return (
              <div key={stage.id}
                className={`flex-shrink-0 w-72 bg-warroom-surface border border-warroom-border rounded-lg border-t-2 ${borderColor} flex flex-col ${isDragOver ? "ring-2 ring-warroom-accent/50 bg-warroom-accent/5" : ""}`}
                onDragOver={(e) => handleDragOver(e, stage.id)} onDragLeave={handleDragLeave} onDrop={(e) => handleDrop(e, stage.id)}>
                {/* Stage Header */}
                <div className="p-3 border-b border-warroom-border">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full border ${color}`}>{stage.probability}%</span>
                      <h3 className="text-sm font-medium text-warroom-text">{stage.name}</h3>
                    </div>
                    <span className="text-xs bg-warroom-bg px-1.5 py-0.5 rounded text-warroom-muted">{stageDeals.length}</span>
                  </div>
                  <div className="text-xs text-warroom-muted">{fmt(stageValue)} total</div>
                </div>

                {/* Deals */}
                <div className="flex-1 p-2 overflow-y-auto space-y-2">
                  {stageDeals.map((deal) => (
                    <div key={deal.id} draggable onDragStart={(e) => handleDragStart(e, deal)}
                      onClick={() => setSelectedDeal(deal)}
                      className={`bg-warroom-bg border border-warroom-border rounded-lg p-3 cursor-grab hover:bg-warroom-border/20 transition-colors ${deal.is_rotten ? "border-l-4 border-l-red-500" : ""}`}>
                      <div className="flex items-start justify-between mb-1.5">
                        <h4 className="font-medium text-xs text-warroom-text line-clamp-2">{deal.title}</h4>
                        {deal.deal_value != null && <span className="text-[10px] font-medium text-green-400 ml-1 flex-shrink-0">{fmt(deal.deal_value)}</span>}
                      </div>
                      {(deal.person_name || deal.organization_name) && (
                        <div className="flex items-center gap-2 text-[10px] text-warroom-muted mb-1.5">
                          {deal.organization_name && <span className="flex items-center gap-0.5"><Building2 size={9} />{deal.organization_name}</span>}
                          {deal.person_name && <span className="flex items-center gap-0.5"><User size={9} />{deal.person_name}</span>}
                        </div>
                      )}
                      <div className="flex items-center justify-between text-[10px] text-warroom-muted">
                        <span className="flex items-center gap-0.5"><Clock size={9} />{deal.days_in_stage === 0 ? "Today" : `${deal.days_in_stage}d`}</span>
                        {deal.is_rotten && <span className="flex items-center gap-0.5 text-red-400"><AlertTriangle size={9} />Rotten</span>}
                        {deal.expected_close_date && <span className="flex items-center gap-0.5"><Calendar size={9} />{new Date(deal.expected_close_date).toLocaleDateString()}</span>}
                      </div>
                    </div>
                  ))}
                  {stageDeals.length === 0 && <div className="text-center py-6 text-warroom-muted text-xs">No deals</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Stage Gate Modal */}
      {gateModal && (
        <StageGateModal isOpen onClose={() => setGateModal(null)} deal={gateModal.deal}
          fromStage={gateModal.fromStage} toStage={gateModal.toStage} onAdvance={handleAdvance} />
      )}

      {/* Demote Confirmation */}
      {demoteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-warroom-surface border border-warroom-border rounded-xl p-6 w-full max-w-sm mx-4">
            <h3 className="text-base font-semibold text-warroom-text mb-2">Demote Deal?</h3>
            <p className="text-sm text-warroom-muted mb-4">Move <span className="text-warroom-text font-medium">{demoteConfirm.deal.title}</span> back to <span className="text-warroom-accent">{demoteConfirm.toStage.name}</span>?</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDemoteConfirm(null)} className="px-4 py-2 text-sm text-warroom-muted hover:text-warroom-text transition">Cancel</button>
              <button onClick={handleDemote} className="px-4 py-2 bg-yellow-600 hover:bg-yellow-600/80 rounded-lg text-sm font-medium transition">Demote</button>
            </div>
          </div>
        </div>
      )}

      {/* Deal Detail Drawer */}
      {selectedDeal && (
        <DealDetailDrawer
          deal={selectedDeal}
          stages={stages}
          onClose={() => setSelectedDeal(null)}
          onAdvance={(deal, fromStage, toStage) => {
            setSelectedDeal(null);
            setGateModal({ deal, fromStage, toStage });
          }}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-red-500/90 text-white px-4 py-2 rounded-lg text-sm shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

