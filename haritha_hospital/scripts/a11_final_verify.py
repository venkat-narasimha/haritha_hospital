"""A.11 Final verification - capture all metrics for output JSON."""
import frappe


def run():
    print("=== A.11 Final Verification ===\n")

    # A.11.1 — Server Script
    ss = frappe.get_all("Server Script", fields=["name", "disabled", "script_type", "reference_doctype", "doctype_event"])
    print(f"A.11.1 Server Scripts ({len(ss)}):")
    for s in ss:
        print(f"  - {s['name']} | disabled={s['disabled']} | {s['script_type']} | {s['reference_doctype']} | {s['doctype_event']}")

    # A.11.2 — Password policy
    print(f"\nA.11.2 System Settings:")
    print(f"  minimum_password_score = {frappe.db.get_single_value('System Settings', 'minimum_password_score')}")
    print(f"  enable_password_policy = {frappe.db.get_single_value('System Settings', 'enable_password_policy')}")
    print(f"  enable_two_factor_auth = {frappe.db.get_single_value('System Settings', 'enable_two_factor_auth')}")

    # A.11.3 — Bulk provision
    total_active = frappe.db.count("Employee", {"status": "Active"})
    with_user = frappe.db.sql("SELECT COUNT(*) FROM tabEmployee WHERE status='Active' AND IFNULL(user_id,'') != ''")[0][0]
    enabled_users = frappe.db.count("User", {"enabled": 1, "name": ("not in", ["Administrator", "Guest"])})
    print(f"\nA.11.3 Bulk Provision:")
    print(f"  Total Active: {total_active}")
    print(f"  With user_id: {with_user}")
    print(f"  Coverage: {with_user}/{total_active} = {round(100*with_user/total_active, 1)}%")
    print(f"  Enabled Users (non-admin/guest): {enabled_users}")

    by_role = frappe.db.sql("""
        SELECT hr.role, COUNT(DISTINCT hr.parent) AS cnt
        FROM `tabHas Role` hr
        INNER JOIN tabUser u ON u.name = hr.parent
        WHERE hr.parenttype='User' AND u.enabled=1 AND u.name NOT IN ('Administrator','Guest')
        GROUP BY hr.role ORDER BY cnt DESC
    """, as_dict=True)
    print(f"  By role:")
    for r in by_role:
        print(f"    {r['role']}: {r['cnt']}")

    # A.11.4 — Module Profiles
    haritha_mp = frappe.get_all("Module Profile", filters={"name": ("like", "Haritha:%")}, fields=["name"])
    print(f"\nA.11.4 Module Profiles ({len(haritha_mp)}):")
    for m in haritha_mp:
        print(f"  - {m['name']}")

    role_mp = frappe.db.sql("""
        SELECT role_name, module_profile FROM tabRole
        WHERE module_profile LIKE 'Haritha:%'
        ORDER BY role_name
    """, as_dict=True)
    print(f"  Role → Module Profile:")
    for r in role_mp:
        print(f"    {r['role_name']} → {r['module_profile']}")

    # A.11.5 — leave_approver
    la_stats = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_active,
            SUM(IF(IFNULL(leave_approver,'')!='', 1, 0)) AS with_approver,
            SUM(IF(leave_approver='Administrator', 1, 0)) AS approver_admin,
            SUM(IF(leave_approver != 'Administrator' AND IFNULL(leave_approver,'')!='', 1, 0)) AS approver_dept_heads
        FROM tabEmployee WHERE status='Active'
    """)[0]
    print(f"\nA.11.5 leave_approver stats:")
    print(f"  Total Active: {la_stats[0]}")
    print(f"  With approver: {la_stats[1]}")
    print(f"  Administrator fallbacks: {la_stats[2]}")
    print(f"  Dept-head approvers: {la_stats[3]}")

    top_app = frappe.db.sql("""
        SELECT leave_approver, COUNT(*) AS cnt
        FROM tabEmployee WHERE status='Active' AND IFNULL(leave_approver,'')!=''
        GROUP BY leave_approver ORDER BY cnt DESC LIMIT 10
    """, as_dict=True)
    print(f"  Top 10 approvers:")
    for r in top_app:
        print(f"    {r['leave_approver']}: {r['cnt']}")

    # A.11.6 — User Permissions
    total_perms = frappe.db.count("User Permission")
    self_perms = frappe.db.count("User Permission", {"allow": "Employee"})
    dept_perms = frappe.db.count("User Permission", {"allow": "Department"})
    print(f"\nA.11.6 User Permissions:")
    print(f"  Total: {total_perms}")
    print(f"  Employee self: {self_perms}")
    print(f"  Department: {dept_perms}")


if __name__ == "__main__":
    run()