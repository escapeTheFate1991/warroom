"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Circle,
  Clock3,
  DollarSign,
  ExternalLink,
  FileText,
  Loader2,
  Mail,
  MessageSquare,
  Paperclip,
  Phone,
  Save,
  Target,
  User,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import EmptyState from "@/components/ui/EmptyState";
import LoadingState from "@/components/ui/LoadingState";
import { Activity, DealFull, Email, PipelineStage } from "./types";
import ScrollTabs from "@/components/ui/ScrollTabs";

type DealTab = "activity" | "emails" | "comments" | "calls" | "tasks" | "notes" | "attachments";

type ContactValue = { value?: string; label?: string };

type PersonRecord = {
  id: number;
  name: string;
  emails?: ContactValue[];
  contact_numbers?: ContactValue[] | null;
  job_title?: string | null;
  organization_id?: number | null;
};

type OrganizationAddress = {
  website?: string;
  street?: string;
  city?: string;
  state?: string;
  country?: string;
};

type OrganizationRecord = {
  id: number;
  name: string;
  address?: OrganizationAddress | null;
};

type DealActivity = Activity & {
  additional?: Record<string, unknown> | null;
  location?: string | null;
  updated_at?: string;
};

type SmsMessage = {
  id: number;
  telnyx_message_id?: string | null;
  direction?: string | null;
  from_number?: string | null;
  to_number?: string | null;
  body?: string | null;
  status?: string | null;
  deal_id?: number | null;
  person_id?: number | null;
  created_at: string;
};

type ToastState = {
  type: "success" | "error";
  message: string;
};

type ActivityFormState = {
  type: string;
  title: string;
  comment: string;
  schedule_from: string;
  schedule_to: string;
};

const STAGE_COLORS: Record<number, string> = {
  0: "bg-red-500/15 text-red-400 border-red-500/20",
  10: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  20: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  40: "bg-blue-600/20 text-blue-300 border-blue-600/30",
  60: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  80: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  100: "bg-green-500/20 text-green-400 border-green-500/30",
};

const ACTIVITY_TYPES = [
  { value: "call", label: "Call" },
  { value: "meeting", label: "Meeting" },
  { value: "email", label: "Email" },
  { value: "note", label: "Note" },
  { value: "task", label: "Task" },
] as const;

const TABS: { id: DealTab; label: string }[] = [
  { id: "activity", label: "Activity" },
  { id: "emails", label: "Emails" },
  { id: "comments", label: "Comments" },
  { id: "calls", label: "Calls" },
  { id: "tasks", label: "Tasks" },
  { id: "notes", label: "Notes" },
  { id: "attachments", label: "Attachments" },
];

const ACTIVITY_ICONS: Record<string, LucideIcon> = {
  call: Phone,
  meeting: User,
  email: Mail,
  note: FileText,
  task: CheckCircle2,
  sms: MessageSquare,
};

const sectionClassName = "rounded-xl border border-warroom-border bg-warroom-surface";
const inputClassName = "w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:border-warroom-accent/60 focus:outline-none";

function normalizeAddress(address: unknown): OrganizationAddress {
  if (!address || typeof address !== "object" || Array.isArray(address)) {
    return {};
  }
  return address as OrganizationAddress;
}

function formatCurrency(amount: number | null | undefined) {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "$0";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value: string | null | undefined, includeTime = false) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return includeTime ? parsed.toLocaleString() : parsed.toLocaleDateString();
}

function getPrimaryValue(values?: ContactValue[] | null) {
  if (!Array.isArray(values) || values.length === 0) return "—";
  return values.find((item) => item?.value?.trim())?.value?.trim() || "—";
}

function getWebsiteHref(website?: string) {
  if (!website) return null;
  return /^https?:\/\//i.test(website) ? website : `https://${website}`;
}

function getStatusMeta(status: boolean | null | undefined) {
  if (status === true) return { label: "Won", className: "bg-green-500/15 text-green-400 border-green-500/20" };
  if (status === false) return { label: "Lost", className: "bg-red-500/15 text-red-400 border-red-500/20" };
  return { label: "Open", className: "bg-blue-500/15 text-blue-400 border-blue-500/20" };
}

