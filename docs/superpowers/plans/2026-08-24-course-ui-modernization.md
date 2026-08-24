# Course UI Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the course pages so student and admin course workflows are clearer, functional, responsive, and not duplicated.

**Architecture:** Keep the existing React/Vite/Tailwind stack and API clients. Add small shared course UI helpers, then update the student catalog, student course detail, admin course list, and admin course setup pages to reuse those helpers and keep actions consistent.

**Tech Stack:** React 18, React Query, React Router, Tailwind CSS, existing Flask API paths.

---

### Task 1: Shared Course UI Helpers

**Files:**
- Create: `frontend/src/shared/components/course/CourseBadges.jsx`

- [ ] Add `formatCourseLevel`, `CourseLevelBadge`, `CourseStatusPill`, and `CourseMetric` helpers for repeated course metadata display.
- [ ] Use compact badge styles with restrained colors that work in light and dark mode.

### Task 2: Student Catalog

**Files:**
- Modify: `frontend/src/student/pages/Catalog.jsx`
- Modify: `frontend/src/student/components/CourseCard.jsx`

- [ ] Add search and level filtering without changing API behavior.
- [ ] Replace stacked list cards with a responsive course grid.
- [ ] Make cards show enrollment state, status, level, lesson count, and one primary action.
- [ ] Remove duplicate local level formatting/colors.

### Task 3: Student Course Detail

**Files:**
- Modify: `frontend/src/student/pages/CourseDetail.jsx`

- [ ] Replace nested hero cards with a single course summary band.
- [ ] Make certificate status compact and secondary.
- [ ] Present lessons as stable list rows with status, source, duration, and actions.
- [ ] Fix mojibake separators and symbols.

### Task 4: Admin Course Pages

**Files:**
- Modify: `frontend/src/admin/pages/CourseList.jsx`
- Modify: `frontend/src/admin/pages/CourseSetup.jsx`

- [ ] Add search and status filters to course list.
- [ ] Consolidate action button styling.
- [ ] Make setup page form and lesson list denser and more modern.
- [ ] Remove duplicate status/metadata formatting where shared helpers fit.

### Task 5: Verification

**Commands:**
- `npm run build`

- [ ] Build succeeds with no React syntax errors.
- [ ] Start dev server on an available port and provide URL.
