"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Building2,
  Loader2,
  Mail,
  MessageSquare,
  Phone,
  PhoneCall,
  RefreshCw,
  Search,
  Volume2,
} from "lucide-react";

import AgentAssignmentCard from "@/components/agents/AgentAssignmentCard";
import EmptyState from "@/components/ui/EmptyState";
import LoadingState from "@/components/ui/LoadingState";
import { API, authFetch } from "@/lib/api";
import type { AgentAssignmentSummary } from "@/lib/agentAssignments";

type ContactValue = { value: string; label?: string | null };

type PersonRecord = {
  id: number;
  name: string;
  emails?: ContactValue[];
  contact_numbers?: ContactValue[] | null;
  job_title?: string | null;
  organization_id?: number | null;
  organization_name?: string | null;
  agent_assignments?: AgentAssignmentSummary[];
  created_at: string;
  updated_at?: string;
};

type DealRecord = {
  id: number;
  title: string;
  deal_value?: number | null;
  status?: boolean | null;
  stage_name?: string | null;
  organization_name?: string | null;
  expected_close_date?: string | null;
  agent_assignments?: AgentAssignmentSummary[];
  stage?: { name?: string | null } | null;
};

type CommunicationHistoryItem = {
  entry_id: string;
  source: string;
  channel: string;
  occurred_at?: string | null;
  created_at: string;
  title?: string | null;
  content?: string | null;
  linked_person_ids: number[];
  linked_deal_ids: number[];
  participant_person_ids: number[];
  direction?: string | null;
  status?: string | null;
  from_number?: string | null;
  to_number?: string | null;
  recording_url?: string | null;
  transcript?: string | null;
  metadata?: Record<string, unknown> | null;
};

type CommunicationHistoryResponse = {
  items?: CommunicationHistoryItem[];
};

type ActiveCall = {
  phoneNumber: string;
  callControlId: string | null;
  callSessionId: string | null;
  direction: string | null;
  isIncoming: boolean;
  status: string;
};

type NoticeTone = "info" | "success" | "error";

const NOTICE_STYLES: Record<NoticeTone, string> = {
  info: "border-blue-500/30 bg-blue-500/10 text-blue-200",
  success: "border-green-500/30 bg-green-500/10 text-green-200",
  error: "border-red-500/30 bg-red-500/10 text-red-200",
};

const TERMINAL_CALL_STATUSES = new Set(["completed", "ended", "failed", "hangup", "rejected", "canceled", "cancelled"]);
const INCOMING_CALL_DIRECTIONS = new Set(["incoming", "inbound"]);
const OUTBOUND_CALL_DIRECTIONS = new Set(["outgoing", "outbound"]);

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function pickString(source: Record<string, unknown> | null, ...keys: string[]): string | null {
  if (!source) return null;
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function getPrimaryValue(values?: ContactValue[] | null): string {
  const first = values?.find((value) => typeof value?.value === "string" && value.value.trim());
  return first?.value?.trim() || "—";
}

function formatTimestamp(value?: string | null) {
  if (!value) return "Unknown time";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown time" : parsed.toLocaleString();
}

function formatMoney(value?: number | null) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function normalizeCallDirection(direction?: string | null) {
  const normalized = (direction || "").trim().toLowerCase();
  if (!normalized) return null;
  if (INCOMING_CALL_DIRECTIONS.has(normalized)) return "incoming";
  if (OUTBOUND_CALL_DIRECTIONS.has(normalized)) return "outbound";
  return normalized;
}

function normalizeCallStatus(status?: string | null) {
  const normalized = (status || "").trim().toLowerCase();
  return normalized || null;
}

function isTerminalCallStatus(status?: string | null) {
  const normalized = normalizeCallStatus(status);
  return normalized ? TERMINAL_CALL_STATUSES.has(normalized) : false;
}

function getHistoryCallMetadata(item: CommunicationHistoryItem) {
  const metadata = asRecord(item.metadata);
  return asRecord(metadata?.additional);
}

function buildActiveCallFromHistory(item: CommunicationHistoryItem): ActiveCall | null {
  if (item.channel !== "call") return null;

  const additional = getHistoryCallMetadata(item);
  const callControlId = pickString(additional, "call_control_id");
  if (!callControlId) return null;

  const status = normalizeCallStatus(item.status) || "initiated";
  if (isTerminalCallStatus(status)) return null;

  const direction = normalizeCallDirection(item.direction);
  const isIncoming = direction === "incoming";
  const phoneNumber = isIncoming ? item.from_number || item.to_number || "Unknown number" : item.to_number || item.from_number || "Unknown number";

  return {
    phoneNumber,
    callControlId,
    callSessionId: pickString(additional, "call_session_id"),
    direction,
    isIncoming,
    status,
  };
}

function findCurrentCall(items: CommunicationHistoryItem[]): ActiveCall | null {
  const pendingIncoming = items
    .filter((item) => normalizeCallDirection(item.direction) === "incoming")
    .map(buildActiveCallFromHistory)
    .find((call) => Boolean(call));

  if (pendingIncoming) return pendingIncoming;

  return items.map(buildActiveCallFromHistory).find((call) => Boolean(call)) || null;
}

function getDealStatusLabel(status?: boolean | null) {
  if (status === true) return "Won";
  if (status === false) return "Lost";
  return "Open";
}

function getHistoryChannelLabel(item: CommunicationHistoryItem) {
  if (item.channel === "sms") return "SMS";
  if (item.channel === "email") return "Email";
  if (item.channel === "call") return "Call";
  return item.channel || item.source;
}

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const payload = await response.json();
    const data = asRecord(payload);
    const detail = data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  } catch {
    // ignore parse errors and fall back
  }
  return fallback;
}

