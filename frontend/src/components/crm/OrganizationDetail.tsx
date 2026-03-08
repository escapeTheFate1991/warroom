"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Building2,
  ChevronDown,
  ChevronUp,
  Edit3,
  ExternalLink,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Save,
  Trash2,
  Users,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import EmptyState from "@/components/ui/EmptyState";
import LoadingState from "@/components/ui/LoadingState";

type OrganizationAddress = {
  website?: string;
  industry?: string;
  annual_revenue?: string | number;
  employee_count?: string | number;
  employees?: string | number;
  street?: string;
  city?: string;
  state?: string;
  country?: string;
};

type OrganizationRecord = {
  id: number;
  name: string;
  address?: OrganizationAddress | null;
  user_id?: number | null;
  leadgen_lead_id?: number | null;
  created_at: string;
  updated_at: string;
};

type ContactValue = {
  value?: string;
  label?: string;
};

type PersonRecord = {
  id: number;
  name: string;
  emails?: ContactValue[] | null;
  contact_numbers?: ContactValue[] | null;
  job_title?: string | null;
  organization_id?: number | null;
};

type DealRecord = {
  id: number;
  title: string;
  deal_value?: string | number | null;
  status?: boolean | null;
  organization_id?: number | null;
  pipeline_id?: number | null;
  stage_id?: number | null;
  user_id?: number | null;
  updated_at: string;
};

type UserRecord = {
  id: number;
  name: string;
};

type PipelineRecord = {
  id: number;
  name: string;
};

type PipelineStageRecord = {
  id: number;
  name: string;
  probability: number;
  sort_order: number;
  pipeline_id: number;
};

type ToastState = {
  type: "success" | "error";
  message: string;
};

type OrganizationFormState = {
  name: string;
  website: string;
  industry: string;
  annualRevenue: string;
  street: string;
  city: string;
  state: string;
  country: string;
};

type DetailTab = "deals" | "contacts";

const AVATAR_STYLES = [
  "bg-indigo-500/15 text-indigo-300",
  "bg-emerald-500/15 text-emerald-300",
  "bg-sky-500/15 text-sky-300",
  "bg-fuchsia-500/15 text-fuchsia-300",
  "bg-amber-500/15 text-amber-300",
  "bg-rose-500/15 text-rose-300",
] as const;

const EMPTY_FORM: OrganizationFormState = {
  name: "",
  website: "",
  industry: "",
  annualRevenue: "",
  street: "",
  city: "",
  state: "",
  country: "",
};

const CURRENCY_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const inputClassName =
  "w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:border-warroom-accent/60 focus:outline-none";

function normalizeAddress(address: unknown): OrganizationAddress {
  if (!address || typeof address !== "object" || Array.isArray(address)) {
    return {};
  }

  return address as OrganizationAddress;
}

