import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="OneMove Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command")

    # score-all command
    subparsers.add_parser("score-all", help="Run ML scoring models")
    # data-quality command
    subparsers.add_parser("data-quality", help="Run data quality checks")
    # refresh-metrics command
    subparsers.add_parser("refresh-metrics", help="Refresh analytic metrics")

    args = parser.parse_args()

    if args.command == "score-all":
        print("Running ML scoring pipelines...")
        from onemove_intelligence.ml.demand_forecast import forecast_demand
        from onemove_intelligence.ml.dispatch_optimizer import optimize_dispatch
        forecast_demand()
        optimize_dispatch()
        print("Scoring complete.")
    elif args.command == "data-quality":
        print("Running data quality checks...")
        from onemove_intelligence.data_quality.checks import run_all_checks
        run_all_checks()
    elif args.command == "refresh-metrics":
        print("Refreshing metrics...")
        from onemove_intelligence.analytics.metric_store import refresh_metrics
        refresh_metrics()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
