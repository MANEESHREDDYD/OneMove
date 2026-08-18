import argparse


def main():
    parser = argparse.ArgumentParser(description="Extract ZonePilot data to ZONEPILOT_DATA_ROOT")
    parser.parse_args()
    print("Snapshot pull simulated. (Using fixtures)")


if __name__ == "__main__":
    main()
