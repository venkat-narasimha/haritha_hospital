"""Verify Roster Manager roles + dept perms + departments."""
import frappe


def run():
    print("=== Roster Manager verification ===")

    # Find Users with Roster Manager role via tabHas Role
    rm_users = frappe.db.sql("""
        SELECT hr.parent AS user_name
        FROM `tabHas Role` hr
        WHERE hr.role='Roster Manager' AND hr.parenttype='User'
    """, as_list=True)
    print(f"\nUsers with Roster Manager role (from tabHas Role): {len(rm_users)}")
    for (u,) in rm_users:
        # Check department via Employee
        emp = frappe.db.get_value("Employee", {"user_id": u}, ["name", "department"], as_dict=True)
        # Check via get_roles
        roles = frappe.get_roles(u)
        has_rm = "Roster Manager" in roles
        print(f"  {u}: dept={emp.get('department') if emp else 'NONE'} | get_roles has RM: {has_rm} | roles: {roles}")

        # Check existing dept perms
        perms = frappe.get_all("User Permission",
            filters={"user": u, "allow": "Department"},
            fields=["for_value"])
        print(f"    Dept-scoped perms: {[p['for_value'] for p in perms]}")

    # Check via tabHas Role also for other key roles
    print("\n=== Users with HR Manager role ===")
    hm_users = frappe.db.sql("""
        SELECT hr.parent AS user_name
        FROM `tabHas Role` hr
        WHERE hr.role='HR Manager' AND hr.parenttype='User'
    """, as_list=True)
    for (u,) in hm_users:
        print(f"  {u}")

    print("\n=== Users with System Manager role ===")
    sm_users = frappe.db.sql("""
        SELECT hr.parent AS user_name
        FROM `tabHas Role` hr
        WHERE hr.role='System Manager' AND hr.parenttype='User'
    """, as_list=True)
    for (u,) in sm_users:
        print(f"  {u}")


if __name__ == "__main__":
    run()