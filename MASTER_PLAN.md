# SMART DIGITAL SEVA — MASTER BUSINESS & PRODUCT PLAN

**Project:** Smart Digital Seva  
**Base:** Bhawanipatna, Odisha  
**Business owner/operator:** Hemanta Sahu  
**Website:** https://smartdigitalseva05-hash.github.io/Smartdigital-seva/  
**Customer phone/WhatsApp:** +91 8458023492  
**WhatsApp Channel:** https://whatsapp.com/channel/0029Vb9JXTj42DchUNDpRx0E  
**Primary language:** Odia, with simple English labels where useful

## 1. Vision

Build Smart Digital Seva into a trusted, customer-first digital assistance platform for people who need help understanding and completing online service processes. Start lean in Bhawanipatna, prove demand and service quality, then expand to nearby areas through repeat customers, referrals, and carefully selected partner operators.

Earn trust through clear pricing, honest timelines, privacy, accurate guidance, and reliable follow-up—not through fear, false guarantees, or misleading government affiliation.

## 2. Customer problems we solve

1. Customers do not know which service or official portal they need.
2. They are unsure which documents are required.
3. They struggle with online forms, uploads, language, or mobile workflows.
4. They cannot easily understand application status or next steps.
5. They waste time travelling before confirming requirements.
6. They miss relevant announcements, deadlines, or service changes.
7. They do not know the service fee, official fee, or expected timeline in advance.

For every service page, publish: who it may be for, eligibility caveat, document checklist, process overview, official portal link, service fee (only after confirmed), government fee (separately identified), expected assistance timeline, common mistakes, and a clear enquiry/request action.

## 3. Product modules

### A. Public website
- Premium, responsive Odia-first design; fast on low-end Android phones and slow networks.
- Home page, service directory, search and categories.
- Individual service detail pages with checklists and FAQs.
- About, contact, transparent pricing, privacy policy, terms, refund/cancellation policy, grievance/contact route.
- WhatsApp Channel updates and click-to-call/WhatsApp.
- Customer testimonials only with genuine consent; no fabricated reviews or counters.
- Accessibility: readable type, contrast, keyboard support, clear error messages.

### B. Customer request workflow
- Request form: customer name, mobile, selected service, preferred contact method, short description.
- Do not ask for Aadhaar number, OTP, passwords, bank PIN, or unnecessary sensitive documents in the first enquiry.
- Generate a unique request/reference number.
- Show acknowledgement and next steps.
- Status stages: Received → Need information → Quotation shared → Customer approved → In progress → Ready/Submitted → Completed / Closed.
- Customer can check status using reference number plus a safe verification method.
- Customer receives updates; start with manual WhatsApp updates, then add approved messaging integration if eligible and cost-effective.
- Customer can request correction or raise a complaint.

### C. Admin dashboard
- Secure owner login; no public admin link or shared password.
- View/search/filter requests by status, service, date.
- Update status, add internal notes, record customer-visible updates.
- Maintain service catalogue, document checklists, fees, availability, FAQs and announcements.
- Record payments/receipts only when actually received; export operational reports.
- Role-based access before adding staff; audit log for important changes.
- Backups and recovery procedure.

### D. Marketing and growth
- WhatsApp Channel: useful, concise, regular updates; avoid spam and unverified claims.
- Google Business Profile: accurate address/service area, hours, phone, real photos, review responses.
- Local SEO: Odia and English service names, Bhawanipatna and relevant service-area pages.
- Shareable service explainers, document checklists, short educational videos, QR code for the website/channel.
- Referral programme only with clear terms and sustainable economics.
- Monthly campaign calendar and simple tracking: enquiries, qualified enquiries, completed jobs, repeat customers, referrals, revenue and expenses.
- No purchased contact lists, unsolicited bulk messages, fake reviews, false urgency, or guaranteed approval claims.

### E. Future expansion
- Add nearby service areas only after reliable operations.
- Partner/agent portal with written service standards and permissions.
- More languages if customers need them.
- Customer account only when there is a clear benefit and adequate security.
- PWA/app wrapper only after the mobile website and workflows are stable.
- Integrations and online payments only through legitimate providers and after policy/compliance review.

## 4. Business model and income

Potential revenue streams:
1. Clearly disclosed assistance/service fee for work actually provided.
2. Form-filling/document preparation support where lawful and within authorised scope.
3. Printing/scanning or other locally available add-on services, if offered transparently.
4. Business-to-business digital support for local shops, after the core service workflow is stable.
5. Partner network revenue only with written agreements, transparent customer pricing, and quality controls.

Never present a government fee as the business's own fee. Confirm current official fees and eligibility from the relevant official source before publishing. Do not promise certificate approval, guaranteed outcomes, or fixed government processing times.

Track unit economics monthly:
- Leads/enquiries
- Qualified enquiries
- Completed paid services
- Average service revenue
- Direct costs and refunds
- Gross contribution per service
- Repeat/referral share
- Customer complaints and resolution time

No income is guaranteed. Validate demand and actual margins before spending on ads, paid tools, or staff.

## 5. Trust, safety and compliance

