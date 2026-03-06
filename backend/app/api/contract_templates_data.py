"""Contract template library — 45 templates across 11 verticals.

All section content uses placeholder variables:
  {{business_name}}, {{business_website}}, {{business_email}},
  {{business_address}}, {{business_phone}}, {{client_name}},
  {{client_company}}, {{client_email}}, {{client_address}},
  {{plan_name}}, {{monthly_price}}, {{setup_fee}},
  {{start_date}}, {{end_date}}, {{term_months}}
"""

# ── Shared Section Builders ──────────────────────────────────────────
# Many templates share nearly identical boilerplate for confidentiality,
# liability, indemnification, and general provisions.  These helpers keep
# the per-template definitions DRY while still producing fully self-contained
# section dicts.


def _parties_section(agreement_type: str = "Service Agreement") -> dict:
    return {
        "title": "Parties",
        "content": (
            f'This {agreement_type} ("Agreement") is entered into as of {{{{start_date}}}} '
            "by and between {{business_name}}, with its principal place of business at "
            "{{business_address}} (\"Provider\"), and {{client_name}}"
            '{{client_company}}, located at {{client_address}} ("Client"). '
            "Provider may be reached at {{business_email}} or {{business_phone}}. "
            "Client may be reached at {{client_email}}."
        ),
    }


def _confidentiality_section() -> dict:
    return {
        "title": "Confidentiality",
        "content": (
            "Each party agrees to hold in strict confidence all Confidential Information "
            "received from the other party. \"Confidential Information\" means any non-public "
            "information disclosed in connection with this Agreement, whether oral, written, "
            "or electronic, including but not limited to business plans, customer data, pricing, "
            "technical specifications, and trade secrets. The receiving party shall not disclose "
            "Confidential Information to any third party without the disclosing party's prior "
            "written consent, except as required by law or to employees and contractors who need "
            "to know and are bound by equivalent obligations. This obligation survives termination "
            "of this Agreement for a period of three (3) years."
        ),
    }


def _liability_section() -> dict:
    return {
        "title": "Limitation of Liability",
        "content": (
            "IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, "
            "CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO THIS AGREEMENT, "
            "INCLUDING BUT NOT LIMITED TO LOSS OF REVENUE, LOSS OF PROFITS, LOSS OF BUSINESS, "
            "OR LOSS OF DATA, REGARDLESS OF THE THEORY OF LIABILITY. {{business_name}}'S TOTAL "
            "AGGREGATE LIABILITY UNDER THIS AGREEMENT SHALL NOT EXCEED THE TOTAL FEES ACTUALLY "
            "PAID BY CLIENT TO {{business_name}} DURING THE TWELVE (12) MONTHS IMMEDIATELY "
            "PRECEDING THE EVENT GIVING RISE TO THE CLAIM."
        ),
    }


def _indemnification_section() -> dict:
    return {
        "title": "Indemnification",
        "content": (
            "Each party (\"Indemnifying Party\") shall indemnify, defend, and hold harmless the "
            "other party and its officers, directors, employees, and agents (\"Indemnified Party\") "
            "from and against any and all claims, damages, losses, liabilities, costs, and expenses "
            "(including reasonable attorneys' fees) arising out of or related to: (a) the Indemnifying "
            "Party's breach of any representation, warranty, or obligation under this Agreement; "
            "(b) the Indemnifying Party's negligence or willful misconduct; or (c) any third-party "
            "claim resulting from the Indemnifying Party's performance or failure to perform under "
            "this Agreement. The Indemnified Party shall provide prompt written notice of any claim "
            "and reasonable cooperation in the defense thereof."
        ),
    }


def _general_provisions_section() -> dict:
    return {
        "title": "General Provisions",
        "content": (
            "This Agreement constitutes the entire understanding between the parties and supersedes "
            "all prior negotiations, representations, and agreements, whether written or oral. No "
            "amendment or modification shall be effective unless in writing and signed by both "
            "parties. This Agreement shall be governed by and construed in accordance with the laws "
            "of the state in which {{business_name}} maintains its principal place of business, "
            "without regard to conflict of law principles. If any provision is held to be invalid "
            "or unenforceable, the remaining provisions shall continue in full force and effect. "
            "Neither party may assign this Agreement without the other party's prior written consent, "
            "except in connection with a merger, acquisition, or sale of substantially all assets. "
            "All notices shall be in writing and delivered via email to the addresses specified herein "
            "or via certified mail to the parties' respective addresses. Failure to enforce any "
            "provision shall not constitute a waiver of future enforcement. This Agreement may be "
            "executed in counterparts, each of which shall be deemed an original."
        ),
    }


def _ip_section_work_for_hire() -> dict:
    return {
        "title": "Intellectual Property",
        "content": (
            "All work product, deliverables, designs, code, content, and materials created by "
            "{{business_name}} specifically for Client under this Agreement (\"Work Product\") "
            "shall become Client's exclusive property upon full payment of all fees due. "
            "{{business_name}} retains ownership of all pre-existing intellectual property, "
            "proprietary tools, frameworks, libraries, and methodologies used in the creation "
            "of the Work Product (\"Provider IP\"). {{business_name}} grants Client a perpetual, "
            "non-exclusive, royalty-free license to use any Provider IP incorporated into the "
            "deliverables. Client grants {{business_name}} permission to display the completed "
            "work in {{business_name}}'s portfolio and marketing materials unless Client provides "
            "written objection within thirty (30) days of project completion."
        ),
    }


def _ip_section_license() -> dict:
    return {
        "title": "Intellectual Property & Licensing",
        "content": (
            "All intellectual property rights in the services, software, tools, and methodologies "
            "provided by {{business_name}} remain the exclusive property of {{business_name}}. "
            "Client is granted a non-exclusive, non-transferable license to use the deliverables "
            "for Client's internal business purposes during the term of this Agreement. Client "
            "shall not reverse engineer, decompile, modify, or create derivative works of any "
            "{{business_name}} proprietary materials. All client-provided content, data, and "
            "materials remain Client's property. Upon termination, Client's license to use "
            "{{business_name}} proprietary materials shall terminate, but Client shall retain "
            "ownership of all Client data and content."
        ),
    }


# ── SEED TEMPLATES ───────────────────────────────────────────────────

