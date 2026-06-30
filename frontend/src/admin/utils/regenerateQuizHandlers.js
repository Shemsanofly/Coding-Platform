import toast from "react-hot-toast";

export function invalidateQuizPipelineQueries(queryClient, courseId, lessonId) {
  queryClient.invalidateQueries({ queryKey: ["admin-lesson-processing", courseId, lessonId] });
  queryClient.invalidateQueries({ queryKey: ["admin-lessons", courseId] });
  queryClient.invalidateQueries({ queryKey: ["admin-quiz-preview", courseId, lessonId] });
  queryClient.invalidateQueries({ queryKey: ["admin-dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["admin-courses"] });
}

/** @deprecated use invalidateQuizPipelineQueries */
export function invalidateRegenerateQueries(queryClient, courseId, lessonId) {
  invalidateQuizPipelineQueries(queryClient, courseId, lessonId);
}

export function friendlyGenerationError(data) {
  const raw = data?.error || data?.message || "";
  const lower = String(raw).toLowerCase();
  if (lower.includes("429") || lower.includes("quota") || lower.includes("rate limit")) {
    return "Gemini rate limit reached. Please wait and try again.";
  }
  if (lower.includes("api key") || (lower.includes("invalid") && lower.includes("key"))) {
    return "Gemini API key is invalid. Check backend/.env and restart Django.";
  }
  if (lower.includes("transcript") || lower.includes("caption")) {
    return "Transcript unavailable for this video. Try another video with captions.";
  }
  return raw || "AI quiz generation failed.";
}

export function handleGenerateResponse(data, { toastIdPrefix = "gen-quiz" } = {}) {
  if (data?.success) {
    toast.success(data.message || "AI quiz generated successfully.", { id: `${toastIdPrefix}-ok` });
    return { ok: true };
  }
  toast.error(friendlyGenerationError(data), { id: `${toastIdPrefix}-fail` });
  return { ok: false };
}

export function handleRegenerateResponse(data, { isManualMode, toastIdPrefix = "regen-quiz" } = {}) {
  if (isManualMode) {
    if (data?.success) {
      toast.success(data.message || "AI quiz regenerated successfully.", { id: `${toastIdPrefix}-ok` });
      return { ok: true, queued: false };
    }
    toast.error(friendlyGenerationError(data), { id: `${toastIdPrefix}-fail` });
    return { ok: false, queued: false };
  }

  if (data?.queued === false) {
    toast.error(data.message || "AI generation could not be queued.", { id: `${toastIdPrefix}-queue` });
    return { ok: false, queued: false };
  }

  toast.success(data?.message || "AI quiz generation has started.", { id: `${toastIdPrefix}-ok` });
  return { ok: true, queued: true };
}
