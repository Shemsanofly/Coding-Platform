export const LESSON_SOURCE_OPTIONS = [
  {
    value: "youtube",
    label: "YouTube",
    urlLabel: "YouTube URL",
    placeholder: "https://www.youtube.com/watch?v=...",
    requiresUrl: true,
    help: "AI quiz generation runs automatically for YouTube lessons.",
  },
  {
    value: "pdf",
    label: "PDF",
    urlLabel: "PDF URL",
    placeholder: "https://example.com/lesson-notes.pdf",
    requiresUrl: true,
    help: "Link to a PDF document students can read or download.",
  },
  {
    value: "webpage",
    label: "Web page",
    urlLabel: "Page URL",
    placeholder: "https://developer.mozilla.org/...",
    requiresUrl: true,
    help: "Link to an article, documentation page, or tutorial.",
  },
  {
    value: "link",
    label: "External link",
    urlLabel: "Resource URL",
    placeholder: "https://...",
    requiresUrl: true,
    help: "Any external learning resource (docs, blog, repo, etc.).",
  },
  {
    value: "internal",
    label: "Platform content",
    urlLabel: "Reference URL (optional)",
    placeholder: "https://... (optional)",
    requiresUrl: false,
    help: "Write lesson content directly on the platform. URL is optional.",
  },
];

export function getLessonSourceOption(value) {
  return LESSON_SOURCE_OPTIONS.find((option) => option.value === value) ?? LESSON_SOURCE_OPTIONS[0];
}

export function formatSourceTypeLabel(value) {
  return getLessonSourceOption(value).label;
}
