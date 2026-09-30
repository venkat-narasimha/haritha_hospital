"""A.11.6 - Re-run A.6 logic: create self-only + dept-scoped User Permissions
"""
import frappe


def run():
    print("=== A.11.6 Bulk User Permissions ===")

    # BEFORE stats
    before_total = frappe.db.count("User Permission")
    before_self = frappe.db.count("User Permission", {"allow": "Employee"})
    before_dept = frappe.db.count("User Permission", {"allow": "Department"})
    print(f"Before: total={before_total}, self={before_self}, dept={before_dept}")

    results = {
        "users_processed": 0,
        "perms_created": 0,
        "skipped": 0,
        "skipped_own_self_perm": 0,
        "by_role": {"employee_self": 0, "leave_approver_dept": 0, "roster_manager_dept": 0},
        "errors": [],
    }

    # Get all enabled Users (System User only, exclude Administrator + Guest)
    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User", "name": ("not in", ["Administrator", "Guest"])},
        fields=["name", "email", "role_profile_name"]
    )

    print(f"Processing {len(users)} enabled Users...")

    for user in users:
        results["users_processed"] += 1
        user_name = user["name"]
        user_roles = set(r[0] for r in frappe.db.sql(
            "SELECT role FROM `tabHas Role` WHERE parent=%s AND parenttype='User'",
            (user_name,)
        ))

        # Skip full-access roles (System Manager has org-wide access)
        if "System Manager" in user_roles:
            results["skipped"] += 1
            continue

        # --- Employee role: self-only User Permission ---
        if "Employee" in user_roles:
            emp = frappe.db.get_value("Employee", {"user_id": user_name}, ["name", "department"], as_dict=True)
            if emp and emp.get("name"):
                # Create self-only User Permission (Employee == self.name)
                existing = frappe.get_all("User Permission",
                    filters={"user": user_name, "allow": "Employee", "for_value": emp["name"]})
                if not existing:
                    try:
                        up = frappe.get_doc({
                            "doctype": "User Permission",
                            "user": user_name,
                            "allow": "Employee",
                            "for_value": emp["name"],
                            "apply_to_all_doctypes": 1,
                        })
                        up.insert(ignore_permissions=True)
                        results["perms_created"] += 1
                        results["by_role"]["employee_self"] += 1
                    except Exception as e:
                        results["errors"].append(f"{user_name} self: {str(e)[:200]}")
                else:
                    results["skipped_own_self_perm"] += 1

        # --- Leave Approver role: dept-scoped User Permissions ---
        if "Leave Approver" in user_roles:
            # Find unique depts this approver handles (employees with this as leave_approver)
            depts = frappe.db.sql("""
                SELECT DISTINCT department FROM tabEmployee
                WHERE leave_approver = %s AND IFNULL(department, '') != ''
            """, (user_name,), as_list=True)
            depts = [d[0] for d in depts]

            for dept in depts:
                existing = frappe.get_all("User Permission",
                    filters={"user": user_name, "allow": "Department", "for_value": dept})
                if not existing:
                    try:
                        up = frappe.get_doc({
                            "doctype": "User Permission",
                            "user": user_name,
                            "allow": "Department",
                            "for_value": dept,
                            "apply_to_all_doctypes": 1,
                        })
                        up.insert(ignore_permissions=True)
                        results["perms_created"] += 1
                        results["by_role"]["leave_approver_dept"] += 1
                    except Exception as e:
                        results["errors"].append(f"{user_name} dept {dept}: {str(e)[:200]}")

        # --- Roster Manager role: dept-scoped User Permissions ---
        if "Roster Manager" in user_roles:
            emp = frappe.db.get_value("Employee", {"user_id": user_name}, ["name", "department"], as_dict=True)
            if emp and emp.get("department"):
                dept = emp["department"]
                existing = frappe.get_all("User Permission",
                    filters={"user": user_name, "allow": "Department", "for_value": dept})
                if not existing:
                    try:
                        up = frappe.get_doc({
                            "doctype": "User Permission",
                            "user": user_name,
                            "allow": "Department",
                            "for_value": dept,
                            "apply_to_all_doctypes": 1,
                        })
                        up.insert(ignore_permissions=True)
                        results["perms_created"] += 1
                        results["by_role"]["roster_manager_dept"] += 1
                    except Exception as e:
                        results["errors"].append(f"{user_name} dept {dept}: {str(e)[:200]}")

    frappe.db.commit()

    print(f"\nResults:")
    print(f"  Users processed: {results['users_processed']}")
    print(f"  Permissions created: {results['perms_created']}")
    print(f"  Skipped (System Manager): {results['skipped']}")
    print(f"  Skipped (own self-perm existed): {results['skipped_own_self_perm']}")
    print(f"  Errors: {len(results['errors'])}")
    print(f"\nBy role:")
    for role, cnt in results["by_role"].items():
        print(f"  {role}: {cnt}")

    if results["errors"]:
        print(f"\nFirst 10 errors:")
        for e in results["errors"][:10]:
            print(f"  {e}")

    # AFTER stats
    after_total = frappe.db.count("User Permission")
    after_self = frappe.db.count("User Permission", {"allow": "Employee"})
    after_dept = frappe.db.count("User Permission", {"allow": "Department"})
    print(f"\nAfter: total={after_total}, self={after_self}, dept={after_dept}")
    print(f"Created: +{after_total - before_total}")


if __name__ == "__main__":
    run()