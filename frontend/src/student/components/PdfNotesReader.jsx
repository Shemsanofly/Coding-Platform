import { useCallback, useEffect, useRef, useState } from "react";
import { viewLessonNotes } from "@/api/studentLearning";
import EmptyState from "@/student/components/EmptyState";
import { extractApiError } from "@/shared/utils/extractApiError";

function isPdfBlob(blob) {
  return (
    blob instanceof Blob &&
    (blob.type === "application/pdf" || blob.type === "application/octet-stream")
  );
}

export default function PdfNotesReader({ lessonId, lessonTitle, onOpened, onScrollDepth }) {
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [objectUrl, setObjectUrl] = useState("");
  const containerRef = useRef(null);
  const openedRef = useRef(false);
  const objectUrlRef = useRef("");

  const revokeUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = "";
    }
  }, []);

  const loadPdf = useCallback(async () => {
    if (!Number.isFinite(lessonId)) {
      setStatus("error");
      setErrorMessage("Invalid lesson.");
      return;
    }

    setStatus("loading");
    setErrorMessage("");
    revokeUrl();
    setObjectUrl("");

    try {
      const response = await viewLessonNotes(lessonId);
      const blob = response.data;
      if (!isPdfBlob(blob)) {
        setStatus("error");
        setErrorMessage("The notes file is not a valid PDF.");
        return;
      }

      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;
      setObjectUrl(url);
      setStatus("ready");

      if (!openedRef.current) {
        openedRef.current = true;
        onOpened?.();
      }
    } catch (error) {
      setStatus("error");
      setErrorMessage(extractApiError(error, "Could not load PDF notes. Please try again."));
    }
  }, [lessonId, onOpened, revokeUrl]);

  useEffect(() => {
    openedRef.current = false;
    loadPdf();
    return () => revokeUrl();
  }, [lessonId, loadPdf, revokeUrl]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || status !== "ready") {
      return undefined;
    }

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = node;
      if (scrollHeight <= clientHeight) {
        onScrollDepth?.(100);
        return;
      }
      const pct = Math.round((scrollTop / (scrollHeight - clientHeight)) * 100);
      onScrollDepth?.(Math.max(0, Math.min(100, pct)));
    };

    node.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => node.removeEventListener("scroll", handleScroll);
  }, [status, onScrollDepth]);

  if (status === "loading") {
    return (
      <div className="space-y-3 rounded-xl border border-line bg-white p-6 dark:border-line/20 dark:bg-black/20">
        <div className="h-4 w-40 animate-pulse rounded bg-reef/50 dark:bg-ocean-950/50" />
        <div className="h-[min(70vh,520px)] min-h-[280px] animate-pulse rounded-lg bg-sand dark:bg-ocean-950/40 sm:min-h-[360px]" />
        <p className="text-sm text-muted dark:text-muted/90">Loading PDF notes…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <EmptyState
        title="PDF notes unavailable"
        message={errorMessage}
        action={
          <button
            type="button"
            onClick={loadPdf}
            className="inline-flex min-h-9 items-center rounded-xl bg-ocean-600 px-4 py-2 text-sm font-semibold text-white hover:bg-reef/400"
          >
            Try again
          </button>
        }
      />
    );
  }

  return (
    <div
      ref={containerRef}
      className="max-h-[min(70vh,640px)] min-h-[280px] overflow-auto rounded-xl border border-line bg-white dark:border-line/20 dark:bg-black/20 sm:min-h-[360px]"
    >
      <object
        data={objectUrl}
        type="application/pdf"
        aria-label={`${lessonTitle || "Lesson"} study notes`}
        className="h-[min(68vh,600px)] min-h-[260px] w-full sm:min-h-[340px]"
      >
        <iframe
          title={`${lessonTitle || "Lesson"} study notes`}
          src={objectUrl}
          className="h-[min(68vh,600px)] min-h-[260px] w-full sm:min-h-[340px]"
        />
      </object>
    </div>
  );
}
