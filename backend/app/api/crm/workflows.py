"""CRM workflow template and versioned workflow endpoints."""

from copy import deepcopy
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db
from app.models.crm.automation import Workflow, WorkflowTemplate
from app.models.crm.audit import AuditLog
from .schemas import WorkflowCloneRequest, WorkflowCreate, WorkflowResponse, WorkflowTemplateResponse, WorkflowUpdate
from .workflow_contract import coerce_workflow_steps, normalize_workflow_payload, workflow_contract_fields

logger = logging.getLogger(__name__)
router = APIRouter()

WORKFLOW_TEMPLATE_SEEDS: List[Dict[str, Any]] = [
    {
        "seed_key": "new-lead-follow-up",
        "name": "New lead follow-up",
        "description": "Kick off a first-touch follow-up whenever a new CRM contact is created.",
        "category": "sales",
        "entity_type": "person",
        "event": "created",
        "condition_type": "and",
        "conditions": [{"field": "emails", "operator": "not_empty"}],
        "actions": [
            {"type": "create_activity", "activity_type": "task", "title": "Call new lead within 1 business day"},
            {"type": "send_email", "subject": "Welcome to WAR ROOM", "body": "Share a quick intro and next steps."},
        ],
    },
    {
        "seed_key": "deal-stage-stall-recovery",
        "name": "Deal stage stall recovery",
        "description": "Watch for deals that sit too long in the same stage and create a recovery sequence.",
        "category": "pipeline",
        "entity_type": "deal",
        "event": "stage_changed",
        "condition_type": "and",
        "conditions": [
            {"field": "days_in_stage", "operator": "gte", "value": 7},
            {"field": "status", "operator": "equals", "value": None},
        ],
        "actions": [
            {"type": "create_activity", "activity_type": "task", "title": "Rescue stalled deal"},
            {"type": "notify_owner", "channel": "inbox", "message": "Deal stalled for 7+ days in current stage."},
        ],
    },
    {
        "seed_key": "proposal-follow-up-reminder",
        "name": "Proposal follow-up reminder",
        "description": "Create a reminder cadence after a proposal or quote event is recorded.",
        "category": "post-sale",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [{"field": "quote_count", "operator": "gte", "value": 1}],
        "actions": [
            {"type": "delay", "duration": "P2D"},
            {"type": "create_activity", "activity_type": "task", "title": "Check in on proposal after 48 hours"},
        ],
    },
    {
        "seed_key": "starter-real-estate-new-lead-instant-response",
        "name": "Real estate — new lead instant response",
        "description": "Acknowledge new buyer or seller inquiries fast, draft the first reply with AI, and escalate if the lead sits untouched.",
        "category": "Real estate • Lead response",
        "entity_type": "person",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "emails", "operator": "not_empty"},
            {"field": "lead_source", "operator": "is_set"},
        ],
        "actions": [
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Respond to new lead within 5 minutes",
                "sla_duration": "PT5M",
                "escalation": {
                    "after": "PT10M",
                    "channel": "inbox",
                    "notify": "team_lead",
                    "message": "Unresponded real-estate lead needs backup coverage.",
                },
            },
            {
                "type": "ai_draft_message",
                "channel": "sms",
                "goal": "Draft a short first-touch text that acknowledges the inquiry and asks for the best callback window.",
                "inputs": ["lead source", "property of interest", "owner notes"],
                "approval_required": True,
                "approval_reason": "Human must verify listing availability, pricing, and fair-housing-safe wording before send.",
            },
            {
                "type": "send_sms",
                "channel": "sms",
                "message": "Send the approved AI draft and attach the booking link placeholder if enabled.",
            },
        ],
    },
    {
        "seed_key": "starter-real-estate-property-inquiry-follow-up",
        "name": "Real estate — property inquiry follow-up",
        "description": "Convert a property-specific inquiry into a fast, compliant follow-up sequence with AI summarization and approval gates.",
        "category": "Real estate • Property follow-up",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "stage", "operator": "equals", "value": "property_inquiry"},
            {"field": "property_id", "operator": "is_set"},
        ],
        "actions": [
            {
                "type": "ai_summarize_context",
                "channel": "inbox",
                "goal": "Summarize the inquiry, preferred property attributes, and urgency for the assigned agent.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Call or text back on the property inquiry within 30 minutes",
                "sla_duration": "PT30M",
                "escalation": {
                    "after": "PT2H",
                    "channel": "inbox",
                    "notify": "broker_on_duty",
                    "message": "Property inquiry has not received a compliant follow-up.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["listing claims", "availability promises", "pricing statements", "disclosure-sensitive language"],
                "approver": "assigned_agent_or_broker",
                "notes": "Approve any property-specific response before it is sent.",
            },
            {
                "type": "send_email",
                "channel": "email",
                "subject": "Property inquiry follow-up",
                "body": "Use the approved draft, attach brochure placeholders, and invite the lead to book a showing.",
            },
        ],
    },
    {
        "seed_key": "starter-real-estate-stale-lead-reactivation",
        "name": "Real estate — stale lead reactivation",
        "description": "Prioritize dormant leads, draft a reactivation message, and sequence follow-up without mutating the starter seed.",
        "category": "Real estate • Reactivation",
        "entity_type": "person",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "days_since_last_contact", "operator": "gte", "value": 14},
            {"field": "status", "operator": "equals", "value": "open"},
        ],
        "actions": [
            {
                "type": "ai_prioritize_lead",
                "channel": "inbox",
                "goal": "Score the stale lead by recency, source quality, and property intent before outreach.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Review reactivation priority and approve outreach within 1 business day",
                "sla_duration": "P1D",
                "escalation": {
                    "after": "P2D",
                    "channel": "inbox",
                    "notify": "lead_owner_manager",
                    "message": "Dormant lead has not entered the reactivation sequence.",
                },
            },
            {
                "type": "ai_draft_message",
                "channel": "email",
                "goal": "Draft a concise reactivation email with a clear next step and updated preferences prompt.",
            },
            {"type": "send_email", "channel": "email", "subject": "Still searching?", "body": "Send the approved reactivation email."},
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["rate or incentive offers", "property-specific claims", "transaction-critical outreach"],
                "approver": "assigned_agent",
                "notes": "Require approval before offering incentives or property-specific updates.",
            },
        ],
    },
    {
        "seed_key": "starter-real-estate-deal-stage-task-orchestration",
        "name": "Real estate — deal-stage task orchestration",
        "description": "When a deal changes stage, summarize context, assign checklist tasks, and route sensitive deal moves through human approval.",
        "category": "Real estate • Deal orchestration",
        "entity_type": "deal",
        "event": "stage_changed",
        "condition_type": "and",
        "conditions": [
            {"field": "stage", "operator": "in", "value": ["showing", "offer", "under_contract"]},
        ],
        "actions": [
            {
                "type": "ai_summarize_context",
                "channel": "inbox",
                "goal": "Summarize stage-change context, blockers, and the next recommended tasks for the agent and coordinator.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Review stage checklist within 15 minutes",
                "sla_duration": "PT15M",
                "escalation": {
                    "after": "PT1H",
                    "channel": "inbox",
                    "notify": "transaction_coordinator",
                    "message": "Stage-change checklist has not been acknowledged.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["offer terms", "price changes", "legal language", "transaction-critical communications"],
                "approver": "agent_or_broker",
                "notes": "Sensitive stage transitions require a human review before outbound communication.",
            },
            {
                "type": "notify_owner",
                "channel": "inbox",
                "message": "Assign the stage checklist tasks and confirm who owns lender, title, and client follow-up.",
            },
        ],
    },
    {
        "seed_key": "starter-real-estate-post-close-nurture-review-ask",
        "name": "Real estate — post-close nurture + review ask",
        "description": "Start a post-close nurture cadence, thank the client, and stage a review/referral ask with human approval for incentives.",
        "category": "Real estate • Post-close nurture",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "status", "operator": "equals", "value": "won"},
            {"field": "closed_at", "operator": "is_set"},
        ],
        "actions": [
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Confirm post-close handoff within 1 business day",
                "sla_duration": "P1D",
                "escalation": {
                    "after": "P2D",
                    "channel": "inbox",
                    "notify": "client_success_owner",
                    "message": "Closed deal has not entered the post-close nurture sequence.",
                },
            },
            {"type": "delay", "duration": "P2D"},
            {
                "type": "ai_draft_message",
                "channel": "email",
                "goal": "Draft a thank-you email with move-in resources and the next touchpoint.",
            },
            {"type": "send_email", "channel": "email", "subject": "Thank you and next steps", "body": "Send the approved post-close email."},
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["review incentives", "referral offers", "warranty or legal claims"],
                "approver": "agent_or_broker",
                "notes": "Review any incentive or claim before the review ask goes out.",
            },
            {"type": "send_sms", "channel": "sms", "message": "Send the approved review or referral follow-up text after the nurture delay."},
        ],
    },
    {
        "seed_key": "starter-home-services-missed-call-after-hours-capture",
        "name": "Home services — missed-call / after-hours capture",
        "description": "Capture after-hours missed calls, summarize urgency, and queue a callback without promising unsupported pricing or ETAs.",
        "category": "Home services • Missed calls",
        "entity_type": "activity",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "missed_call"},
            {"field": "time_window", "operator": "equals", "value": "after_hours"},
        ],
        "actions": [
            {
                "type": "ai_extract_details",
                "channel": "inbox",
                "goal": "Extract service type, urgency, location, and preferred callback window from voicemail or notes.",
            },
            {
                "type": "send_sms",
                "channel": "sms",
                "message": "Send the after-hours acknowledgment with business-hours callback expectations and an emergency disclaimer placeholder.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Return missed call within 15 minutes of the next business opening",
                "sla_duration": "PT15M",
                "escalation": {
                    "after": "PT30M",
                    "channel": "inbox",
                    "notify": "dispatch_lead",
                    "message": "After-hours missed call has not been returned.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["emergency dispatch promises", "pricing estimates", "arrival-time commitments"],
                "approver": "dispatcher",
                "notes": "A human must approve any ETA or quote language before send.",
            },
        ],
    },
    {
        "seed_key": "starter-home-services-appointment-confirmation-reminder",
        "name": "Home services — appointment confirmation + reminder",
        "description": "Confirm newly booked appointments, send timed reminders, and escalate missing confirmations back to dispatch.",
        "category": "Home services • Appointment reminders",
        "entity_type": "activity",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "appointment"},
            {"field": "status", "operator": "equals", "value": "scheduled"},
        ],
        "actions": [
            {
                "type": "ai_extract_details",
                "channel": "inbox",
                "goal": "Extract appointment time, service window, address, and technician notes for outbound reminders.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Confirm the appointment within 30 minutes of booking",
                "sla_duration": "PT30M",
                "escalation": {
                    "after": "PT1H",
                    "channel": "inbox",
                    "notify": "dispatch_lead",
                    "message": "Scheduled appointment is still missing a confirmation touch.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["reschedule fees", "permit or compliance instructions", "scope-change pricing"],
                "approver": "dispatcher",
                "notes": "Exceptions require a human-approved message before send.",
            },
            {"type": "send_sms", "channel": "sms", "message": "Send appointment confirmation with configurable arrival window placeholders."},
            {"type": "send_email", "channel": "email", "subject": "Appointment confirmed", "body": "Send the service appointment confirmation email."},
            {"type": "delay", "duration": "P1D"},
            {"type": "send_sms", "channel": "sms", "message": "Send the 24-hour reminder and preparation checklist."},
        ],
    },
    {
        "seed_key": "starter-home-services-on-the-way-delay-notification",
        "name": "Home services — on-the-way / delay notification",
        "description": "Draft technician ETA updates, notify customers about delays, and require a human check before new promises go out.",
        "category": "Home services • Dispatch updates",
        "entity_type": "activity",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "appointment"},
            {"field": "status", "operator": "in", "value": ["on_the_way", "delayed"]},
        ],
        "actions": [
            {
                "type": "ai_draft_message",
                "channel": "sms",
                "goal": "Draft an ETA update that reflects route status, technician name, and revised service window.",
                "approval_required": True,
                "approval_reason": "A human must confirm any new arrival-time promise before notifying the customer.",
            },
            {"type": "send_sms", "channel": "sms", "message": "Send the approved on-the-way or delay update."},
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Confirm ETA update within 10 minutes of route change",
                "sla_duration": "PT10M",
                "escalation": {
                    "after": "PT15M",
                    "channel": "inbox",
                    "notify": "dispatch_lead",
                    "message": "Customer has not been updated about the route change.",
                },
            },
            {"type": "notify_owner", "channel": "inbox", "message": "If delivery is uncertain, call the customer manually and log the conversation."},
        ],
    },
    {
        "seed_key": "starter-home-services-estimate-follow-up",
        "name": "Home services — estimate follow-up",
        "description": "Chase open estimates with AI prioritization and reminder messaging while forcing human review for pricing changes.",
        "category": "Home services • Estimate follow-up",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "estimate_sent", "operator": "equals", "value": True},
            {"field": "status", "operator": "equals", "value": "open"},
        ],
        "actions": [
            {
                "type": "ai_prioritize_lead",
                "channel": "inbox",
                "goal": "Rank open estimates by value, urgency, and recency so the team can work the best opportunities first.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Review estimate follow-up within 2 days",
                "sla_duration": "P2D",
                "escalation": {
                    "after": "P5D",
                    "channel": "inbox",
                    "notify": "sales_manager",
                    "message": "Estimate follow-up is overdue and needs intervention.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["discount changes", "quote revisions", "scope updates", "payment-term changes"],
                "approver": "estimator_or_manager",
                "notes": "Any pricing or scope change must be human-approved before send.",
            },
            {
                "type": "send_email",
                "channel": "email",
                "subject": "Following up on your estimate",
                "body": "Send the approved estimate follow-up email with booking and financing placeholders if enabled.",
            },
            {"type": "delay", "duration": "P3D"},
            {"type": "send_sms", "channel": "sms", "message": "Send the estimate reminder text if there is still no reply."},
        ],
    },
    {
        "seed_key": "starter-home-services-completed-job-review-payment-follow-up",
        "name": "Home services — completed-job review + payment follow-up",
        "description": "Wrap up completed jobs with AI summaries, review asks, and payment reminders while keeping refunds and credits behind approval.",
        "category": "Home services • Post-job follow-up",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "job_status", "operator": "equals", "value": "completed"},
            {"field": "invoice_status", "operator": "in", "value": ["sent", "partially_paid", "unpaid"]},
        ],
        "actions": [
            {
                "type": "ai_summarize_context",
                "channel": "inbox",
                "goal": "Summarize completed work, open issues, and invoice status before customer follow-up.",
            },
            {
                "type": "create_activity",
                "activity_type": "task",
                "title": "Send post-job wrap-up within 1 business day",
                "sla_duration": "P1D",
                "escalation": {
                    "after": "P2D",
                    "channel": "inbox",
                    "notify": "service_manager",
                    "message": "Completed job has not received a review or payment follow-up.",
                },
            },
            {
                "type": "approval_gate",
                "channel": "manual",
                "required_for": ["refunds", "credits", "warranty claims", "payment-plan changes"],
                "approver": "service_manager",
                "notes": "Require approval before discussing concessions or payment changes.",
            },
            {"type": "send_email", "channel": "email", "subject": "Thanks for choosing us", "body": "Send the post-job thank-you, review ask, and invoice summary."},
            {"type": "delay", "duration": "P2D"},
            {"type": "send_sms", "channel": "sms", "message": "Send the approved payment reminder or review nudge if the invoice remains open."},
        ],
    },
    # ── Healthcare / Appointment Management ──
    {
        "seed_key": "appointment-confirmation-sms",
        "name": "Appointment confirmation via SMS",
        "description": "Automatically send an SMS confirmation when an appointment is booked, with a reminder 24 hours before.",
        "category": "Healthcare • Appointments",
        "entity_type": "activity",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "appointment"},
        ],
        "actions": [
            {"type": "send_sms", "channel": "sms", "message": "Confirm the appointment details — date, time, location, and any preparation instructions."},
            {"type": "delay", "duration": "PT24H_BEFORE"},
            {"type": "send_sms", "channel": "sms", "message": "Send a friendly reminder 24 hours before the appointment with check-in instructions."},
        ],
    },
    {
        "seed_key": "appointment-no-show-follow-up",
        "name": "No-show follow up",
        "description": "When a patient or client misses an appointment, automatically reach out to reschedule.",
        "category": "Healthcare • Appointments",
        "entity_type": "activity",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "status", "operator": "equals", "value": "no_show"},
        ],
        "actions": [
            {"type": "send_sms", "channel": "sms", "message": "We missed you today. Would you like to reschedule? Reply YES and we'll find a time that works."},
            {"type": "delay", "duration": "P1D"},
            {"type": "create_activity", "activity_type": "task", "title": "Follow up on no-show — call to reschedule"},
            {"type": "notify_owner", "channel": "inbox", "message": "Patient/client no-show. SMS sent, follow-up task created."},
        ],
    },
    {
        "seed_key": "appointment-cancellation-reschedule",
        "name": "Cancellation and reschedule offer",
        "description": "When an appointment is cancelled, offer to reschedule and optionally fill the slot from a waitlist.",
        "category": "Healthcare • Appointments",
        "entity_type": "activity",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "status", "operator": "equals", "value": "cancelled"},
        ],
        "actions": [
            {"type": "send_sms", "channel": "sms", "message": "Your appointment has been cancelled. Would you like to reschedule? We have openings this week."},
            {"type": "create_activity", "activity_type": "task", "title": "Check waitlist to fill cancelled slot"},
        ],
    },
    # ── IVR / Phone System ──
    {
        "seed_key": "basic-ivr-call-routing",
        "name": "Phone menu and call routing",
        "description": "Set up an automated phone menu that greets callers, shares business hours, and routes them to the right department or voicemail.",
        "category": "Phone • IVR",
        "entity_type": "activity",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "incoming_call"},
        ],
        "actions": [
            {"type": "ai_generate", "goal": "Generate a professional greeting TwiML that welcomes the caller, states business hours, and offers options: Press 1 for sales, 2 for support, 3 for billing."},
            {"type": "make_call", "channel": "phone", "message": "Route the call based on the caller's selection or send to voicemail if outside business hours."},
            {"type": "create_activity", "activity_type": "task", "title": "Review incoming call and follow up if needed"},
        ],
    },
    {
        "seed_key": "after-hours-voicemail",
        "name": "After hours auto-response",
        "description": "When a call comes in outside business hours, play a message with your hours and offer to take a voicemail or send a callback SMS.",
        "category": "Phone • IVR",
        "entity_type": "activity",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "activity_type", "operator": "equals", "value": "incoming_call"},
            {"field": "time_of_day", "operator": "not_between", "value": "09:00-17:00"},
        ],
        "actions": [
            {"type": "send_sms", "channel": "sms", "message": "Thanks for calling! We're currently closed. Our hours are Mon-Fri 9am-5pm. We'll call you back on the next business day."},
            {"type": "create_activity", "activity_type": "task", "title": "Return after-hours call on next business day"},
            {"type": "notify_owner", "channel": "inbox", "message": "After-hours call received. SMS auto-response sent, callback task created."},
        ],
    },
    # ── General Business ──
    {
        "seed_key": "new-contact-welcome-sequence",
        "name": "Welcome sequence for new contacts",
        "description": "When a new contact is added, send a welcome email and schedule a follow-up call within 48 hours.",
        "category": "Sales",
        "entity_type": "person",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "emails", "operator": "not_empty"},
        ],
        "actions": [
            {"type": "send_email", "subject": "Welcome aboard!", "body": "Send a warm welcome with links to useful resources and next steps."},
            {"type": "delay", "duration": "P2D"},
            {"type": "create_activity", "activity_type": "task", "title": "Intro call with new contact"},
        ],
    },
    {
        "seed_key": "invoice-overdue-reminder",
        "name": "Overdue invoice reminder",
        "description": "Automatically send a polite reminder when an invoice becomes overdue, with escalating follow-ups.",
        "category": "Finance",
        "entity_type": "deal",
        "event": "updated",
        "condition_type": "and",
        "conditions": [
            {"field": "invoice_status", "operator": "equals", "value": "overdue"},
        ],
        "actions": [
            {"type": "send_email", "subject": "Friendly reminder: Invoice past due", "body": "Send a professional reminder about the outstanding balance with payment instructions."},
            {"type": "delay", "duration": "P7D"},
            {"type": "send_sms", "channel": "sms", "message": "Send a follow-up SMS reminder if the invoice is still unpaid after 7 days."},
            {"type": "create_activity", "activity_type": "task", "title": "Call about overdue invoice if still unpaid"},
        ],
    },
    # ── Contact Form Intake Pipeline ──
    {
        "seed_key": "contact-form-ai-intake",
        "name": "Contact form AI intake call",
        "description": "When a contact form is submitted, send a confirmation SMS, then call the prospect with an AI agent that asks about their pain points, services needed, and scheduling preference. Auto-creates a calendar event.",
        "category": "Sales • Intake",
        "entity_type": "contact_submission",
        "event": "created",
        "condition_type": "and",
        "conditions": [
            {"field": "phone", "operator": "not_empty"},
        ],
        "actions": [
            {"type": "send_email", "subject": "We received your request — here's what happens next", "body": "Auto-reply confirming receipt and letting them know a call is coming."},
            {"type": "send_sms", "channel": "sms", "message": "Confirmation SMS: we received your inquiry and will call you in a few minutes to schedule a consultation."},
            {"type": "delay", "duration": "PT2M"},
            {"type": "make_call", "channel": "phone", "message": "AI intake call: ask about pain points, services interested in, and scheduling preference."},
            {"type": "create_activity", "activity_type": "meeting", "title": "Consultation meeting — auto-scheduled from AI intake call"},
            {"type": "notify_owner", "channel": "inbox", "message": "New lead intake completed. Call transcript and meeting details available."},
        ],
    },
]


