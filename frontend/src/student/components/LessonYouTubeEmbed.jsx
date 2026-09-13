import { useEffect, useRef } from "react";

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

/**
 * Resolves when window.YT.Player is usable (loads iframe API once).
 */
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

/**
 * Renders a YouTube player via IFrame API and reports max watch percentage (0–100).
 */
export default function LessonYouTubeEmbed({ videoId, title, onWatchPercent }) {
  const containerRef = useRef(null);
  const playerRef = useRef(null);
  const maxPctRef = useRef(0);
  const pollRef = useRef(null);
  const callbackRef = useRef(onWatchPercent);

  useEffect(() => {
    callbackRef.current = onWatchPercent;
  }, [onWatchPercent]);

  useEffect(() => {
    maxPctRef.current = 0;
  }, [videoId]);

  useEffect(() => {
    let cancelled = false;

    const setup = async () => {
      if (!videoId || !containerRef.current) {
        return;
      }
      await ensureYouTubeIframeApi();
      if (cancelled || !window.YT || !window.YT.Player || !containerRef.current) {
        return;
      }

      playerRef.current = new window.YT.Player(containerRef.current, {
        videoId,
        width: "100%",
        height: "100%",
        playerVars: {
          enablejsapi: 1,
          origin:
            typeof window !== "undefined" && window.location?.origin
              ? window.location.origin
              : undefined,
        },
        events: {
          onReady: (event) => {
            const player = event.target;
            pollRef.current = window.setInterval(() => {
              try {
                const dur = player.getDuration();
                const cur = player.getCurrentTime();
                if (!dur || dur <= 0 || cur < 0) {
                  return;
                }
                const pct = Math.min(100, Math.round((cur / dur) * 100));
                if (pct > maxPctRef.current) {
                  maxPctRef.current = pct;
                  callbackRef.current(maxPctRef.current);
                }
              } catch {
                /* cross-origin or teardown */
              }
            }, 3000);
          },
        },
      });
    };

    void setup();

    return () => {
      cancelled = true;
      if (pollRef.current) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
      try {
        playerRef.current?.destroy?.();
      } catch {
        /* ignore */
      }
      playerRef.current = null;
    };
  }, [videoId]);

  if (!videoId) {
    return null;
  }

  return (
    <div className="aspect-video min-h-[320px] w-full">
      <div ref={containerRef} className="h-full w-full" title={title} />
    </div>
  );
}
