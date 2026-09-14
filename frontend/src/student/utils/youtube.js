const SCRIPT_SRC = "https://www.youtube.com/iframe_api";

/** @type {(() => void)[]} */
const pendingReady = [];

function flushYouTubeReady() {
  while (pendingReady.length) {
    const cb = pendingReady.shift();
    try {
      cb();
    } catch {
      /* ignore */
    }
  }
}

if (typeof window !== "undefined") {
  const previous = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = () => {
    if (typeof previous === "function") {
      previous();
    }
    flushYouTubeReady();
  };
}

function injectIframeApiScript() {
  if (typeof document === "undefined") {
    return;
  }
  if (document.querySelector(`script[src="${SCRIPT_SRC}"]`)) {
    return;
  }
  const tag = document.createElement("script");
  tag.src = SCRIPT_SRC;
  tag.async = true;
  document.head.appendChild(tag);
}

export function ensureYouTubeIframeApi() {
  return new Promise((resolve) => {
    if (typeof window === "undefined") {
      resolve();
      return;
    }
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }
    pendingReady.push(resolve);
    injectIframeApiScript();
  });
}

export function extractYoutubeVideoId(embedUrl) {
  const m = String(embedUrl || "").match(/\/embed\/([^?&/]+)/);
  return m ? m[1] : "";
}
