# Official Certificate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an official LearnCode Certificate of Completion that is generated dynamically for eligible students and downloadable as a secure A4 landscape PDF.

**Architecture:** Extend the existing Django `progress` certificate model/service/API and React certificate pages. Keep eligibility, official data, certificate number, verification code, QR URL, PDF rendering, and authorization in the backend. Use the frontend only for read-only preview, download actions, and public verification display.

**Tech Stack:** Django 5.2, Django REST Framework, ReportLab, React 18, Vite, Tailwind CSS.

---

### Task 1: Backend Tests

**Files:**
- Modify: `backend/progress/tests/test_certificates.py`

- [ ] Add tests for official metadata snapshots, A4 landscape one-page PDF, QR URL text, sanitized filename, valid/revoked/not-found verification responses, long student names and course titles, missing asset fallbacks, and cross-student download denial.

- [ ] Run: `python manage.py test progress.tests.test_certificates -v 2`

- [ ] Expected: the new tests fail because the current PDF is Letter landscape, lacks official metadata fields, uses a simple filename, and does not expose the requested public verification state.

### Task 2: Certificate Model

**Files:**
- Modify: `backend/progress/models.py`
- Create: `backend/progress/migrations/0006_certificate_official_metadata.py`
- Modify: `backend/progress/admin.py`

- [ ] Add snapshot fields: `completion_date`, `platform_name`, `platform_website`, `instructor_name`, `course_duration`, `verification_url`, `ceo_name`, `ceo_title`, and `revoked_at`.

- [ ] Add admin display/search fields for certificate number, student name, course title, status, issue date, and revoked date.

- [ ] Run: `python manage.py test progress.tests.test_certificates -v 2`

- [ ] Expected: model-related failures move forward to service/API/PDF behavior failures.

### Task 3: Certificate Service

**Files:**
- Modify: `backend/progress/services/certificates.py`
- Create: `backend/progress/assets/certificates/ceo-signature.png`
- Create: `backend/progress/assets/certificates/learncode-logo.png`
- Modify: `backend/core/settings.py`
- Modify: `backend/.env.example`

- [ ] Add settings for platform name, platform website, certificate public base URL, logo path, CEO signature path, CEO name, and CEO title.

- [ ] Add placeholder PNG assets for the logo and CEO signature.

- [ ] Replace the ReportLab renderer with A4 landscape drawing: cream background, navy/gold double border, official headings, wrapped formal wording, QR code with quiet zone, official seal, CEO signature section, footer authenticity statement, and fallback logo/signature rendering.

- [ ] Generate certificate numbers in a professional format and verification codes with secure random tokens.

- [ ] Save trusted metadata snapshots from backend records and settings.

- [ ] Add sanitized PDF filenames.

- [ ] Run: `python manage.py test progress.tests.test_certificates -v 2`

- [ ] Expected: service/PDF tests pass or reveal API serialization gaps.

### Task 4: API and Serializers

**Files:**
- Modify: `backend/progress/serializers.py`
- Modify: `backend/progress/views.py`
- Modify: `backend/progress/urls.py`

- [ ] Expose read-only certificate preview fields needed by the frontend.

- [ ] Add `GET /api/certificates/<certificate_id>/` for student/admin preview with the same access control as download.

- [ ] Improve public verification response to distinguish `VALID`, `REVOKED`, and `NOT_FOUND` without leaking database IDs.

- [ ] Use sanitized professional filenames in certificate downloads.

- [ ] Log generation and revocation events.

- [ ] Run: `python manage.py test progress.tests.test_certificates -v 2`

- [ ] Expected: targeted backend tests pass.

### Task 5: Frontend Preview and Verification

**Files:**
- Modify: `frontend/src/api/certificates.js`
- Create: `frontend/src/student/components/CertificatePreview.jsx`
- Create: `frontend/src/student/pages/CertificateDetail.jsx`
- Modify: `frontend/src/student/pages/MyCertificates.jsx`
- Modify: `frontend/src/student/pages/CourseDetail.jsx`
- Modify: `frontend/src/shared/pages/CertificateVerification.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] Add API helper for certificate detail.

- [ ] Build a read-only certificate preview component matching the official PDF structure.

- [ ] Add a protected student certificate detail page with Download PDF and verification status.

- [ ] Link course detail and certificate list to preview.

- [ ] Update public verification page to show valid, revoked, and not-found states with safe data only.

- [ ] Run: `npm run build`

- [ ] Expected: frontend build succeeds.

### Task 6: Final Verification

**Files:**
- Generated media under `backend/media/certificates/...`

- [ ] Run targeted backend tests.

- [ ] Run full backend tests as feasible.

- [ ] Run frontend build.

- [ ] Generate a certificate from development test data.

- [ ] Inspect the PDF page size, page count, QR URL text, CEO signature section, certificate number, verification code, and revoked verification behavior.

- [ ] Report implemented design, created/modified files, migration, environment variables, asset locations, manual testing steps, QR testing steps, and assumptions.