function trimToUndefined(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function buildAddressPayload(form: OrganizationFormState) {
  const payload = {
    website: trimToUndefined(form.website),
    industry: trimToUndefined(form.industry),
    annual_revenue: trimToUndefined(form.annualRevenue),
    street: trimToUndefined(form.street),
    city: trimToUndefined(form.city),
    state: trimToUndefined(form.state),
    country: trimToUndefined(form.country),
  };

  const populatedEntries = Object.entries(payload).filter(([, value]) => value !== undefined);
  return populatedEntries.length > 0 ? Object.fromEntries(populatedEntries) : null;
}

function organizationToFormState(organization: OrganizationRecord | null): OrganizationFormState {
  const address = normalizeAddress(organization?.address);
  return {
    name: organization?.name ?? "",
    website: address.website ?? "",
    industry: address.industry ?? "",
    annualRevenue:
      address.annual_revenue === null || address.annual_revenue === undefined ? "" : String(address.annual_revenue),
    street: address.street ?? "",
    city: address.city ?? "",
    state: address.state ?? "",
    country: address.country ?? "",
  };
}

function getAvatarStyle(name: string) {
  const firstCharacter = name.trim().charCodeAt(0) || 65;
  return AVATAR_STYLES[firstCharacter % AVATAR_STYLES.length];
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatCurrency(value: unknown) {
  if (value === null || value === undefined) return "—";

  const rawValue = String(value).trim();
  if (!rawValue) return "—";

  if (typeof value === "number") {
    return CURRENCY_FORMATTER.format(value);
  }

  const parsed = Number(rawValue.replace(/[^0-9.-]/g, ""));
  if (/^[\s$0-9,.-]+$/.test(rawValue) && Number.isFinite(parsed)) {
    return CURRENCY_FORMATTER.format(parsed);
  }

  return rawValue;
}

function formatEmployeeCount(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toLocaleString();
  const rawValue = String(value).trim();
  if (!rawValue) return "—";
  const parsed = Number(rawValue.replace(/[^0-9.-]/g, ""));
  return Number.isFinite(parsed) && /^[\s0-9,.-]+$/.test(rawValue) ? parsed.toLocaleString() : rawValue;
}

function getWebsiteHref(website?: string) {
  if (!website) return null;
  return /^https?:\/\//i.test(website) ? website : `https://${website}`;
}

function getPrimaryValue(values?: ContactValue[] | null) {
  if (!Array.isArray(values) || values.length === 0) return "—";
  return values.find((item) => item?.value?.trim())?.value?.trim() || "—";
}

function getDealStatusMeta(status: boolean | null | undefined) {
  if (status === true) {
    return { label: "Won", className: "bg-green-500/15 text-green-400 border-green-500/20" };
  }
  if (status === false) {
    return { label: "Lost", className: "bg-red-500/15 text-red-400 border-red-500/20" };
  }
  return { label: "Open", className: "bg-blue-500/15 text-blue-400 border-blue-500/20" };
}

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const data: unknown = await response.json();
    if (data && typeof data === "object") {
      const detail = (data as { detail?: unknown }).detail;
      const message = (data as { message?: unknown }).message;
      if (typeof detail === "string" && detail.trim()) return detail;
      if (typeof message === "string" && message.trim()) return message;
    }
  } catch {
    // Ignore JSON parse errors and fall back to the default message.
  }

  return fallback;
}

