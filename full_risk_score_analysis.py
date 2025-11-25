"""
MASTER ANALYSIS SCRIPT
Runs the complete pipeline:
1. Live Data Fetching (Holders & Transfers)
2. Holder Snapshot Analysis (YOUR CODE)
3. Wash Trading Detection
4. Bot Detection
5. Combined Risk Scoring
"""

import sys
import os
from config import config

# Import modules
from data_fetcher import LiveDataFetcher
from wash_trading_detector import TransactionBasedWashTradingDetector
from bot_detector import BotDetector
from combined_analyzer import CombinedAnalyzer
from holder_analyzer import HolderAnalyzer

def main():
    # 1. Setup
    if not config.validate():
        sys.exit(1)
        
    print("\n" + "#"*70)
    print("STARTING FULL TOKEN RISK ASSESSMENT")
    print(f"Chain: {config.CHAIN}")
    print("#"*70)

    # Initialize Fetcher once
    fetcher = LiveDataFetcher(config.ARKHAM_API_KEY)

    # We loop through all tokens defined in .env
    for token_address in config.TOKENS:
        print(f"\n\n>>> ANALYZING TOKEN: {token_address}")
        
        # ====================================================
        # STEP 1: FETCH HOLDER DATA (Via LiveDataFetcher)
        # ====================================================
        # Retrieve data FIRST before initializing analyzer
        holders_data = fetcher.fetch_token_holders(token_address, config.CHAIN)

        # ====================================================
        # STEP 2: RUN SNAPSHOT ANALYSIS
        # ====================================================
        if holders_data:
            try:
                # Pass DATA to analyzer, pass FETCHER to run_analysis for AMM deep dive
                holder_analyzer = HolderAnalyzer(token_address, holders_data)
                holder_analyzer.run_analysis(fetcher)
            except Exception as e:
                print(f"⚠ Holder Analysis Failed: {e}")
        else:
            print("⚠ Skipping Holder Analysis (No data fetched)")

        # ====================================================
        # STEP 3: FETCH TRANSFER DATA (Via LiveDataFetcher)
        # ====================================================
        user_flows = fetcher.fetch_and_process_token(token_address)
        
        if user_flows is None or user_flows.empty:
            print("⚠ Skipping detailed transfer analysis (No data)")
            continue

        # Save temporary file for wash trading detector to load
        temp_filename = f"temp_{token_address}_flows.csv"
        user_flows.to_csv(f"outputs/data/processed/{temp_filename}", index=False)

        # ====================================================
        # STEP 4: PARTNER MODULE (Wash Trading)
        # ====================================================
        # try:
        wash_detector = TransactionBasedWashTradingDetector(temp_filename)
        wash_detector.extract_user_flows() # Re-processes the temp file
        wash_detector.run_all_analyses()
        # except Exception as e:
        #     print(f"⚠ Wash Trading Analysis Failed: {e}")
        #     continue

        # ====================================================
        # STEP 5: PARTNER MODULE (Bot Detection)
        # ====================================================
        try:
            bot_detector = BotDetector(
                api_key=config.ARKHAM_API_KEY,
                user_flows=user_flows,
                time_window=config.TIME_WINDOW
            )
            # Run classification (using small sample if quick mode is on)
            sample = 50 if config.QUICK_MODE else None
            bot_detector.classify_wallets(sample_size=sample)
        except Exception as e:
            print(f"⚠ Bot Detection Failed: {e}")
            continue

        # ====================================================
        # STEP 6: PARTNER MODULE (Combined Report)
        # ====================================================
        try:
            combiner = CombinedAnalyzer(wash_detector, bot_detector, token_address)
            combiner.create_combined_analysis()
            combiner.save_results(config.OUTPUT_DIR, token_address)
        except Exception as e:
            print(f"⚠ Combined Analysis Failed: {e}")

    print("\n" + "#"*70)
    print("✅ FULL PIPELINE COMPLETE")
    print(f"Check {config.OUTPUT_DIR} for reports.")
    print("#"*70)

if __name__ == "__main__":
    main()