- Clearly state that Smart Digital Seva is an independent assistance service, not a government department or official portal.
- Link to official portals where appropriate; customer submits/approves their own application and data wherever required.
- Collect the minimum data needed; explain purpose and retention; restrict access; delete data when no longer required, subject to legal recordkeeping needs.
- Never request or store OTPs, passwords, UPI PINs, card PINs, or bank login credentials.
- Do not impersonate government services, use government emblems misleadingly, or claim authorisation/accreditation unless documented.
- Publish service availability, fees, refund rules, limitations, and complaint contact.
- Obtain consent before sending promotional messages or publishing testimonials/photos.
- Follow applicable Indian privacy, consumer, advertising, tax, payment and messaging rules; seek qualified advice where required.

## 6. Technical architecture — staged, low-cost first

### Phase 1: Stable public website
- Keep the existing index.html as the public entry point.
- Keep creator_studio_pro.html untouched.
- Put new pages/assets in separate files and test before linking them.
- Use semantic HTML, responsive CSS, accessible forms, and lightweight JavaScript.
- Add a clear 404 page and basic metadata.

### Phase 2: Backend and secure data
- Evaluate Supabase for database, authentication, row-level security, and server-side functions.
- Proposed entities: services, service_documents, enquiries, enquiry_events, customers (only if necessary), announcements, payments (minimal ledger), staff_roles, audit_events.
- Enforce row-level security; customers may only access their own verified request; staff access is role-limited.
- Never place service-role secrets or private API keys in browser code or public GitHub files.
- Use server-side validation, rate limits, spam protection, backups and retention rules.

### Phase 3: Notifications and payments
- Start with manual WhatsApp updates and click-to-chat to avoid unnecessary costs.
- Consider official WhatsApp Business Platform integration only after checking eligibility, template rules, consent, and pricing.
- Add payment gateway only when a real business need exists; verify payment server-side and issue clear receipts/refund records. Never store card data.

### Phase 4: Scale
- Add reporting, staff roles, partner operations, service-area pages, and integrations only after the previous phase is stable and measured.

## 7. Delivery roadmap and acceptance checks

### Milestone 0 — Discovery and audit
- Confirm service list, actual delivery capability, service fees, official fees, operating hours, contact channels, and policies.
- Test existing site on Android, slow connection, and common screen sizes.
- Check all links, images, forms, spelling, and page loading.
**Done when:** all public claims are verified and all visible links work.

### Milestone 1 — Professional website foundation
- Premium Odia home page, service directory, individual service information, FAQ, contact, trust and policy pages.
- Search/filter, WhatsApp Channel, click-to-call and click-to-chat.
**Done when:** mobile usability, accessibility basics, links and content pass a manual test checklist.

### Milestone 2 — Enquiry and reference workflow
- Secure request submission, reference number, customer acknowledgement and admin request list.
**Done when:** test requests save correctly, validation works, duplicate/spam handling exists, and private records are not public.

### Milestone 3 — Admin and customer status
- Admin login, status changes, event history, customer status lookup and customer-visible updates.
**Done when:** unauthorised users cannot see or change another customer's request.

### Milestone 4 — Marketing system
- Google Business Profile setup, local SEO pages, content calendar, QR/share links, consent-based reviews and analytics.
**Done when:** enquiry source and conversion can be measured without collecting unnecessary personal data.

### Milestone 5 — Optimise and expand
- Review metrics, customer feedback, service profitability, error rate and turnaround time.
**Done when:** repeatable operating process exists before hiring or adding partner locations.

## 8. Weekly operating rhythm

- Daily: check new enquiries, reply, confirm fees/documents, update request statuses.
- Weekly: publish 1–2 useful channel updates, review pending requests, resolve complaints, check broken links.
- Monthly: review revenue/costs, top services, conversion, customer feedback, privacy/security, and next month's content plan.

## 9. Quality assurance checklist

Before every release:
- Test Android mobile, desktop and small screen.
- Test all navigation, service enquiry links, phone, email and channel links.
- Test search/filter and form validation.
- Check Odia text rendering and spelling.
- Check no private keys, customer records or credentials are committed to GitHub.
- Check privacy notice, fee clarity, government-independence notice and consent.
- Test loading, broken images, keyboard focus and error states.
- Keep a backup/known-good commit and a short release note.
- Do not call a feature complete until its real end-to-end workflow is tested.

## 10. Immediate next actions

1. Confirm the actual services that can currently be delivered.
2. Create a verified service-and-fee catalogue; keep unknown fees unpublished until checked.
3. Audit the live website and repository before changing production pages.
4. Design the page map and customer journey.
5. Build and test one milestone at a time; preserve existing index.html until a reviewed replacement is ready and keep creator_studio_pro.html untouched.

**Project principle:** Trust first, solve a real customer problem, measure the result, then scale. A beautiful website attracts attention; reliable service, transparent pricing and follow-through create a sustainable business.


---

## 11. Development progress — 1 November 2026

**Owner decision confirmed:** business model = own services + future partner/platform model; budget = ₹0; initial reach = Bhawanipatna/local area.

