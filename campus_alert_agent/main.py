"""Main entry point for campus_alert_agent."""
import time
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

import config
from database import init_db, is_already_seen, mark_as_seen
from scraper import scrape_url
from analyzer import analyze_content
from alerter import send_alert

logging.basicConfig(
    level=logging.INFO, 
    format="[%(asctime)s] %(levelname)s: %(message)s", 
    datefmt="%Y-%m-%d %H:%M:%S"
)

def run_check() -> None:
    """Run a single check cycle over all sources."""
    logging.info("Starting check cycle...")
    
    for url in config.SOURCES:
        logging.info(f"Scraping: {url}")
        scrape_result = scrape_url(url)
        
        if not scrape_result.get("success"):
            logging.warning(f"Failed to scrape {url}. Error: {scrape_result.get('error')}")
            continue
            
        content_hash = scrape_result["content_hash"]
        if is_already_seen(url, content_hash):
            logging.info(f"Skipping (already seen): {url}")
            continue
            
        logging.info(f"Analyzing content from: {url}")
        analysis = analyze_content(url, scrape_result["text"])
        
        detected = analysis.get("detected")
        confidence = analysis.get("confidence")
        
        if not detected or confidence == "low":
            logging.info(f"No relevant content at: {url}")
            continue
            
        if detected and confidence in ("high", "medium"):
            logging.info(f"DETECTED at {url} — confidence: {confidence} — sending alerts!")
            send_alert(url, analysis.get("summary", ""), analysis.get("relevant_excerpt", ""))
            mark_as_seen(url, content_hash)
            
        time.sleep(3)
        
    logging.info("Check cycle complete.")

def main() -> None:
    """Main function to initialize and start the scheduler."""
    print(f"""
============================================
 Campus Alert Agent v1.0.0
 Powered by: Google Gemini ({config.GEMINI_MODEL})
 Monitoring: {len(config.SOURCES)} sources
 Check interval: every {config.CHECK_INTERVAL_MINUTES} minutes
============================================
""")
    init_db()
    
    scheduler = BlockingScheduler()
    scheduler.add_job(run_check, 'interval', minutes=config.CHECK_INTERVAL_MINUTES)
    
    run_check()
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logging.info("Shutting down... Goodbye!")

if __name__ == "__main__":
    main()
