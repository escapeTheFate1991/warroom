"use client";

import { useState } from "react";
import { Phone, MessageSquare, Mail, X, Send, Loader2 } from "lucide-react";
import { API, authFetch } from "@/lib/api";

/* ── Types ─────────────────────────────────────────────── */

interface QuickActionsProps {
  phone?: string | null;
  email?: string | null;
  name?: string;
  className?: string;
  size?: "sm" | "md";
}

type ModalMode = "sms" | "email" | "call" | null;

/* ── Component ─────────────────────────────────────────── */

export default function QuickActions({ phone, email, name, className = "", size = "sm" }: QuickActionsProps) {
  const [modal, setModal] = useState<ModalMode>(null);
  const [body, setBody] = useState("");
  const [subject, setSubject] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const iconSize = size === "sm" ? 12 : 14;
  const btnClass = size === "sm"
    ? "p-1.5 rounded-lg transition"
    : "p-2 rounded-xl transition";

  const handleSMS = async () => {
    if (!phone || !body.trim()) return;
    setSending(true);
    setResult(null);
    try {
      const res = await authFetch(`${API}/api/twilio/sms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: phone, body: body.trim() }),
      });
      if (res.ok) {
        setResult({ ok: true, msg: "SMS sent" });
        setBody("");
        setTimeout(() => { setModal(null); setResult(null); }, 2000);
      } else {
        const data = await res.json().catch(() => ({}));
        setResult({ ok: false, msg: data.detail || "Failed to send SMS" });
      }
    } catch {
      setResult({ ok: false, msg: "Network error" });
    } finally {
      setSending(false);
    }
  };

  const handleCall = async () => {
    if (!phone) return;
    setSending(true);
    setResult(null);
    try {
      const res = await authFetch(`${API}/api/twilio/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: phone }),
      });
      if (res.ok) {
        setResult({ ok: true, msg: "Call initiated" });
        setTimeout(() => { setModal(null); setResult(null); }, 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        setResult({ ok: false, msg: data.detail || "Failed to initiate call" });
      }
    } catch {
      setResult({ ok: false, msg: "Network error" });
    } finally {
      setSending(false);
    }
  };

  const handleEmail = async () => {
    if (!email || !body.trim()) return;
    setSending(true);
    setResult(null);
    try {
      const res = await authFetch(`${API}/api/email/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: email, subject: subject || `Message from War Room`, body: body.trim() }),
      });
      if (res.ok) {
        setResult({ ok: true, msg: "Email sent" });
        setBody("");
        setSubject("");
        setTimeout(() => { setModal(null); setResult(null); }, 2000);
      } else {
        const data = await res.json().catch(() => ({}));
        setResult({ ok: false, msg: data.detail || "Failed to send email" });
      }
    } catch {
      setResult({ ok: false, msg: "Network error" });
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div className={`flex items-center gap-1 ${className}`} onClick={(e) => e.stopPropagation()}>
        {phone && (
          <>
            <button
              onClick={() => setModal("sms")}
              className={`${btnClass} text-cyan-400 hover:bg-cyan-500/10`}
              title="Send SMS"
            >
              <MessageSquare size={iconSize} />
            </button>
            <button
              onClick={() => setModal("call")}
              className={`${btnClass} text-green-400 hover:bg-green-500/10`}
              title="Call"
            >
              <Phone size={iconSize} />
            </button>
          </>
        )}
        {email && (
          <button
            onClick={() => setModal("email")}
            className={`${btnClass} text-blue-400 hover:bg-blue-500/10`}
            title="Send Email"
          >
            <Mail size={iconSize} />
          </button>
        )}
      </div>

      {/* ── Modal ── */}
      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => { setModal(null); setResult(null); }}>
          <div className="bg-warroom-surface border border-warroom-border rounded-2xl w-full max-w-md overflow-hidden" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-warroom-border">
              <div className="flex items-center gap-2">
                {modal === "sms" && <MessageSquare size={16} className="text-cyan-400" />}
                {modal === "call" && <Phone size={16} className="text-green-400" />}
                {modal === "email" && <Mail size={16} className="text-blue-400" />}
                <h3 className="text-sm font-semibold text-warroom-text">
                  {modal === "sms" ? "Send SMS" : modal === "call" ? "Make Call" : "Send Email"}
                </h3>
              </div>
              <button onClick={() => { setModal(null); setResult(null); }} className="p-1 text-warroom-muted hover:text-warroom-text">
                <X size={16} />
              </button>
            </div>

            {/* Body */}
            <div className="p-5 space-y-4">
              {/* To */}
              <div>
                <label className="text-xs text-warroom-muted mb-1 block">To</label>
                <p className="text-sm text-warroom-text">
                  {name && <span className="font-medium">{name} · </span>}
                  {modal === "email" ? email : phone}
                </p>
              </div>

              {/* Call confirmation */}
              {modal === "call" && (
                <div className="bg-green-500/5 border border-green-500/20 rounded-xl p-4 text-center">
                  <Phone size={24} className="text-green-400 mx-auto mb-2" />
                  <p className="text-sm text-warroom-text">Ready to call {name || phone}?</p>
                  <p className="text-xs text-warroom-muted mt-1">This will initiate a call via Twilio</p>
                </div>
              )}

              {/* Email subject */}
              {modal === "email" && (
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">Subject</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Email subject..."
                    className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50"
                  />
                </div>
              )}

              {/* Message body (SMS & Email) */}
              {(modal === "sms" || modal === "email") && (
                <div>
                  <label className="text-xs text-warroom-muted mb-1 block">Message</label>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    placeholder={modal === "sms" ? "Type your message..." : "Write your email..."}
                    rows={modal === "sms" ? 3 : 5}
                    className="w-full bg-warroom-bg border border-warroom-border rounded-xl px-3 py-2 text-sm text-warroom-text placeholder-warroom-muted/40 focus:outline-none focus:border-warroom-accent/50 resize-none"
                  />
                  {modal === "sms" && (
                    <p className="text-[10px] text-warroom-muted mt-1">{body.length}/160 characters</p>
                  )}
                </div>
              )}

              {/* Result */}
              {result && (
                <p className={`text-xs ${result.ok ? "text-green-400" : "text-red-400"}`}>
                  {result.ok ? "✓" : "✗"} {result.msg}
                </p>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setModal(null); setResult(null); }}
                  className="px-3 py-2 text-xs text-warroom-muted hover:text-warroom-text transition"
                >
                  Cancel
                </button>
                <button
                  onClick={modal === "sms" ? handleSMS : modal === "call" ? handleCall : handleEmail}
                  disabled={sending || (modal !== "call" && !body.trim())}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-white transition disabled:opacity-40 ${
                    modal === "sms" ? "bg-cyan-600 hover:bg-cyan-500" :
                    modal === "call" ? "bg-green-600 hover:bg-green-500" :
                    "bg-blue-600 hover:bg-blue-500"
                  }`}
                >
                  {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                  {modal === "call" ? "Call Now" : "Send"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
