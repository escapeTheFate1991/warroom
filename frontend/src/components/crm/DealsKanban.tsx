"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Plus, Briefcase, DollarSign, Calendar, RefreshCw, Filter, User, Building2, Clock, AlertTriangle } from "lucide-react";
import DealDrawer from "./DealDrawer";
import DealForm from "./DealForm";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8300";

interface Pipeline {
  id: number;
  name: string;
  is_default: boolean;
  rotten_days: number;
}

interface PipelineStage {
  id: number;
  code: string;
  name: string;
  probability: number;
  sort_order: number;
  pipeline_id: number;
}

interface Deal {
  id: number;
  title: string;
  description: string | null;
  deal_value: number | null;
  status: boolean | null;
  expected_close_date: string | null;
  person_name: string | null;
  organization_name: string | null;
  stage_id: number;
  pipeline_id: number;
  created_at: string;
  updated_at: string;
  days_in_stage: number;
  is_rotten: boolean;
}

interface DealFull extends Deal {
  person_id: number | null;
  organization_id: number | null;
  source_id: number | null;
  type_id: number | null;
  user_id: number | null;
  lost_reason: string | null;
  closed_at: string | null;
}

const STAGE_COLORS: Record<number, string> = {
  0: "bg-gray-500/20 text-gray-400 border-gray-500/30", // 0% probability (lost)
  10: "bg-gray-500/20 text-gray-400 border-gray-500/30", // new
  20: "bg-blue-500/20 text-blue-400 border-blue-500/30", // contacted
  40: "bg-blue-600/20 text-blue-300 border-blue-600/30", // qualified
  60: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", // proposal
  80: "bg-orange-500/20 text-orange-400 border-orange-500/30", // negotiation
  100: "bg-green-500/20 text-green-400 border-green-500/30", // won
};

