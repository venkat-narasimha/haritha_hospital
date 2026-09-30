"""A.11.3b - Fix role_profile_name on existing Users
The previous A.11.3 bulk provision didn't persist role_profile_name on the User records.
This script sets role_profile_name again for all created Users and saves them,
which should trigger Frappe's hooks to populate tabHas Role from the profile.
"""
import frappe
import secrets
import string
import re


DESIGNATION_TO_ROLE_PROFILE = {
    "Chief Operating Officer": "Haritha: System Manager",
    "Medical Superintendent": "Haritha: HR Manager",
    "Senior Vice President": "Haritha: HR Manager",
    "Nursing Superintendent": "Haritha: Roster Manager",
    "Nursing Supervisor": "Haritha: Roster Manager",
    "Incharge": "Haritha: Leave Approver",
    "Incharge - Micu": "Haritha: Leave Approver",
    "Supervisor": "Haritha: Leave Approver",
}
DEFAULT_ROLE_PROFILE = "Haritha: Employee"


def run():
    print("=== A.11.3b Fix role_profile_name on Users ===")

    # Bypass User throttle (in case any updates trigger User saves)
    frappe.flags.in_import = True

    # Get all employees with user_id, plus the existing testuser
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ("!=", "")},
        fields=["name", "employee_name", "designation", "user_id"]
    )
    print(f"Found {len(employees)} Active employees with user_id")

    # Build map user_id → role_profile
    user_to_rp = {}
    for emp in employees:
        rp = DESIGNATION_TO_ROLE_PROFILE.get(emp["designation"], DEFAULT_ROLE_PROFILE)
        user_to_rp[emp["user_id"]] = rp

    # Also include the existing testuser (Employee HR-EMP-00421 with NULL designation → default Employee)
    if frappe.db.exists("User", "testuser@harithahosptials.com"):
        # testuser is per Designation 10 → Haritha: Employee
        user_to_rp["testuser@harithahosptials.com"] = DEFAULT_ROLE_PROFILE

    results = {"updated": 0, "skipped_existing": 0, "errors": 0, "error_detail": []}

    for user_name, role_profile in user_to_rp.items():
        if not frappe.db.exists("User", user_name):
            results["errors"] += 1
            results["error_detail"].append(f"{user_name}: User not found")
            continue
        try:
            user = frappe.get_doc("User", user_name)
            if user.role_profile_name == role_profile:
                results["skipped_existing"] += 1
                continue

            user.role_profile_name = role_profile
            user.module_profile = "Haritha: Employee Modules"
            user.save(ignore_permissions=True)
            frappe.db.commit()
            results["updated"] += 1
        except Exception as e:
            results["errors"] += 1
            results["error_detail"].append(f"{user_name}: {str(e)[:200]}")
            try:
                frappe.db.rollback()
            except Exception:
                pass

    print(f"\nResults:")
    print(f"  Updated: {results['updated']}")
    print(f"  Skipped (already correct): {results['skipped_existing']}")
    print(f"  Errors: {results['errors']}")

    if results["error_detail"]:
        print(f"\nFirst 5 errors:")
        for e in results["error_detail"][:5]:
            print(f"  {e}")

    # Verify final state
    print("\n=== Verification ===")
    by_profile = frappe.db.sql("""
        SELECT IFNULL(role_profile_name,'(none)') AS profile, COUNT(*) AS cnt
        FROM tabUser WHERE enabled=1 GROUP BY role_profile_name ORDER BY cnt DESC
    """, as_dict=True)
    print(f"Users by role profile:")
    for r in by_profile:
        print(f"  {r['profile']}: {r['cnt']}")


if __name__ == "__main__":
    run()