def _copy_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return deepcopy(fallback)
    return deepcopy(value)


def build_workflow_clone_from_template(template: Any, override_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a new workflow payload from an immutable template without mutating the template."""
    return {
        "name": override_data.get("name") or template.name,
        "description": override_data.get("description") if "description" in override_data else getattr(template, "description", None),
        "entity_type": override_data.get("entity_type") or template.entity_type,
        "event": override_data.get("event") or template.event,
        "condition_type": override_data.get("condition_type") or getattr(template, "condition_type", "and"),
        "conditions": coerce_workflow_steps(_copy_json(override_data.get("conditions"), getattr(template, "conditions", []))),
        "actions": coerce_workflow_steps(_copy_json(override_data.get("actions"), getattr(template, "actions", []))),
        "is_active": override_data.get("is_active", False),
        "template_id": getattr(template, "id", None),
        "derived_from_workflow_id": None,
        "root_workflow_id": None,
        "version": 1,
    }


def build_workflow_clone_from_workflow(workflow: Any, override_data: Dict[str, Any], *, next_version: int) -> Dict[str, Any]:
    """Build a new versioned workflow payload from an existing workflow without mutating the source."""
    root_workflow_id = getattr(workflow, "root_workflow_id", None) or workflow.id
    return {
        "name": override_data.get("name") or workflow.name,
        "description": override_data.get("description") if "description" in override_data else getattr(workflow, "description", None),
        "entity_type": override_data.get("entity_type") or workflow.entity_type,
        "event": override_data.get("event") or workflow.event,
        "condition_type": override_data.get("condition_type") or getattr(workflow, "condition_type", "and"),
        "conditions": coerce_workflow_steps(_copy_json(override_data.get("conditions"), getattr(workflow, "conditions", []))),
        "actions": coerce_workflow_steps(_copy_json(override_data.get("actions"), getattr(workflow, "actions", []))),
        "is_active": override_data.get("is_active", getattr(workflow, "is_active", False)),
        "template_id": getattr(workflow, "template_id", None),
        "derived_from_workflow_id": workflow.id,
        "root_workflow_id": root_workflow_id,
        "version": next_version,
    }


def _serialize_template(template: WorkflowTemplate) -> WorkflowTemplateResponse:
    return WorkflowTemplateResponse.model_validate(
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": getattr(template, "category", None),
            "entity_type": template.entity_type,
            "event": template.event,
            "condition_type": template.condition_type or "and",
            "conditions": coerce_workflow_steps(template.conditions),
            "actions": coerce_workflow_steps(template.actions),
            "is_seed": bool(getattr(template, "is_seed", False)),
            "seed_key": getattr(template, "seed_key", None),
            "version": getattr(template, "version", 1) or 1,
            "provenance": {
                "kind": "seed" if getattr(template, "is_seed", False) else "custom",
                "seed_key": getattr(template, "seed_key", None),
                "derived_from_template_id": getattr(template, "derived_from_template_id", None),
                "root_template_id": getattr(template, "root_template_id", None) or template.id,
                "version": getattr(template, "version", 1) or 1,
            },
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
    )


def _serialize_workflow(
    workflow: Workflow,
    template_map: Dict[int, WorkflowTemplate],
    lineage_map: Dict[int, Workflow],
) -> WorkflowResponse:
    template = template_map.get(workflow.template_id) if workflow.template_id else None
    source = lineage_map.get(workflow.derived_from_workflow_id) if workflow.derived_from_workflow_id else None
    root_id = workflow.root_workflow_id or workflow.id
    root = lineage_map.get(root_id)
    return WorkflowResponse.model_validate(
        {
            **workflow_contract_fields(workflow),
            "template_id": workflow.template_id,
            "derived_from_workflow_id": workflow.derived_from_workflow_id,
            "root_workflow_id": root_id,
            "version": getattr(workflow, "version", 1) or 1,
            "provenance": {
                "template_id": workflow.template_id,
                "template_name": getattr(template, "name", None),
                "template_seed_key": getattr(template, "seed_key", None),
                "derived_from_workflow_id": workflow.derived_from_workflow_id,
                "derived_from_workflow_name": getattr(source, "name", None),
                "root_workflow_id": root_id,
                "root_workflow_name": getattr(root, "name", workflow.name),
                "version": getattr(workflow, "version", 1) or 1,
            },
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at,
        }
    )


async def _with_workflow_provenance(db: AsyncSession, workflows: list[Workflow]) -> list[WorkflowResponse]:
    if not workflows:
        return []

    template_ids = sorted({workflow.template_id for workflow in workflows if workflow.template_id is not None})
    lineage_ids = sorted(
        {workflow.id for workflow in workflows}
        | {workflow.root_workflow_id for workflow in workflows if workflow.root_workflow_id is not None}
        | {workflow.derived_from_workflow_id for workflow in workflows if workflow.derived_from_workflow_id is not None}
    )

    template_map: Dict[int, WorkflowTemplate] = {}
    if template_ids:
        result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id.in_(template_ids)))
        template_map = {template.id: template for template in result.scalars().all()}

    lineage_map: Dict[int, Workflow] = {workflow.id: workflow for workflow in workflows}
    if lineage_ids:
        result = await db.execute(select(Workflow).where(Workflow.id.in_(lineage_ids)))
        lineage_map.update({workflow.id: workflow for workflow in result.scalars().all()})

    return [_serialize_workflow(workflow, template_map, lineage_map) for workflow in workflows]


async def _ensure_seed_templates(db: AsyncSession) -> None:
    existing_result = await db.execute(select(WorkflowTemplate.seed_key).where(WorkflowTemplate.seed_key.is_not(None)))
    existing_seed_keys = set(existing_result.scalars().all())
    created = False

    for seed in WORKFLOW_TEMPLATE_SEEDS:
        if seed["seed_key"] in existing_seed_keys:
            continue
        template = WorkflowTemplate(
            name=seed["name"],
            description=seed["description"],
            category=seed["category"],
            entity_type=seed["entity_type"],
            event=seed["event"],
            condition_type=seed.get("condition_type", "and"),
            conditions=deepcopy(seed["conditions"]),
            actions=deepcopy(seed["actions"]),
            is_seed=True,
            seed_key=seed["seed_key"],
            version=1,
        )
        db.add(template)
        await db.flush()
        template.root_template_id = template.id
        created = True

    if created:
        await db.commit()


async def _next_workflow_version(db: AsyncSession, root_workflow_id: int) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Workflow.version), 0)).where(
            or_(Workflow.root_workflow_id == root_workflow_id, Workflow.id == root_workflow_id)
        )
    )
    return int(result.scalar_one() or 0) + 1


async def log_audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: Optional[int] = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
):
    """Log audit trail for workflow operations."""
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )
    )


@router.get("/workflow-templates", response_model=List[WorkflowTemplateResponse])
async def list_workflow_templates(
    seed_only: Optional[bool] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List workflow templates for the gallery, ensuring starter seeds exist."""
    await _ensure_seed_templates(db)
    query = select(WorkflowTemplate)
    if seed_only is not None:
        query = query.where(WorkflowTemplate.is_seed == seed_only)
    query = query.order_by(WorkflowTemplate.is_seed.desc(), WorkflowTemplate.category, WorkflowTemplate.name).offset(offset).limit(limit)
    result = await db.execute(query)
    return [_serialize_template(template) for template in result.scalars().all()]


@router.get("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_template(template_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get a single workflow template."""
    await _ensure_seed_templates(db)
    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return _serialize_template(template)


@router.post("/workflow-templates/{template_id}/clone", response_model=WorkflowResponse)
async def clone_workflow_from_template(
    template_id: int,
    data: WorkflowCloneRequest,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Create a new workflow from an immutable template without mutating the seed/template."""
    await _ensure_seed_templates(db)
    result = await db.execute(select(WorkflowTemplate).where(WorkflowTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    payload = build_workflow_clone_from_template(template, data.model_dump(exclude_unset=True))
    workflow = Workflow(**payload)
    db.add(workflow)
    await db.flush()
    workflow.root_workflow_id = workflow.id

    await log_audit(
        db,
        "workflow",
        workflow.id,
        "created_from_template",
        user_id=user_id,
        new_values={**payload, "root_workflow_id": workflow.id},
    )
    await db.commit()
    await db.refresh(workflow)
    return (await _with_workflow_provenance(db, [workflow]))[0]


@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    template_id: Optional[int] = None,
    root_workflow_id: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_crm_db),
):
    """List saved workflows and their visible provenance/version metadata."""
    query = select(Workflow)
    if template_id is not None:
        query = query.where(Workflow.template_id == template_id)
    if root_workflow_id is not None:
        query = query.where(or_(Workflow.root_workflow_id == root_workflow_id, Workflow.id == root_workflow_id))
    query = query.order_by(func.coalesce(Workflow.root_workflow_id, Workflow.id).desc(), Workflow.version.desc(), Workflow.updated_at.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return await _with_workflow_provenance(db, result.scalars().all())


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: int, db: AsyncSession = Depends(get_crm_db)):
    """Get a single saved workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return (await _with_workflow_provenance(db, [workflow]))[0]


@router.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(
    data: WorkflowCreate,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Create a saved workflow directly from the workflow platform."""
    payload = normalize_workflow_payload(data)
    workflow = Workflow(**payload)
    db.add(workflow)
    await db.flush()
    workflow.root_workflow_id = workflow.id

    await log_audit(
        db,
        "workflow",
        workflow.id,
        "created",
        user_id=user_id,
        new_values={**payload, "root_workflow_id": workflow.id, "version": workflow.version or 1},
    )
    await db.commit()
    await db.refresh(workflow)
    return (await _with_workflow_provenance(db, [workflow]))[0]


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Update an existing workflow in place."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    old_values = {
        **workflow_contract_fields(workflow),
        "template_id": workflow.template_id,
        "derived_from_workflow_id": workflow.derived_from_workflow_id,
        "root_workflow_id": workflow.root_workflow_id,
        "version": workflow.version,
    }
    update_data = normalize_workflow_payload(data, existing=workflow)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    await log_audit(
        db,
        "workflow",
        workflow.id,
        "updated",
        user_id=user_id,
        old_values=old_values,
        new_values=update_data,
    )
    await db.commit()
    await db.refresh(workflow)
    return (await _with_workflow_provenance(db, [workflow]))[0]


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Delete a saved workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    old_values = {
        **workflow_contract_fields(workflow),
        "template_id": workflow.template_id,
        "derived_from_workflow_id": workflow.derived_from_workflow_id,
        "root_workflow_id": workflow.root_workflow_id,
        "version": workflow.version,
    }
    await db.delete(workflow)

    await log_audit(
        db,
        "workflow",
        workflow_id,
        "deleted",
        user_id=user_id,
        old_values=old_values,
    )
    await db.commit()
    return {"status": "deleted", "workflow_id": workflow_id}


@router.post("/workflows/{workflow_id}/clone", response_model=WorkflowResponse)
async def clone_workflow_version(
    workflow_id: int,
    data: WorkflowCloneRequest,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_crm_db),
):
    """Save a workflow as a new versioned copy instead of mutating the current one."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    source_workflow = result.scalar_one_or_none()
    if not source_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    next_version = await _next_workflow_version(db, source_workflow.root_workflow_id or source_workflow.id)
    payload = build_workflow_clone_from_workflow(source_workflow, data.model_dump(exclude_unset=True), next_version=next_version)
    workflow = Workflow(**payload)
    db.add(workflow)

    await log_audit(
        db,
        "workflow",
        workflow_id,
        "version_cloned",
        user_id=user_id,
        old_values={"source_workflow_id": source_workflow.id, "version": source_workflow.version},
        new_values=payload,
    )
    await db.commit()
    await db.refresh(workflow)
    return (await _with_workflow_provenance(db, [workflow]))[0]