function parseCurrencyInput(value: string) {
  const normalized = value.replace(/[^0-9.-]/g, "").trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function toIsoString(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function getOccurredAt(activity: DealActivity) {
  return activity.schedule_from || activity.schedule_to || activity.created_at;
}

function getAdditionalString(activity: DealActivity, ...keys: string[]) {
  const additional = activity.additional;
  if (!additional || typeof additional !== "object") return null;
  for (const key of keys) {
    const value = additional[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return null;
}

function formatFromAddress(value: Email["from_addr"]) {
  if (!value) return "Unknown sender";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    const name = "name" in value && typeof value.name === "string" ? value.name : "";
    const email = "email" in value && typeof value.email === "string"
      ? value.email
      : "address" in value && typeof value.address === "string"
        ? value.address
        : "";
    return [name, email].filter(Boolean).join(" • ") || "Unknown sender";
  }
  return "Unknown sender";
}

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object" && "detail" in data && typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    // ignore parse failure
  }
  return fallback;
}

async function fetchOptionalJson<T>(url: string): Promise<T | null> {
  try {
    const response = await authFetch(url);
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export default function DealPage({ dealId, onBack }: { dealId: number; onBack: () => void }) {
  const [activeTab, setActiveTab] = useState<DealTab>("activity");
  const [deal, setDeal] = useState<DealFull | null>(null);
  const [person, setPerson] = useState<PersonRecord | null>(null);
  const [organization, setOrganization] = useState<OrganizationRecord | null>(null);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [activities, setActivities] = useState<DealActivity[]>([]);
  const [emails, setEmails] = useState<Email[]>([]);
  const [smsMessages, setSmsMessages] = useState<SmsMessage[]>([]);
  const [loadingDeal, setLoadingDeal] = useState(true);
  const [loadingActivities, setLoadingActivities] = useState(true);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [loadingSms, setLoadingSms] = useState(false);
  const [emailsLoaded, setEmailsLoaded] = useState(false);
  const [smsLoaded, setSmsLoaded] = useState(false);
  const [error, setError] = useState("");
  const [activityError, setActivityError] = useState("");
  const [emailError, setEmailError] = useState("");
  const [smsError, setSmsError] = useState("");
  const [showDetails, setShowDetails] = useState(true);
  const [savingDescription, setSavingDescription] = useState(false);
  const [savingForecast, setSavingForecast] = useState(false);
  const [movingStage, setMovingStage] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState<null | "won" | "lost">(null);
  const [creatingActivity, setCreatingActivity] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<number | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [descriptionDraft, setDescriptionDraft] = useState("");
  const [expectedCloseDateDraft, setExpectedCloseDateDraft] = useState("");
  const [dealValueDraft, setDealValueDraft] = useState("");
  const [activityForm, setActivityForm] = useState<ActivityFormState>({
    type: "note",
    title: "",
    comment: "",
    schedule_from: "",
    schedule_to: "",
  });

  const showToast = useCallback((type: ToastState["type"], message: string) => {
    setToast({ type, message });
    window.setTimeout(() => {
      setToast((current) => (current?.message === message ? null : current));
    }, 3000);
  }, []);

  const loadDealBundle = useCallback(async (silent = false) => {
    if (!silent) setLoadingDeal(true);
    setError("");

    try {
      const dealResponse = await authFetch(`${API}/api/crm/deals/${dealId}`);
      if (!dealResponse.ok) {
        throw new Error(await getErrorMessage(dealResponse, `Failed to load deal (${dealResponse.status})`));
      }

      const dealData = (await dealResponse.json()) as DealFull;
      setDeal(dealData);
      setDescriptionDraft(dealData.description || "");
      setExpectedCloseDateDraft(dealData.expected_close_date || "");
      setDealValueDraft(dealData.deal_value === null || dealData.deal_value === undefined ? "" : String(dealData.deal_value));

      const [personData, organizationData, stageData] = await Promise.all([
        dealData.person_id ? fetchOptionalJson<PersonRecord>(`${API}/api/crm/persons/${dealData.person_id}`) : Promise.resolve(null),
        dealData.organization_id ? fetchOptionalJson<OrganizationRecord>(`${API}/api/crm/organizations/${dealData.organization_id}`) : Promise.resolve(null),
        dealData.pipeline_id ? fetchOptionalJson<PipelineStage[]>(`${API}/api/crm/pipelines/${dealData.pipeline_id}/stages`) : Promise.resolve(null),
      ]);

      setPerson(personData);
      setOrganization(organizationData);
      setStages((stageData || []).slice().sort((left, right) => left.sort_order - right.sort_order));
    } catch (loadError) {
      console.error("Failed to load deal:", loadError);
      setError(loadError instanceof Error ? loadError.message : "Failed to load deal.");
      setDeal(null);
      setPerson(null);
      setOrganization(null);
      setStages([]);
    } finally {
      if (!silent) setLoadingDeal(false);
    }
  }, [dealId]);

  const loadActivities = useCallback(async (silent = false) => {
    if (!silent) setLoadingActivities(true);
    setActivityError("");
    try {
      const response = await authFetch(`${API}/api/crm/activities?deal_id=${dealId}`);
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, `Failed to load activities (${response.status})`));
      }
      const data = (await response.json()) as DealActivity[];
      setActivities(Array.isArray(data) ? data : []);
    } catch (loadError) {
      console.error("Failed to load activities:", loadError);
      setActivityError(loadError instanceof Error ? loadError.message : "Failed to load activities.");
      setActivities([]);
    } finally {
      if (!silent) setLoadingActivities(false);
    }
  }, [dealId]);

  const loadEmails = useCallback(async () => {
    setLoadingEmails(true);
    setEmailError("");
    try {
      const response = await authFetch(`${API}/api/crm/emails?deal_id=${dealId}`);
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, `Failed to load emails (${response.status})`));
      }
      const data = (await response.json()) as Email[];
      setEmails(Array.isArray(data) ? data : []);
    } catch (loadError) {
      console.error("Failed to load emails:", loadError);
      setEmailError(loadError instanceof Error ? loadError.message : "Failed to load emails.");
      setEmails([]);
    } finally {
      setEmailsLoaded(true);
      setLoadingEmails(false);
    }
  }, [dealId]);

  const loadSmsMessages = useCallback(async () => {
    setLoadingSms(true);
    setSmsError("");
    try {
      const response = await authFetch(`${API}/api/telnyx/sms-messages?deal_id=${dealId}`);
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, `Failed to load messages (${response.status})`));
      }
      const data = (await response.json()) as SmsMessage[];
      setSmsMessages(Array.isArray(data) ? data : []);
    } catch (loadError) {
      console.error("Failed to load SMS messages:", loadError);
      setSmsError(loadError instanceof Error ? loadError.message : "Failed to load SMS messages.");
      setSmsMessages([]);
    } finally {
      setSmsLoaded(true);
      setLoadingSms(false);
    }
  }, [dealId]);

  useEffect(() => {
    void loadDealBundle();
    void loadActivities();
  }, [loadDealBundle, loadActivities]);

  useEffect(() => {
    if (activeTab === "emails" && !emailsLoaded && !loadingEmails) {
      void loadEmails();
    }
    if (activeTab === "calls" && !smsLoaded && !loadingSms) {
      void loadSmsMessages();
    }
  }, [activeTab, emailsLoaded, loadEmails, loadSmsMessages, loadingEmails, loadingSms, smsLoaded]);

  const currentStage = useMemo(
    () => stages.find((stage) => stage.id === deal?.stage_id) || null,
    [deal?.stage_id, stages],
  );
  const currentStageIndex = useMemo(
    () => stages.findIndex((stage) => stage.id === deal?.stage_id),
    [deal?.stage_id, stages],
  );
  const nextStage = currentStageIndex >= 0 && currentStageIndex < stages.length - 1 ? stages[currentStageIndex + 1] : null;
  const probability = currentStage?.probability ?? 0;
  const stageColor = STAGE_COLORS[probability] || STAGE_COLORS[0];
  const statusMeta = getStatusMeta(deal?.status);
  const weightedValue = ((parseCurrencyInput(dealValueDraft) || 0) * probability) / 100;
  const address = normalizeAddress(organization?.address);
  const websiteHref = getWebsiteHref(address.website);
  const contactName = person?.name || deal?.person_name || "No contact linked";
  const organizationName = organization?.name || deal?.organization_name || "—";
  const commentsDirty = descriptionDraft !== (deal?.description || "");
  const forecastDirty = expectedCloseDateDraft !== (deal?.expected_close_date || "") || parseCurrencyInput(dealValueDraft) !== (deal?.deal_value ?? null);
  const taskActivities = useMemo(() => activities.filter((activity) => activity.type === "task"), [activities]);
  const callActivities = useMemo(() => activities.filter((activity) => activity.type === "call"), [activities]);
  const communications = useMemo(() => {
    const callItems = callActivities.map((activity) => ({
      id: `call-${activity.id}`,
      kind: "call" as const,
      occurredAt: getOccurredAt(activity),
      activity,
    }));
    const smsItems = smsMessages.map((message) => ({
      id: `sms-${message.id}`,
      kind: "sms" as const,
      occurredAt: message.created_at,
      message,
    }));

    return [...callItems, ...smsItems].sort(
      (left, right) => new Date(right.occurredAt).getTime() - new Date(left.occurredAt).getTime(),
    );
  }, [callActivities, smsMessages]);

  const handleMoveStage = useCallback(async (stageId: number) => {
    if (!deal || stageId === deal.stage_id) return;
    setMovingStage(true);
    try {
      const response = await authFetch(`${API}/api/crm/deals/${deal.id}/stage`, {
        method: "PUT",
        body: JSON.stringify({ stage_id: stageId }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to update deal stage."));
      }
      await loadDealBundle(true);
      showToast("success", "Deal stage updated.");
    } catch (moveError) {
      console.error("Failed to update stage:", moveError);
      showToast("error", moveError instanceof Error ? moveError.message : "Failed to update deal stage.");
    } finally {
      setMovingStage(false);
    }
  }, [deal, loadDealBundle, showToast]);

  const handleSetStatus = useCallback(async (status: boolean) => {
    if (!deal) return;
    setUpdatingStatus(status ? "won" : "lost");
    try {
      const response = await authFetch(`${API}/api/crm/deals/${deal.id}`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to update deal status."));
      }
      await loadDealBundle(true);
      showToast("success", status ? "Deal marked as won." : "Deal marked as lost.");
    } catch (statusError) {
      console.error("Failed to update status:", statusError);
      showToast("error", statusError instanceof Error ? statusError.message : "Failed to update deal status.");
    } finally {
      setUpdatingStatus(null);
    }
  }, [deal, loadDealBundle, showToast]);

  const saveDescription = useCallback(async () => {
    if (!deal || !commentsDirty) return;
    setSavingDescription(true);
    try {
      const response = await authFetch(`${API}/api/crm/deals/${deal.id}`, {
        method: "PUT",
        body: JSON.stringify({ description: descriptionDraft.trim() || null }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to save notes."));
      }
      await loadDealBundle(true);
      showToast("success", "Deal notes saved.");
    } catch (saveError) {
      console.error("Failed to save description:", saveError);
      showToast("error", saveError instanceof Error ? saveError.message : "Failed to save notes.");
    } finally {
      setSavingDescription(false);
    }
  }, [commentsDirty, deal, descriptionDraft, loadDealBundle, showToast]);

  const saveForecast = useCallback(async () => {
    if (!deal || !forecastDirty) return;
    setSavingForecast(true);
    try {
      const response = await authFetch(`${API}/api/crm/deals/${deal.id}`, {
        method: "PUT",
        body: JSON.stringify({
          expected_close_date: expectedCloseDateDraft || null,
          deal_value: parseCurrencyInput(dealValueDraft),
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to update forecast details."));
      }
      await loadDealBundle(true);
      showToast("success", "Forecast details updated.");
    } catch (saveError) {
      console.error("Failed to save forecast:", saveError);
      showToast("error", saveError instanceof Error ? saveError.message : "Failed to update forecast details.");
    } finally {
      setSavingForecast(false);
    }
  }, [deal, dealValueDraft, expectedCloseDateDraft, forecastDirty, loadDealBundle, showToast]);

  const handleAddActivity = useCallback(async () => {
    if (!activityForm.title.trim()) return;
    setCreatingActivity(true);
    try {
      const createResponse = await authFetch(`${API}/api/crm/activities`, {
        method: "POST",
        body: JSON.stringify({
          type: activityForm.type,
          title: activityForm.title.trim(),
          comment: activityForm.comment.trim() || null,
          schedule_from: toIsoString(activityForm.schedule_from),
          schedule_to: toIsoString(activityForm.schedule_to),
        }),
      });
      if (!createResponse.ok) {
        throw new Error(await getErrorMessage(createResponse, "Failed to create activity."));
      }

      const createdActivity = (await createResponse.json()) as DealActivity;
      const linkResponse = await authFetch(`${API}/api/crm/deals/${dealId}/activities`, {
        method: "POST",
        body: JSON.stringify({ activity_id: createdActivity.id }),
      });
      if (!linkResponse.ok) {
        throw new Error(await getErrorMessage(linkResponse, "Activity created, but linking it to the deal failed."));
      }

      setActivityForm({ type: "note", title: "", comment: "", schedule_from: "", schedule_to: "" });
      await loadActivities();
      showToast("success", "Activity added to deal.");
    } catch (createError) {
      console.error("Failed to add activity:", createError);
      showToast("error", createError instanceof Error ? createError.message : "Failed to add activity.");
    } finally {
      setCreatingActivity(false);
    }
  }, [activityForm, dealId, loadActivities, showToast]);

  const handleToggleTask = useCallback(async (activity: DealActivity) => {
    setUpdatingTaskId(activity.id);
    try {
      const response = activity.is_done
        ? await authFetch(`${API}/api/crm/activities/${activity.id}`, {
            method: "PUT",
            body: JSON.stringify({ is_done: false }),
          })
        : await authFetch(`${API}/api/crm/activities/${activity.id}/done`, { method: "PUT" });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to update task status."));
      }

      await loadActivities(true);
    } catch (taskError) {
      console.error("Failed to update task:", taskError);
      showToast("error", taskError instanceof Error ? taskError.message : "Failed to update task status.");
    } finally {
      setUpdatingTaskId(null);
    }
  }, [loadActivities, showToast]);

  if (loadingDeal) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
        <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
          >
            <ArrowLeft size={16} />
            <span>Back to pipeline</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className={sectionClassName}>
            <LoadingState message="Loading deal details..." />
          </div>
        </div>
      </div>
    );
  }

  if (error || !deal) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
        <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
          >
            <ArrowLeft size={16} />
            <span>Back to pipeline</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error || "Deal not found."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
      <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <button
              type="button"
              onClick={onBack}
              className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
            >
              <ArrowLeft size={16} />
              <span>Back to pipeline</span>
            </button>

            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-warroom-muted">
              <span>Sales Pipeline</span>
              <ChevronRight size={14} />
              <span className="font-medium text-warroom-text">{deal.title}</span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-semibold tracking-tight text-warroom-text">{deal.title}</h2>
              <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${statusMeta.className}`}>
                {statusMeta.label}
              </span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-warroom-muted">
              <span className="inline-flex items-center gap-2"><User size={14} />{contactName}</span>
              <span className="inline-flex items-center gap-2"><Building2 size={14} />{organizationName}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <select
                value={deal.stage_id || ""}
                onChange={(event) => {
                  const nextStageId = Number(event.target.value);
                  if (Number.isFinite(nextStageId) && nextStageId > 0) {
                    void handleMoveStage(nextStageId);
                  }
                }}
                disabled={movingStage || stages.length === 0}
                className={`min-w-[180px] appearance-none rounded-lg border px-3 py-2 pr-9 text-sm font-medium ${stageColor} disabled:cursor-not-allowed disabled:opacity-60`}
              >
                {stages.map((stage) => (
                  <option key={stage.id} value={stage.id}>
                    {stage.name} ({stage.probability}%)
                  </option>
                ))}
              </select>
              {movingStage ? (
                <Loader2 size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-warroom-text" />
              ) : (
                <ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-warroom-text" />
              )}
            </div>

            <button
              type="button"
              onClick={() => void handleSetStatus(true)}
              disabled={updatingStatus !== null}
              className="inline-flex items-center gap-2 rounded-lg border border-green-500/20 bg-green-500/15 px-4 py-2 text-sm font-medium text-green-400 transition hover:bg-green-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {updatingStatus === "won" ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              Won
            </button>

            <button
              type="button"
              onClick={() => void handleSetStatus(false)}
              disabled={updatingStatus !== null}
              className="inline-flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/15 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {updatingStatus === "lost" ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
              Lost
            </button>
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        <section className="flex min-h-0 flex-1 flex-col bg-warroom-bg xl:w-[65%]">
          <ScrollTabs
            tabs={TABS.map(t => ({ id: t.id, label: t.label }))}
            active={activeTab}
            onChange={(id) => setActiveTab(id as DealTab)}
          />

          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "activity" && (
              <div className="space-y-6">
                <div className={sectionClassName}>
                  <div className="border-b border-warroom-border px-5 py-4">
                    <h3 className="text-sm font-semibold text-warroom-text">Add Activity</h3>
                    <p className="mt-1 text-xs text-warroom-muted">Create a call, note, task, or email touchpoint for this deal.</p>
                  </div>
                  <div className="grid gap-3 p-5 md:grid-cols-2">
                    <select
                      value={activityForm.type}
                      onChange={(event) => setActivityForm((current) => ({ ...current, type: event.target.value }))}
                      className={inputClassName}
                    >
                      {ACTIVITY_TYPES.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      value={activityForm.title}
                      onChange={(event) => setActivityForm((current) => ({ ...current, title: event.target.value }))}
                      placeholder="Activity title"
                      className={inputClassName}
                    />
                    <input
                      type="datetime-local"
                      value={activityForm.schedule_from}
                      onChange={(event) => setActivityForm((current) => ({ ...current, schedule_from: event.target.value }))}
                      className={inputClassName}
                    />
                    <input
                      type="datetime-local"
                      value={activityForm.schedule_to}
                      onChange={(event) => setActivityForm((current) => ({ ...current, schedule_to: event.target.value }))}
                      className={inputClassName}
                    />
                    <div className="md:col-span-2">
                      <textarea
                        value={activityForm.comment}
                        onChange={(event) => setActivityForm((current) => ({ ...current, comment: event.target.value }))}
                        rows={3}
                        placeholder="Add context or notes"
                        className={`${inputClassName} resize-none`}
                      />
                    </div>
                    <div className="flex justify-end md:col-span-2">
                      <button
                        type="button"
                        onClick={() => void handleAddActivity()}
                        disabled={creatingActivity || !activityForm.title.trim()}
                        className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {creatingActivity ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                        Add Activity
                      </button>
                    </div>
                  </div>
                </div>

                <div className={sectionClassName}>
                  <div className="border-b border-warroom-border px-5 py-4">
                    <h3 className="text-sm font-semibold text-warroom-text">Activity Timeline</h3>
                  </div>

                  {loadingActivities ? (
                    <div className="p-6">
                      <LoadingState message="Loading activity timeline..." />
                    </div>
                  ) : activityError ? (
                    <div className="px-5 py-4 text-sm text-red-300">{activityError}</div>
                  ) : activities.length === 0 ? (
                    <EmptyState
                      icon={<Clock3 size={32} />}
                      title="No activity yet"
                      description="Activity linked to this deal will appear here once calls, notes, tasks, or emails are logged."
                    />
                  ) : (
                    <div className="p-5">
                      <div className="space-y-5">
                        {activities
                          .slice()
                          .sort((left, right) => new Date(getOccurredAt(right)).getTime() - new Date(getOccurredAt(left)).getTime())
                          .map((activity, index) => {
                            const Icon = ACTIVITY_ICONS[activity.type] || FileText;
                            return (
                              <div key={activity.id} className="relative pl-10">
                                {index < activities.length - 1 && (
                                  <div className="absolute left-[13px] top-8 h-[calc(100%+1rem)] w-px bg-warroom-border" />
                                )}
                                <div className="absolute left-0 top-0 flex h-7 w-7 items-center justify-center rounded-full border border-warroom-border bg-warroom-bg text-warroom-muted">
                                  <Icon size={14} />
                                </div>
                                <div className="rounded-lg border border-warroom-border bg-warroom-bg/70 p-4">
                                  <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                      <div className="flex flex-wrap items-center gap-2">
                                        <h4 className="text-sm font-medium text-warroom-text">{activity.title || "Untitled activity"}</h4>
                                        {activity.is_done && (
                                          <span className="inline-flex rounded-full border border-green-500/20 bg-green-500/15 px-2 py-0.5 text-[11px] font-medium text-green-400">
                                            Done
                                          </span>
                                        )}
                                      </div>
                                      <p className="mt-1 text-xs uppercase tracking-wide text-warroom-muted">{activity.type}</p>
                                    </div>
                                    <span className="text-xs text-warroom-muted">{formatDate(getOccurredAt(activity), true)}</span>
                                  </div>
                                  <p className="mt-3 text-sm leading-6 text-warroom-text/90">{activity.comment || "No additional notes."}</p>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === "emails" && (
              <div className={sectionClassName}>
                <div className="border-b border-warroom-border px-5 py-4">
                  <h3 className="text-sm font-semibold text-warroom-text">Emails</h3>
                </div>
                {loadingEmails ? (
                  <div className="p-6"><LoadingState message="Loading emails..." /></div>
                ) : emailError ? (
                  <div className="px-5 py-4 text-sm text-red-300">{emailError}</div>
                ) : emails.length === 0 ? (
                  <EmptyState icon={<Mail size={32} />} title="No emails linked" description="Emails related to this deal will appear here once messages are synced." />
                ) : (
                  <div className="divide-y divide-warroom-border">
                    {emails.map((email) => (
                      <div key={email.id} className="flex items-start justify-between gap-4 px-5 py-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="truncate text-sm font-medium text-warroom-text">{email.subject || "(No subject)"}</h4>
                            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${email.is_read ? "border-green-500/20 bg-green-500/15 text-green-400" : "border-yellow-500/20 bg-yellow-500/15 text-yellow-400"}`}>
                              {email.is_read ? "Read" : "Unread"}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-warroom-muted">{formatFromAddress(email.from_addr)}</p>
                        </div>
                        <span className="whitespace-nowrap text-xs text-warroom-muted">{formatDate(email.created_at, true)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {(activeTab === "comments" || activeTab === "notes") && (
              <div className={sectionClassName}>
                <div className="border-b border-warroom-border px-5 py-4">
                  <h3 className="text-sm font-semibold text-warroom-text">{activeTab === "comments" ? "Comments" : "Notes"}</h3>
                  <p className="mt-1 text-xs text-warroom-muted">This is currently backed by the deal description field.</p>
                </div>
                <div className="space-y-4 p-5">
                  <textarea
                    value={descriptionDraft}
                    onChange={(event) => setDescriptionDraft(event.target.value)}
                    onBlur={() => { void saveDescription(); }}
                    rows={12}
                    className={`${inputClassName} resize-none`}
                    placeholder="Add notes, context, objections, or next-step details for this deal..."
                  />
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => void saveDescription()}
                      disabled={savingDescription || !commentsDirty}
                      className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {savingDescription ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                      Save
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "calls" && (
              <div className={sectionClassName}>
                <div className="border-b border-warroom-border px-5 py-4">
                  <h3 className="text-sm font-semibold text-warroom-text">Calls & SMS</h3>
                </div>
                {loadingActivities || loadingSms ? (
                  <div className="p-6"><LoadingState message="Loading communications..." /></div>
                ) : activityError || smsError ? (
                  <div className="px-5 py-4 text-sm text-red-300">{activityError || smsError}</div>
                ) : communications.length === 0 ? (
                  <EmptyState icon={<Phone size={32} />} title="No communications yet" description="Calls and SMS messages tied to this deal will show up in a unified timeline here." />
                ) : (
                  <div className="divide-y divide-warroom-border">
                    {communications.map((item) => {
                      if (item.kind === "call") {
                        const phoneNumber = getAdditionalString(item.activity, "phone_number", "to_number", "from_number") || item.activity.location || "Unknown number";
                        const duration = getAdditionalString(item.activity, "duration", "duration_seconds");
                        return (
                          <div key={item.id} className="px-5 py-4">
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5 rounded-full border border-warroom-border bg-warroom-bg p-2 text-warroom-muted">
                                <Phone size={14} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <h4 className="text-sm font-medium text-warroom-text">{item.activity.title || "Call logged"}</h4>
                                  <span className="text-xs text-warroom-muted">{formatDate(item.occurredAt, true)}</span>
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-warroom-muted">
                                  <span>{phoneNumber}</span>
                                  <span>{duration ? `${duration} sec` : "Duration unavailable"}</span>
                                </div>
                                <p className="mt-2 text-sm text-warroom-text/90">{item.activity.comment || "No call notes provided."}</p>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      const counterpart = item.message.direction === "outbound" ? item.message.to_number : item.message.from_number;
                      return (
                        <div key={item.id} className="px-5 py-4">
                          <div className="flex items-start gap-3">
                            <div className="mt-0.5 rounded-full border border-warroom-border bg-warroom-bg p-2 text-warroom-muted">
                              <MessageSquare size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <h4 className="text-sm font-medium text-warroom-text">SMS {counterpart ? `with ${counterpart}` : "message"}</h4>
                                <span className="text-xs text-warroom-muted">{formatDate(item.occurredAt, true)}</span>
                              </div>
                              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-warroom-muted">
                                <span className="capitalize">{item.message.direction || "unknown"}</span>
                                <span>Status: {item.message.status || "unknown"}</span>
                              </div>
                              <p className="mt-2 text-sm text-warroom-text/90">{item.message.body || "No SMS body captured."}</p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {activeTab === "tasks" && (
              <div className={sectionClassName}>
                <div className="border-b border-warroom-border px-5 py-4">
                  <h3 className="text-sm font-semibold text-warroom-text">Tasks</h3>
                </div>
                {loadingActivities ? (
                  <div className="p-6"><LoadingState message="Loading tasks..." /></div>
                ) : activityError ? (
                  <div className="px-5 py-4 text-sm text-red-300">{activityError}</div>
                ) : taskActivities.length === 0 ? (
                  <EmptyState icon={<CheckCircle2 size={32} />} title="No tasks yet" description="Task-type activities linked to this deal will appear here as a checklist." />
                ) : (
                  <div className="divide-y divide-warroom-border">
                    {taskActivities
                      .slice()
                      .sort((left, right) => new Date(getOccurredAt(left)).getTime() - new Date(getOccurredAt(right)).getTime())
                      .map((task) => (
                        <div key={task.id} className="flex items-start gap-3 px-5 py-4">
                          <button
                            type="button"
                            onClick={() => void handleToggleTask(task)}
                            className="mt-0.5 text-warroom-muted transition hover:text-warroom-text"
                            disabled={updatingTaskId === task.id}
                          >
                            {updatingTaskId === task.id ? (
                              <Loader2 size={18} className="animate-spin" />
                            ) : task.is_done ? (
                              <CheckCircle2 size={18} className="text-green-400" />
                            ) : (
                              <Circle size={18} />
                            )}
                          </button>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <h4 className={`text-sm font-medium ${task.is_done ? "text-warroom-muted line-through" : "text-warroom-text"}`}>
                                {task.title || "Untitled task"}
                              </h4>
                              <span className="text-xs text-warroom-muted">Due {formatDate(task.schedule_to || task.schedule_from)}</span>
                            </div>
                            <p className="mt-1 text-sm text-warroom-muted">{task.comment || "No task notes added."}</p>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "attachments" && (
              <div className={sectionClassName}>
                <div className="border-b border-warroom-border px-5 py-4">
                  <h3 className="text-sm font-semibold text-warroom-text">Attachments</h3>
                  <p className="mt-1 text-xs text-warroom-muted">File attachments are not connected for deals yet.</p>
                </div>
                <div className="p-6">
                  <EmptyState
                    icon={<Paperclip className="h-10 w-10" />}
                    title="No attachments yet"
                    description="This view is ready for deal attachments, but there is no attachment API wired up yet. No files are uploaded or requested from this page today."
                  />
                </div>
              </div>
            )}
          </div>
        </section>

        <aside className="w-full flex-shrink-0 overflow-y-auto border-l border-warroom-border bg-warroom-surface xl:w-[35%]">
          <div className="space-y-6 p-6">
            <div className={sectionClassName}>
              <div className="border-b border-warroom-border px-5 py-4">
                <h3 className="text-sm font-semibold text-warroom-text">Contacts</h3>
              </div>
              <div className="space-y-4 p-5 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wide text-warroom-muted">Person</div>
                  <div className="mt-1 font-medium text-warroom-text">{contactName}</div>
                </div>
                <div className="space-y-2 text-warroom-muted">
                  <div className="flex items-center gap-2"><Mail size={14} />{getPrimaryValue(person?.emails)}</div>
                  <div className="flex items-center gap-2"><Phone size={14} />{getPrimaryValue(person?.contact_numbers)}</div>
                  <div className="flex items-center gap-2"><Building2 size={14} />{organizationName}</div>
                </div>
              </div>
            </div>

            <div className={sectionClassName}>
              <div className="border-b border-warroom-border px-5 py-4">
                <h3 className="text-sm font-semibold text-warroom-text">Forecasted Sales</h3>
              </div>
              <div className="space-y-4 p-5">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Expected Close Date</label>
                  <input
                    type="date"
                    value={expectedCloseDateDraft}
                    onChange={(event) => setExpectedCloseDateDraft(event.target.value)}
                    onBlur={() => { void saveForecast(); }}
                    className={inputClassName}
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-lg border border-warroom-border bg-warroom-bg/60 p-4">
                    <div className="text-xs uppercase tracking-wide text-warroom-muted">Probability</div>
                    <div className="mt-2 text-lg font-semibold text-warroom-text">{probability}%</div>
                  </div>
                  <div className="rounded-lg border border-warroom-border bg-warroom-bg/60 p-4">
                    <div className="text-xs uppercase tracking-wide text-warroom-muted">Weighted Value</div>
                    <div className="mt-2 text-lg font-semibold text-green-400">{formatCurrency(weightedValue)}</div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Deal Amount</label>
                  <input
                    type="text"
                    value={dealValueDraft}
                    onChange={(event) => setDealValueDraft(event.target.value)}
                    onBlur={() => { void saveForecast(); }}
                    className={inputClassName}
                    placeholder="$25,000"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => void saveForecast()}
                    disabled={savingForecast || !forecastDirty}
                    className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {savingForecast ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    Save
                  </button>
                </div>
              </div>
            </div>

            <div className={`${sectionClassName} overflow-hidden`}>
              <button
                type="button"
                onClick={() => setShowDetails((current) => !current)}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <div>
                  <h3 className="text-sm font-semibold text-warroom-text">Details</h3>
                  <p className="mt-1 text-xs text-warroom-muted">Organization, source, timing, and pipeline health.</p>
                </div>
                {showDetails ? <ChevronUp size={18} className="text-warroom-muted" /> : <ChevronDown size={18} className="text-warroom-muted" />}
              </button>

              {showDetails && (
                <dl className="space-y-4 border-t border-warroom-border px-5 py-4 text-sm">
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Organization</dt>
                    <dd className="text-warroom-text">{organizationName}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Website</dt>
                    <dd className="text-warroom-text">
                      {websiteHref ? (
                        <a href={websiteHref} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-warroom-accent hover:underline">
                          <ExternalLink size={14} />
                          <span>{address.website}</span>
                        </a>
                      ) : (
                        "—"
                      )}
                    </dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Source</dt>
                    <dd className="text-warroom-text">{deal.source_name || "—"}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Type</dt>
                    <dd className="text-warroom-text">{deal.type_name || "—"}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Created</dt>
                    <dd className="text-warroom-text">{formatDate(deal.created_at, true)}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Last Modified</dt>
                    <dd className="text-warroom-text">{formatDate(deal.updated_at, true)}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Days in Stage</dt>
                    <dd className="text-warroom-text">{deal.days_in_stage ?? 0}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Rotten Indicator</dt>
                    <dd className="text-warroom-text">
                      {deal.is_rotten ? (
                        <span className="inline-flex items-center gap-2 text-red-400"><AlertTriangle size={14} />Rotten</span>
                      ) : (
                        "Healthy"
                      )}
                    </dd>
                  </div>
                </dl>
              )}
            </div>

            <div className={sectionClassName}>
              <div className="border-b border-warroom-border px-5 py-4">
                <h3 className="text-sm font-semibold text-warroom-text">Next Step</h3>
              </div>
              <div className="space-y-4 p-5">
                <div className="rounded-lg border border-warroom-border bg-warroom-bg/60 p-4">
                  <div className="text-xs uppercase tracking-wide text-warroom-muted">Current Stage</div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${stageColor}`}>
                      {currentStage?.name || "Unassigned"}
                    </span>
                    <span className="text-sm text-warroom-muted">{probability}% probability</span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => { if (nextStage) void handleMoveStage(nextStage.id); }}
                  disabled={!nextStage || movingStage}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-warroom-accent px-4 py-2.5 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {movingStage ? <Loader2 size={14} className="animate-spin" /> : <Target size={14} />}
                  {nextStage ? `Advance to ${nextStage.name}` : "No further stage"}
                </button>

                <div className="text-sm text-warroom-muted">
                  Next stage: <span className="text-warroom-text">{nextStage?.name || "None"}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {toast && (
        <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium text-white shadow-lg ${toast.type === "success" ? "bg-green-600/90" : "bg-red-600/90"}`}>
          <span>{toast.message}</span>
          <button type="button" onClick={() => setToast(null)} className="opacity-80 transition hover:opacity-100">×</button>
        </div>
      )}
    </div>
  );
}