export default function DealsKanban() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [dealsByStage, setDealsByStage] = useState<Record<number, Deal[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedDeal, setSelectedDeal] = useState<DealFull | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingDeal, setEditingDeal] = useState<DealFull | null>(null);
  
  // Drag and drop state
  const [draggedDeal, setDraggedDeal] = useState<Deal | null>(null);
  const [dragOverStage, setDragOverStage] = useState<number | null>(null);
  const dragItemRef = useRef<HTMLDivElement>(null);

  // Load pipelines on mount
  useEffect(() => {
    loadPipelines();
  }, []);

  // Load stages and deals when pipeline changes
  useEffect(() => {
    if (selectedPipeline) {
      loadStagesAndDeals();
    }
  }, [selectedPipeline]);

  const loadPipelines = async () => {
    try {
      const response = await fetch(`${API}/api/crm/pipelines`);
      if (response.ok) {
        const data = await response.json();
        setPipelines(data);
        // Select default pipeline or first one
        const defaultPipeline = data.find((p: Pipeline) => p.is_default) || data[0];
        if (defaultPipeline) {
          setSelectedPipeline(defaultPipeline);
        }
      }
    } catch (error) {
      console.error("Failed to load pipelines:", error);
    }
  };

  const loadStagesAndDeals = async () => {
    if (!selectedPipeline) return;
    
    setLoading(true);
    try {
      // Load stages
      const stagesResponse = await fetch(`${API}/api/crm/pipelines/${selectedPipeline.id}/stages`);
      if (stagesResponse.ok) {
        const stagesData = await stagesResponse.json();
        setStages(stagesData);
        
        // Load deals for this pipeline
        const dealsResponse = await fetch(`${API}/api/crm/deals?pipeline_id=${selectedPipeline.id}`);
        if (dealsResponse.ok) {
          const dealsData = await dealsResponse.json();
          
          // Group deals by stage
          const grouped: Record<number, Deal[]> = {};
          stagesData.forEach((stage: PipelineStage) => {
            grouped[stage.id] = dealsData.filter((deal: Deal) => deal.stage_id === stage.id);
          });
          setDealsByStage(grouped);
        }
      }
    } catch (error) {
      console.error("Failed to load stages and deals:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDealClick = async (deal: Deal) => {
    try {
      // Fetch full deal data
      const response = await fetch(`${API}/api/crm/deals/${deal.id}`);
      if (response.ok) {
        const fullDeal: DealFull = await response.json();
        setSelectedDeal(fullDeal);
        setIsDrawerOpen(true);
      }
    } catch (error) {
      console.error("Failed to fetch deal details:", error);
    }
  };

  const handleNewDeal = () => {
    setEditingDeal(null);
    setIsFormOpen(true);
  };

  const handleEditDeal = (deal: DealFull) => {
    setEditingDeal(deal);
    setIsFormOpen(true);
  };

  const handleDealUpdate = (updatedDeal: DealFull) => {
    // Update deals in the kanban board
    setDealsByStage(prev => {
      const newDeals = { ...prev };
      
      // Remove from old stage if stage changed
      Object.keys(newDeals).forEach(stageId => {
        const numStageId = parseInt(stageId);
        newDeals[numStageId] = newDeals[numStageId].filter(d => d.id !== updatedDeal.id);
      });
      
      // Add to new stage
      if (newDeals[updatedDeal.stage_id]) {
        newDeals[updatedDeal.stage_id].push(updatedDeal);
      }
      
      return newDeals;
    });
    
    // Update selected deal if it's the same
    if (selectedDeal?.id === updatedDeal.id) {
      setSelectedDeal(updatedDeal);
    }
  };

  const handleDealCreate = (newDeal: DealFull) => {
    // Add to the appropriate stage
    setDealsByStage(prev => ({
      ...prev,
      [newDeal.stage_id]: [...(prev[newDeal.stage_id] || []), newDeal]
    }));
    setIsFormOpen(false);
  };

  // Drag and drop handlers
  const handleDragStart = (e: React.DragEvent, deal: Deal) => {
    setDraggedDeal(deal);
    e.dataTransfer.effectAllowed = 'move';
    
    // Set drag image
    if (dragItemRef.current) {
      e.dataTransfer.setDragImage(dragItemRef.current, 10, 10);
    }
  };

  const handleDragOver = (e: React.DragEvent, stageId: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverStage(stageId);
  };

  const handleDragLeave = () => {
    setDragOverStage(null);
  };

  const handleDrop = async (e: React.DragEvent, targetStageId: number) => {
    e.preventDefault();
    setDragOverStage(null);
    
    if (!draggedDeal || draggedDeal.stage_id === targetStageId) {
      setDraggedDeal(null);
      return;
    }

    try {
      // Update deal stage on server
      const response = await fetch(`${API}/api/crm/deals/${draggedDeal.id}/stage`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage_id: targetStageId })
      });

      if (response.ok) {
        // Update local state
        const updatedDeal = { ...draggedDeal, stage_id: targetStageId };
        
        setDealsByStage(prev => {
          const newDeals = { ...prev };
          
          // Remove from old stage
          newDeals[draggedDeal.stage_id] = newDeals[draggedDeal.stage_id].filter(
            d => d.id !== draggedDeal.id
          );
          
          // Add to new stage
          if (!newDeals[targetStageId]) {
            newDeals[targetStageId] = [];
          }
          newDeals[targetStageId].push(updatedDeal);
          
          return newDeals;
        });
      }
    } catch (error) {
      console.error("Failed to move deal:", error);
    } finally {
      setDraggedDeal(null);
    }
  };

  const getDealCardClass = (deal: Deal) => {
    let classes = "bg-warroom-surface border border-warroom-border rounded-lg p-3 cursor-pointer hover:bg-warroom-border/20 transition-colors mb-2";
    
    if (deal.is_rotten) {
      classes += " border-l-4 border-l-red-500";
    }
    
    return classes;
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

  const formatDaysInStage = (days: number) => {
    if (days === 0) return "Today";
    if (days === 1) return "1 day";
    return `${days} days`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw size={24} className="animate-spin text-warroom-muted" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-warroom-border flex items-center px-6 justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Briefcase size={16} />
            Deals
          </h2>
          
          {/* Pipeline Selector */}
          <select
            value={selectedPipeline?.id || ""}
            onChange={(e) => {
              const pipeline = pipelines.find(p => p.id === parseInt(e.target.value));
              setSelectedPipeline(pipeline || null);
            }}
            className="bg-warroom-surface border border-warroom-border rounded-lg px-3 py-1.5 text-sm text-warroom-text focus:outline-none focus:border-warroom-accent"
            style={{ colorScheme: "dark" }}
          >
            {pipelines.map((pipeline) => (
              <option key={pipeline.id} value={pipeline.id}>
                {pipeline.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadStagesAndDeals}
            className="text-warroom-muted hover:text-warroom-text transition p-2"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
          <button
            onClick={handleNewDeal}
            className="px-4 py-2 bg-warroom-accent hover:bg-warroom-accent/80 rounded-lg text-sm font-medium transition flex items-center gap-2"
          >
            <Plus size={16} />
            New Deal
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 p-6 overflow-x-auto">
        <div className="flex gap-6 h-full min-w-fit">
          {stages.map((stage) => {
            const stageDeals = dealsByStage[stage.id] || [];
            const stageValue = stageDeals.reduce((sum, deal) => sum + (deal.deal_value || 0), 0);
            const stageColor = STAGE_COLORS[stage.probability] || STAGE_COLORS[0];
            const isDragOver = dragOverStage === stage.id;

            return (
              <div
                key={stage.id}
                className={`flex-shrink-0 w-80 bg-warroom-surface border border-warroom-border rounded-lg ${
                  isDragOver ? "border-blue-500 bg-blue-500/5" : ""
                }`}
                onDragOver={(e) => handleDragOver(e, stage.id)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, stage.id)}
              >
                {/* Stage Header */}
                <div className="p-4 border-b border-warroom-border">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full border ${stageColor}`}>
                        {stage.probability}%
                      </span>
                      <h3 className="font-medium text-warroom-text">{stage.name}</h3>
                    </div>
                    <span className="text-xs text-warroom-muted">{stageDeals.length}</span>
                  </div>
                  <div className="text-xs text-warroom-muted">
                    {formatCurrency(stageValue)} total
                  </div>
                </div>

                {/* Deals List */}
                <div className="p-4 flex-1 overflow-y-auto">
                  {stageDeals.map((deal) => (
                    <div
                      key={deal.id}
                      className={getDealCardClass(deal)}
                      draggable
                      onDragStart={(e) => handleDragStart(e, deal)}
                      onClick={() => handleDealClick(deal)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-sm text-warroom-text line-clamp-2">
                          {deal.title}
                        </h4>
                        {deal.deal_value && (
                          <span className="text-xs font-medium text-green-400 ml-2 flex-shrink-0">
                            {formatCurrency(deal.deal_value)}
                          </span>
                        )}
                      </div>

                      {(deal.person_name || deal.organization_name) && (
                        <div className="flex items-center gap-1 text-xs text-warroom-muted mb-2">
                          {deal.person_name && (
                            <div className="flex items-center gap-1">
                              <User size={10} />
                              <span>{deal.person_name}</span>
                            </div>
                          )}
                          {deal.organization_name && (
                            <div className="flex items-center gap-1">
                              <Building2 size={10} />
                              <span>{deal.organization_name}</span>
                            </div>
                          )}
                        </div>
                      )}

                      <div className="flex items-center justify-between text-xs text-warroom-muted">
                        <div className="flex items-center gap-1">
                          <Clock size={10} />
                          <span>{formatDaysInStage(deal.days_in_stage)}</span>
                        </div>
                        
                        {deal.is_rotten && (
                          <div className="flex items-center gap-1 text-red-400">
                            <AlertTriangle size={10} />
                            <span>Rotten</span>
                          </div>
                        )}

                        {deal.expected_close_date && (
                          <div className="flex items-center gap-1">
                            <Calendar size={10} />
                            <span>{new Date(deal.expected_close_date).toLocaleDateString()}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {stageDeals.length === 0 && (
                    <div className="text-center py-8 text-warroom-muted">
                      <div className="text-xs">No deals in this stage</div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hidden drag image element */}
      <div
        ref={dragItemRef}
        className="fixed -top-10 -left-10 bg-warroom-surface border border-warroom-border rounded-lg p-2 text-xs pointer-events-none z-50"
        style={{ opacity: 0 }}
      >
        Moving deal...
      </div>

      {/* Deal Drawer */}
      <DealDrawer
        deal={selectedDeal}
        isOpen={isDrawerOpen}
        onClose={() => {
          setIsDrawerOpen(false);
          setSelectedDeal(null);
        }}
        onUpdate={handleDealUpdate}
        onEdit={handleEditDeal}
      />

      {/* Deal Form Modal */}
      <DealForm
        deal={editingDeal}
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setEditingDeal(null);
        }}
        onSave={editingDeal ? handleDealUpdate : handleDealCreate}
        pipelines={pipelines}
        stages={stages}
      />
    </div>
  );
}