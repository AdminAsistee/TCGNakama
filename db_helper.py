import sys
from app.cost_db import get_all_costs, set_cost, get_all_grades, set_grade, get_trending_searches

def print_help():
    print("""
TCG Nakama DB Helper
Usage:
  python db_helper.py list-costs          - List all buy prices
  python db_helper.py set-cost <id> <val> - Set buy price for a product
  python db_helper.py list-grades         - List all product grades
  python db_helper.py set-grade <id> <g>  - Set grade for a product
  python db_helper.py trending           - Show trending searches
    """)

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1]

    if cmd == "list-costs":
        costs = get_all_costs()
        print("\n--- Product Costs ---")
        for pid, cost in costs.items():
            print(f"ID: {pid} | Price: ${cost}")
        if not costs:
            print("No costs found.")

    elif cmd == "set-cost":
        if len(sys.argv) < 4:
            print("Error: Missing product ID or price.")
            return
        pid, price = sys.argv[2], float(sys.argv[3])
        set_cost(pid, price)
        print(f"Success: Set {pid} cost to ${price}")

    elif cmd == "list-grades":
        grades = get_all_grades()
        print("\n--- Product Grades ---")
        for pid, grade in grades.items():
            print(f"ID: {pid} | Grade: {grade}")
        if not grades:
            print("No grades found.")

    elif cmd == "set-grade":
        if len(sys.argv) < 4:
            print("Error: Missing product ID or grade.")
            return
        pid, grade = sys.argv[2], sys.argv[3]
        set_grade(pid, grade)
        print(f"Success: Set {pid} grade to {grade}")

    elif cmd == "trending":
        searches = get_trending_searches()
        print("\n--- Trending Searches ---")
        for s in searches:
            print(f"Query: {s['query']} | Count: {s['count']}")
        if not searches:
            print("No search logs found.")

    else:
        print_help()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