### Completed
- [x] Audited the current repository file list and inspected the existing Odia homepage.
- [x] Preserved `creator_studio_pro.html`; it was not modified.
- [x] Created `customer_request.html`, a mobile-friendly preliminary enquiry page.
- [x] The enquiry page opens WhatsApp with a prefilled message for the customer to review and send. It does not save enquiries to a database.
- [x] Added links from the homepage navigation and hero area to the enquiry page.
- [x] Kept the homepage and enquiry page free of file uploads and requests for OTPs, passwords, UPI PINs or bank credentials.

### Current limitations
- The enquiry flow is WhatsApp handoff only; there is no automatic reference number, database, admin dashboard or customer status tracking yet.
- Service availability, document requirements, government fees and Smart Digital Seva assistance fees must be verified before being advertised as confirmed.
- GitHub Pages deployment and live mobile behaviour still require a real-device check after publishing.

### Next actions
1. Test the homepage and `customer_request.html` on an Android phone, including every navigation and WhatsApp link.
2. Confirm exactly which services the operator can currently provide and under what authority/partner arrangement.
3. Build a verified service catalogue with official source links, document checklists and separately stated fees; leave unverified prices unpublished.
4. Only after that, design a secure enquiry record/reference workflow. Never store customer data in public HTML or a public repository.
5. Keep `creator_studio_pro.html` untouched and use backups/reviewed commits for future homepage changes.


## 12. Pricing update — 1 November 2026

The owner-approved Smart Digital Seva assistance fees currently displayed in the homepage service catalogue are:

- ROR / land record copy: ₹19
- Income certificate assistance: ₹99
- Caste certificate assistance: ₹99
- Residence certificate assistance: ₹99
- PAN card assistance: ₹129
- e-Shram assistance: ₹119. The e-Shram government registration itself is free; ₹119 is only the Smart Digital Seva assistance fee.
- Character certificate assistance: ₹149
- e-Pauti: area-wise price; confirm and quote before starting.
- Online form filling: ₹99
- Other services: service-wise quotation before starting.
- Aadhaar section remains information-only and directs customers to authorised centres.

All displayed prices are Smart Digital Seva assistance fees, not government fees. Government, portal or provider charges, if any, must be separately identified and confirmed before collecting payment. Do not promise approval or a government processing timeline.

## 13. Deployment and release status — 1 November 2026

- Removed the duplicate custom Pages workflow file `.github/workflows/deploy-pages.yml`; GitHub-managed Pages deployment is the only deployment workflow.
- The one-time stale-deployment inspector found the older Pages deployment was already marked `succeed` by the Pages API.
- GitHub Actions run `41291628141` completed successfully: build, deploy and report-build-status jobs all succeeded.
- Subsequent commits adding the customer information pages triggered fresh Pages runs; the latest run must be checked before declaring the newest files live.
- Source contains all 11 owner-approved price-line elements. Live visual verification on Android is still required.
- `creator_studio_pro.html` remains protected and must not be modified during this work.

## 14. Remaining work

1. Clear the stuck GitHub Pages deployment and rerun the managed Pages deployment.
2. Verify the live homepage displays all approved service fees on Android; check desktop and narrow-screen layouts too.
3. Test the homepage navigation, customer enquiry page and WhatsApp handoff end-to-end.
4. Confirm actual service availability and the operator's authority/partner arrangements before advertising each service as deliverable.
5. Build service detail pages with verified official links, document checklists and FAQs.
6. Later, plan a secure backend for enquiry records, reference numbers and admin status tracking. Do not put customer records or private keys in public HTML or GitHub.
7. Preserve `creator_studio_pro.html`; use separate files for future tools and test before linking them.



## 15. Additional public website pages — 1 November 2026

- Added `service_guide.html` with the 11 listed services, preliminary document checklists and official portal links for Odisha eDistrict, Bhulekh, e-Pauti, e-Shram, Income Tax/PAN, UIDAI and Odisha Police.
- Added `faq.html` explaining independent-service status, assistance fees vs government charges, e-Shram's free government registration, WhatsApp-only enquiry limitations, privacy and no approval guarantee.
- Added `policies.html` covering enquiry data handling, sensitive-data warnings, fees, cancellations/refunds, third-party portals and complaints contact.
- Linked the guide, FAQ and policies from the homepage and enquiry page.
- Checklists are preliminary, not a guarantee of exact requirements. Official portal/authority instructions prevail.
- The enquiry form remains WhatsApp handoff only: it does not persist enquiries, generate secure reference numbers or provide status tracking.
- No dedicated Smart Digital Seva Supabase project was identified. Existing projects belong to other named workstreams; do not modify them without the owner's explicit project selection.
- Next technical milestone: choose/create a dedicated backend project at confirmed $0 cost, configure authentication, RLS, enquiry storage, reference numbers and admin/customer status workflows. Do not claim backend functionality until end-to-end tests pass.

## 16. SEO and navigation additions — 1 November 2026

- Added an Odia `404.html` fallback page.
- Added `robots.txt` and `sitemap.xml` for the public homepage, enquiry page, service guide, FAQ and policies.
- Added canonical URL and Open Graph sharing metadata to `index.html`.
- These are source-level changes; search engine indexing and social preview appearance need external verification after deployment.
