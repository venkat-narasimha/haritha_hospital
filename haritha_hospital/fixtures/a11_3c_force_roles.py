"""A.11.3c - Force-set roles via direct tabHas Role insertion.
Frappe's User controller isn't persisting role_profile_name, so we directly add
the correct roles to tabHas Role based on each Employee's designation mapping.
"""
import frappe


DESIGNATION_TO_ROLES = {
    "Chief Operating Officer": ["System Manager"],
    "Medical Superintendent": ["HR Manager"],
    "Senior Vice President": ["HR Manager"],
    "Nursing Superintendent": ["Roster Manager"],
    "Nursing Supervisor": ["Roster Manager"],
    "Incharge": ["Leave Approver"],
    "Incharge - Micu": ["Leave Approver"],
    "Supervisor": ["Leave Approver"],
}
DEFAULT_ROLES = ["Employee"]


def run():
    print("=== A.11.3c Force-set roles via tabHas Role ===")

    frappe.flags.in_import = True

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ("!=", "")},
        fields=["name", "employee_name", "designation", "user_id"]
    )
    print(f"Found {len(employees)} Active employees with user_id")

    # For each employee, compute desired roles
    user_to_roles = {}
    for emp in employees:
        additional = DESIGNATION_TO_ROLES.get(emp["designation"], [])
        roles = DEFAULT_ROLES + additional  # Employee + role-specific
        user_to_roles[emp["user_id"]] = roles

    # Special case: testuser → Employee only
    if frappe.db.exists("User", "testuser@harithahosptials.com"):
        user_to_roles["testuser@harithahosptials.com"] = ["Employee"]

    results = {"users_updated": 0, "roles_added": 0, "roles_existed": 0, "errors": 0, "error_detail": []}

    for user_name, desired_roles in user_to_roles.items():
        if not frappe.db.exists("User", user_name):
            results["errors"] += 1
            results["error_detail"].append(f"{user_name}: User not found")
            continue

        try:
            # Get existing roles
            existing = set(r[0] for r in frappe.db.sql(
                "SELECT role FROM `tabHas Role` WHERE parent=%s AND parenttype='User'",
                (user_name,),
            ))

            # Add missing roles
            added_for_user = 0
            for role in desired_roles:
                if role not in existing:
                    frappe.get_doc({
                        "doctype": "Has Role",
                        "parent": user_name,
                        "parenttype": "User",
                        "parentfield": "roles",
                        "role": role,
                    }).insert(ignore_permissions=True)
                    added_for_user += 1
                    results["roles_added"] += 1
                else:
                    results["roles_existed"] += 1

            if added_for_user > 0:
                results["users_updated"] += 1
        except Exception as e:
            results["errors"] += 1
            results["error_detail"].append(f"{user_name}: {str(e)[:200]}")
            try:
                frappe.db.rollback()
            except Exception:
                pass

    frappe.db.commit()

    print(f"\nResults:")
    print(f"  Users updated: {results['users_updated']}")
    print(f"  Roles added: {results['roles_added']}")
    print(f"  Roles existed: {results['roles_existed']}")
    print(f"  Errors: {results['errors']}")

    if results["error_detail"]:
        print(f"\nFirst 5 errors:")
        for e in results["error_detail"][:5]:
            print(f"  {e}")

    # Verification: count users per role
    print("\n=== Verification: Users by role ===")
    by_role = frappe.db.sql("""
        SELECT role, COUNT(DISTINCT parent) AS cnt
        FROM `tabHas Role`
        WHERE parenttype='User' AND parent IN (
            SELECT name FROM tabUser WHERE enabled=1 AND name NOT IN ('Administrator','Guest')
        )
        GROUP BY role ORDER BY cnt DESC
    """, as_dict=True)
    for r in by_role:
        print(f"  {r['role']}: {r['cnt']}")

    # Role Profile distribution
    print("\n=== role_profile_name on Users ===")
    by_profile = frappe.db.sql("""
        SELECT IFNULL(role_profile_name,'(none)') AS profile, COUNT(*) AS cnt
        FROM tabUser WHERE enabled=1 GROUP BY role_profile_name ORDER BY cnt DESC
    """, as_dict=True)
    for r in by_profile:
        print(f"  {r['profile']}: {r['cnt']}")


if __name__ == "__main__":
    run()