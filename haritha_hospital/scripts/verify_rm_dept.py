"""Verify Roster Manager roles and dept-scoped User Permissions."""
import frappe


def run():
    print("=== Verify Roster Manager status ===")

    # Find Users with Haritha: Roster Manager profile
    rm_users = frappe.get_all("User",
        filters={"role_profile_name": "Haritha: Roster Manager", "enabled": 1},
        fields=["name", "email", "role_profile_name"])

    print(f"\nUsers with role_profile_name='Haritha: Roster Manager': {len(rm_users)}")
    for u in rm_users:
        roles = frappe.get_roles(u["name"])
        print(f"  - {u['name']} (roles: {roles})")

        # Check dept
        emp = frappe.db.get_value("Employee", {"user_id": u["name"]}, ["name", "department"], as_dict=True)
        if emp:
            print(f"    Employee: {emp.get('name')}, dept: {emp.get('department')}")
        else:
            print(f"    NO Employee record")

        # Check existing User Permissions
        perms = frappe.get_all("User Permission",
            filters={"user": u["name"], "allow": "Department"},
            fields=["for_value", "name"])
        print(f"    Dept-scoped perms: {perms}")

    # Also check by role
    print("\n=== Users with 'Roster Manager' in roles ===")
    rm_role_users = frappe.db.sql("""
        SELECT DISTINCT u.name, u.email, u.role_profile_name
        FROM tabUser u
        INNER JOIN `tabHas Role` hr ON hr.parent = u.name AND hr.role = 'Roster Manager'
        WHERE u.enabled = 1
    """, as_dict=True)
    print(f"Found {len(rm_role_users)} Users with Roster Manager role")
    for u in rm_role_users:
        print(f"  - {u['name']} (profile: {u['role_profile_name']})")


if __name__ == "__main__":
    run()