export default function CommunicationsConsole() {
  const [searchQuery, setSearchQuery] = useState("");
  const [people, setPeople] = useState<PersonRecord[]>([]);
  const [peopleLoading, setPeopleLoading] = useState(true);
  const [peopleError, setPeopleError] = useState("");

  const [selectedPerson, setSelectedPerson] = useState<PersonRecord | null>(null);
  const [bundleLoading, setBundleLoading] = useState(false);
  const [detailsError, setDetailsError] = useState("");
  const [history, setHistory] = useState<CommunicationHistoryItem[]>([]);
  const [deals, setDeals] = useState<DealRecord[]>([]);
  const [selectedDealId, setSelectedDealId] = useState<number | null>(null);
  const [selectedDeal, setSelectedDeal] = useState<DealRecord | null>(null);

  const [activeCall, setActiveCall] = useState<ActiveCall | null>(null);
  const [speechText, setSpeechText] = useState("");
  const [smsBody, setSmsBody] = useState("");
  const [notice, setNotice] = useState<{ tone: NoticeTone; text: string } | null>(null);
  const [dialing, setDialing] = useState(false);
  const [answering, setAnswering] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [hangingUp, setHangingUp] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [sendingSms, setSendingSms] = useState(false);

  const primaryPhone = useMemo(() => getPrimaryValue(selectedPerson?.contact_numbers), [selectedPerson]);
  const primaryEmail = useMemo(() => getPrimaryValue(selectedPerson?.emails), [selectedPerson]);

  const loadPeople = useCallback(async (query: string) => {
    setPeopleLoading(true);
    setPeopleError("");
    try {
      const trimmed = query.trim();
      const endpoint = trimmed
        ? `${API}/api/crm/contacts/persons/search?q=${encodeURIComponent(trimmed)}&limit=25`
        : `${API}/api/crm/contacts/persons?limit=25`;
      const response = await authFetch(endpoint);
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to load CRM contacts."));
      }
      const data = (await response.json()) as PersonRecord[];
      setPeople(Array.isArray(data) ? data : []);
    } catch (error) {
      setPeople([]);
      setPeopleError(error instanceof Error ? error.message : "Failed to load CRM contacts.");
    } finally {
      setPeopleLoading(false);
    }
  }, []);

  const loadPersonBundle = useCallback(async (person: PersonRecord) => {
    const switchingPerson = selectedPerson?.id !== person.id;
    if (switchingPerson) {
      setActiveCall(null);
      setSpeechText("");
      setSmsBody("");
      setNotice(null);
      setSelectedDealId(null);
      setSelectedDeal(null);
      setDeals([]);
      setHistory([]);
    }

    setSelectedPerson(person);
    setBundleLoading(true);
    setDetailsError("");

    try {
      const [personResponse, dealsResponse, historyResponse] = await Promise.all([
        authFetch(`${API}/api/crm/persons/${person.id}`),
        authFetch(`${API}/api/crm/persons/${person.id}/deals`),
        authFetch(`${API}/api/crm/communications/history?person_id=${person.id}&limit=100`),
      ]);

      if (!personResponse.ok) {
        throw new Error(await getErrorMessage(personResponse, "Failed to load contact details."));
      }
      if (!dealsResponse.ok) {
        throw new Error(await getErrorMessage(dealsResponse, "Failed to load linked deals."));
      }
      if (!historyResponse.ok) {
        throw new Error(await getErrorMessage(historyResponse, "Failed to load communications timeline."));
      }

      const personPayload = (await personResponse.json()) as PersonRecord;
      const dealPayload = (await dealsResponse.json()) as DealRecord[];
      const historyPayload = (await historyResponse.json()) as CommunicationHistoryResponse;
      const nextDeals = Array.isArray(dealPayload) ? dealPayload : [];

      setSelectedPerson({
        ...person,
        ...personPayload,
        organization_name: person.organization_name ?? personPayload.organization_name ?? null,
      });
      const nextHistory = Array.isArray(historyPayload.items) ? historyPayload.items : [];
      setDeals(nextDeals);
      setHistory(nextHistory);
      const nextActiveCall = findCurrentCall(nextHistory);
      setActiveCall((current) => {
        if (switchingPerson) return nextActiveCall;
        if (nextActiveCall) return nextActiveCall;
        return current;
      });

      const preferredDeal = nextDeals.find((deal) => deal.status == null) || nextDeals[0] || null;
      setSelectedDealId((current) => (current && nextDeals.some((deal) => deal.id === current) ? current : preferredDeal?.id ?? null));
    } catch (error) {
      setDetailsError(error instanceof Error ? error.message : "Failed to load operator context.");
    } finally {
      setBundleLoading(false);
    }
  }, [selectedPerson?.id]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadPeople(searchQuery);
    }, searchQuery.trim() ? 200 : 0);
    return () => window.clearTimeout(handle);
  }, [loadPeople, searchQuery]);

  useEffect(() => {
    if (!selectedPerson && people.length > 0 && !peopleLoading) {
      void loadPersonBundle(people[0]);
    }
  }, [loadPersonBundle, people, peopleLoading, selectedPerson]);

  useEffect(() => {
    if (!selectedDealId) {
      setSelectedDeal(null);
      return;
    }

    let cancelled = false;
    const summary = deals.find((deal) => deal.id === selectedDealId) || null;
    setSelectedDeal(summary);

    const loadDeal = async () => {
      const response = await authFetch(`${API}/api/crm/deals/${selectedDealId}`);
      if (!response.ok || cancelled) return;
      const payload = (await response.json()) as DealRecord;
      if (!cancelled) setSelectedDeal(summary ? { ...summary, ...payload } : payload);
    };

    void loadDeal();
    return () => {
      cancelled = true;
    };
  }, [deals, selectedDealId]);

  const refreshCurrentPerson = useCallback(async () => {
    if (!selectedPerson) return;
    await loadPersonBundle(selectedPerson);
  }, [loadPersonBundle, selectedPerson]);

  const pendingIncomingCall = useMemo(() => {
    if (!activeCall?.isIncoming) return null;
    const status = normalizeCallStatus(activeCall.status);
    if (!status || status === "answered" || status === "answer requested") return null;
    if (isTerminalCallStatus(status) || status === "reject requested" || status === "hangup requested") return null;
    return activeCall;
  }, [activeCall]);

  const liveCallReadyForSpeech = useMemo(() => {
    if (!activeCall?.callControlId) return false;
    if (pendingIncomingCall) return false;
    return !isTerminalCallStatus(activeCall.status);
  }, [activeCall, pendingIncomingCall]);

  const handleDial = useCallback(async () => {
    if (!selectedPerson || primaryPhone === "—") {
      setNotice({ tone: "error", text: "Select a CRM contact with a phone number before dialing." });
      return;
    }

    setDialing(true);
    setNotice(null);
    try {
      const response = await authFetch(`${API}/api/telnyx/call`, {
        method: "POST",
        body: JSON.stringify({ phone_number: primaryPhone }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to start the Telnyx call."));
      }

      const payload = asRecord(await response.json());
      const nestedPayload = asRecord(payload?.payload);
      const callControlId = pickString(payload, "call_control_id") || pickString(nestedPayload, "call_control_id");
      const callSessionId = pickString(payload, "call_session_id") || pickString(nestedPayload, "call_session_id");
      const status = pickString(payload, "state", "status") || pickString(nestedPayload, "state", "status") || "dialing";

      setActiveCall({
        phoneNumber: primaryPhone,
        callControlId,
        callSessionId,
        direction: "outbound",
        isIncoming: false,
        status,
      });
      setNotice({ tone: "success", text: `Dialing ${selectedPerson.name} via Telnyx.` });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to start the Telnyx call." });
    } finally {
      setDialing(false);
    }
  }, [primaryPhone, selectedPerson]);

  const handleAnswer = useCallback(async () => {
    if (!pendingIncomingCall?.callControlId) {
      setNotice({ tone: "error", text: "No incoming Telnyx call is available to answer." });
      return;
    }

    setAnswering(true);
    try {
      const response = await authFetch(`${API}/api/telnyx/answer`, {
        method: "POST",
        body: JSON.stringify({ call_control_id: pendingIncomingCall.callControlId }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to answer the incoming call."));
      }
      setActiveCall((current) => (current ? { ...current, status: "answer requested" } : current));
      setNotice({ tone: "success", text: "Incoming call answer requested. Live status will update after the Telnyx webhook lands." });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to answer the incoming call." });
    } finally {
      setAnswering(false);
    }
  }, [pendingIncomingCall]);

  const handleReject = useCallback(async () => {
    if (!pendingIncomingCall?.callControlId) {
      setNotice({ tone: "error", text: "No incoming Telnyx call is available to reject." });
      return;
    }

    setRejecting(true);
    try {
      const response = await authFetch(`${API}/api/telnyx/reject`, {
        method: "POST",
        body: JSON.stringify({ call_control_id: pendingIncomingCall.callControlId }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to reject the incoming call."));
      }
      setActiveCall((current) => (current ? { ...current, status: "reject requested" } : current));
      setNotice({ tone: "info", text: "Incoming call reject requested. Timeline status will update once the Telnyx webhook lands." });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to reject the incoming call." });
    } finally {
      setRejecting(false);
    }
  }, [pendingIncomingCall]);

  const handleHangup = useCallback(async () => {
    if (!activeCall?.callControlId) {
      setNotice({ tone: "error", text: "This call has no Telnyx call control id yet, so hangup is unavailable." });
      return;
    }

    setHangingUp(true);
    try {
      const response = await authFetch(`${API}/api/telnyx/hangup`, {
        method: "POST",
        body: JSON.stringify({ call_control_id: activeCall.callControlId }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to hang up the active call."));
      }
      setActiveCall((current) => (current ? { ...current, status: "hangup requested" } : current));
      setNotice({ tone: "info", text: "Hangup requested. Timeline status will update once the Telnyx webhook lands." });
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to hang up the active call." });
    } finally {
      setHangingUp(false);
    }
  }, [activeCall]);

  const handleSpeak = useCallback(async () => {
    if (!activeCall?.callControlId) {
      setNotice({ tone: "error", text: "Start a live call before sending operator speech to Telnyx." });
      return;
    }
    if (!speechText.trim()) return;

    setSpeaking(true);
    try {
      const response = await authFetch(`${API}/api/telnyx/speak`, {
        method: "POST",
        body: JSON.stringify({ call_control_id: activeCall.callControlId, text: speechText.trim() }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to speak text on the active call."));
      }
      setNotice({ tone: "success", text: "Operator speech sent to the active call." });
      setSpeechText("");
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to speak text on the active call." });
    } finally {
      setSpeaking(false);
    }
  }, [activeCall, speechText]);

  const handleSendSms = useCallback(async () => {
    if (!selectedPerson || primaryPhone === "—") {
      setNotice({ tone: "error", text: "Select a CRM contact with a phone number before sending SMS." });
      return;
    }
    if (!smsBody.trim()) return;

    setSendingSms(true);
    try {
      const response = await authFetch(`${API}/api/telnyx/sms`, {
        method: "POST",
        body: JSON.stringify({
          to: primaryPhone,
          body: smsBody.trim(),
          person_id: selectedPerson.id,
          deal_id: selectedDeal?.id ?? null,
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, "Failed to send the Telnyx SMS."));
      }
      setSmsBody("");
      setNotice({ tone: "success", text: `SMS queued for ${selectedPerson.name}.` });
      await refreshCurrentPerson();
    } catch (error) {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Failed to send the Telnyx SMS." });
    } finally {
      setSendingSms(false);
    }
  }, [primaryPhone, refreshCurrentPerson, selectedDeal?.id, selectedPerson, smsBody]);

  return (
    <div className="grid h-full min-h-0 grid-cols-1 overflow-hidden lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="flex min-h-0 flex-col border-r border-warroom-border bg-warroom-surface/60">
        <div className="border-b border-warroom-border px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
            <PhoneCall size={16} className="text-warroom-accent" />
            Communications Console
          </div>
          <p className="mt-1 text-xs text-warroom-muted">Pick a CRM contact, then handle the call, SMS, and operator context from one surface.</p>
          <div className="relative mt-4">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-warroom-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search CRM contacts..."
              className="w-full rounded-lg border border-warroom-border bg-warroom-bg py-2 pl-9 pr-3 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:border-warroom-accent/60 focus:outline-none"
            />
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {peopleLoading && people.length === 0 ? <LoadingState message="Loading CRM contacts..." /> : null}
          {!peopleLoading && peopleError ? <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{peopleError}</div> : null}
          {!peopleLoading && !peopleError && people.length === 0 ? (
            <EmptyState
              icon={<Phone size={30} />}
              title="No contacts found"
              description="Try a different CRM search to start the operator flow."
            />
          ) : null}

          <div className="space-y-2">
            {people.map((person) => {
              const isActive = person.id === selectedPerson?.id;
              return (
                <button
                  key={person.id}
                  type="button"
                  onClick={() => void loadPersonBundle(person)}
                  className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                    isActive
                      ? "border-warroom-accent bg-warroom-accent/10"
                      : "border-warroom-border bg-warroom-bg/60 hover:border-warroom-accent/40 hover:bg-warroom-bg"
                  }`}
                >
                  <div className="text-sm font-medium text-warroom-text">{person.name}</div>
                  <div className="mt-1 text-xs text-warroom-muted">{person.organization_name || person.job_title || "No organization linked"}</div>
                  <div className="mt-2 space-y-1 text-xs text-warroom-muted">
                    <div className="flex items-center gap-1.5"><Phone size={12} />{getPrimaryValue(person.contact_numbers)}</div>
                    <div className="flex items-center gap-1.5"><Mail size={12} />{getPrimaryValue(person.emails)}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </aside>

      <section className="min-h-0 overflow-y-auto bg-warroom-bg p-6">
        {!selectedPerson ? (
          <EmptyState
            icon={<PhoneCall size={36} />}
            title="Select a contact"
            description="Choose a CRM contact from the left rail to open the dedicated operator workspace."
          />
        ) : (
          <div className="space-y-6">
            <div className="flex flex-col gap-4 rounded-2xl border border-warroom-border bg-warroom-surface p-5 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="flex items-center gap-2 text-lg font-semibold text-warroom-text">
                  <PhoneCall size={18} className="text-warroom-accent" />
                  {selectedPerson.name}
                </div>
                <div className="mt-2 flex flex-wrap gap-4 text-sm text-warroom-muted">
                  <span className="flex items-center gap-2"><Phone size={14} />{primaryPhone}</span>
                  <span className="flex items-center gap-2"><Mail size={14} />{primaryEmail}</span>
                  <span className="flex items-center gap-2"><Building2 size={14} />{selectedPerson.organization_name || "No organization linked"}</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void refreshCurrentPerson()}
                  disabled={bundleLoading}
                  className="inline-flex items-center gap-2 rounded-lg border border-warroom-border px-3 py-2 text-sm text-warroom-text transition hover:border-warroom-accent/40 disabled:opacity-50"
                >
                  {bundleLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  Refresh context
                </button>
              </div>
            </div>

            {notice ? (
              <div className={`rounded-xl border px-4 py-3 text-sm ${NOTICE_STYLES[notice.tone]}`}>
                {notice.text}
              </div>
            ) : null}

            {detailsError ? (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{detailsError}</div>
            ) : null}

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
              <div className="space-y-6">
                <div className="rounded-2xl border border-warroom-border bg-warroom-surface p-5">
                  <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <h2 className="text-sm font-semibold text-warroom-text">Live call controls</h2>
                      <p className="mt-1 text-xs text-warroom-muted">Handle outbound dialing, incoming answer/reject, hangup, and operator speech from the same Telnyx-powered console.</p>
                    </div>
                    <div className="rounded-full border border-warroom-border bg-warroom-bg px-3 py-1 text-xs text-warroom-muted">
                      {activeCall ? `Call status: ${activeCall.status}` : "No live call started"}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
                    <div className="rounded-xl border border-warroom-border bg-warroom-bg/60 p-4">
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Call target</div>
                      <div className="mt-2 text-lg font-semibold text-warroom-text">{activeCall?.phoneNumber || primaryPhone}</div>
                      <div className="mt-1 text-sm text-warroom-muted">CRM contact: {selectedPerson.name}</div>
                      {activeCall?.direction ? <div className="mt-2 text-xs text-warroom-muted capitalize">Direction: {activeCall.direction}</div> : null}
                      {activeCall?.callControlId ? <div className="mt-2 text-xs text-warroom-muted">Call control ID: {activeCall.callControlId}</div> : null}
                      {activeCall?.callSessionId ? <div className="mt-1 text-xs text-warroom-muted">Call session ID: {activeCall.callSessionId}</div> : null}
                    </div>

                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        onClick={() => void handleDial()}
                        disabled={dialing || primaryPhone === "—" || Boolean(pendingIncomingCall)}
                        className="inline-flex items-center justify-center gap-2 rounded-lg bg-warroom-accent px-3 py-2.5 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:opacity-50"
                      >
                        {dialing ? <Loader2 size={14} className="animate-spin" /> : <PhoneCall size={14} />}
                        Start call
                      </button>
                      {pendingIncomingCall ? (
                        <>
                          <button
                            type="button"
                            onClick={() => void handleAnswer()}
                            disabled={answering || !pendingIncomingCall.callControlId}
                            className="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-3 py-2.5 text-sm font-medium text-white transition hover:bg-green-500 disabled:opacity-50"
                          >
                            {answering ? <Loader2 size={14} className="animate-spin" /> : <PhoneCall size={14} />}
                            Answer incoming
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleReject()}
                            disabled={rejecting || !pendingIncomingCall.callControlId}
                            className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-400/40 px-3 py-2.5 text-sm text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
                          >
                            {rejecting ? <Loader2 size={14} className="animate-spin" /> : <Phone size={14} />}
                            Reject incoming
                          </button>
                        </>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => void handleHangup()}
                        disabled={hangingUp || !activeCall?.callControlId || Boolean(pendingIncomingCall)}
                        className="inline-flex items-center justify-center gap-2 rounded-lg border border-warroom-border px-3 py-2.5 text-sm text-warroom-text transition hover:border-red-400/40 hover:text-red-300 disabled:opacity-50"
                      >
                        {hangingUp ? <Loader2 size={14} className="animate-spin" /> : <Phone size={14} />}
                        Hang up
                      </button>
                    </div>
                  </div>

                  <div className="mt-5 rounded-xl border border-warroom-border bg-warroom-bg/50 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-warroom-text">
                      <Volume2 size={15} className="text-warroom-accent" />
                      Operator speech prompt
                    </div>
                    <p className="mt-1 text-xs text-warroom-muted">Send a spoken line into the live Telnyx call without leaving the console.</p>
                    <textarea
                      value={speechText}
                      onChange={(event) => setSpeechText(event.target.value)}
                      placeholder="Example: Hi, this is War Room calling to follow up on your inquiry..."
                      className="mt-3 min-h-[92px] w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:border-warroom-accent/60 focus:outline-none"
                    />
                    <div className="mt-3 flex justify-end">
                      <button
                        type="button"
                        onClick={() => void handleSpeak()}
                        disabled={speaking || !speechText.trim() || !liveCallReadyForSpeech}
                        className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-3 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:opacity-50"
                      >
                        {speaking ? <Loader2 size={14} className="animate-spin" /> : <Volume2 size={14} />}
                        Speak on call
                      </button>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-warroom-border bg-warroom-surface p-5">
                  <div className="flex items-center gap-2 text-sm font-semibold text-warroom-text">
                    <MessageSquare size={15} className="text-warroom-accent" />
                    SMS operator flow
                  </div>
                  <p className="mt-1 text-xs text-warroom-muted">Outbound messages reuse the existing Telnyx SMS endpoint and link back to the selected CRM person/deal context.</p>
                  <textarea
                    value={smsBody}
                    onChange={(event) => setSmsBody(event.target.value)}
                    placeholder="Write the follow-up text you want to send..."
                    className="mt-3 min-h-[120px] w-full rounded-xl border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text placeholder:text-warroom-muted/60 focus:border-warroom-accent/60 focus:outline-none"
                  />
                  <div className="mt-3 flex items-center justify-between gap-3 text-xs text-warroom-muted">
                    <div>Linked deal: {selectedDeal?.title || "None selected"}</div>
                    <button
                      type="button"
                      onClick={() => void handleSendSms()}
                      disabled={sendingSms || !smsBody.trim() || primaryPhone === "—"}
                      className="inline-flex items-center gap-2 rounded-lg bg-warroom-accent px-3 py-2 text-sm font-medium text-white transition hover:bg-warroom-accent/80 disabled:opacity-50"
                    >
                      {sendingSms ? <Loader2 size={14} className="animate-spin" /> : <MessageSquare size={14} />}
                      Send SMS
                    </button>
                  </div>
                </div>

                <div className="rounded-2xl border border-warroom-border bg-warroom-surface p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 className="text-sm font-semibold text-warroom-text">Communications timeline</h2>
                      <p className="mt-1 text-xs text-warroom-muted">Unified CRM history across calls, SMS, and email for the selected operator context.</p>
                    </div>
                    <div className="rounded-full border border-warroom-border bg-warroom-bg px-3 py-1 text-xs text-warroom-muted">
                      {history.length} item{history.length === 1 ? "" : "s"}
                    </div>
                  </div>

                  {bundleLoading ? <LoadingState message="Loading communications timeline..." /> : null}
                  {!bundleLoading && history.length === 0 ? (
                    <EmptyState
                      icon={<Phone size={30} />}
                      title="No communications yet"
                      description="Calls, SMS messages, and linked email activity will appear here for the selected CRM contact."
                    />
                  ) : null}

                  {!bundleLoading && history.length > 0 ? (
                    <div className="mt-4 divide-y divide-warroom-border">
                      {history.map((item) => {
                        const counterpart = item.direction === "outbound" ? item.to_number : item.from_number;
                        return (
                          <div key={item.entry_id} className="py-4 first:pt-0 last:pb-0">
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5 rounded-full border border-warroom-border bg-warroom-bg p-2 text-warroom-muted">
                                {item.channel === "email" ? <Mail size={14} /> : item.channel === "sms" ? <MessageSquare size={14} /> : <Phone size={14} />}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <div className="text-sm font-medium text-warroom-text">{item.title || `${getHistoryChannelLabel(item)} activity`}</div>
                                  <div className="text-xs text-warroom-muted">{formatTimestamp(item.occurred_at || item.created_at)}</div>
                                </div>
                                <div className="mt-2 flex flex-wrap gap-2 text-xs text-warroom-muted">
                                  <span className="rounded-full border border-warroom-border bg-warroom-bg px-2 py-1">{getHistoryChannelLabel(item)}</span>
                                  {item.direction ? <span className="rounded-full border border-warroom-border bg-warroom-bg px-2 py-1 capitalize">{item.direction}</span> : null}
                                  {item.status ? <span className="rounded-full border border-warroom-border bg-warroom-bg px-2 py-1 capitalize">{item.status}</span> : null}
                                  {counterpart ? <span className="rounded-full border border-warroom-border bg-warroom-bg px-2 py-1">{counterpart}</span> : null}
                                </div>
                                {item.content ? <p className="mt-3 whitespace-pre-wrap text-sm text-warroom-text/90">{item.content}</p> : null}
                                {item.recording_url ? (
                                  <a
                                    href={item.recording_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-3 inline-flex text-sm text-warroom-accent hover:underline"
                                  >
                                    Open recording
                                  </a>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="space-y-6">
                <div className="rounded-2xl border border-warroom-border bg-warroom-surface p-5">
                  <h2 className="text-sm font-semibold text-warroom-text">CRM contact context</h2>
                  <div className="mt-4 space-y-3 text-sm">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Name</div>
                      <div className="mt-1 text-warroom-text">{selectedPerson.name}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Job title</div>
                      <div className="mt-1 text-warroom-text">{selectedPerson.job_title || "—"}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Primary phone</div>
                      <div className="mt-1 text-warroom-text">{primaryPhone}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Primary email</div>
                      <div className="mt-1 text-warroom-text">{primaryEmail}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-warroom-muted">Organization</div>
                      <div className="mt-1 text-warroom-text">{selectedPerson.organization_name || "—"}</div>
                    </div>
                  </div>
                </div>

                <AgentAssignmentCard
                  entityType="crm_contact"
                  entityId={selectedPerson.id}
                  initialAssignments={selectedPerson.agent_assignments}
                  title={`Work contact: ${selectedPerson.name}`}
                />

                <div className="rounded-2xl border border-warroom-border bg-warroom-surface p-5">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-sm font-semibold text-warroom-text">Deal context</h2>
                    <div className="text-xs text-warroom-muted">{deals.length} linked deal{deals.length === 1 ? "" : "s"}</div>
                  </div>

                  {deals.length > 0 ? (
                    <select
                      value={selectedDealId ?? ""}
                      onChange={(event) => setSelectedDealId(event.target.value ? Number(event.target.value) : null)}
                      className="mt-3 w-full rounded-lg border border-warroom-border bg-warroom-bg px-3 py-2 text-sm text-warroom-text focus:border-warroom-accent/60 focus:outline-none"
                    >
                      {deals.map((deal) => (
                        <option key={deal.id} value={deal.id}>{deal.title}</option>
                      ))}
                    </select>
                  ) : null}

                  {selectedDeal ? (
                    <div className="mt-4 space-y-3 text-sm">
                      <div>
                        <div className="text-xs uppercase tracking-wide text-warroom-muted">Stage</div>
                        <div className="mt-1 text-warroom-text">{selectedDeal.stage_name || selectedDeal.stage?.name || "—"}</div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-wide text-warroom-muted">Value</div>
                        <div className="mt-1 text-warroom-text">{formatMoney(selectedDeal.deal_value)}</div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-wide text-warroom-muted">Status</div>
                        <div className="mt-1 text-warroom-text">{getDealStatusLabel(selectedDeal.status)}</div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-wide text-warroom-muted">Expected close</div>
                        <div className="mt-1 text-warroom-text">{selectedDeal.expected_close_date || "—"}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-4 rounded-xl border border-dashed border-warroom-border px-4 py-3 text-sm text-warroom-muted">
                      No linked deals yet. SMS can still be sent at the contact level.
                    </div>
                  )}
                </div>

                {selectedDeal ? (
                  <AgentAssignmentCard
                    entityType="crm_deal"
                    entityId={selectedDeal.id}
                    initialAssignments={selectedDeal.agent_assignments}
                    title={`Work deal: ${selectedDeal.title}`}
                  />
                ) : null}
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}