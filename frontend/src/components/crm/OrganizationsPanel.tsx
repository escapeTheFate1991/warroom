"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowUpDown,
  Building2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Edit3,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { API, authFetch } from "@/lib/api";
import EmptyState from "@/components/ui/EmptyState";
import LoadingState from "@/components/ui/LoadingState";
import OrganizationDetail from "./OrganizationDetail";

type OrganizationAddress = {
  website?: string;
  industry?: string;
  annual_revenue?: string | number;
  street?: string;
  city?: string;
  state?: string;
  country?: string;
};

type Organization = {
  id: number;
  name: string;
  address?: OrganizationAddress | null;
  user_id?: number | null;
  leadgen_lead_id?: number | null;
  created_at: string;
  updated_at: string;
};

type SortKey = "name" | "website" | "industry" | "annual_revenue" | "deals_count" | "updated_at";

type SortState = {
  key: SortKey;
  direction: "asc" | "desc";
};

type ToastState = {
  type: "success" | "error" | "info";
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

const PAGE_SIZE = 20;
const MAX_FETCH_LIMIT = 500;
const SEARCH_DEBOUNCE_MS = 300;
const CURRENCY_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

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

const inputClassName =
  "w-full rounded-lg bg-warroom-bg border border-warroom-border px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:outline-none focus:border-warroom-accent/60";

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

function organizationToFormState(organization: Organization | null): OrganizationFormState {
  const address = normalizeAddress(organization?.address);
  return {
    name: organization?.name ?? "",
    website: address.website ?? "",
    industry: address.industry ?? "",
    annualRevenue:
      address.annual_revenue === null || address.annual_revenue === undefined
        ? ""
        : String(address.annual_revenue),
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

function getSortValue(organization: Organization, key: SortKey): number | string | null {
  const address = normalizeAddress(organization.address);

  switch (key) {
    case "name":
      return organization.name;
    case "website":
      return address.website ?? "";
    case "industry":
      return address.industry ?? "";
    case "annual_revenue": {
      const revenue = address.annual_revenue;
      if (typeof revenue === "number") return revenue;
      const rawRevenue = String(revenue ?? "").trim();
      const parsedRevenue = Number(rawRevenue.replace(/[^0-9.-]/g, ""));
      if (rawRevenue && Number.isFinite(parsedRevenue)) {
        return parsedRevenue;
      }
      return rawRevenue;
    }
    case "deals_count":
      return null;
    case "updated_at":
      return new Date(organization.updated_at).getTime();
    default:
      return organization.name;
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatRevenue(value: unknown) {
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

function SortHeader({
  label,
  sortKey,
  sortState,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sortState: SortState;
  onSort: (key: SortKey) => void;
}) {
  const isActive = sortState.key === sortKey;
  const Icon = !isActive ? ArrowUpDown : sortState.direction === "asc" ? ChevronUp : ChevronDown;

  return (
    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-warroom-muted">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`inline-flex items-center gap-1.5 transition-colors ${
          isActive ? "text-warroom-text" : "hover:text-warroom-text"
        }`}
      >
        <span>{label}</span>
        <Icon size={14} />
      </button>
    </th>
  );
}

export default function OrganizationsPanel() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [error, setError] = useState("");
  const [toast, setToast] = useState<ToastState | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingOrganization, setEditingOrganization] = useState<Organization | null>(null);
  const [formState, setFormState] = useState<OrganizationFormState>(EMPTY_FORM);
  const [sortState, setSortState] = useState<SortState>({ key: "name", direction: "asc" });
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setCurrentPage(1);
    }, SEARCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [searchQuery]);

  useEffect(() => {
    if (!toast) return;

    const timeoutId = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const fetchOrganizations = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        limit: String(MAX_FETCH_LIMIT),
        offset: "0",
      });

      if (debouncedSearch) {
        params.set("search", debouncedSearch);
      }

      const response = await authFetch(`${API}/api/crm/organizations?${params.toString()}`);
      if (!response.ok) {
        setError(await getErrorMessage(response, `Failed to load organizations (${response.status})`));
        setOrganizations([]);
        return;
      }

      const data: unknown = await response.json();
      setOrganizations(Array.isArray(data) ? (data as Organization[]) : []);
    } catch (fetchError) {
      console.error("Failed to load organizations:", fetchError);
      setError("Failed to load organizations.");
      setOrganizations([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    fetchOrganizations();
  }, [fetchOrganizations]);

  const sortedOrganizations = useMemo(() => {
    return [...organizations].sort((first, second) => {
      const firstValue = getSortValue(first, sortState.key);
      const secondValue = getSortValue(second, sortState.key);

      const firstEmpty = firstValue === null || firstValue === undefined || firstValue === "";
      const secondEmpty = secondValue === null || secondValue === undefined || secondValue === "";

      if (firstEmpty && secondEmpty) return 0;
      if (firstEmpty) return 1;
      if (secondEmpty) return -1;

      const comparison =
        typeof firstValue === "number" && typeof secondValue === "number"
          ? firstValue - secondValue
          : String(firstValue).localeCompare(String(secondValue), undefined, {
              numeric: true,
              sensitivity: "base",
            });

      return sortState.direction === "asc" ? comparison : -comparison;
    });
  }, [organizations, sortState]);

  const totalOrganizations = sortedOrganizations.length;
  const totalPages = Math.max(1, Math.ceil(totalOrganizations / PAGE_SIZE));

  useEffect(() => {
    setCurrentPage((previousPage) => Math.min(previousPage, totalPages));
  }, [totalPages]);

  const paginatedOrganizations = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return sortedOrganizations.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, sortedOrganizations]);

  const showingStart = totalOrganizations === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const showingEnd = totalOrganizations === 0 ? 0 : Math.min(currentPage * PAGE_SIZE, totalOrganizations);

  const openCreateModal = () => {
    setEditingOrganization(null);
    setFormState(EMPTY_FORM);
    setShowModal(true);
  };

  const openEditModal = (organization: Organization) => {
    setEditingOrganization(organization);
    setFormState(organizationToFormState(organization));
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setEditingOrganization(null);
    setFormState(EMPTY_FORM);
  };

  const handleSort = (key: SortKey) => {
    setSortState((current) => {
      if (current.key === key) {
        return { key, direction: current.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: key === "updated_at" ? "desc" : "asc" };
    });
  };

  const handleFormFieldChange = (field: keyof OrganizationFormState, value: string) => {
    setFormState((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!formState.name.trim()) {
      setToast({ type: "error", message: "Organization name is required." });
      return;
    }

    setSaving(true);

    try {
      const response = await authFetch(
        editingOrganization
          ? `${API}/api/crm/organizations/${editingOrganization.id}`
          : `${API}/api/crm/organizations`,
        {
          method: editingOrganization ? "PUT" : "POST",
          body: JSON.stringify({
            name: formState.name.trim(),
            address: buildAddressPayload(formState),
          }),
        },
      );

      if (!response.ok) {
        throw new Error(
          await getErrorMessage(
            response,
            editingOrganization ? "Failed to update organization." : "Failed to create organization.",
          ),
        );
      }

      closeModal();
      await fetchOrganizations();
      setToast({
        type: "success",
        message: editingOrganization ? "Organization updated." : "Organization created.",
      });
    } catch (submitError) {
      console.error("Failed to save organization:", submitError);
      setToast({
        type: "error",
        message: submitError instanceof Error ? submitError.message : "Failed to save organization.",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (organization: Organization) => {
    if (!window.confirm(`Delete organization "${organization.name}"?`)) return;

    try {
      const response = await authFetch(`${API}/api/crm/organizations/${organization.id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to delete organization."));
      }

      await fetchOrganizations();
      setToast({ type: "success", message: "Organization deleted." });
    } catch (deleteError) {
      console.error("Failed to delete organization:", deleteError);
      setToast({
        type: "error",
        message: deleteError instanceof Error ? deleteError.message : "Failed to delete organization.",
      });
    }
  };

  const handleRowClick = (organization: Organization) => {
    setSelectedOrgId(organization.id);
  };

  if (selectedOrgId !== null) {
    return (
      <OrganizationDetail
        organizationId={selectedOrgId}
        onBack={() => {
          setSelectedOrgId(null);
          fetchOrganizations();
        }}
      />
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b border-warroom-border bg-warroom-bg/80 backdrop-blur-sm">
        <div className="flex flex-col gap-4 px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-warroom-accent/20 bg-warroom-accent/10 text-warroom-accent">
                <Building2 size={20} />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-warroom-text">Organizations</h2>
                <p className="text-sm text-warroom-muted">Track companies, account details, and CRM metadata.</p>
              </div>
            </div>

            <button
              type="button"
              onClick={openCreateModal}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/85"
            >
              <Plus size={16} />
              <span>Create</span>
            </button>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full sm:max-w-sm">
              <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search organizations by name"
                className="w-full rounded-lg border border-warroom-border bg-warroom-surface py-2 pl-9 pr-3 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:outline-none focus:border-warroom-accent/60"
              />
            </div>

            <button
              type="button"
              onClick={fetchOrganizations}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-warroom-border bg-warroom-surface px-4 py-2 text-sm text-warroom-muted transition hover:text-warroom-text"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="overflow-hidden rounded-xl border border-warroom-border bg-warroom-surface">
          {error && (
            <div className="border-b border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          {loading ? (
            <LoadingState message="Loading organizations..." />
          ) : totalOrganizations === 0 ? (
            <EmptyState
              icon={<Building2 size={40} />}
              title={debouncedSearch ? "No organizations match your search" : "No organizations yet"}
              description={
                debouncedSearch
                  ? "Try a different organization name or clear your search to see all results."
                  : "Create your first organization to start managing company records in CRM."
              }
              action={
                debouncedSearch
                  ? { label: "Clear Search", onClick: () => setSearchQuery("") }
                  : { label: "Create Organization", onClick: openCreateModal }
              }
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="min-w-[1080px] w-full text-sm">
                  <thead className="bg-warroom-bg/80 backdrop-blur-sm">
                    <tr className="border-b border-warroom-border/80">
                      <SortHeader label="Organization name" sortKey="name" sortState={sortState} onSort={handleSort} />
                      <SortHeader label="Website" sortKey="website" sortState={sortState} onSort={handleSort} />
                      <SortHeader label="Industry" sortKey="industry" sortState={sortState} onSort={handleSort} />
                      <SortHeader label="Annual Revenue" sortKey="annual_revenue" sortState={sortState} onSort={handleSort} />
                      <SortHeader label="Deals count" sortKey="deals_count" sortState={sortState} onSort={handleSort} />
                      <SortHeader label="Last Modified" sortKey="updated_at" sortState={sortState} onSort={handleSort} />
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-warroom-muted">
                        Actions
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {paginatedOrganizations.map((organization) => {
                      const address = normalizeAddress(organization.address);
                      const initial = organization.name.trim().charAt(0).toUpperCase() || "O";
                      const location = [address.city, address.state, address.country].filter(Boolean).join(", ");

                      return (
                        <tr
                          key={organization.id}
                          onClick={() => handleRowClick(organization)}
                          className="cursor-pointer border-b border-warroom-border/50 transition hover:bg-warroom-bg/50"
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div
                                className={`flex h-10 w-10 items-center justify-center rounded-full border border-white/10 font-semibold ${getAvatarStyle(organization.name)}`}
                              >
                                {initial}
                              </div>
                              <div className="min-w-0">
                                <div className="truncate font-medium text-warroom-text">{organization.name}</div>
                                <div className="truncate text-xs text-warroom-muted">{location || "No location added"}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-warroom-muted">{address.website || "—"}</td>
                          <td className="px-4 py-3 text-warroom-muted">{address.industry || "—"}</td>
                          <td className="px-4 py-3 text-warroom-muted">{formatRevenue(address.annual_revenue)}</td>
                          <td className="px-4 py-3 text-warroom-muted">—</td>
                          <td className="px-4 py-3 text-warroom-muted">{formatDate(organization.updated_at)}</td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openEditModal(organization);
                                }}
                                className="rounded-lg p-2 text-warroom-muted transition hover:bg-warroom-bg hover:text-warroom-text"
                                title="Edit organization"
                              >
                                <Edit3 size={15} />
                              </button>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleDelete(organization);
                                }}
                                className="rounded-lg p-2 text-warroom-muted transition hover:bg-red-500/10 hover:text-red-400"
                                title="Delete organization"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-col gap-3 border-t border-warroom-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-sm text-warroom-muted">
                  Showing {showingStart}-{showingEnd} of {totalOrganizations}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                    disabled={currentPage === 1}
                    className="inline-flex items-center gap-1 rounded-lg border border-warroom-border px-3 py-2 text-sm text-warroom-muted transition hover:text-warroom-text disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ChevronLeft size={16} />
                    <span>Previous</span>
                  </button>

                  <div className="px-2 text-sm text-warroom-muted">
                    Page {currentPage} of {totalPages}
                  </div>

                  <button
                    type="button"
                    onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                    disabled={currentPage === totalPages}
                    className="inline-flex items-center gap-1 rounded-lg border border-warroom-border px-3 py-2 text-sm text-warroom-muted transition hover:text-warroom-text disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <span>Next</span>
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={closeModal}>
          <div
            className="w-full max-w-3xl rounded-2xl border border-warroom-border bg-warroom-surface shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-warroom-border px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold text-warroom-text">
                  {editingOrganization ? "Edit Organization" : "Create Organization"}
                </h3>
                <p className="mt-1 text-sm text-warroom-muted">
                  Save website, industry, revenue, and address details into the organization record.
                </p>
              </div>
              <button
                type="button"
                onClick={closeModal}
                className="rounded-lg p-2 text-warroom-muted transition hover:bg-warroom-bg hover:text-warroom-text"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5 px-6 py-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Name *
                  </label>
                  <input
                    type="text"
                    value={formState.name}
                    onChange={(event) => handleFormFieldChange("name", event.target.value)}
                    className={inputClassName}
                    placeholder="Acme Inc."
                    required
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Website
                  </label>
                  <input
                    type="text"
                    value={formState.website}
                    onChange={(event) => handleFormFieldChange("website", event.target.value)}
                    className={inputClassName}
                    placeholder="https://example.com"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Industry
                  </label>
                  <input
                    type="text"
                    value={formState.industry}
                    onChange={(event) => handleFormFieldChange("industry", event.target.value)}
                    className={inputClassName}
                    placeholder="Software"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Annual Revenue
                  </label>
                  <input
                    type="text"
                    value={formState.annualRevenue}
                    onChange={(event) => handleFormFieldChange("annualRevenue", event.target.value)}
                    className={inputClassName}
                    placeholder="$1,000,000"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Street
                  </label>
                  <input
                    type="text"
                    value={formState.street}
                    onChange={(event) => handleFormFieldChange("street", event.target.value)}
                    className={inputClassName}
                    placeholder="123 Market Street"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    City
                  </label>
                  <input
                    type="text"
                    value={formState.city}
                    onChange={(event) => handleFormFieldChange("city", event.target.value)}
                    className={inputClassName}
                    placeholder="San Francisco"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    State
                  </label>
                  <input
                    type="text"
                    value={formState.state}
                    onChange={(event) => handleFormFieldChange("state", event.target.value)}
                    className={inputClassName}
                    placeholder="CA"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-warroom-muted">
                    Country
                  </label>
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
                  onClick={closeModal}
                  className="rounded-lg px-4 py-2 text-sm text-warroom-muted transition hover:text-warroom-text"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/85 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                  <span>{editingOrganization ? "Save Changes" : "Create Organization"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-[60] flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium text-white shadow-lg ${
            toast.type === "success"
              ? "bg-green-600/90"
              : toast.type === "error"
                ? "bg-red-600/90"
                : "bg-warroom-accent/95"
          }`}
        >
          <span>{toast.message}</span>
          <button type="button" onClick={() => setToast(null)} className="opacity-80 transition hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}