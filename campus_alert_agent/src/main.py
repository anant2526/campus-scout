"""
Campus Alert Agent — Main Entry Point

DESIGN: This is a single-execution batch job, NOT a daemon.
  1. Start
  2. Load previously seen results
  3. Scrape each source URL
  4. Analyze new content via Gemini
  5. Send notifications for new detections
  6. Save updated seen results
  7. Exit

GitHub Actions calls this script on a cron schedule (every 8 hours).
The script has its own internal timeout protection (50 minutes) as a
safety net before the GitHub Actions 60-minute hard kill.
"""
import os
import sys
import time
import signal
import logging
import traceback

import config
from storage import load_seen_results, save_seen_results, is_new_result, mark_as_seen
from checker import scrape_url, analyze_content
from notifier import send_alert


# ══════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """Configure structured logging to both file and console."""
    os.makedirs("logs", exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — persistent log for GitHub Actions artifact upload
    file_handler = logging.FileHandler(config.LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Console handler — visible in GitHub Actions live log
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# ══════════════════════════════════════════════════════════════════════════
# TIMEOUT PROTECTION
# ══════════════════════════════════════════════════════════════════════════

_seen_results_ref = {}  # Module-level reference for the signal handler


def _timeout_handler(signum, frame):
    """
    Called when the internal timeout fires.
    Saves partial results and exits gracefully.
    """
    logging.warning(
        f"⏰ INTERNAL TIMEOUT reached ({config.INTERNAL_TIMEOUT_SECONDS}s). "
        "Saving partial results and exiting gracefully."
    )
    save_seen_results(_seen_results_ref)
    logging.info("Partial results saved. Exiting.")
    sys.exit(0)


# ══════════════════════════════════════════════════════════════════════════
# CORE AGENT LOGIC
# ══════════════════════════════════════════════════════════════════════════

def run_agent_once() -> None:
    """
    Run a single check cycle over all configured sources.
    This is the complete agent lifecycle — no loops, no retries at this level.
    """
    global _seen_results_ref

    logging.info("=" * 60)
    logging.info("🚀 Campus Alert Agent — Starting check cycle")
    logging.info(f"   Model: {config.GEMINI_MODEL}")
    logging.info(f"   Sources: {len(config.SOURCES)}")
    logging.info("=" * 60)

    # Load persisted seen results
    seen = load_seen_results()
    _seen_results_ref = seen  # Allow timeout handler to save partial state

    stats = {"scraped": 0, "analyzed": 0, "detected": 0, "skipped_dup": 0, "errors": 0}

    for url in config.SOURCES:
        try:
            # ── Step 1: Scrape ────────────────────────────────────────
            logging.info(f"📡 Scraping: {url}")
            scrape_result = scrape_url(url)

            if not scrape_result.get("success"):
                logging.warning(f"❌ Failed to scrape {url}: {scrape_result.get('error')}")
                stats["errors"] += 1
                continue

            stats["scraped"] += 1
            content_hash = scrape_result["content_hash"]

            # ── Step 2: Duplicate check ───────────────────────────────
            if not is_new_result(seen, url, content_hash):
                logging.info(f"⏭️  Skipping (already seen): {url}")
                stats["skipped_dup"] += 1
                continue

            # ── Step 3: Analyze with Gemini ───────────────────────────
            logging.info(f"🧠 Analyzing content from: {url}")
            analysis = analyze_content(url, scrape_result["text"])
            stats["analyzed"] += 1

            detected = analysis.get("detected")
            confidence = analysis.get("confidence")

            if not detected or confidence == "low":
                logging.info(f"🔍 No relevant content at: {url}")
                # Still mark as seen to avoid re-analyzing unchanged content
                seen = mark_as_seen(seen, url, content_hash)
                continue

            # ── Step 4: DETECTION! Send alerts ────────────────────────
            if detected and confidence in ("high", "medium"):
                logging.info(
                    f"🎯 DETECTED at {url} — confidence: {confidence} — sending alerts!"
                )
                send_alert(
                    url,
                    analysis.get("summary", ""),
                    analysis.get("relevant_excerpt", ""),
                )
                stats["detected"] += 1

            # Mark as seen regardless of confidence
            seen = mark_as_seen(seen, url, content_hash)

            # Small delay between sources to be respectful
            time.sleep(2)

        except Exception as e:
            logging.error(f"💥 Unexpected error processing {url}: {e}")
            logging.error(traceback.format_exc())
            stats["errors"] += 1

    # ── Save results ──────────────────────────────────────────────────
    save_seen_results(seen)

    # ── Summary ───────────────────────────────────────────────────────
    logging.info("=" * 60)
    logging.info("✅ Check cycle complete!")
    logging.info(f"   Scraped:  {stats['scraped']}")
    logging.info(f"   Analyzed: {stats['analyzed']}")
    logging.info(f"   Detected: {stats['detected']}")
    logging.info(f"   Skipped (dup): {stats['skipped_dup']}")
    logging.info(f"   Errors:   {stats['errors']}")
    logging.info("=" * 60)


# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Main entry point — setup, run once, exit."""
    setup_logging()

    # Install internal timeout handler (SIGALRM is Unix-only, which is
    # fine since GitHub Actions runs on ubuntu-latest).
    try:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(config.INTERNAL_TIMEOUT_SECONDS)
        logging.info(
            f"⏱️  Internal timeout set: {config.INTERNAL_TIMEOUT_SECONDS}s "
            f"({config.INTERNAL_TIMEOUT_SECONDS // 60} min)"
        )
    except AttributeError:
        # SIGALRM not available on Windows — skip timeout for local dev
        logging.warning("SIGALRM not available — internal timeout disabled (Windows?).")

    try:
        run_agent_once()
    except Exception as e:
        logging.critical(f"💀 Agent crashed: {e}")
        logging.critical(traceback.format_exc())
        # Still try to save whatever we have
        save_seen_results(_seen_results_ref)
        sys.exit(1)
    finally:
        # Cancel any remaining alarm
        try:
            signal.alarm(0)
        except AttributeError:
            pass

    logging.info("👋 Agent finished. Goodbye!")


if __name__ == "__main__":
    main()
