import sys


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python cli.py [smoke]")
        return
    if args[0] == "smoke":
        print("smoke: placeholder OK")
        return
    print("Unknown command. Usage: python cli.py [smoke]")


if __name__ == "__main__":
    main()