export default function OrganizationDetail({
  organizationId,
  onBack,
}: {
  organizationId: number;
  onBack: () => void;
}) {
  const [organization, setOrganization] = useState<OrganizationRecord | null>(null);
  const [deals, setDeals] = useState<DealRecord[]>([]);
  const [contacts, setContacts] = useState<PersonRecord[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [stages, setStages] = useState<PipelineStageRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<DetailTab>("deals");
  const [showDetails, setShowDetails] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [formState, setFormState] = useState<OrganizationFormState>(EMPTY_FORM);

  useEffect(() => {
    if (!toast) return;
    const timeoutId = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const loadStages = useCallback(async (pipelines: PipelineRecord[], organizationDeals: DealRecord[]) => {
    const pipelineIds = Array.from(
      new Set(organizationDeals.map((deal) => deal.pipeline_id).filter((id): id is number => typeof id === "number")),
    );

    if (pipelineIds.length === 0) {
      setStages([]);
      return;
    }

    const validPipelineIds = pipelineIds.filter((pipelineId) => pipelines.some((pipeline) => pipeline.id === pipelineId));
    const stageResponses = await Promise.allSettled(
      validPipelineIds.map((pipelineId) => authFetch(`${API}/api/crm/pipelines/${pipelineId}/stages`)),
    );

    const nextStages: PipelineStageRecord[] = [];

    for (const result of stageResponses) {
      if (result.status !== "fulfilled") {
        console.error("Failed to load pipeline stages:", result.reason);
        continue;
      }

      if (!result.value.ok) {
        console.error("Failed to load pipeline stages:", result.value.status);
        continue;
      }

      const data: unknown = await result.value.json();
      if (Array.isArray(data)) {
        nextStages.push(...(data as PipelineStageRecord[]));
      }
    }

    setStages(nextStages);
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [organizationResponse, contactsResponse, dealsResponse, usersResponse, pipelinesResponse] = await Promise.all([
        authFetch(`${API}/api/crm/organizations/${organizationId}`),
        authFetch(`${API}/api/crm/organizations/${organizationId}/persons`),
        authFetch(`${API}/api/crm/deals?limit=500&offset=0`),
        authFetch(`${API}/api/crm/users?limit=500&offset=0`),
        authFetch(`${API}/api/crm/pipelines`),
      ]);

      if (!organizationResponse.ok) {
        throw new Error(await getErrorMessage(organizationResponse, `Failed to load organization (${organizationResponse.status})`));
      }

      const organizationData: unknown = await organizationResponse.json();
      const nextOrganization = organizationData as OrganizationRecord;
      setOrganization(nextOrganization);
      setFormState(organizationToFormState(nextOrganization));

      if (contactsResponse.ok) {
        const contactsData: unknown = await contactsResponse.json();
        setContacts(Array.isArray(contactsData) ? (contactsData as PersonRecord[]) : []);
      } else {
        console.error("Failed to load organization contacts:", contactsResponse.status);
        setContacts([]);
      }

      let nextDeals: DealRecord[] = [];
      if (dealsResponse.ok) {
        const dealsData: unknown = await dealsResponse.json();
        nextDeals = Array.isArray(dealsData)
          ? (dealsData as DealRecord[])
              .filter((deal) => deal.organization_id === organizationId)
              .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
          : [];
      } else {
        console.error("Failed to load deals:", dealsResponse.status);
      }
      setDeals(nextDeals);

      if (usersResponse.ok) {
        const usersData: unknown = await usersResponse.json();
        setUsers(Array.isArray(usersData) ? (usersData as UserRecord[]) : []);
      } else {
        console.error("Failed to load users:", usersResponse.status);
        setUsers([]);
      }

      let nextPipelines: PipelineRecord[] = [];
      if (pipelinesResponse.ok) {
        const pipelinesData: unknown = await pipelinesResponse.json();
        nextPipelines = Array.isArray(pipelinesData) ? (pipelinesData as PipelineRecord[]) : [];
      } else {
        console.error("Failed to load pipelines:", pipelinesResponse.status);
      }

      await loadStages(nextPipelines, nextDeals);
    } catch (loadError) {
      console.error("Failed to load organization detail:", loadError);
      setError(loadError instanceof Error ? loadError.message : "Failed to load organization detail.");
      setOrganization(null);
      setDeals([]);
      setContacts([]);
      setUsers([]);
      setStages([]);
    } finally {
      setLoading(false);
    }
  }, [loadStages, organizationId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const userMap = useMemo(() => new Map(users.map((user) => [user.id, user.name])), [users]);

  const stageMap = useMemo(() => new Map(stages.map((stage) => [stage.id, stage.name])), [stages]);

  const handleFormFieldChange = (field: keyof OrganizationFormState, value: string) => {
    setFormState((current) => ({ ...current, [field]: value }));
  };

  const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!organization) return;
    if (!formState.name.trim()) {
      setToast({ type: "error", message: "Organization name is required." });
      return;
    }

    setSaving(true);

    try {
      const response = await authFetch(`${API}/api/crm/organizations/${organization.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: formState.name.trim(),
          address: buildAddressPayload(formState),
        }),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to update organization."));
      }

      const updatedOrganization: unknown = await response.json();
      setOrganization(updatedOrganization as OrganizationRecord);
      setFormState(organizationToFormState(updatedOrganization as OrganizationRecord));
      setIsEditing(false);
      setToast({ type: "success", message: "Organization updated." });
    } catch (saveError) {
      console.error("Failed to update organization:", saveError);
      setToast({
        type: "error",
        message: saveError instanceof Error ? saveError.message : "Failed to update organization.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!organization) return;
    if (!window.confirm(`Delete organization "${organization.name}"?`)) return;

    setDeleting(true);

    try {
      const response = await authFetch(`${API}/api/crm/organizations/${organization.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to delete organization."));
      }

      onBack();
    } catch (deleteError) {
      console.error("Failed to delete organization:", deleteError);
      setToast({
        type: "error",
        message: deleteError instanceof Error ? deleteError.message : "Failed to delete organization.",
      });
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
        <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
          >
            <ArrowLeft size={16} />
            <span>Back to organizations</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className="rounded-xl border border-warroom-border bg-warroom-surface">
            <LoadingState message="Loading organization details..." />
          </div>
        </div>
      </div>
    );
  }

  if (error || !organization) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
        <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
          >
            <ArrowLeft size={16} />
            <span>Back to organizations</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {error || "Organization not found."}
          </div>
        </div>
      </div>
    );
  }

  const address = normalizeAddress(organization.address);
  const initial = organization.name.trim().charAt(0).toUpperCase() || "O";
  const location = [address.city, address.state, address.country].filter(Boolean).join(", ");
  const websiteHref = getWebsiteHref(address.website);
  const employeeCount = address.employee_count ?? address.employees;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-warroom-bg">
      <div className="border-b border-warroom-border bg-warroom-surface px-6 py-4">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm font-medium text-warroom-muted transition hover:text-warroom-text"
        >
          <ArrowLeft size={16} />
          <span>Back to organizations</span>
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        <aside className="w-full flex-shrink-0 overflow-y-auto border-r border-warroom-border bg-warroom-surface xl:w-[35%]">
          <div className="space-y-6 p-6">
            <div className="flex items-start gap-4">
              <div
                className={`flex h-20 w-20 items-center justify-center rounded-full border border-white/10 text-3xl font-semibold ${getAvatarStyle(organization.name)}`}
              >
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-warroom-muted">
                  <Building2 size={14} />
                  <span>Organization</span>
                </div>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-warroom-text">{organization.name}</h2>
                {websiteHref ? (
                  <a
                    href={websiteHref}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-2 text-sm text-warroom-accent transition hover:underline"
                  >
                    <ExternalLink size={14} />
                    <span>{address.website}</span>
                  </a>
                ) : (
                  <p className="mt-3 text-sm text-warroom-muted">No website added</p>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => {
                  setFormState(organizationToFormState(organization));
                  setIsEditing(true);
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-warroom-border bg-warroom-bg px-4 py-2 text-sm font-medium text-warroom-text transition hover:border-warroom-accent/30 hover:text-warroom-accent"
              >
                <Edit3 size={16} />
                <span>Edit</span>
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="inline-flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-300 transition hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleting ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                <span>Delete</span>
              </button>
            </div>

            {isEditing && (
              <div className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-4">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-warroom-text">Edit Organization</h3>
                    <p className="mt-1 text-xs text-warroom-muted">Update account profile and address details.</p>
                  </div>
                </div>

                <form onSubmit={handleSave} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Name *</label>
                    <input
                      type="text"
                      value={formState.name}
                      onChange={(event) => handleFormFieldChange("name", event.target.value)}
                      className={inputClassName}
                      placeholder="Acme Inc."
                      required
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-1.5 sm:col-span-2">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Website</label>
                      <input
                        type="text"
                        value={formState.website}
                        onChange={(event) => handleFormFieldChange("website", event.target.value)}
                        className={inputClassName}
                        placeholder="https://example.com"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Industry</label>
                      <input
                        type="text"
                        value={formState.industry}
                        onChange={(event) => handleFormFieldChange("industry", event.target.value)}
                        className={inputClassName}
                        placeholder="Software"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Annual Revenue</label>
                      <input
                        type="text"
                        value={formState.annualRevenue}
                        onChange={(event) => handleFormFieldChange("annualRevenue", event.target.value)}
                        className={inputClassName}
                        placeholder="$1,000,000"
                      />
                    </div>

                    <div className="space-y-1.5 sm:col-span-2">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Street</label>
                      <input
                        type="text"
                        value={formState.street}
                        onChange={(event) => handleFormFieldChange("street", event.target.value)}
                        className={inputClassName}
                        placeholder="123 Market Street"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">City</label>
                      <input
                        type="text"
                        value={formState.city}
                        onChange={(event) => handleFormFieldChange("city", event.target.value)}
                        className={inputClassName}
                        placeholder="San Francisco"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">State</label>
                      <input
                        type="text"
                        value={formState.state}
                        onChange={(event) => handleFormFieldChange("state", event.target.value)}
                        className={inputClassName}
                        placeholder="CA"
                      />
                    </div>

                    <div className="space-y-1.5 sm:col-span-2">
                      <label className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Country</label>
                      <input
                        type="text"
                        value={formState.country}
                        onChange={(event) => handleFormFieldChange("country", event.target.value)}
                        className={inputClassName}
                        placeholder="USA"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-3 border-t border-warroom-border pt-4">
                    <button
                      type="button"
                      onClick={() => {
                        setIsEditing(false);
                        setFormState(organizationToFormState(organization));
                      }}
                      className="rounded-lg px-4 py-2 text-sm text-warroom-muted transition hover:text-warroom-text"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={saving}
                      className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/85 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                      <span>Save Changes</span>
                    </button>
                  </div>
                </form>
              </div>
            )}

            <div className="overflow-hidden rounded-xl border border-warroom-border bg-warroom-bg/40">
              <button
                type="button"
                onClick={() => setShowDetails((current) => !current)}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <div>
                  <h3 className="text-sm font-semibold text-warroom-text">Details</h3>
                  <p className="mt-1 text-xs text-warroom-muted">Organization profile, territory, and timeline.</p>
                </div>
                {showDetails ? <ChevronUp size={18} className="text-warroom-muted" /> : <ChevronDown size={18} className="text-warroom-muted" />}
              </button>

              {showDetails && (
                <dl className="space-y-4 border-t border-warroom-border px-5 py-4 text-sm">
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Industry</dt>
                    <dd className="text-warroom-text">{address.industry || "—"}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Employee Count</dt>
                    <dd className="text-warroom-text">{formatEmployeeCount(employeeCount)}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Annual Revenue</dt>
                    <dd className="text-warroom-text">{formatCurrency(address.annual_revenue)}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Territory / Address</dt>
                    <dd className="flex items-start gap-2 text-warroom-text">
                      <MapPin size={16} className="mt-0.5 flex-shrink-0 text-warroom-muted" />
                      <span>{location || "—"}</span>
                    </dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Created Date</dt>
                    <dd className="text-warroom-text">{formatDateTime(organization.created_at)}</dd>
                  </div>
                  <div className="grid gap-1">
                    <dt className="text-xs font-medium uppercase tracking-wide text-warroom-muted">Last Modified</dt>
                    <dd className="text-warroom-text">{formatDateTime(organization.updated_at)}</dd>
                  </div>
                </dl>
              )}
            </div>
          </div>
        </aside>

        <section className="flex min-h-0 flex-1 flex-col bg-warroom-bg">
          <div className="border-b border-warroom-border bg-warroom-surface">
            <div className="flex overflow-x-auto px-6">
              {[
                { id: "deals" as const, label: `Deals (${deals.length})`, icon: Building2 },
                { id: "contacts" as const, label: `Contacts (${contacts.length})`, icon: Users },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActiveTab(id)}
                  className={`flex items-center gap-2 whitespace-nowrap border-b-2 px-5 py-3 text-sm font-medium transition ${
                    activeTab === id
                      ? "border-warroom-accent bg-warroom-accent/5 text-warroom-accent"
                      : "border-transparent text-warroom-muted hover:text-warroom-text"
                  }`}
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "deals" ? (
              <div className="overflow-hidden rounded-xl border border-warroom-border bg-warroom-surface">
                {deals.length === 0 ? (
                  <EmptyState
                    icon={<Building2 size={36} />}
                    title="No deals linked to this organization"
                    description="Deals connected to this organization will appear here once opportunities are created."
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-[880px] w-full text-sm">
                      <thead className="bg-warroom-bg/80 backdrop-blur-sm">
                        <tr className="border-b border-warroom-border/80">
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Deal Title</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Status</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Amount</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Stage</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Owner</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Last Modified</th>
                        </tr>
                      </thead>
                      <tbody>
                        {deals.map((deal) => {
                          const statusMeta = getDealStatusMeta(deal.status);

                          return (
                            <tr
                              key={deal.id}
                              onClick={() => console.info("Deal row clicked", deal)}
                              className="cursor-pointer border-b border-warroom-border/50 transition hover:bg-warroom-bg/50"
                            >
                              <td className="px-4 py-3 font-medium text-warroom-text">{deal.title}</td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${statusMeta.className}`}>
                                  {statusMeta.label}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-warroom-muted">{formatCurrency(deal.deal_value)}</td>
                              <td className="px-4 py-3 text-warroom-muted">
                                {deal.stage_id ? stageMap.get(deal.stage_id) || `Stage #${deal.stage_id}` : "—"}
                              </td>
                              <td className="px-4 py-3 text-warroom-muted">
                                {deal.user_id ? userMap.get(deal.user_id) || `User #${deal.user_id}` : "—"}
                              </td>
                              <td className="px-4 py-3 text-warroom-muted">{formatDate(deal.updated_at)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-warroom-border bg-warroom-surface">
                {contacts.length === 0 ? (
                  <EmptyState
                    icon={<Users size={36} />}
                    title="No contacts at this organization"
                    description="People associated with this organization will appear here after they are added in CRM."
                  />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-[760px] w-full text-sm">
                      <thead className="bg-warroom-bg/80 backdrop-blur-sm">
                        <tr className="border-b border-warroom-border/80">
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Name</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Job Title</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Email</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">Phone</th>
                        </tr>
                      </thead>
                      <tbody>
                        {contacts.map((contact) => {
                          const contactInitial = contact.name.trim().charAt(0).toUpperCase() || "C";

                          return (
                            <tr key={contact.id} className="border-b border-warroom-border/50">
                              <td className="px-4 py-3">
                                <div className="flex items-center gap-3">
                                  <div
                                    className={`flex h-9 w-9 items-center justify-center rounded-full border border-white/10 font-semibold ${getAvatarStyle(contact.name)}`}
                                  >
                                    {contactInitial}
                                  </div>
                                  <div className="min-w-0">
                                    <div className="truncate font-medium text-warroom-text">{contact.name}</div>
                                  </div>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-warroom-muted">{contact.job_title || "—"}</td>
                              <td className="px-4 py-3 text-warroom-muted">
                                <span className="inline-flex items-center gap-2">
                                  <Mail size={14} className="text-warroom-muted" />
                                  <span>{getPrimaryValue(contact.emails)}</span>
                                </span>
                              </td>
                              <td className="px-4 py-3 text-warroom-muted">
                                <span className="inline-flex items-center gap-2">
                                  <Phone size={14} className="text-warroom-muted" />
                                  <span>{getPrimaryValue(contact.contact_numbers)}</span>
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium text-white shadow-lg ${
            toast.type === "success" ? "bg-green-600/90" : "bg-red-600/90"
          }`}
        >
          <span>{toast.message}</span>
          <button type="button" onClick={() => setToast(null)} className="opacity-80 transition hover:opacity-100">
            ×
          </button>
        </div>
      )}
    </div>
  );
}