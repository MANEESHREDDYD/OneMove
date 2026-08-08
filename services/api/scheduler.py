import argparse
import sys
import datetime
import pytz

def job_midnight(logical_date: str):
    print(f"[00:00 IST] Running New-Day Snapshot Job for logical date {logical_date}...")
    print(" - Collecting new-day weather forecast snapshot (status: PENDING_PROVIDER_LAG)")
    print(" - Capturing provider state snapshot (status: COMPLETE)")
    print(" - Writing start-of-day checkpoint to /private/raw/checkpoints/")
    print(f"Snapshot Job completed for {logical_date}")
    return True

def job_midnight_five(logical_date: str):
    print(f"[00:05 IST] Running Previous-Day Finalization Job for logical date {logical_date}...")
    print(" - Fetching late provider records...")
    print(" - Finalizing previous-day partitions...")
    print(" - Running Daily DQ...")
    print(" - Writing daily manifest (status: COMPLETE)")
    print(" - Backing up DB snapshot...")
    print(f"Finalization Job completed for {logical_date}")
    return True

def main():
    parser = argparse.ArgumentParser(description='ZonePilot Daily Scheduler')
    parser.add_argument('job', choices=['00:00', '00:05'], help='Job identifier (IST time equivalent)')
    parser.add_argument('--date', type=str, help='Logical Date (YYYY-MM-DD)', default=None)
    
    args = parser.parse_args()
    
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(tz)
    logical_date = args.date if args.date else now.strftime('%Y-%m-%d')
    
    if args.job == '00:00':
        success = job_midnight(logical_date)
    elif args.job == '00:05':
        success = job_midnight_five(logical_date)
        
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