SEED_TEMPLATES = [
    # ──────────────────────────────────────────────────────────────
    # EXISTING WaaS TEMPLATES (updated with placeholders)
    # ──────────────────────────────────────────────────────────────
    {
        "name": "WaaS — Foundation",
        "plan_name": "Foundation",
        "monthly_price": 299.00,
        "setup_fee": 999.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Custom website design & build",
                "Managed hosting",
                "SSL certificate",
                "Daily backups",
                "Monthly maintenance",
                "Email support",
            ],
        },
        "sections": [
            _parties_section("Website-as-a-Service Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall deliver a professionally designed and developed custom "
                    "website tailored to Client's brand and business requirements under the "
                    "{{plan_name}} plan. Services include managed hosting on enterprise-grade "
                    "infrastructure, SSL certificate provisioning and renewal, automated daily "
                    "backups with 30-day retention, monthly maintenance including software updates "
                    "and security patches, and email-based technical support during standard "
                    "business hours (Mon–Fri, 9 AM – 5 PM EST). Client may contact "
                    "{{business_email}} for support requests."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee of {{setup_fee}} and a recurring "
                    "monthly service fee of {{monthly_price}} as specified in the Plan Details. "
                    "Monthly fees are billed on the first of each month and are due within fifteen "
                    "(15) days of invoice date. Late payments are subject to a 1.5% monthly finance "
                    "charge. {{business_name}} reserves the right to suspend services for accounts "
                    "more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on {{start_date}} and continue for an initial "
                    "term of {{term_months}} months, ending on {{end_date}}. Unless either party "
                    "provides written notice of non-renewal at least thirty (30) days prior to the "
                    "end of the current term, this Agreement shall automatically renew for successive "
                    "periods equal to the initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate this Agreement for cause upon thirty (30) days' "
                    "written notice if the other party materially breaches any provision and fails "
                    "to cure such breach within the notice period. Client may terminate for "
                    "convenience with thirty (30) days' written notice, subject to payment of any "
                    "outstanding fees through the end of the notice period. Upon termination, "
                    "{{business_name}} shall deliver all Client content and assist with migration "
                    "for up to fifteen (15) business days."
                ),
            },
            _ip_section_work_for_hire(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "WaaS — Operational",
        "plan_name": "Operational",
        "monthly_price": 599.00,
        "setup_fee": 1499.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Everything in Foundation plan",
                "SEO optimization",
                "Monthly analytics report",
                "Content updates (up to 4/mo)",
                "Priority support",
                "Social media integration",
            ],
        },
        "sections": [
            _parties_section("Website-as-a-Service Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall deliver all Foundation-tier services plus: search engine "
                    "optimization (SEO) including keyword research, on-page optimization, and "
                    "technical SEO audits; monthly analytics reports covering traffic, engagement, "
                    "and conversion metrics; up to four (4) content updates per month including text, "
                    "image, and minor layout changes; priority technical support with guaranteed "
                    "4-hour response time during business hours; and social media integration including "
                    "feed embedding, share buttons, and Open Graph optimization."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee of {{setup_fee}} and a recurring "
                    "monthly service fee of {{monthly_price}}. Monthly fees are billed on the first "
                    "of each month and are due within fifteen (15) days of invoice date. Late payments "
                    "are subject to a 1.5% monthly finance charge. {{business_name}} reserves the "
                    "right to suspend services for accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on {{start_date}} and continue for {{term_months}} "
                    "months until {{end_date}}. Unless either party provides written notice of "
                    "non-renewal at least thirty (30) days prior to the end of the current term, "
                    "this Agreement shall automatically renew for successive periods equal to the "
                    "initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate this Agreement for cause upon thirty (30) days' "
                    "written notice if the other party materially breaches any provision and fails "
                    "to cure such breach within the notice period. Client may terminate for "
                    "convenience with thirty (30) days' notice, subject to payment of outstanding "
                    "fees. Upon termination, {{business_name}} shall deliver all Client content and "
                    "assist with migration for up to fifteen (15) business days."
                ),
            },
            _ip_section_work_for_hire(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "WaaS — Growth",
        "plan_name": "Growth",
        "monthly_price": 1200.00,
        "setup_fee": 2499.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Everything in Operational plan",
                "Advanced SEO strategy",
                "Blog content creation",
                "A/B testing",
                "Conversion optimization",
                "Dedicated account manager",
                "Bi-weekly strategy calls",
            ],
        },
        "sections": [
            _parties_section("Website-as-a-Service Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall deliver all Operational-tier services plus: advanced "
                    "SEO strategy including competitor analysis, link building, and content gap "
                    "analysis; professional blog content creation including research, writing, and "
                    "publication of SEO-optimized articles; A/B testing of landing pages, CTAs, and "
                    "key conversion points; ongoing conversion rate optimization with monthly "
                    "recommendations; a dedicated account manager as Client's single point of "
                    "contact; and bi-weekly strategy calls to review performance and align on priorities."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee of {{setup_fee}} and a recurring "
                    "monthly service fee of {{monthly_price}}. Monthly fees are billed on the first "
                    "of each month and are due within fifteen (15) days of invoice date. Late payments "
                    "are subject to a 1.5% monthly finance charge. {{business_name}} reserves the "
                    "right to suspend services for accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement shall commence on {{start_date}} and continue for {{term_months}} "
                    "months until {{end_date}}. Unless either party provides written notice at least "
                    "thirty (30) days prior, this Agreement renews automatically for successive "
                    "periods equal to the initial term at the then-current rates."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate for cause upon thirty (30) days' written notice if "
                    "the other party materially breaches and fails to cure within the notice period. "
                    "Client may terminate for convenience with thirty (30) days' notice, subject to "
                    "payment of outstanding fees. Upon termination, {{business_name}} shall deliver "
                    "all Client content and assist with migration for up to fifteen (15) business days."
                ),
            },
            _ip_section_work_for_hire(),
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # WEB & DIGITAL SERVICES
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Website Design & Development Agreement",
        "plan_name": "Website Design & Development",
        "monthly_price": 0,
        "setup_fee": 5000.00,
        "default_terms": {
            "term_months": 3,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Custom website design (up to 10 pages)",
                "Responsive/mobile-friendly development",
                "Content management system setup",
                "Contact forms and basic integrations",
                "Browser and device testing",
                "30-day post-launch support",
            ],
        },
        "sections": [
            _parties_section("Website Design & Development Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall design and develop a custom website for {{client_name}} "
                    "({{client_company}}) in accordance with the specifications agreed upon during "
                    "the discovery phase. The project includes: (a) discovery and requirements "
                    "gathering; (b) wireframing and design mockups for Client approval; (c) front-end "
                    "and back-end development; (d) content management system (CMS) setup and "
                    "configuration; (e) responsive design for mobile, tablet, and desktop; "
                    "(f) integration of contact forms and agreed-upon third-party services; "
                    "(g) cross-browser testing; and (h) deployment to Client's hosting environment. "
                    "Any features or pages beyond the agreed scope require a written change order "
                    "with associated cost and timeline adjustments."
                ),
            },
            {
                "title": "Project Timeline & Milestones",
                "content": (
                    "The project shall be completed within the {{term_months}}-month term beginning "
                    "{{start_date}}. Key milestones: (1) Discovery & wireframes — Week 1-2; "
                    "(2) Design mockups for approval — Week 3-4; (3) Development sprint — Week 5-8; "
                    "(4) Client review & revisions — Week 9-10; (5) Testing & launch — Week 11-12. "
                    "Client agrees to provide feedback within five (5) business days of each "
                    "milestone delivery. Delays caused by Client's failure to provide timely feedback "
                    "or content may extend the project timeline accordingly."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The total project fee is {{setup_fee}}, payable in three (3) installments: "
                    "(a) 40% due upon execution of this Agreement; (b) 30% due upon design approval; "
                    "(c) 30% due upon project completion and launch. All invoices are due within "
                    "fifteen (15) days of issuance. Late payments are subject to a 1.5% monthly "
                    "finance charge. {{business_name}} reserves the right to pause work on the "
                    "project if any invoice remains unpaid for more than fifteen (15) days."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide all content (text, images, logos, branding assets) "
                    "in a timely manner; (b) designate a single point of contact authorized to "
                    "provide approvals and feedback; (c) provide access to hosting, domain registrar, "
                    "and any third-party accounts necessary for project completion; (d) review and "
                    "approve deliverables within the timeframes specified; (e) ensure all content "
                    "provided does not infringe on any third-party intellectual property rights."
                ),
            },
            {
                "title": "Revisions & Change Orders",
                "content": (
                    "This Agreement includes up to two (2) rounds of design revisions and one (1) "
                    "round of development revisions. Additional revisions or scope changes beyond "
                    "what is specified in the Scope of Work shall require a written change order "
                    "signed by both parties, detailing the additional work, cost, and timeline "
                    "impact. {{business_name}} shall provide a change order estimate within three "
                    "(3) business days of Client's request."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Warranties & Post-Launch Support",
                "content": (
                    "{{business_name}} warrants that the website shall function substantially as "
                    "described in the approved specifications for a period of thirty (30) days "
                    "following launch (\"Warranty Period\"). During the Warranty Period, "
                    "{{business_name}} shall correct any defects or bugs at no additional charge. "
                    "This warranty does not cover issues caused by Client modifications, third-party "
                    "plugins or services, hosting environment changes, or browser updates released "
                    "after the launch date."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Website Maintenance & Support Agreement",
        "plan_name": "Website Maintenance & Support",
        "monthly_price": 499.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "CMS and plugin updates",
                "Security monitoring and patching",
                "Daily automated backups",
                "Up to 4 hours of content updates per month",
                "Uptime monitoring (99.9% SLA)",
                "Monthly performance reports",
                "Priority email and phone support",
            ],
        },
        "sections": [
            _parties_section("Website Maintenance & Support Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide ongoing website maintenance and support services "
                    "for {{client_name}} ({{client_company}}) including: (a) CMS core, theme, and "
                    "plugin updates performed weekly or as critical patches are released; "
                    "(b) security monitoring, malware scanning, and vulnerability patching; "
                    "(c) automated daily backups with 30-day retention and on-demand restoration; "
                    "(d) up to four (4) hours of content updates, minor design changes, or "
                    "troubleshooting per month; (e) uptime monitoring with 99.9% availability target; "
                    "(f) monthly performance and analytics reports; (g) priority support via email "
                    "({{business_email}}) and phone ({{business_phone}}) with 4-hour response time "
                    "during business hours."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a recurring monthly service fee of {{monthly_price}}. "
                    "Monthly fees are billed on the first of each month and are due within fifteen "
                    "(15) days. Unused maintenance hours do not roll over. Additional hours beyond "
                    "the included allocation are billed at $125/hour. Late payments are subject to "
                    "a 1.5% monthly finance charge. {{business_name}} may suspend services for "
                    "accounts more than thirty (30) days past due."
                ),
            },
            {
                "title": "Service Level Agreement",
                "content": (
                    "{{business_name}} commits to 99.9% website uptime measured monthly, excluding "
                    "scheduled maintenance windows (communicated 48 hours in advance). Critical "
                    "issues (site down, security breach) will receive a response within one (1) hour "
                    "and resolution within four (4) hours. Non-critical issues will receive a "
                    "response within four (4) business hours. If uptime falls below 99.9% in any "
                    "calendar month due to {{business_name}}'s fault, Client shall receive a credit "
                    "of 5% of that month's fee for each additional 0.1% of downtime, up to 50% of "
                    "the monthly fee."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement commences on {{start_date}} and continues for {{term_months}} "
                    "months until {{end_date}}. The Agreement automatically renews for successive "
                    "{{term_months}}-month periods unless either party provides written notice of "
                    "non-renewal at least thirty (30) days before the end of the current term."
                ),
            },
            {
                "title": "Termination",
                "content": (
                    "Either party may terminate for cause upon thirty (30) days' written notice if "
                    "the other party materially breaches and fails to cure within the notice period. "
                    "Client may terminate for convenience with thirty (30) days' notice. Upon "
                    "termination, {{business_name}} shall: (a) provide Client with a final backup "
                    "of all website files and databases; (b) assist with migration to a new provider "
                    "for up to five (5) business days; (c) provide all login credentials and "
                    "documentation necessary for continued operation."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "E-Commerce Development Agreement",
        "plan_name": "E-Commerce Development",
        "monthly_price": 299.00,
        "setup_fee": 8000.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Custom e-commerce storefront design",
                "Product catalog setup (up to 500 SKUs)",
                "Payment gateway integration",
                "Shipping calculator integration",
                "Inventory management system",
                "Order management and notifications",
                "Ongoing maintenance and support",
            ],
        },
        "sections": [
            _parties_section("E-Commerce Development Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall design, develop, and launch a custom e-commerce "
                    "storefront for {{client_name}} ({{client_company}}). The project includes: "
                    "(a) custom storefront design with responsive layout; (b) product catalog setup "
                    "and configuration for up to 500 SKUs; (c) payment gateway integration "
                    "(Stripe, PayPal, or equivalent); (d) shipping calculator and fulfillment "
                    "integration; (e) inventory management system; (f) customer account management; "
                    "(g) order processing workflow with email notifications; (h) SEO-optimized "
                    "product pages; (i) analytics and conversion tracking setup. The ongoing monthly "
                    "fee covers hosting, security, updates, and up to two (2) hours of support."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The project development fee is {{setup_fee}}, payable as follows: 35% upon "
                    "contract execution, 35% upon design approval, and 30% upon launch. The ongoing "
                    "monthly maintenance and hosting fee of {{monthly_price}} begins upon launch and "
                    "is billed on the first of each month. All invoices are net-15. Late payments "
                    "incur a 1.5% monthly finance charge."
                ),
            },
            {
                "title": "Transaction Fees & Third-Party Costs",
                "content": (
                    "Payment gateway transaction fees, SSL certificates (if not included in hosting), "
                    "domain registration, third-party app subscriptions, and shipping carrier charges "
                    "are the responsibility of Client and are not included in the fees specified "
                    "in this Agreement. {{business_name}} shall advise Client of estimated "
                    "third-party costs during the discovery phase but is not liable for changes in "
                    "third-party pricing."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "The development phase is estimated at {{term_months}} months beginning "
                    "{{start_date}}. Upon launch, the ongoing maintenance agreement continues "
                    "month-to-month with automatic renewal. Either party may cancel the maintenance "
                    "agreement with thirty (30) days' written notice."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Data Handling & PCI Compliance",
                "content": (
                    "{{business_name}} shall implement industry-standard security practices for the "
                    "e-commerce platform. All payment processing shall be handled by PCI-DSS "
                    "compliant third-party payment processors; no credit card data shall be stored "
                    "on the website's servers. Client is responsible for maintaining PCI compliance "
                    "for any payment data they directly handle. {{business_name}} shall implement "
                    "SSL encryption, secure authentication, and regular security updates."
                ),
            },
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Mobile App Development Agreement",
        "plan_name": "Mobile App Development",
        "monthly_price": 0,
        "setup_fee": 25000.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Native or cross-platform mobile app",
                "UI/UX design and prototyping",
                "API development and integration",
                "App Store and Google Play submission",
                "QA testing across devices",
                "60-day post-launch bug fixes",
            ],
        },
        "sections": [
            _parties_section("Mobile App Development Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall design, develop, test, and deploy a mobile application "
                    "for {{client_name}} ({{client_company}}) as detailed in the project specification "
                    "document (\"Spec\") agreed upon during discovery. The project includes: "
                    "(a) UI/UX design with interactive prototypes; (b) native or cross-platform "
                    "development as specified; (c) back-end API development and/or integration with "
                    "Client's existing systems; (d) QA testing across target devices and OS versions; "
                    "(e) submission to Apple App Store and/or Google Play Store; (f) sixty (60) days "
                    "of post-launch bug fixes. Features not in the approved Spec require a change order."
                ),
            },
            {
                "title": "Project Phases & Milestones",
                "content": (
                    "The project shall proceed in the following phases over approximately "
                    "{{term_months}} months: Phase 1 — Discovery & Architecture (Weeks 1–3): "
                    "requirements documentation, technical architecture, project plan. Phase 2 — "
                    "Design (Weeks 4–7): wireframes, UI design, interactive prototype, Client "
                    "approval. Phase 3 — Development Sprint 1 (Weeks 8–14): core features, API "
                    "integration, alpha build. Phase 4 — Development Sprint 2 (Weeks 15–20): "
                    "remaining features, beta build. Phase 5 — QA & Launch (Weeks 21–24): testing, "
                    "bug fixes, store submission. Each phase requires Client sign-off before "
                    "proceeding to the next."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The total project fee is {{setup_fee}}, payable in milestone installments: "
                    "20% upon contract execution, 20% upon design approval (Phase 2 complete), "
                    "25% upon alpha delivery (Phase 3 complete), 20% upon beta delivery (Phase 4 "
                    "complete), and 15% upon app store submission (Phase 5 complete). All invoices "
                    "are net-15. Work may be paused if payments are more than fifteen (15) days "
                    "overdue."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide complete requirements during the discovery phase; "
                    "(b) designate a product owner as the single point of contact for decisions; "
                    "(c) provide all branding assets, content, and API credentials; (d) review and "
                    "approve deliverables within five (5) business days of each milestone; "
                    "(e) provide Apple Developer and Google Play Console accounts for app submission; "
                    "(f) participate in weekly status calls throughout the project."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Warranties & Post-Launch Support",
                "content": (
                    "{{business_name}} warrants that the application shall function substantially "
                    "as described in the approved Spec for sixty (60) days following initial app "
                    "store approval (\"Warranty Period\"). Bugs and defects discovered during the "
                    "Warranty Period shall be corrected at no additional charge. This warranty does "
                    "not cover: (a) issues caused by OS updates released after launch; (b) "
                    "third-party service outages; (c) modifications made by parties other than "
                    "{{business_name}}; (d) features not included in the approved Spec."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "SEO Services Agreement",
        "plan_name": "SEO Services",
        "monthly_price": 1500.00,
        "setup_fee": 500.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Comprehensive SEO audit",
                "Keyword research and strategy",
                "On-page optimization",
                "Technical SEO fixes",
                "Link building (5-10 quality backlinks/mo)",
                "Monthly ranking and traffic reports",
                "Competitor analysis",
            ],
        },
        "sections": [
            _parties_section("SEO Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide search engine optimization services for "
                    "{{client_name}} ({{client_company}}) including: (a) comprehensive initial SEO "
                    "audit of Client's website; (b) keyword research and strategic targeting; "
                    "(c) on-page optimization including meta tags, headers, content, and internal "
                    "linking; (d) technical SEO including site speed, mobile optimization, schema "
                    "markup, and crawlability; (e) off-page SEO including link building (5-10 quality "
                    "backlinks per month); (f) monthly ranking and organic traffic reports; "
                    "(g) ongoing competitor analysis and strategy adjustments."
                ),
            },
            {
                "title": "Performance Metrics & Reporting",
                "content": (
                    "{{business_name}} shall provide monthly reports including: keyword rankings for "
                    "agreed target terms, organic traffic volume and trends, backlink acquisition "
                    "summary, technical health score, and recommendations for the following month. "
                    "Reports are delivered by the 10th of each month for the prior month's "
                    "performance. Client acknowledges that SEO is a long-term strategy and that "
                    "{{business_name}} does not guarantee specific rankings, as search engine "
                    "algorithms are outside {{business_name}}'s control."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time audit and setup fee of {{setup_fee}} and a "
                    "recurring monthly fee of {{monthly_price}}. Monthly fees are billed on the "
                    "first of each month, net-15. The initial audit and setup fee is due upon "
                    "contract execution. Late payments incur a 1.5% monthly finance charge."
                ),
            },
            {
                "title": "Term & Renewal",
                "content": (
                    "This Agreement commences on {{start_date}} for an initial term of "
                    "{{term_months}} months ending {{end_date}}. The minimum term reflects the "
                    "time required for SEO efforts to produce measurable results. After the initial "
                    "term, this Agreement renews month-to-month unless either party provides thirty "
                    "(30) days' written notice of cancellation."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide {{business_name}} with CMS and analytics access; "
                    "(b) review and approve content recommendations within five (5) business days; "
                    "(c) not engage another SEO provider simultaneously without disclosure; "
                    "(d) promptly communicate any website changes, redesigns, or domain changes "
                    "that may impact SEO performance."
                ),
            },
            {
                "title": "Ethical Practices",
                "content": (
                    "{{business_name}} employs only white-hat SEO techniques in compliance with "
                    "Google's Webmaster Guidelines. {{business_name}} shall not engage in keyword "
                    "stuffing, cloaking, paid link schemes, or any practices that could result in "
                    "search engine penalties. If Client requests tactics that {{business_name}} "
                    "determines to be in violation of search engine guidelines, {{business_name}} "
                    "shall decline and propose compliant alternatives."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Digital Marketing Services Agreement",
        "plan_name": "Digital Marketing Services",
        "monthly_price": 2500.00,
        "setup_fee": 1000.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Paid advertising management (Google, Meta)",
                "Campaign strategy and planning",
                "Ad creative development",
                "Landing page optimization",
                "Conversion tracking setup",
                "Bi-weekly performance reports",
                "Monthly strategy calls",
            ],
        },
        "sections": [
            _parties_section("Digital Marketing Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide digital marketing services for {{client_name}} "
                    "({{client_company}}) including: (a) paid advertising campaign management across "
                    "agreed platforms (Google Ads, Meta/Facebook Ads, etc.); (b) campaign strategy, "
                    "audience targeting, and budget allocation; (c) ad creative development including "
                    "copy and visual assets; (d) landing page optimization recommendations; "
                    "(e) conversion tracking and analytics setup; (f) bi-weekly performance reports "
                    "with KPI tracking; (g) monthly strategy calls to review results and plan ahead. "
                    "Ad spend budgets are separate from the service fee and are the responsibility "
                    "of Client."
                ),
            },
            {
                "title": "Ad Spend & Budget",
                "content": (
                    "The monthly service fee of {{monthly_price}} covers {{business_name}}'s "
                    "management services only. Client's advertising budget (\"Ad Spend\") is "
                    "separate and shall be funded directly by Client through their advertising "
                    "platform accounts. {{business_name}} shall recommend monthly ad spend levels "
                    "but final budget decisions rest with Client. {{business_name}} shall not be "
                    "responsible for results attributable to insufficient ad spend."
                ),
            },
            {
                "title": "KPIs & Reporting",
                "content": (
                    "{{business_name}} and Client shall agree on key performance indicators (KPIs) "
                    "during onboarding, which may include: cost per acquisition (CPA), return on "
                    "ad spend (ROAS), click-through rate (CTR), conversion rate, and lead volume. "
                    "{{business_name}} shall optimize campaigns toward agreed KPIs but does not "
                    "guarantee specific results, as outcomes depend on market conditions, ad spend "
                    "levels, Client's offer, and other factors outside {{business_name}}'s control."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time onboarding fee of {{setup_fee}} and a recurring "
                    "monthly management fee of {{monthly_price}}. Fees are billed on the first of "
                    "each month, net-15. The onboarding fee covers account audits, tracking setup, "
                    "and initial campaign architecture."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. After the initial term, it renews month-to-month. Either party "
                    "may terminate with thirty (30) days' written notice. Upon termination, "
                    "{{business_name}} shall transfer all campaign data, audiences, and account "
                    "access to Client within five (5) business days."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Social Media Management Agreement",
        "plan_name": "Social Media Management",
        "monthly_price": 1800.00,
        "setup_fee": 500.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Content calendar creation",
                "12-16 posts per month across platforms",
                "Graphic design for social posts",
                "Community engagement and response",
                "Hashtag strategy",
                "Monthly analytics report",
                "Platform-specific optimization",
            ],
        },
        "sections": [
            _parties_section("Social Media Management Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall manage social media accounts for {{client_name}} "
                    "({{client_company}}) on the following platforms as agreed: [platforms to be "
                    "specified]. Services include: (a) monthly content calendar creation, subject to "
                    "Client approval; (b) 12-16 original posts per month with custom graphics; "
                    "(c) community management including responding to comments and messages within "
                    "24 hours during business days; (d) hashtag research and optimization; "
                    "(e) monthly analytics report with engagement metrics and growth tracking; "
                    "(f) platform-specific content optimization."
                ),
            },
            {
                "title": "Content Approval Process",
                "content": (
                    "{{business_name}} shall submit the monthly content calendar for Client's "
                    "review and approval at least seven (7) days before the start of each month. "
                    "Client shall approve or request revisions within three (3) business days. "
                    "Failure to respond within this timeframe constitutes approval. {{business_name}} "
                    "shall not publish any content that has not been approved through this process, "
                    "except for real-time engagement responses and community management."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time setup fee of {{setup_fee}} (covering account "
                    "audits, branding alignment, and content strategy development) and a recurring "
                    "monthly fee of {{monthly_price}}. Monthly fees are billed on the first of each "
                    "month, net-15."
                ),
            },
            {
                "title": "Account Ownership & Access",
                "content": (
                    "All social media accounts remain the exclusive property of Client. "
                    "{{business_name}} shall be granted administrative or editor access as needed "
                    "to perform services. {{business_name}} shall not change account passwords, "
                    "ownership settings, or connected accounts without Client's explicit written "
                    "consent. Upon termination, {{business_name}} shall relinquish all access "
                    "within two (2) business days."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. After "
                    "the initial term, it renews month-to-month. Either party may terminate with "
                    "thirty (30) days' written notice. Upon termination, {{business_name}} shall "
                    "deliver all scheduled content, design files, and analytics data to Client."
                ),
            },
            _ip_section_work_for_hire(),
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Content Creation Agreement",
        "plan_name": "Content Creation",
        "monthly_price": 1200.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "8 blog posts/articles per month (800-1200 words)",
                "SEO keyword integration",
                "2 rounds of revisions per piece",
                "Meta descriptions and title tags",
                "Content calendar planning",
                "Monthly editorial strategy call",
            ],
        },
        "sections": [
            _parties_section("Content Creation Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide content creation services for {{client_name}} "
                    "({{client_company}}) including: (a) eight (8) blog posts or articles per month, "
                    "800–1,200 words each; (b) SEO keyword research and integration; (c) meta "
                    "descriptions and optimized title tags; (d) content calendar planning with "
                    "monthly editorial strategy calls; (e) up to two (2) rounds of revisions per "
                    "piece. Additional content types (video scripts, whitepapers, case studies) "
                    "are available at additional cost upon written agreement."
                ),
            },
            {
                "title": "Content Delivery & Approval",
                "content": (
                    "Content shall be delivered in batches of two (2) pieces per week via shared "
                    "document or Client's CMS. Client shall review and provide feedback within "
                    "three (3) business days of delivery. Approved content is considered final. "
                    "{{business_name}} shall publish approved content to Client's CMS upon request "
                    "or deliver in Client's preferred format."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a recurring monthly fee of {{monthly_price}} billed on "
                    "the first of each month, net-15. Unused content credits do not roll over to "
                    "the following month. Additional pieces beyond the monthly allocation are billed "
                    "at $150 per piece."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. It renews month-to-month thereafter. Either party may terminate "
                    "with thirty (30) days' written notice. Content in progress at the time of "
                    "termination shall be completed and delivered."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Originality Guarantee",
                "content": (
                    "{{business_name}} warrants that all content created under this Agreement shall "
                    "be original work and shall not infringe upon any third-party intellectual "
                    "property rights. All content shall be checked for plagiarism before delivery. "
                    "{{business_name}} shall not use AI-generated content without Client's explicit "
                    "written consent. If any content is found to be non-original, {{business_name}} "
                    "shall replace it at no additional charge."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # TECHNOLOGY & SaaS
    # ──────────────────────────────────────────────────────────────
    {
        "name": "SaaS Subscription Agreement",
        "plan_name": "SaaS Subscription",
        "monthly_price": 99.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Software license and access",
                "Hosting and infrastructure",
                "Automatic updates and patches",
                "99.9% uptime SLA",
                "Data backup and recovery",
                "Standard support (email, docs)",
            ],
        },
        "sections": [
            _parties_section("SaaS Subscription Agreement"),
            {
                "title": "License Grant",
                "content": (
                    "{{business_name}} grants {{client_name}} ({{client_company}}) a non-exclusive, "
                    "non-transferable, revocable license to access and use the {{plan_name}} software "
                    "platform (\"Service\") during the term of this Agreement, solely for Client's "
                    "internal business purposes. This license does not convey ownership of the "
                    "Service or any underlying intellectual property. Client may not sublicense, "
                    "resell, or provide access to third parties without {{business_name}}'s prior "
                    "written consent."
                ),
            },
            {
                "title": "Service Level Agreement",
                "content": (
                    "{{business_name}} guarantees 99.9% uptime availability for the Service, "
                    "measured monthly, excluding scheduled maintenance (communicated 72 hours in "
                    "advance). If availability falls below 99.9% in any calendar month, Client "
                    "shall receive service credits: 10% of monthly fee for availability between "
                    "99.0%-99.9%, 25% for 95.0%-99.0%, and 50% for below 95.0%. Credits must be "
                    "requested within thirty (30) days and apply to future invoices only."
                ),
            },
            {
                "title": "Data Handling & Security",
                "content": (
                    "Client retains full ownership of all data uploaded to or generated within the "
                    "Service (\"Client Data\"). {{business_name}} shall: (a) process Client Data "
                    "only as necessary to provide the Service; (b) maintain industry-standard "
                    "security measures including encryption at rest and in transit; (c) perform "
                    "daily automated backups with 30-day retention; (d) promptly notify Client of "
                    "any confirmed data breach affecting Client Data; (e) upon termination, provide "
                    "Client Data export in standard formats within thirty (30) days and delete all "
                    "copies within sixty (60) days unless legally required to retain."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a recurring monthly fee of {{monthly_price}} for the "
                    "{{plan_name}} plan. Fees are billed monthly in advance on the subscription "
                    "start date. All fees are non-refundable except as expressly provided in the "
                    "SLA credits. {{business_name}} may adjust pricing upon thirty (30) days' "
                    "written notice, effective at the next renewal period."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. It auto-renews for successive {{term_months}}-month terms unless "
                    "either party provides thirty (30) days' written notice before renewal. "
                    "{{business_name}} may terminate immediately for Client's material breach, "
                    "including unauthorized use, non-payment for thirty (30) or more days, or "
                    "violation of acceptable use policies."
                ),
            },
            {
                "title": "Acceptable Use",
                "content": (
                    "Client shall not: (a) use the Service for any unlawful purpose; (b) attempt "
                    "to reverse engineer, decompile, or disassemble the Service; (c) upload malware "
                    "or malicious code; (d) exceed documented rate limits or usage quotas; (e) share "
                    "credentials with unauthorized users; (f) use the Service to compete with "
                    "{{business_name}}. Violation may result in immediate suspension or termination."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "API Integration Services Agreement",
        "plan_name": "API Integration Services",
        "monthly_price": 0,
        "setup_fee": 7500.00,
        "default_terms": {
            "term_months": 3,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "API architecture and design",
                "Custom integration development",
                "Data mapping and transformation",
                "Testing and documentation",
                "Deployment and go-live support",
                "30-day post-deployment support",
            ],
        },
        "sections": [
            _parties_section("API Integration Services Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall design and develop custom API integrations for "
                    "{{client_name}} ({{client_company}}) connecting the systems and platforms "
                    "identified in the technical specification document. Services include: "
                    "(a) integration architecture and data flow design; (b) API endpoint development "
                    "or configuration; (c) data mapping, transformation, and validation logic; "
                    "(d) error handling and retry mechanisms; (e) automated testing; (f) technical "
                    "documentation; (g) deployment to Client's infrastructure; (h) thirty (30) days "
                    "of post-deployment monitoring and bug fixes."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The total project fee is {{setup_fee}}, payable: 50% upon execution, 50% upon "
                    "successful deployment and Client acceptance. All invoices are net-15. "
                    "{{business_name}} reserves the right to pause work if invoices are overdue "
                    "by more than fifteen (15) days."
                ),
            },
            {
                "title": "Technical Requirements & Access",
                "content": (
                    "Client shall provide: (a) API documentation for all third-party systems to be "
                    "integrated; (b) test and production environment credentials; (c) a designated "
                    "technical contact for troubleshooting; (d) test data sets representative of "
                    "production data volumes. {{business_name}} shall handle all credentials "
                    "securely and return or destroy them upon project completion."
                ),
            },
            {
                "title": "Acceptance Testing",
                "content": (
                    "Upon delivery, Client shall have ten (10) business days to conduct acceptance "
                    "testing against the agreed specification. Client shall document any issues in "
                    "writing. Issues that constitute deviations from the specification shall be "
                    "corrected by {{business_name}} at no additional cost. If Client does not "
                    "provide written rejection within the testing period, the deliverable shall be "
                    "deemed accepted."
                ),
            },
            _ip_section_work_for_hire(),
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "IT Support & Managed Services Agreement",
        "plan_name": "IT Support & Managed Services",
        "monthly_price": 2000.00,
        "setup_fee": 500.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Helpdesk support (Mon-Fri, 8am-6pm)",
                "Remote troubleshooting",
                "Network monitoring",
                "Patch management",
                "Backup monitoring and testing",
                "Quarterly security reviews",
                "Asset inventory management",
            ],
        },
        "sections": [
            _parties_section("IT Support & Managed Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide managed IT support services for {{client_name}} "
                    "({{client_company}}) including: (a) helpdesk support via email, phone, and "
                    "ticketing system during business hours (Mon–Fri, 8 AM – 6 PM); (b) remote "
                    "troubleshooting and issue resolution; (c) 24/7 network and infrastructure "
                    "monitoring; (d) operating system and application patch management; (e) backup "
                    "monitoring and quarterly restore testing; (f) quarterly security assessments; "
                    "(g) hardware and software asset inventory management. On-site support, if "
                    "required, is billed at $150/hour plus travel expenses."
                ),
            },
            {
                "title": "Response Times",
                "content": (
                    "{{business_name}} commits to the following response times: Critical (system "
                    "down): 30 minutes response, 4-hour resolution target. High (major feature "
                    "impaired): 1-hour response, 8-hour resolution target. Medium (minor issue): "
                    "4-hour response, 24-hour resolution target. Low (request/question): 8-hour "
                    "response, 72-hour resolution target. Resolution targets are best-effort and "
                    "may be extended for complex issues with Client notification."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Client agrees to pay a one-time onboarding fee of {{setup_fee}} and a "
                    "recurring monthly fee of {{monthly_price}} billed on the first of each month, "
                    "net-15. The monthly fee covers support for up to [number] users/devices. "
                    "Additional users/devices are billed at $50/user/month."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with automatic renewal for successive {{term_months}}-month terms. "
                    "Either party may terminate with thirty (30) days' written notice. Upon "
                    "termination, {{business_name}} shall provide a complete handoff package "
                    "including network documentation, credentials, and asset inventory."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Cloud Hosting Agreement",
        "plan_name": "Cloud Hosting",
        "monthly_price": 350.00,
        "setup_fee": 250.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Dedicated cloud server resources",
                "99.95% uptime SLA",
                "Automated daily backups",
                "DDoS protection",
                "SSL/TLS certificates",
                "24/7 server monitoring",
                "Scalable resource allocation",
            ],
        },
        "sections": [
            _parties_section("Cloud Hosting Agreement"),
            {
                "title": "Hosting Services",
                "content": (
                    "{{business_name}} shall provide cloud hosting services for {{client_name}} "
                    "({{client_company}}) including: dedicated server resources as specified in the "
                    "{{plan_name}} plan, 99.95% guaranteed uptime, automated daily backups with "
                    "30-day retention, DDoS mitigation, SSL/TLS certificate management, 24/7 "
                    "server health monitoring, and scalable resource allocation upon request."
                ),
            },
            {
                "title": "Service Level Agreement",
                "content": (
                    "{{business_name}} guarantees 99.95% network and server uptime per calendar "
                    "month. Downtime is measured from the time {{business_name}} is notified or "
                    "detects an outage until service restoration. Scheduled maintenance does not "
                    "count toward downtime and will be communicated 72 hours in advance. SLA "
                    "credits: 10% monthly credit for 99.0%–99.95%, 25% for 95%–99%, 50% for below "
                    "95%. Credits apply to future invoices only and must be requested in writing."
                ),
            },
            {
                "title": "Data & Backups",
                "content": (
                    "Client retains ownership of all hosted data. {{business_name}} performs "
                    "automated daily backups and retains them for thirty (30) days. On-demand "
                    "restoration is available at no additional charge. {{business_name}} shall "
                    "not access Client data except as necessary to provide the hosting services "
                    "or when required by law."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The setup/migration fee is {{setup_fee}}, due upon execution. Monthly hosting "
                    "of {{monthly_price}} is billed on the first of each month, net-15. Overage "
                    "charges for bandwidth or storage beyond plan limits are billed monthly at "
                    "published overage rates. Non-payment for thirty (30) days may result in service "
                    "suspension with five (5) days' prior notice."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may cancel with thirty (30) days' "
                    "notice. Upon termination, {{business_name}} shall provide a complete data export "
                    "and maintain Client data for thirty (30) days post-termination before deletion."
                ),
            },
            {
                "title": "Acceptable Use Policy",
                "content": (
                    "Client shall not use the hosting services for: (a) illegal activities; "
                    "(b) distributing malware or spam; (c) hosting content that infringes "
                    "intellectual property rights; (d) cryptocurrency mining; (e) conducting "
                    "denial-of-service attacks. Violation may result in immediate suspension."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Software Development Agreement",
        "plan_name": "Software Development",
        "monthly_price": 0,
        "setup_fee": 30000.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Custom software design and architecture",
                "Full-stack development",
                "Database design and implementation",
                "API development",
                "QA testing and bug fixes",
                "Deployment and documentation",
                "90-day warranty period",
            ],
        },
        "sections": [
            _parties_section("Software Development Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall design, develop, test, and deploy custom software for "
                    "{{client_name}} ({{client_company}}) as described in the Software Requirements "
                    "Specification (\"SRS\") document mutually agreed upon during the discovery "
                    "phase. The SRS is incorporated by reference into this Agreement. Any changes "
                    "to the SRS after approval require a formal change order signed by both parties."
                ),
            },
            {
                "title": "Development Process",
                "content": (
                    "{{business_name}} shall follow an agile development methodology with two-week "
                    "sprints. Client shall participate in: (a) sprint planning sessions; "
                    "(b) mid-sprint demos as requested; (c) sprint review and acceptance. "
                    "{{business_name}} shall maintain a project management board accessible to "
                    "Client and provide weekly written status updates."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The total project fee is {{setup_fee}}, payable in milestone installments "
                    "aligned with the project plan: 25% upon execution (discovery and architecture), "
                    "25% at midpoint (core development complete), 25% upon feature completion, and "
                    "25% upon final delivery and acceptance. All invoices are net-15."
                ),
            },
            {
                "title": "Acceptance & Warranty",
                "content": (
                    "Client has fifteen (15) business days after each milestone delivery to accept "
                    "or identify defects. Defects that deviate from the SRS are corrected at no "
                    "charge. After final acceptance, {{business_name}} provides a ninety (90) day "
                    "warranty period during which bugs in the delivered software are fixed at no "
                    "additional cost. This warranty does not cover: issues from Client modifications, "
                    "third-party system changes, or requirements not in the SRS."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Source Code & Documentation",
                "content": (
                    "Upon full payment, {{business_name}} shall deliver: (a) complete source code "
                    "in a version-controlled repository; (b) technical documentation including "
                    "architecture diagrams, API documentation, and deployment instructions; "
                    "(c) user documentation or training materials as specified in the SRS. "
                    "{{business_name}} shall use industry-standard coding practices and maintain "
                    "readable, well-documented code throughout the project."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Technology Consulting Agreement",
        "plan_name": "Technology Consulting",
        "monthly_price": 3000.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 3,
            "auto_renew": True,
            "cancellation_notice_days": 14,
            "includes": [
                "Technology strategy advisory",
                "Architecture reviews",
                "Vendor evaluation and selection",
                "Up to 20 hours/month",
                "Weekly consulting sessions",
                "Written recommendations and roadmaps",
            ],
        },
        "sections": [
            _parties_section("Technology Consulting Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide technology consulting services to {{client_name}} "
                    "({{client_company}}) including: strategic technology advisory, system "
                    "architecture reviews, vendor evaluation and selection guidance, technology "
                    "roadmap development, and implementation oversight. Services are delivered "
                    "through weekly consulting sessions (60-90 minutes), written analyses and "
                    "recommendations, and ad hoc consultations as needed within the monthly "
                    "hour allocation."
                ),
            },
            {
                "title": "Hours & Engagement Model",
                "content": (
                    "The monthly retainer of {{monthly_price}} includes up to twenty (20) hours of "
                    "consulting time per month. Hours are tracked in 15-minute increments and "
                    "reported monthly. Unused hours do not roll over. Additional hours beyond the "
                    "allocation are available at $175/hour with Client's prior approval. "
                    "{{business_name}} shall notify Client when 80% of monthly hours are consumed."
                ),
            },
            {
                "title": "Deliverables",
                "content": (
                    "{{business_name}} shall provide written deliverables as appropriate, including: "
                    "technology assessment reports, architecture diagrams, vendor comparison matrices, "
                    "implementation roadmaps, and meeting summaries. All deliverables become Client's "
                    "property upon delivery. Recommendations are advisory in nature; implementation "
                    "decisions and their outcomes remain Client's responsibility."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. It "
                    "renews month-to-month thereafter. Either party may terminate with fourteen "
                    "(14) days' written notice. Fees for partial months are prorated."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # CREATIVE & MARKETING
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Graphic Design Services Agreement",
        "plan_name": "Graphic Design Services",
        "monthly_price": 1500.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Logo design and brand identity",
                "Marketing collateral design",
                "Print-ready files",
                "Up to 20 design hours/month",
                "2 rounds of revisions per project",
                "Source files delivered",
            ],
        },
        "sections": [
            _parties_section("Graphic Design Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide graphic design services for {{client_name}} "
                    "({{client_company}}) including but not limited to: logo design and brand "
                    "identity development, marketing collateral (brochures, flyers, banners), "
                    "digital assets (social media graphics, email templates, web graphics), "
                    "print-ready file preparation, and brand guideline documentation. Up to twenty "
                    "(20) design hours per month are included in the retainer."
                ),
            },
            {
                "title": "Design Process & Revisions",
                "content": (
                    "Each design project follows: (1) creative brief from Client; (2) initial "
                    "concept presentation (2-3 options); (3) Client feedback; (4) up to two (2) "
                    "rounds of revisions; (5) final delivery. Additional revision rounds are billed "
                    "at $100/hour. Client approvals must be provided in writing (email is sufficient). "
                    "Designs approved by Client are deemed final."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly retainer of {{monthly_price}} is billed on the first of each month, "
                    "net-15. Unused hours do not roll over. Additional hours are billed at $100/hour "
                    "with Client's prior approval. Rush projects (turnaround under 48 hours) incur "
                    "a 50% surcharge."
                ),
            },
            {
                "title": "File Delivery & Ownership",
                "content": (
                    "Upon full payment, all custom designs become Client's property. {{business_name}} "
                    "shall deliver: (a) print-ready files (PDF, EPS, AI); (b) digital files (PNG, "
                    "JPG, SVG); (c) editable source files. {{business_name}} retains the right to "
                    "display completed work in its portfolio. Stock images, fonts, or licensed assets "
                    "used in designs are subject to their respective license terms, which "
                    "{{business_name}} shall disclose to Client."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may terminate with thirty (30) "
                    "days' notice. Work in progress at termination shall be completed and delivered "
                    "with proportional payment."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Video Production Agreement",
        "plan_name": "Video Production",
        "monthly_price": 0,
        "setup_fee": 5000.00,
        "default_terms": {
            "term_months": 2,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Pre-production (scripting, storyboarding)",
                "Filming (up to 1 day on location)",
                "Post-production editing",
                "Color grading and audio mixing",
                "2 rounds of revisions",
                "Final delivery in multiple formats",
            ],
        },
        "sections": [
            _parties_section("Video Production Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall produce video content for {{client_name}} "
                    "({{client_company}}) including: (a) pre-production: creative concept development, "
                    "scriptwriting, storyboarding, casting (if applicable), location scouting; "
                    "(b) production: filming up to one (1) day on location with professional "
                    "equipment and crew; (c) post-production: editing, color grading, audio mixing, "
                    "motion graphics, and music licensing. Final deliverable: [specify video length "
                    "and quantity] delivered in formats suitable for web, social media, and broadcast."
                ),
            },
            {
                "title": "Production Schedule",
                "content": (
                    "Pre-production: Weeks 1-2. Filming: Week 3-4. Post-production: Weeks 5-8. "
                    "Client must approve the script and storyboard before filming commences. "
                    "Rescheduling filming within 7 days of the scheduled date incurs a $500 "
                    "rescheduling fee. Weather-related rescheduling is free of charge."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Total production fee: {{setup_fee}}. Payment schedule: 50% upon execution "
                    "(covers pre-production and books filming date), 50% upon delivery of final "
                    "edited video. Music licensing, talent fees, location permits, and travel "
                    "expenses beyond [radius] miles are additional costs disclosed in advance."
                ),
            },
            {
                "title": "Revisions & Delivery",
                "content": (
                    "Two (2) rounds of revisions are included. Each revision round must be "
                    "submitted as a consolidated written document within five (5) business days of "
                    "receiving the edit. Additional revision rounds are billed at $200/hour. Final "
                    "delivery includes: MP4 (H.264/H.265), MOV (ProRes for broadcast), and "
                    "platform-specific exports as needed."
                ),
            },
            {
                "title": "Usage Rights & Licensing",
                "content": (
                    "Upon full payment, Client receives a perpetual, worldwide license to use the "
                    "final video for any purpose. {{business_name}} retains the right to use the "
                    "video in its portfolio and reel. Raw/unedited footage remains the property of "
                    "{{business_name}} unless purchased separately. Licensed music and stock footage "
                    "are subject to their respective license restrictions."
                ),
            },
            {
                "title": "Cancellation",
                "content": (
                    "If Client cancels before filming: {{business_name}} retains the pre-production "
                    "deposit (50%). If Client cancels after filming: Client owes the full project "
                    "fee. {{business_name}} may cancel due to force majeure with a full refund of "
                    "amounts paid for undelivered work."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Photography Services Agreement",
        "plan_name": "Photography Services",
        "monthly_price": 0,
        "setup_fee": 2500.00,
        "default_terms": {
            "term_months": 1,
            "auto_renew": False,
            "cancellation_notice_days": 7,
            "includes": [
                "Up to 4-hour photography session",
                "Professional editing and retouching",
                "50+ edited images delivered digitally",
                "Online gallery for selection",
                "Commercial usage license",
                "2-week delivery turnaround",
            ],
        },
        "sections": [
            _parties_section("Photography Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide professional photography services for "
                    "{{client_name}} ({{client_company}}) including: up to four (4) hours of "
                    "on-location or studio photography, professional editing and retouching of "
                    "selected images, delivery of fifty (50) or more edited high-resolution images "
                    "via online gallery, and a commercial usage license as detailed below."
                ),
            },
            {
                "title": "Session Details & Scheduling",
                "content": (
                    "Session date: [to be scheduled]. Location: [to be determined]. Client is "
                    "responsible for securing location access and permits. Rescheduling with less "
                    "than 48 hours' notice incurs a $250 rebooking fee. No-show without 24-hour "
                    "notice forfeits the full session fee. Weather-dependent outdoor sessions will "
                    "be rescheduled at no charge with mutual agreement."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Session fee: {{setup_fee}}. Payment: 50% non-refundable deposit upon booking, "
                    "50% balance due before delivery of final images. Additional hours during the "
                    "session are billed at $300/hour. Rush editing (under 5 business days) incurs "
                    "a 50% surcharge."
                ),
            },
            {
                "title": "Usage Rights & Licensing",
                "content": (
                    "Client receives a non-exclusive, perpetual, worldwide license to use the "
                    "delivered images for commercial purposes including marketing, advertising, "
                    "social media, print, and web use. {{business_name}} retains copyright ownership "
                    "and the right to use images in portfolio, marketing, and contest submissions. "
                    "Client shall not sell or sublicense the images to third parties. Exclusive "
                    "licensing is available for an additional fee upon request."
                ),
            },
            {
                "title": "Delivery & Image Selection",
                "content": (
                    "{{business_name}} shall deliver an online proof gallery within seven (7) "
                    "business days of the session. Client selects images for final editing. Edited "
                    "images are delivered within fourteen (14) business days of selection. Files are "
                    "delivered as high-resolution JPEG and/or TIFF. RAW files are not included but "
                    "are available for purchase separately."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Brand Strategy Agreement",
        "plan_name": "Brand Strategy",
        "monthly_price": 0,
        "setup_fee": 10000.00,
        "default_terms": {
            "term_months": 3,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Brand audit and competitive analysis",
                "Target audience research",
                "Brand positioning and messaging",
                "Visual identity direction",
                "Brand guidelines document",
                "Implementation roadmap",
            ],
        },
        "sections": [
            _parties_section("Brand Strategy Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} shall develop a comprehensive brand strategy for "
                    "{{client_name}} ({{client_company}}) including: (a) brand audit assessing "
                    "current positioning, assets, and market perception; (b) competitive landscape "
                    "analysis; (c) target audience research and persona development; (d) brand "
                    "positioning statement and key messaging framework; (e) visual identity "
                    "direction (mood boards, color palette, typography recommendations); "
                    "(f) comprehensive brand guidelines document; (g) implementation roadmap with "
                    "priorities and timeline."
                ),
            },
            {
                "title": "Process & Timeline",
                "content": (
                    "Phase 1 — Discovery (Weeks 1-3): stakeholder interviews, brand audit, "
                    "competitive analysis, audience research. Phase 2 — Strategy Development "
                    "(Weeks 4-8): positioning, messaging, visual direction. Phase 3 — Documentation "
                    "(Weeks 9-12): brand guidelines, implementation roadmap, presentation to "
                    "stakeholders. Client shall participate in scheduled workshops and provide "
                    "feedback within five (5) business days at each phase gate."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Total project fee: {{setup_fee}}. Payment: 40% upon execution, 30% upon "
                    "completion of Phase 1, 30% upon delivery of final brand guidelines. All "
                    "invoices are net-15."
                ),
            },
            {
                "title": "Deliverables & Ownership",
                "content": (
                    "Client shall receive: (a) brand strategy presentation deck; (b) brand "
                    "guidelines document (PDF and editable format); (c) messaging framework; "
                    "(d) visual direction reference materials; (e) implementation roadmap. All "
                    "deliverables become Client's property upon full payment. {{business_name}} "
                    "retains the right to reference the engagement in its portfolio."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # BUSINESS SERVICES
    # ──────────────────────────────────────────────────────────────
    {
        "name": "General Consulting Agreement",
        "plan_name": "General Consulting",
        "monthly_price": 2500.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Strategic advisory services",
                "Up to 15 hours/month",
                "Bi-weekly consulting sessions",
                "Written recommendations",
                "Email/phone support",
                "Quarterly business reviews",
            ],
        },
        "sections": [
            _parties_section("General Consulting Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide consulting and advisory services to "
                    "{{client_name}} ({{client_company}}) in the areas mutually agreed upon during "
                    "onboarding. Services include: strategic advisory, process improvement "
                    "recommendations, operational assessments, and implementation guidance. Services "
                    "are delivered through bi-weekly consulting sessions, written analyses, and "
                    "ad hoc email/phone consultations."
                ),
            },
            {
                "title": "Engagement Model",
                "content": (
                    "The monthly retainer of {{monthly_price}} includes up to fifteen (15) hours "
                    "of consulting per month, tracked in 15-minute increments. Unused hours do not "
                    "roll over. Additional hours are available at $200/hour with prior approval. "
                    "{{business_name}} shall provide monthly hour utilization reports."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly retainer of {{monthly_price}} billed on the first of each month, "
                    "net-15. Late payments incur a 1.5% monthly finance charge. Travel expenses "
                    "for on-site work (if requested) are billed separately with prior approval."
                ),
            },
            {
                "title": "Independent Contractor Status",
                "content": (
                    "{{business_name}} performs services as an independent contractor, not an "
                    "employee, partner, or agent of Client. {{business_name}} controls the manner "
                    "and means of performing services. {{business_name}} is responsible for its own "
                    "taxes, insurance, and benefits. Nothing in this Agreement creates an "
                    "employment, partnership, joint venture, or agency relationship."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may terminate with thirty (30) "
                    "days' notice. Partial months are prorated."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Business Coaching Agreement",
        "plan_name": "Business Coaching",
        "monthly_price": 1500.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "4 one-on-one coaching sessions/month (60 min each)",
                "Goal setting and accountability",
                "Action plan development",
                "Email support between sessions",
                "Resource library access",
                "Monthly progress reviews",
            ],
        },
        "sections": [
            _parties_section("Business Coaching Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide business coaching services to {{client_name}} "
                    "({{client_company}}) including: four (4) one-on-one coaching sessions per month "
                    "(60 minutes each, conducted via video call or in person), goal setting and "
                    "accountability frameworks, action plan development, email support between "
                    "sessions (24-hour response during business days), access to {{business_name}}'s "
                    "resource library, and monthly progress reviews."
                ),
            },
            {
                "title": "Coaching Relationship",
                "content": (
                    "The coaching relationship is designed to support Client's professional "
                    "development and business growth. {{business_name}} provides guidance, "
                    "accountability, and frameworks, but Client retains full decision-making "
                    "authority. Coaching is not therapy, legal advice, or financial advice. "
                    "{{business_name}} may refer Client to appropriate professionals when topics "
                    "fall outside coaching scope."
                ),
            },
            {
                "title": "Session Scheduling & Cancellation",
                "content": (
                    "Sessions are scheduled at mutually agreed times. Client may reschedule with "
                    "at least 24 hours' notice. Sessions cancelled with less than 24 hours' notice "
                    "or no-shows are forfeited and count toward the monthly allocation. Unused "
                    "sessions do not roll over. {{business_name}} shall provide reasonable "
                    "accommodation for scheduling conflicts."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly fee of {{monthly_price}} is billed on the first of each month, net-15. "
                    "A minimum commitment of {{term_months}} months is required for meaningful "
                    "coaching results."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. It renews month-to-month thereafter. Either party may terminate "
                    "with thirty (30) days' notice."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Freelancer/Independent Contractor Agreement",
        "plan_name": "Independent Contractor",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Defined scope of work",
                "Hourly or project-based payment",
                "IP assignment upon payment",
                "Independent contractor status",
                "Mutual confidentiality",
            ],
        },
        "sections": [
            _parties_section("Independent Contractor Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{client_name}} ({{client_company}}) engages {{business_name}} as an "
                    "independent contractor to perform the following services: [describe services]. "
                    "The specific deliverables, timelines, and milestones are detailed in "
                    "Exhibit A attached hereto. Changes to scope require written agreement from "
                    "both parties."
                ),
            },
            {
                "title": "Compensation",
                "content": (
                    "Client shall compensate {{business_name}} at a rate of [hourly rate/project "
                    "fee] as detailed in Exhibit A. Invoices are submitted [weekly/bi-weekly/monthly] "
                    "and are due within fifteen (15) days. {{business_name}} is responsible for "
                    "all taxes arising from compensation received under this Agreement."
                ),
            },
            {
                "title": "Independent Contractor Status",
                "content": (
                    "{{business_name}} is an independent contractor, not an employee of "
                    "{{client_company}}. {{business_name}} controls the time, place, and manner of "
                    "performing work. {{business_name}} receives no employee benefits and is "
                    "responsible for its own insurance, taxes, and business expenses. "
                    "{{business_name}} may engage subcontractors with Client's prior written consent."
                ),
            },
            _ip_section_work_for_hire(),
            {
                "title": "Non-Solicitation",
                "content": (
                    "During the term and for twelve (12) months following termination, neither party "
                    "shall directly solicit or hire the other party's employees or contractors who "
                    "were involved in the performance of this Agreement, without prior written consent."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} and continues until {{end_date}} or "
                    "completion of the scope of work, whichever comes first. Either party may "
                    "terminate with fourteen (14) days' written notice. Upon termination, "
                    "{{business_name}} shall deliver all completed and in-progress work, and Client "
                    "shall pay for all services rendered through the termination date."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Non-Disclosure Agreement (NDA)",
        "plan_name": "Non-Disclosure Agreement",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 24,
            "auto_renew": False,
            "cancellation_notice_days": 0,
            "includes": [
                "Mutual confidentiality obligations",
                "Defined confidential information",
                "Permitted disclosures",
                "Return/destruction of information",
                "Injunctive relief provisions",
            ],
        },
        "sections": [
            {
                "title": "Parties",
                "content": (
                    "This Non-Disclosure Agreement (\"Agreement\") is entered into as of "
                    "{{start_date}} by and between {{business_name}}, located at {{business_address}} "
                    "(\"Disclosing Party\" and/or \"Receiving Party\"), and {{client_name}} "
                    "({{client_company}}), located at {{client_address}} (\"Disclosing Party\" "
                    "and/or \"Receiving Party\"). This is a mutual NDA — each party may be both a "
                    "Disclosing Party and a Receiving Party."
                ),
            },
            {
                "title": "Definition of Confidential Information",
                "content": (
                    "\"Confidential Information\" means any and all non-public information disclosed "
                    "by either party to the other, whether orally, in writing, electronically, or "
                    "by observation, including but not limited to: business plans, financial data, "
                    "customer lists, pricing strategies, marketing plans, technical specifications, "
                    "product roadmaps, source code, algorithms, trade secrets, inventions, and any "
                    "information marked as \"confidential\" or that a reasonable person would "
                    "understand to be confidential given the nature of the information and "
                    "circumstances of disclosure."
                ),
            },
            {
                "title": "Exclusions",
                "content": (
                    "Confidential Information does not include information that: (a) is or becomes "
                    "publicly available through no fault of the Receiving Party; (b) was known to "
                    "the Receiving Party prior to disclosure, as documented; (c) is independently "
                    "developed by the Receiving Party without use of Confidential Information; "
                    "(d) is rightfully received from a third party without restriction; or "
                    "(e) is required to be disclosed by law, regulation, or court order, provided "
                    "the Receiving Party gives prompt notice and cooperates to seek protective measures."
                ),
            },
            {
                "title": "Obligations",
                "content": (
                    "The Receiving Party shall: (a) use Confidential Information solely for the "
                    "purpose of evaluating or pursuing a business relationship between the parties; "
                    "(b) restrict disclosure to employees, contractors, and advisors who need to "
                    "know and are bound by equivalent confidentiality obligations; (c) protect "
                    "Confidential Information with at least the same degree of care used for its "
                    "own confidential information, but no less than reasonable care; (d) not "
                    "reverse engineer, decompile, or analyze any tangible items containing "
                    "Confidential Information without prior written consent."
                ),
            },
            {
                "title": "Term & Duration",
                "content": (
                    "This Agreement is effective from {{start_date}} and the duty to exchange "
                    "Confidential Information continues until {{end_date}}. The confidentiality "
                    "obligations herein shall survive termination and continue for a period of "
                    "{{term_months}} months from the date of disclosure of each item of "
                    "Confidential Information."
                ),
            },
            {
                "title": "Return of Information",
                "content": (
                    "Upon written request or termination of this Agreement, the Receiving Party "
                    "shall promptly return or destroy all Confidential Information and any copies "
                    "thereof, and provide written certification of destruction. The Receiving Party "
                    "may retain one archival copy solely for legal compliance purposes, subject to "
                    "the ongoing confidentiality obligations."
                ),
            },
            {
                "title": "Remedies",
                "content": (
                    "The parties acknowledge that unauthorized disclosure of Confidential "
                    "Information may cause irreparable harm for which monetary damages may be "
                    "insufficient. Accordingly, either party may seek injunctive or equitable relief "
                    "in addition to any other remedies available at law. This Agreement does not "
                    "obligate either party to enter into any further agreement or business "
                    "relationship."
                ),
            },
            _general_provisions_section(),
        ],
    },
    {
        "name": "Partnership Agreement",
        "plan_name": "Partnership Agreement",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 24,
            "auto_renew": True,
            "cancellation_notice_days": 90,
            "includes": [
                "Roles and responsibilities",
                "Revenue sharing structure",
                "Decision-making authority",
                "Dispute resolution",
                "Exit and dissolution terms",
            ],
        },
        "sections": [
            {
                "title": "Parties & Formation",
                "content": (
                    "This Partnership Agreement (\"Agreement\") is entered into as of {{start_date}} "
                    "by and between {{business_name}}, located at {{business_address}}, and "
                    "{{client_name}} ({{client_company}}), located at {{client_address}}. The "
                    "parties hereby form a partnership (\"Partnership\") for the purpose of "
                    "[describe purpose]. The Partnership shall operate under the name [Partnership "
                    "Name] with its principal place of business at [address]."
                ),
            },
            {
                "title": "Roles & Responsibilities",
                "content": (
                    "Each partner's roles and responsibilities are as follows: {{business_name}} "
                    "shall be responsible for [describe responsibilities]. {{client_name}} shall be "
                    "responsible for [describe responsibilities]. Major decisions affecting the "
                    "Partnership — including expenditures over $[amount], new contracts, hiring, "
                    "and strategic direction — require unanimous written consent of all partners."
                ),
            },
            {
                "title": "Capital Contributions & Revenue Sharing",
                "content": (
                    "Initial capital contributions: {{business_name}}: $[amount]. {{client_name}}: "
                    "$[amount]. Revenue shall be distributed as follows: [percentage split]. "
                    "Distributions shall be made [monthly/quarterly] within fifteen (15) days of "
                    "period close. Each partner shall bear losses in proportion to their ownership "
                    "percentage. Additional capital contributions require mutual written agreement."
                ),
            },
            {
                "title": "Financial Management",
                "content": (
                    "The Partnership shall maintain a dedicated bank account. Both partners shall "
                    "have access to financial records. A quarterly financial statement shall be "
                    "prepared and shared. Each partner may audit the Partnership's books upon "
                    "reasonable notice. Tax returns shall be filed timely, and each partner is "
                    "responsible for taxes on their share of Partnership income."
                ),
            },
            {
                "title": "Term & Duration",
                "content": (
                    "The Partnership commences on {{start_date}} and continues for {{term_months}} "
                    "months until {{end_date}}, automatically renewing unless either party provides "
                    "ninety (90) days' written notice of intent to dissolve."
                ),
            },
            {
                "title": "Withdrawal & Dissolution",
                "content": (
                    "A partner may withdraw with ninety (90) days' written notice. The remaining "
                    "partner has the right of first refusal to purchase the withdrawing partner's "
                    "interest at fair market value determined by an independent appraiser. Upon "
                    "dissolution, Partnership assets shall be liquidated, debts paid, and remaining "
                    "proceeds distributed according to ownership percentages."
                ),
            },
            {
                "title": "Dispute Resolution",
                "content": (
                    "Disputes arising under this Agreement shall first be addressed through good-faith "
                    "negotiation. If unresolved within thirty (30) days, parties shall engage in "
                    "mediation with a mutually agreed mediator. If mediation fails, disputes shall "
                    "be submitted to binding arbitration under the rules of the American Arbitration "
                    "Association. Each party bears its own costs unless the arbitrator awards otherwise."
                ),
            },
            _confidentiality_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Referral Agreement",
        "plan_name": "Referral Agreement",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Referral commission structure",
                "Tracking and attribution",
                "Payment terms and schedule",
                "Exclusivity terms (if any)",
                "Performance reporting",
            ],
        },
        "sections": [
            _parties_section("Referral Agreement"),
            {
                "title": "Referral Program",
                "content": (
                    "{{business_name}} engages {{client_name}} ({{client_company}}) as a referral "
                    "partner (\"Referrer\") to introduce potential customers to {{business_name}}'s "
                    "products and services. Referrer shall introduce prospective clients through the "
                    "designated referral process (referral link, email introduction, or referral form "
                    "at {{business_website}}). All referrals must be new prospects not already in "
                    "{{business_name}}'s pipeline."
                ),
            },
            {
                "title": "Commission Structure",
                "content": (
                    "Referrer shall earn a commission of [percentage]% on the first [12 months / "
                    "contract value] of revenue generated from each qualified referral that converts "
                    "to a paying customer. A referral is \"qualified\" when the prospect signs a "
                    "contract and makes their first payment. Commissions are calculated on net "
                    "revenue (excluding taxes, refunds, and chargebacks)."
                ),
            },
            {
                "title": "Tracking & Attribution",
                "content": (
                    "Referrals are tracked via [referral link / CRM entry / written introduction]. "
                    "Attribution expires ninety (90) days after initial referral if the prospect has "
                    "not engaged. Disputes regarding attribution shall be resolved by "
                    "{{business_name}} in good faith, with documentation provided to Referrer upon "
                    "request."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Commissions are calculated monthly and paid within thirty (30) days of the "
                    "referred client's payment being received. Minimum payout threshold: $100. "
                    "Amounts below the threshold roll over to the next month. Referrer is responsible "
                    "for all taxes on commission income. {{business_name}} shall provide monthly "
                    "referral activity reports."
                ),
            },
            {
                "title": "Referrer Obligations",
                "content": (
                    "Referrer shall: (a) represent {{business_name}}'s services accurately; (b) not "
                    "make guarantees or commitments on {{business_name}}'s behalf; (c) comply with "
                    "all applicable laws and regulations including anti-spam laws; (d) disclose the "
                    "referral relationship when required by law or regulation. {{business_name}} "
                    "shall provide Referrer with approved marketing materials and messaging guidelines."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may terminate with thirty (30) "
                    "days' notice. Upon termination, Referrer continues to earn commissions on "
                    "referred clients who convert within sixty (60) days of termination. No "
                    "commissions are earned on referrals made after the termination date."
                ),
            },
            _confidentiality_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # PROFESSIONAL SERVICES
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Legal Services Retainer",
        "plan_name": "Legal Services Retainer",
        "monthly_price": 3500.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Up to 10 hours/month of legal services",
                "Contract review and drafting",
                "Legal consultation and advisory",
                "Regulatory compliance guidance",
                "Correspondence and negotiation",
                "Monthly billing statements",
            ],
        },
        "sections": [
            _parties_section("Legal Services Retainer Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide legal services to {{client_name}} "
                    "({{client_company}}) including: contract review and drafting, general legal "
                    "consultation, regulatory compliance guidance, correspondence on Client's "
                    "behalf, and negotiation support. Services are limited to the areas of law in "
                    "which {{business_name}} is qualified to practice. Litigation, appearances in "
                    "court, and specialized matters may require separate engagement agreements."
                ),
            },
            {
                "title": "Retainer & Billing",
                "content": (
                    "The monthly retainer of {{monthly_price}} covers up to ten (10) hours of legal "
                    "services per month. Time is tracked in six (6) minute increments. Additional "
                    "hours are billed at $350/hour. {{business_name}} shall provide monthly detailed "
                    "billing statements showing time entries, descriptions, and amounts. The retainer "
                    "is non-refundable for each month in which services are available, regardless of "
                    "utilization."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide complete and accurate information relevant to the "
                    "legal matters; (b) respond to requests for information within a reasonable time; "
                    "(c) make decisions regarding legal strategy after receiving {{business_name}}'s "
                    "advice; (d) not take actions that conflict with {{business_name}}'s legal advice "
                    "without disclosure. Client acknowledges that legal outcomes cannot be guaranteed."
                ),
            },
            {
                "title": "Conflicts of Interest",
                "content": (
                    "{{business_name}} has conducted a conflict check and, to the best of its "
                    "knowledge, represents no parties whose interests are adverse to Client's in "
                    "the matters covered by this Agreement. {{business_name}} shall promptly notify "
                    "Client if a conflict arises and may need to decline representation in specific "
                    "matters. Client consents to {{business_name}} representing other clients in "
                    "matters unrelated to Client's engagement."
                ),
            },
            {
                "title": "Attorney-Client Privilege",
                "content": (
                    "Communications between {{business_name}} and Client are protected by "
                    "attorney-client privilege. Client should mark communications as "
                    "\"Privileged and Confidential\" to help preserve this protection. Client "
                    "controls the privilege and may waive it; {{business_name}} shall not waive "
                    "the privilege without Client's written consent."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. Either "
                    "party may terminate with thirty (30) days' written notice. Upon termination, "
                    "{{business_name}} shall return Client's files and documents and cooperate in "
                    "transitioning matters to successor counsel."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Accounting & Bookkeeping Agreement",
        "plan_name": "Accounting & Bookkeeping",
        "monthly_price": 800.00,
        "setup_fee": 250.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Monthly bookkeeping",
                "Bank and credit card reconciliation",
                "Monthly financial statements",
                "Accounts payable/receivable management",
                "Quarterly tax estimates",
                "Year-end tax preparation support",
            ],
        },
        "sections": [
            _parties_section("Accounting & Bookkeeping Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide accounting and bookkeeping services for "
                    "{{client_name}} ({{client_company}}) including: monthly transaction recording "
                    "and categorization, bank and credit card reconciliation, preparation of monthly "
                    "financial statements (income statement, balance sheet, cash flow statement), "
                    "accounts payable and receivable tracking, quarterly estimated tax calculations, "
                    "and year-end financial package preparation for tax filing."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide timely access to bank feeds, credit card statements, "
                    "and financial documents; (b) provide receipts and supporting documentation "
                    "within five (5) business days of request; (c) approve transactions requiring "
                    "judgment calls within three (3) business days; (d) maintain organized records "
                    "of business expenses."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Setup/onboarding fee of {{setup_fee}} is due upon execution. Monthly service "
                    "fee of {{monthly_price}} is billed on the first of each month, net-15. "
                    "Additional services (payroll processing, audit support, specialized tax work) "
                    "are quoted separately."
                ),
            },
            {
                "title": "Accuracy & Limitations",
                "content": (
                    "{{business_name}} shall exercise professional care and diligence in performing "
                    "services. The accuracy of financial records depends on the completeness and "
                    "accuracy of information provided by Client. {{business_name}} does not perform "
                    "audits and does not express an opinion on the financial statements. Client is "
                    "ultimately responsible for the accuracy of tax filings."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may terminate with thirty (30) "
                    "days' notice. Upon termination, {{business_name}} shall deliver all financial "
                    "records, books, and access credentials to Client within fifteen (15) business days."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "HR & Recruiting Agreement",
        "plan_name": "HR & Recruiting",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Candidate sourcing and screening",
                "Interview coordination",
                "Reference checks",
                "Offer negotiation support",
                "90-day placement guarantee",
                "Replacement search if needed",
            ],
        },
        "sections": [
            _parties_section("HR & Recruiting Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide recruitment and placement services for "
                    "{{client_name}} ({{client_company}}) including: candidate sourcing through "
                    "job boards, professional networks, and direct outreach; resume screening and "
                    "qualification assessment; interview scheduling and coordination; reference "
                    "and background checks for finalist candidates; offer negotiation support; "
                    "and onboarding transition assistance."
                ),
            },
            {
                "title": "Placement Fees",
                "content": (
                    "Client agrees to pay a placement fee equal to [percentage]% of the placed "
                    "candidate's first-year base salary. The fee is due within thirty (30) days of "
                    "the candidate's start date. For contingency searches, no fee is owed unless a "
                    "candidate is placed. For retained searches, fees are structured as: 1/3 upon "
                    "engagement, 1/3 upon presentation of shortlist, 1/3 upon placement."
                ),
            },
            {
                "title": "Guarantee Period",
                "content": (
                    "{{business_name}} provides a ninety (90) day guarantee on all placements. If a "
                    "placed candidate voluntarily resigns or is terminated for cause within ninety "
                    "(90) days of start date, {{business_name}} shall conduct a replacement search "
                    "at no additional fee. The guarantee is void if: (a) the position's scope or "
                    "compensation changes materially; (b) Client eliminates the position; (c) "
                    "termination is due to layoffs or restructuring."
                ),
            },
            {
                "title": "Candidate Ownership",
                "content": (
                    "Candidates presented by {{business_name}} are considered {{business_name}}'s "
                    "referrals for twelve (12) months from the date of introduction. If Client "
                    "hires a referred candidate within this period (whether for the original role "
                    "or any other), the placement fee applies."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months with "
                    "auto-renewal. Either party may terminate with thirty (30) days' notice. "
                    "Termination does not affect fees owed for placements already made or the "
                    "guarantee period for active placements."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Real Estate Services Agreement",
        "plan_name": "Real Estate Services",
        "monthly_price": 0,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Property listing and marketing",
                "Professional photography",
                "MLS listing management",
                "Open house coordination",
                "Offer negotiation",
                "Transaction management through closing",
            ],
        },
        "sections": [
            _parties_section("Real Estate Services Agreement"),
            {
                "title": "Listing & Marketing Services",
                "content": (
                    "{{business_name}} shall provide real estate brokerage services for "
                    "{{client_name}} ({{client_company}}) including: listing the property on the "
                    "Multiple Listing Service (MLS) and major real estate platforms, professional "
                    "photography and virtual tour creation, marketing materials and advertising, "
                    "open house scheduling and hosting, buyer inquiries management, and showing "
                    "coordination."
                ),
            },
            {
                "title": "Commission & Compensation",
                "content": (
                    "Client agrees to pay {{business_name}} a commission of [percentage]% of the "
                    "final sale price upon successful closing. The commission is split with the "
                    "buyer's agent (if applicable) as follows: [split details]. Commission is "
                    "earned upon closing and is payable from closing proceeds. If the property "
                    "does not sell during the listing term, no commission is owed."
                ),
            },
            {
                "title": "Exclusivity",
                "content": (
                    "This is an [exclusive right to sell / exclusive agency / open listing] "
                    "agreement. During the listing term, Client agrees to [exclusivity terms]. "
                    "If Client enters into a transaction with a buyer procured by another agent "
                    "or by Client directly during the listing term, commission obligations depend "
                    "on the listing type selected."
                ),
            },
            {
                "title": "Listing Term",
                "content": (
                    "The listing period commences on {{start_date}} and expires on {{end_date}} "
                    "({{term_months}} months). The listing does not auto-renew. Extension requires "
                    "a written amendment signed by both parties. Either party may terminate with "
                    "thirty (30) days' written notice, subject to any pending offers."
                ),
            },
            {
                "title": "Client Representations",
                "content": (
                    "Client represents that: (a) Client has legal authority to sell the property; "
                    "(b) Client will disclose all known material defects; (c) the property "
                    "information provided is accurate; (d) there are no undisclosed liens, "
                    "encumbrances, or legal actions affecting the property. Client shall indemnify "
                    "{{business_name}} for claims arising from misrepresentation."
                ),
            },
            {
                "title": "Agency Disclosure",
                "content": (
                    "{{business_name}} acts as Client's agent in this transaction. "
                    "{{business_name}} owes Client fiduciary duties of loyalty, confidentiality, "
                    "disclosure, obedience, and reasonable care. {{business_name}} shall disclose "
                    "any dual agency situation and obtain written consent before proceeding."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # CONSTRUCTION & TRADES
    # ──────────────────────────────────────────────────────────────
    {
        "name": "General Contractor Agreement",
        "plan_name": "General Contractor",
        "monthly_price": 0,
        "setup_fee": 50000.00,
        "default_terms": {
            "term_months": 6,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Project management and oversight",
                "Labor and material procurement",
                "Subcontractor management",
                "Building permit coordination",
                "Quality inspections",
                "1-year workmanship warranty",
            ],
        },
        "sections": [
            _parties_section("General Contractor Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} (\"Contractor\") shall perform construction services for "
                    "{{client_name}} ({{client_company}}) (\"Owner\") as described in the project "
                    "plans, specifications, and bid documents (collectively, \"Plans\") attached as "
                    "Exhibit A. Work includes: all labor, materials, equipment, and services "
                    "necessary to complete the project in accordance with the Plans, applicable "
                    "building codes, and local regulations."
                ),
            },
            {
                "title": "Contract Price & Payment Schedule",
                "content": (
                    "The total contract price is {{setup_fee}} (\"Contract Price\"). Payment "
                    "schedule: 10% upon execution (mobilization), followed by monthly progress "
                    "payments based on percentage of work completed, verified by inspection. "
                    "Contractor shall submit monthly payment applications by the 25th of each month. "
                    "Owner shall pay within fifteen (15) days of approved application. Owner may "
                    "retain 10% of each payment until substantial completion."
                ),
            },
            {
                "title": "Change Orders",
                "content": (
                    "Changes to the scope, schedule, or Contract Price require a written Change "
                    "Order signed by both parties before additional work begins. Contractor shall "
                    "provide a Change Order proposal within five (5) business days of Owner's "
                    "request, including cost and schedule impact. Work performed without an approved "
                    "Change Order is at Contractor's sole risk and expense."
                ),
            },
            {
                "title": "Project Timeline",
                "content": (
                    "Work shall commence within [number] days of execution and shall be substantially "
                    "complete within {{term_months}} months (by {{end_date}}). Time is of the "
                    "essence. Delays caused by weather, permit issues, material shortages, or Owner "
                    "changes shall extend the timeline by a commensurate period. Contractor shall "
                    "provide a detailed project schedule within ten (10) days of execution and "
                    "update it bi-weekly."
                ),
            },
            {
                "title": "Permits, Insurance & Safety",
                "content": (
                    "Contractor shall: (a) obtain all required building permits; (b) maintain "
                    "general liability insurance ($1M per occurrence / $2M aggregate), workers' "
                    "compensation, and commercial auto insurance; (c) comply with OSHA and local "
                    "safety regulations; (d) maintain a clean and safe job site. Certificates of "
                    "insurance shall be provided to Owner before work commences."
                ),
            },
            {
                "title": "Warranty",
                "content": (
                    "Contractor warrants all workmanship for one (1) year from substantial "
                    "completion. Materials are warranted per manufacturer terms. Contractor shall "
                    "promptly repair defective work discovered during the warranty period at no "
                    "cost to Owner. This warranty does not cover damage caused by Owner's misuse, "
                    "lack of maintenance, or modifications by others."
                ),
            },
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Subcontractor Agreement",
        "plan_name": "Subcontractor Services",
        "monthly_price": 0,
        "setup_fee": 15000.00,
        "default_terms": {
            "term_months": 3,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Specified trade work",
                "Materials and labor",
                "Insurance and licensing",
                "Compliance with project schedule",
                "Cleanup and debris removal",
            ],
        },
        "sections": [
            _parties_section("Subcontractor Agreement"),
            {
                "title": "Scope of Work",
                "content": (
                    "{{business_name}} (\"General Contractor\") engages {{client_name}} "
                    "({{client_company}}) (\"Subcontractor\") to perform the following trade work: "
                    "[describe specific trade/scope]. Work shall be performed in accordance with "
                    "the project plans and specifications provided by General Contractor. "
                    "Subcontractor shall furnish all labor, materials, tools, and equipment "
                    "necessary unless otherwise specified."
                ),
            },
            {
                "title": "Schedule & Coordination",
                "content": (
                    "Subcontractor shall commence work on or about {{start_date}} and complete "
                    "all work by {{end_date}}. Subcontractor shall coordinate with General "
                    "Contractor's project schedule and other trades on site. Subcontractor shall "
                    "maintain adequate workforce to meet schedule requirements and notify General "
                    "Contractor immediately of any anticipated delays."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "The subcontract value is {{setup_fee}}. Payment: progress payments based on "
                    "work completed, submitted via monthly payment applications. General Contractor "
                    "shall pay within fifteen (15) days of receiving payment from Owner for "
                    "Subcontractor's work. General Contractor may retain 10% until project "
                    "completion. Final payment due within thirty (30) days of Subcontractor's "
                    "work being accepted."
                ),
            },
            {
                "title": "Insurance & Compliance",
                "content": (
                    "Subcontractor shall maintain: general liability insurance ($1M per occurrence), "
                    "workers' compensation as required by law, and commercial auto insurance. "
                    "Subcontractor shall hold all required licenses and permits for the trade work. "
                    "Subcontractor shall comply with OSHA regulations and site safety rules."
                ),
            },
            {
                "title": "Cleanup & Site Conditions",
                "content": (
                    "Subcontractor shall maintain a clean work area and remove debris daily. Upon "
                    "completion, Subcontractor shall remove all equipment, excess materials, and "
                    "debris from the site. Failure to maintain cleanliness may result in back-charges "
                    "at $50/hour for cleanup performed by others."
                ),
            },
            _indemnification_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Interior Design Agreement",
        "plan_name": "Interior Design",
        "monthly_price": 0,
        "setup_fee": 8000.00,
        "default_terms": {
            "term_months": 4,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Space planning and layout",
                "Design concept development",
                "Material and finish selections",
                "Furniture procurement coordination",
                "Vendor management",
                "Installation oversight",
            ],
        },
        "sections": [
            _parties_section("Interior Design Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide interior design services for {{client_name}} "
                    "({{client_company}}) for the space located at [property address]. Services "
                    "include: (a) initial consultation and needs assessment; (b) space planning and "
                    "layout design; (c) design concept presentation with mood boards and renderings; "
                    "(d) material, finish, and color palette selection; (e) furniture and fixture "
                    "selection and procurement coordination; (f) vendor and contractor coordination; "
                    "(g) installation supervision and final styling."
                ),
            },
            {
                "title": "Design Phases",
                "content": (
                    "Phase 1 — Concept (Weeks 1-3): site assessment, client brief, concept "
                    "presentation. Phase 2 — Development (Weeks 4-8): detailed plans, material "
                    "selections, furniture specifications. Phase 3 — Procurement (Weeks 9-12): "
                    "ordering, vendor coordination, lead time management. Phase 4 — Installation "
                    "(Weeks 13-16): delivery coordination, installation, styling, final walkthrough. "
                    "Client approval is required before proceeding from each phase."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Design fee: {{setup_fee}}, payable: 40% upon execution, 30% upon Phase 2 "
                    "completion, 30% upon installation. Furniture and material costs are separate "
                    "and billed directly to Client or through {{business_name}} with a [percentage]% "
                    "procurement markup. All invoices are net-15."
                ),
            },
            {
                "title": "Procurement & Purchasing",
                "content": (
                    "{{business_name}} may purchase items on Client's behalf using trade accounts "
                    "and designer discounts. Client is responsible for all product costs, shipping, "
                    "and applicable taxes. {{business_name}} applies a standard procurement fee of "
                    "[percentage]% to cover ordering, tracking, and coordination. Returns and "
                    "exchanges are subject to vendor policies; {{business_name}} shall facilitate "
                    "but is not liable for vendor return policies."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide access to the space for measurements and installation; "
                    "(b) approve designs and selections within five (5) business days; (c) make "
                    "timely decisions to avoid project delays; (d) pay invoices on schedule to avoid "
                    "procurement delays."
                ),
            },
            _ip_section_work_for_hire(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Landscaping Services Agreement",
        "plan_name": "Landscaping Services",
        "monthly_price": 450.00,
        "setup_fee": 2000.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Weekly lawn maintenance",
                "Seasonal planting and mulching",
                "Irrigation system management",
                "Tree and shrub pruning",
                "Leaf and debris removal",
                "Snow removal (seasonal)",
            ],
        },
        "sections": [
            _parties_section("Landscaping Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide landscaping maintenance services for "
                    "{{client_name}} at the property located at {{client_address}}. Services "
                    "include: weekly lawn mowing, edging, and blowing (March–November); seasonal "
                    "planting, mulching, and bed maintenance; irrigation system activation, "
                    "winterization, and monthly inspections; tree and shrub pruning (spring and "
                    "fall); leaf removal (fall season); and snow removal for walkways and driveways "
                    "(winter season, triggered at 2+ inches accumulation)."
                ),
            },
            {
                "title": "Seasonal Schedule",
                "content": (
                    "Spring (Mar–May): cleanup, mulching, planting, irrigation activation. "
                    "Summer (Jun–Aug): weekly mowing, irrigation monitoring, pest treatment. "
                    "Fall (Sep–Nov): leaf removal, aeration, overseeding, winterization. "
                    "Winter (Dec–Feb): snow removal, equipment maintenance, spring planning."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Annual maintenance is billed as equal monthly installments of {{monthly_price}} "
                    "(twelve months). Initial landscape design/installation fee: {{setup_fee}}. "
                    "Monthly invoices are due on the first of each month, net-15. Additional services "
                    "(hardscaping, major tree removal, irrigation repair) are quoted separately."
                ),
            },
            {
                "title": "Access & Property",
                "content": (
                    "Client shall provide {{business_name}} with gate codes, keys, or other access "
                    "necessary to perform services. {{business_name}} shall take reasonable care to "
                    "avoid damage to Client's property but is not liable for pre-existing conditions, "
                    "underground utilities not properly marked, or damage caused by weather events."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}, with auto-renewal. Either party may terminate with thirty (30) "
                    "days' notice. Seasonal work already scheduled at the time of termination shall "
                    "be completed and billed."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # EVENTS & HOSPITALITY
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Event Planning Agreement",
        "plan_name": "Event Planning",
        "monthly_price": 0,
        "setup_fee": 5000.00,
        "default_terms": {
            "term_months": 4,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Full event planning and coordination",
                "Venue selection assistance",
                "Vendor sourcing and management",
                "Timeline and logistics management",
                "Day-of coordination",
                "Post-event wrap-up",
            ],
        },
        "sections": [
            _parties_section("Event Planning Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide event planning and coordination services for "
                    "{{client_name}} ({{client_company}}) for the following event: [event name/type] "
                    "on [event date] at [venue or TBD]. Services include: venue selection and "
                    "booking assistance, vendor sourcing (catering, entertainment, florals, "
                    "AV/lighting, photography), budget development and tracking, timeline and "
                    "logistics management, guest management (RSVPs, seating), day-of coordination "
                    "with on-site team, and post-event vendor settlement."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Planning fee: {{setup_fee}}. Payment: 50% non-refundable retainer upon "
                    "execution, 25% sixty (60) days before event, 25% final payment fourteen (14) "
                    "days before event. Vendor costs are separate and paid directly by Client or "
                    "through {{business_name}} as agent. {{business_name}} may charge a coordination "
                    "fee of [percentage]% on vendor services booked through {{business_name}}."
                ),
            },
            {
                "title": "Cancellation & Postponement",
                "content": (
                    "If Client cancels more than ninety (90) days before the event: 50% retainer "
                    "is forfeited. Cancellation 30-90 days before: 75% of total fee owed. "
                    "Cancellation less than 30 days: 100% of total fee owed. Postponement: one "
                    "date change is accommodated at no additional fee if the new date is within "
                    "six (6) months. Additional changes incur a $500 rescheduling fee. Vendor "
                    "cancellation fees are Client's responsibility."
                ),
            },
            {
                "title": "Force Majeure",
                "content": (
                    "Neither party shall be liable for failure to perform due to circumstances "
                    "beyond reasonable control, including natural disasters, pandemic restrictions, "
                    "government orders, venue closures, or extreme weather. In such cases, "
                    "{{business_name}} shall use best efforts to reschedule or modify the event. "
                    "Unrecoverable vendor deposits remain Client's responsibility."
                ),
            },
            {
                "title": "Client Responsibilities",
                "content": (
                    "Client shall: (a) provide timely decisions and approvals (within 5 business "
                    "days); (b) communicate final guest count at least fourteen (14) days before "
                    "the event; (c) provide any special requirements (dietary, accessibility) in "
                    "advance; (d) designate a single decision-maker for the planning process."
                ),
            },
            _liability_section(),
            _indemnification_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Catering Agreement",
        "plan_name": "Catering Services",
        "monthly_price": 0,
        "setup_fee": 3500.00,
        "default_terms": {
            "term_months": 1,
            "auto_renew": False,
            "cancellation_notice_days": 14,
            "includes": [
                "Menu planning and customization",
                "Food preparation and service",
                "Service staff",
                "Tableware and linens (rental)",
                "Setup and cleanup",
                "Food tasting session",
            ],
        },
        "sections": [
            _parties_section("Catering Agreement"),
            {
                "title": "Event Details & Menu",
                "content": (
                    "{{business_name}} shall provide catering services for {{client_name}} "
                    "({{client_company}}) for the event on [date] at [venue]. Estimated guest count: "
                    "[number]. Menu: as detailed in Exhibit A (Menu Selection). Final guest count "
                    "must be confirmed fourteen (14) days before the event. The confirmed count is "
                    "the minimum billed, even if actual attendance is lower. Increases up to 10% "
                    "above confirmed count are accommodated when possible."
                ),
            },
            {
                "title": "Pricing & Payment",
                "content": (
                    "Total estimated cost: {{setup_fee}} based on [number] guests at $[per person] "
                    "per person. Payment: 30% non-refundable deposit upon contract execution, "
                    "balance due seven (7) days before the event based on confirmed guest count. "
                    "Final invoice adjustments for actual attendance are due within seven (7) days "
                    "of the event. Gratuity is [included / not included]."
                ),
            },
            {
                "title": "Food Safety & Allergies",
                "content": (
                    "{{business_name}} maintains all required food handler certifications and health "
                    "department permits. Client shall communicate all known food allergies and "
                    "dietary restrictions at least fourteen (14) days before the event. "
                    "{{business_name}} shall clearly label menu items containing common allergens. "
                    "{{business_name}} is not liable for allergic reactions when proper disclosure "
                    "was not made."
                ),
            },
            {
                "title": "Setup, Service & Cleanup",
                "content": (
                    "{{business_name}} shall arrive at the venue [number] hours before the event "
                    "for setup. Service includes [buffet / plated / family style / stations]. "
                    "Cleanup includes removal of all food, equipment, and catering supplies. "
                    "Client is responsible for providing adequate access, power, and running water "
                    "at the venue."
                ),
            },
            {
                "title": "Cancellation",
                "content": (
                    "Cancellation more than thirty (30) days before: deposit forfeited. "
                    "Cancellation 14–30 days before: 50% of total owed. Cancellation less than "
                    "14 days: 100% owed. Menu changes within seven (7) days of the event are "
                    "subject to availability and may incur surcharges."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Venue Rental Agreement",
        "plan_name": "Venue Rental",
        "monthly_price": 0,
        "setup_fee": 5000.00,
        "default_terms": {
            "term_months": 1,
            "auto_renew": False,
            "cancellation_notice_days": 30,
            "includes": [
                "Venue rental for specified dates/hours",
                "Tables and chairs (standard setup)",
                "Basic AV equipment",
                "Parking access",
                "On-site venue coordinator",
                "Cleaning service",
            ],
        },
        "sections": [
            _parties_section("Venue Rental Agreement"),
            {
                "title": "Rental Details",
                "content": (
                    "{{business_name}} (\"Venue\") agrees to rent the following space to "
                    "{{client_name}} ({{client_company}}) (\"Renter\"): [space name/description]. "
                    "Event date(s): [date]. Access time: [start time] to [end time]. Maximum "
                    "capacity: [number] persons. Event type: [describe]. The space includes: "
                    "standard table and chair setup, basic AV equipment (projector, screen, "
                    "microphone), restroom access, and parking for [number] vehicles."
                ),
            },
            {
                "title": "Rental Fee & Deposit",
                "content": (
                    "Total rental fee: {{setup_fee}}. Payment: 50% deposit to secure the date, "
                    "non-refundable after fourteen (14) days of booking. Balance due fourteen (14) "
                    "days before the event. Security deposit of $[amount] due with balance, "
                    "refundable within fourteen (14) days post-event less any deductions for "
                    "damage, excessive cleaning, or overtime."
                ),
            },
            {
                "title": "Rules & Restrictions",
                "content": (
                    "Renter shall: (a) not exceed venue capacity; (b) comply with noise ordinances "
                    "and quiet hours; (c) not affix anything to walls/ceilings without approval; "
                    "(d) not bring open flames (candles) without prior approval; (e) ensure all "
                    "vendors carry required insurance; (f) remove all decorations by the end of "
                    "the rental period. Renter is responsible for the conduct of all guests "
                    "and vendors."
                ),
            },
            {
                "title": "Insurance & Liability",
                "content": (
                    "Renter shall obtain event liability insurance with a minimum of $1,000,000 "
                    "per occurrence naming {{business_name}} as additional insured. Proof of "
                    "insurance must be provided fourteen (14) days before the event. Renter is "
                    "responsible for any damage to the venue, equipment, or property caused by "
                    "Renter, guests, or vendors."
                ),
            },
            {
                "title": "Cancellation",
                "content": (
                    "Cancellation more than ninety (90) days before: deposit minus $500 "
                    "administrative fee is refundable. 30–90 days: 50% of total owed. Less than "
                    "30 days: 100% owed. Date changes are treated as cancellation and rebooking "
                    "at current rates, subject to availability."
                ),
            },
            {
                "title": "Damage & Cleanup",
                "content": (
                    "Renter shall return the venue in the condition received. Basic cleanup "
                    "(sweeping, trash removal) is included. Excessive cleanup needs (stains, "
                    "decoration adhesive removal) are charged at $75/hour against the security "
                    "deposit. Damage to property, fixtures, or equipment is assessed at repair or "
                    "replacement cost."
                ),
            },
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # HEALTHCARE & WELLNESS
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Telehealth Services Agreement",
        "plan_name": "Telehealth Services",
        "monthly_price": 200.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Virtual consultations",
                "Secure video platform access",
                "Appointment scheduling",
                "Basic health assessments",
                "Prescription coordination (where applicable)",
                "Secure messaging with provider",
            ],
        },
        "sections": [
            _parties_section("Telehealth Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide telehealth services to {{client_name}} "
                    "including virtual health consultations via secure video platform, basic health "
                    "assessments, wellness guidance, and prescription coordination where legally "
                    "permitted. Services are provided by licensed healthcare professionals. "
                    "Telehealth is not a substitute for emergency care; Client should call 911 "
                    "for emergencies."
                ),
            },
            {
                "title": "Informed Consent for Telehealth",
                "content": (
                    "Client acknowledges and consents to: (a) the use of electronic communications "
                    "for health consultations; (b) the limitations of telehealth, including inability "
                    "to perform physical examinations; (c) the possibility that the provider may "
                    "determine telehealth is inappropriate and recommend in-person care; (d) the "
                    "potential for technology failures that may interrupt service. Client has the "
                    "right to withdraw consent at any time."
                ),
            },
            {
                "title": "Privacy & HIPAA Compliance",
                "content": (
                    "{{business_name}} complies with the Health Insurance Portability and "
                    "Accountability Act (HIPAA) and maintains appropriate safeguards for protected "
                    "health information (PHI). All telehealth sessions use HIPAA-compliant, "
                    "encrypted video platforms. {{business_name}}'s Notice of Privacy Practices is "
                    "available at {{business_website}} or upon request. Client's health information "
                    "shall not be shared without consent except as permitted by HIPAA."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly membership fee of {{monthly_price}} includes [number] virtual "
                    "consultations per month. Additional consultations are billed at $[rate] each. "
                    "Monthly fee is billed on the first of each month, net-15. Insurance billing "
                    "is [included / not included]; Client is responsible for verifying coverage."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. It "
                    "renews month-to-month. Either party may terminate with thirty (30) days' "
                    "notice. {{business_name}} may terminate immediately if continued treatment "
                    "is clinically inappropriate. {{business_name}} shall provide referrals upon "
                    "request at termination."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Personal Training Agreement",
        "plan_name": "Personal Training",
        "monthly_price": 400.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 3,
            "auto_renew": True,
            "cancellation_notice_days": 14,
            "includes": [
                "8 personal training sessions/month",
                "Custom workout programming",
                "Nutritional guidance",
                "Progress tracking and assessments",
                "App access for workout logging",
                "Email support between sessions",
            ],
        },
        "sections": [
            _parties_section("Personal Training Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide personal training services to {{client_name}} "
                    "including: eight (8) personal training sessions per month (approximately 60 "
                    "minutes each), customized workout programming, basic nutritional guidance, "
                    "monthly fitness assessments and progress tracking, and email support between "
                    "sessions for form checks and questions."
                ),
            },
            {
                "title": "Assumption of Risk & Liability Waiver",
                "content": (
                    "Client acknowledges that physical exercise involves inherent risks including "
                    "but not limited to: muscle strains, sprains, fractures, cardiovascular events, "
                    "and other injuries. Client represents that they are physically fit to "
                    "participate in exercise, have consulted with a physician if appropriate, and "
                    "have disclosed any medical conditions, injuries, or medications to "
                    "{{business_name}}. CLIENT VOLUNTARILY ASSUMES ALL RISKS AND RELEASES "
                    "{{business_name}} FROM LIABILITY FOR INJURIES EXCEPT THOSE CAUSED BY GROSS "
                    "NEGLIGENCE OR WILLFUL MISCONDUCT."
                ),
            },
            {
                "title": "Session Scheduling & Cancellation",
                "content": (
                    "Sessions are scheduled at mutually agreed times. Client may reschedule with "
                    "at least twelve (12) hours' notice. Sessions cancelled with less than 12 hours' "
                    "notice or no-shows are forfeited. Unused sessions do not roll over to the "
                    "following month. {{business_name}} will make reasonable efforts to accommodate "
                    "scheduling preferences."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly fee of {{monthly_price}} is billed on the first of each month, due "
                    "upon receipt. Late payments result in session suspension until the account "
                    "is current."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. It renews month-to-month thereafter. Either party may terminate "
                    "with fourteen (14) days' notice. No refunds for partial months."
                ),
            },
            {
                "title": "Health Disclaimer",
                "content": (
                    "{{business_name}} is not a licensed medical provider. Training and nutritional "
                    "guidance provided are for general fitness purposes only and do not constitute "
                    "medical advice. Client should consult a physician before beginning any exercise "
                    "program. {{business_name}} reserves the right to refuse or modify services if "
                    "Client's health condition poses unacceptable risk."
                ),
            },
            _general_provisions_section(),
        ],
    },
    {
        "name": "Salon/Spa Services Agreement",
        "plan_name": "Salon/Spa Membership",
        "monthly_price": 150.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 30,
            "includes": [
                "Monthly signature service credit",
                "Member-only pricing on add-ons",
                "Priority booking",
                "Birthday complimentary service",
                "Product discounts (15%)",
                "Guest pass (1 per quarter)",
            ],
        },
        "sections": [
            _parties_section("Salon/Spa Membership Agreement"),
            {
                "title": "Membership Benefits",
                "content": (
                    "{{business_name}} provides {{client_name}} with the following membership "
                    "benefits: one (1) signature service credit per month (valued at up to $[value]), "
                    "member pricing on additional services, priority appointment booking, one "
                    "complimentary birthday service per year, 15% discount on retail products, "
                    "and one guest pass per quarter."
                ),
            },
            {
                "title": "Service Credits & Rollover",
                "content": (
                    "Monthly service credits must be used within the calendar month. Unused credits "
                    "may roll over for up to two (2) months (maximum of three months' credits "
                    "accumulated). Credits beyond three months expire. Credits have no cash value "
                    "and are non-transferable except for guest passes."
                ),
            },
            {
                "title": "Booking & Cancellation",
                "content": (
                    "Appointments are scheduled through {{business_website}} or by calling "
                    "{{business_phone}}. Members enjoy priority booking but must cancel or "
                    "reschedule at least twenty-four (24) hours in advance. Late cancellations "
                    "forfeit the service credit or incur a $50 fee for non-credit appointments. "
                    "No-shows forfeit the credit and incur a $75 fee."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly membership fee of {{monthly_price}} is charged to Client's payment "
                    "method on file on the first of each month. Failed payments will be retried "
                    "twice. Membership benefits are suspended if payment is not received within "
                    "fifteen (15) days."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. After "
                    "the initial term, membership renews month-to-month. Either party may cancel "
                    "with thirty (30) days' notice. No refunds for partial months. Outstanding "
                    "credits may be used during the notice period."
                ),
            },
            {
                "title": "Health & Safety",
                "content": (
                    "Client agrees to disclose all relevant health conditions, allergies, and "
                    "medications that may affect services. {{business_name}} reserves the right to "
                    "decline services if a client presents with contagious conditions or if "
                    "proceeding would pose a health risk. {{business_name}} maintains all required "
                    "health and safety certifications and sanitization protocols."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # EDUCATION & TRAINING
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Tutoring/Coaching Services Agreement",
        "plan_name": "Tutoring/Coaching Services",
        "monthly_price": 600.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 6,
            "auto_renew": True,
            "cancellation_notice_days": 14,
            "includes": [
                "8 tutoring/coaching sessions per month",
                "Customized learning plan",
                "Progress assessments",
                "Session notes and resources",
                "Email support between sessions",
                "Quarterly progress report",
            ],
        },
        "sections": [
            _parties_section("Tutoring/Coaching Services Agreement"),
            {
                "title": "Scope of Services",
                "content": (
                    "{{business_name}} shall provide tutoring and/or coaching services to "
                    "{{client_name}} including: eight (8) sessions per month (60 minutes each, "
                    "conducted in person or via video call), customized learning plan based on "
                    "initial assessment, progress evaluations, session notes and supplemental "
                    "materials, email support between sessions, and quarterly progress reports."
                ),
            },
            {
                "title": "Scheduling & Cancellation",
                "content": (
                    "Sessions are scheduled on a recurring weekly basis at mutually agreed times. "
                    "Client may reschedule with at least twenty-four (24) hours' notice. Sessions "
                    "cancelled with less than 24 hours' notice are forfeited. No-shows without "
                    "notice are forfeited. Unused sessions do not roll over. {{business_name}} "
                    "shall provide at least 48 hours' notice for any instructor-initiated "
                    "cancellations and offer a makeup session."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly fee of {{monthly_price}} is billed on the first of each month, "
                    "net-15. Additional sessions beyond the monthly allocation are billed at "
                    "$85/session."
                ),
            },
            {
                "title": "No Guarantee of Results",
                "content": (
                    "{{business_name}} commits to providing quality instruction and support but "
                    "cannot guarantee specific academic outcomes, test scores, or learning "
                    "milestones. Results depend on Client's engagement, effort, practice, and other "
                    "factors outside {{business_name}}'s control. {{business_name}} shall provide "
                    "honest assessments of progress and adjust the learning plan as needed."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months ending "
                    "{{end_date}}. It renews month-to-month. Either party may terminate with "
                    "fourteen (14) days' notice. No refunds for partial months."
                ),
            },
            _confidentiality_section(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Online Course License Agreement",
        "plan_name": "Online Course License",
        "monthly_price": 49.00,
        "setup_fee": 0,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 14,
            "includes": [
                "Full course library access",
                "Video lessons and materials",
                "Downloadable resources",
                "Community forum access",
                "Certificate of completion",
                "Lifetime updates during subscription",
            ],
        },
        "sections": [
            _parties_section("Online Course License Agreement"),
            {
                "title": "License Grant",
                "content": (
                    "{{business_name}} grants {{client_name}} a non-exclusive, non-transferable, "
                    "revocable license to access the online course content (\"Course Materials\") "
                    "during the term of this Agreement for personal or internal professional "
                    "development purposes. Client shall not share login credentials, record or "
                    "redistribute Course Materials, or use them for competing commercial purposes."
                ),
            },
            {
                "title": "Course Content & Updates",
                "content": (
                    "{{business_name}} shall provide access to the course library at "
                    "{{business_website}}, including video lessons, downloadable resources, quizzes, "
                    "and community forum. {{business_name}} may update, modify, or retire course "
                    "content at any time. Subscribers receive all updates during their active "
                    "subscription. Certificate of completion is issued upon finishing required modules."
                ),
            },
            {
                "title": "Payment Terms",
                "content": (
                    "Monthly subscription fee of {{monthly_price}} is charged to Client's payment "
                    "method on file. Annual prepayment is available at a discounted rate. All fees "
                    "are non-refundable except as provided in the refund policy below."
                ),
            },
            {
                "title": "Refund Policy",
                "content": (
                    "New subscribers may request a full refund within fourteen (14) days of initial "
                    "purchase if less than 20% of course content has been accessed. Refund requests "
                    "after 14 days or after accessing more than 20% of content are not eligible. "
                    "Refund requests should be directed to {{business_email}}."
                ),
            },
            {
                "title": "Term & Termination",
                "content": (
                    "This Agreement commences on {{start_date}} for {{term_months}} months. It "
                    "renews automatically. Client may cancel at any time with fourteen (14) days' "
                    "notice; access continues through the end of the current billing period. "
                    "{{business_name}} may terminate for violation of the license terms. Upon "
                    "termination, access to Course Materials is revoked but certificates of "
                    "completion already earned are retained."
                ),
            },
            _ip_section_license(),
            _liability_section(),
            _general_provisions_section(),
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # RENTAL & PROPERTY
    # ──────────────────────────────────────────────────────────────
    {
        "name": "Equipment Rental Agreement",
        "plan_name": "Equipment Rental",
        "monthly_price": 0,
        "setup_fee": 1500.00,
        "default_terms": {
            "term_months": 1,
            "auto_renew": False,
            "cancellation_notice_days": 7,
            "includes": [
                "Equipment as listed in inventory",
                "Delivery and pickup",
                "Operating instructions",
                "Basic maintenance during rental",
                "Damage waiver option",
                "24/7 emergency support line",
            ],
        },
        "sections": [
            _parties_section("Equipment Rental Agreement"),
            {
                "title": "Equipment Description",
                "content": (
                    "{{business_name}} (\"Lessor\") agrees to rent the following equipment to "
                    "{{client_name}} ({{client_company}}) (\"Lessee\"): [detailed equipment list "
                    "with serial numbers, condition, and estimated value — see Exhibit A]. "
                    "Lessee acknowledges receiving the equipment in good working condition and "
                    "agrees to return it in the same condition, normal wear excepted."
                ),
            },
            {
                "title": "Rental Period & Rates",
                "content": (
                    "Rental period: {{start_date}} to {{end_date}} ({{term_months}} months). "
                    "Total rental fee: {{setup_fee}}. Extensions must be requested in writing at "
                    "least three (3) days before the return date and are subject to availability "
                    "and prorated charges. Equipment returned late without extension is charged at "
                    "150% of the daily rental rate."
                ),
            },
            {
                "title": "Security Deposit",
                "content": (
                    "Lessee shall pay a security deposit of $[amount] upon execution, refundable "
                    "within fourteen (14) days of equipment return, less deductions for damage, "
                    "missing items, excessive cleaning, or late return charges. If damage exceeds "
                    "the deposit, Lessee is responsible for the balance."
                ),
            },
            {
                "title": "Use & Care",
                "content": (
                    "Lessee shall: (a) use equipment only for its intended purpose; (b) not modify, "
                    "disassemble, or repair equipment without written consent; (c) operate equipment "
                    "only with trained personnel; (d) keep equipment secure and protected from "
                    "weather; (e) not sublease equipment to third parties. Lessee is responsible "
                    "for all fuel, consumables, and operator costs."
                ),
            },
            {
                "title": "Damage, Loss & Insurance",
                "content": (
                    "Lessee is responsible for all damage to or loss/theft of equipment from "
                    "delivery until return, except for normal wear. Lessee shall maintain adequate "
                    "insurance covering the full replacement value of the equipment and provide "
                    "proof upon request. An optional damage waiver is available for [percentage]% "
                    "of the rental fee, which limits Lessee's liability to $[deductible] per incident."
                ),
            },
            {
                "title": "Delivery & Return",
                "content": (
                    "Delivery and pickup are included within [radius] miles. Additional distance "
                    "is charged at $[rate]/mile. Equipment must be returned clean, fueled (if "
                    "applicable), and in operable condition. Lessee shall notify {{business_name}} "
                    "immediately of any equipment malfunction. {{business_name}} shall respond to "
                    "equipment issues within [timeframe]."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
    {
        "name": "Office Space Lease Agreement",
        "plan_name": "Office Space Lease",
        "monthly_price": 2500.00,
        "setup_fee": 5000.00,
        "default_terms": {
            "term_months": 12,
            "auto_renew": True,
            "cancellation_notice_days": 90,
            "includes": [
                "Office space as described",
                "Common area access",
                "Utilities (electric, water, HVAC)",
                "Internet connectivity",
                "Janitorial services",
                "Building security and access",
                "Parking allocation",
            ],
        },
        "sections": [
            {
                "title": "Parties",
                "content": (
                    "This Office Space Lease Agreement (\"Lease\") is entered into as of "
                    "{{start_date}} by and between {{business_name}}, with its principal address "
                    "at {{business_address}} (\"Landlord\"), and {{client_name}} ({{client_company}}), "
                    "located at {{client_address}} (\"Tenant\"). Landlord may be reached at "
                    "{{business_email}} or {{business_phone}}."
                ),
            },
            {
                "title": "Premises",
                "content": (
                    "Landlord leases to Tenant the following premises: [suite/unit number, floor, "
                    "building address, approximate square footage] (\"Premises\"). The Premises "
                    "includes access to common areas: lobbies, restrooms, hallways, parking areas, "
                    "and shared conference rooms (subject to reservation policies)."
                ),
            },
            {
                "title": "Rent & Deposits",
                "content": (
                    "Monthly rent: {{monthly_price}}, due on the first of each month. Security "
                    "deposit: {{setup_fee}} (equal to [number] months' rent), due upon execution, "
                    "refundable within thirty (30) days of lease termination less deductions for "
                    "unpaid rent, damages beyond normal wear, or cleaning costs. Rent increases "
                    "upon renewal shall not exceed [percentage]% annually unless mutually agreed."
                ),
            },
            {
                "title": "Late Payment & Default",
                "content": (
                    "Rent paid after the fifth (5th) of the month incurs a late fee of 5% of "
                    "monthly rent. If rent remains unpaid for fifteen (15) days, Landlord shall "
                    "provide written notice of default. If Tenant fails to cure within ten (10) "
                    "days of notice, Landlord may pursue remedies including lease termination and "
                    "eviction in accordance with applicable law."
                ),
            },
            {
                "title": "Permitted Use & Restrictions",
                "content": (
                    "Tenant shall use the Premises solely for general office purposes consistent "
                    "with the building's commercial designation. Tenant shall not: (a) use the "
                    "Premises for illegal activities; (b) create excessive noise; (c) store "
                    "hazardous materials; (d) make structural alterations without written consent; "
                    "(e) sublease without Landlord's prior written consent."
                ),
            },
            {
                "title": "Maintenance & Repairs",
                "content": (
                    "Landlord shall maintain: building structure, roof, exterior, HVAC systems, "
                    "plumbing, electrical systems, elevators, common areas, and janitorial services. "
                    "Tenant shall maintain the interior of the Premises in good condition and "
                    "promptly report maintenance issues. Tenant-caused damage is Tenant's financial "
                    "responsibility."
                ),
            },
            {
                "title": "Lease Term & Renewal",
                "content": (
                    "This Lease commences on {{start_date}} and expires on {{end_date}} "
                    "({{term_months}} months). Unless either party provides written notice of "
                    "non-renewal at least ninety (90) days before expiration, the Lease "
                    "automatically renews for successive twelve (12) month terms."
                ),
            },
            {
                "title": "Termination & Surrender",
                "content": (
                    "Either party may terminate with ninety (90) days' written notice at the end "
                    "of any term. Early termination by Tenant requires payment of a termination "
                    "fee equal to three (3) months' rent. Upon expiration or termination, Tenant "
                    "shall surrender the Premises in broom-clean condition, remove all personal "
                    "property, and return all keys and access devices."
                ),
            },
            _liability_section(),
            _general_provisions_section(),
        ],
    },
]