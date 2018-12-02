#! /usr/bin/python3.6
from dataLayer import DataLayer

def main():
    runner = DataLayer()
    runner.RefreshFromStore()

if __name__ == "__main__":
    main()