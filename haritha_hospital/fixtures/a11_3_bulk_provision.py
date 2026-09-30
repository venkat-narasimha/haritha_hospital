"""A.11.3 - Bulk provision ~210 Employee Users
Usage: bench --site pberpprod.duckdns.org execute haritha_hospital.fixtures.a11_3.run
This file is a module that gets called via bench execute (single namespace, no cell-splitting).
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
MODULE_PROFILE_NAME = "Haritha: Employee Modules"


def run():
    print("=== A.11.3 Bulk Provision ===")
    # Bypass User creation throttle (default 60 per 60s) — bulk provisioning needs to exceed this
    frappe.flags.in_import = True

    total_active = frappe.db.count("Employee", {"status": "Active"})
    before_with_user = frappe.db.sql(
        "SELECT COUNT(*) FROM tabEmployee WHERE status='Active' AND IFNULL(user_id,'') != ''"
    )[0][0]
    print(f"Total Active employees: {total_active}")
    print(f"Before: with user_id = {before_with_user}")

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "designation", "department",
                "user_id", "company_email", "personal_email"]
    )

    results = {
        "total": 0,
        "created": 0,
        "skipped_existing": 0,
        "skipped_collision": 0,
        "errors": 0,
        "by_role_profile": {"System Manager": 0, "HR Manager": 0, "HR User": 0,
                            "Roster Manager": 0, "Leave Approver": 0, "Employee": 0},
        "errors_detail": [],
        "collision_detail": [],
    }

    alphabet = string.ascii_letters + string.digits

    for emp in employees:
        results["total"] += 1
        if emp.user_id and frappe.db.exists("User", emp.user_id):
            results["skipped_existing"] += 1
            continue

        role_profile = DESIGNATION_TO_ROLE_PROFILE.get(emp.designation, DEFAULT_ROLE_PROFILE)
        rp_short = role_profile.replace("Haritha: ", "")
        if rp_short not in results["by_role_profile"]:
            rp_short = "Employee"

        # Generate email
        email = emp.company_email or emp.personal_email
        if not email:
            emp_id = emp.name or ""
            m = re.search(r"(\d+)$", emp_id)
            tail = m.group(1).lstrip("0") if m else ""
            slug = re.sub(r"[^a-z0-9]+", "", (emp.employee_name or "").lower())
            base = slug + tail if tail else slug
            email = base + "@harithahospitals.com"

        # Handle email collisions
        suffix = 0
        original_email = email
        while frappe.db.exists("User", email):
            suffix += 1
            local, _, domain = original_email.partition("@")
            email = local + str(suffix) + "@" + domain
        if suffix > 0:
            results["skipped_collision"] += 1
            results["collision_detail"].append(f"{emp.name} -> {email} (suffix={suffix})")

        # Generate password
        pwd = ''.join(secrets.choice(alphabet) for _ in range(16))

        try:
            first = (emp.employee_name or emp.name).split()[0] if (emp.employee_name or emp.name) else emp.name
            last = ""
            if emp.employee_name and len((emp.employee_name or "").split()) > 1:
                last = " ".join(emp.employee_name.split()[1:])

            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": first[:140],
                "last_name": last[:140],
                "username": email,
                "send_welcome_email": 0,
                "user_type": "System User",
                "new_password": pwd,
                "enabled": 1,
                "role_profile_name": role_profile,
                "module_profile": MODULE_PROFILE_NAME,
            })
            user.flags.no_welcome_email = True
            user.flags.ignore_password_policy = False
            user.insert(ignore_permissions=True)
            frappe.db.commit()

            emp_doc = frappe.get_doc("Employee", emp.name)
            emp_doc.user_id = email
            emp_doc.save(ignore_permissions=True)
            frappe.db.commit()

            results["created"] += 1
            results["by_role_profile"][rp_short] += 1
        except Exception as e:
            results["errors"] += 1
            results["errors_detail"].append(f"{emp.name}: {str(e)[:200]}")
            try:
                frappe.db.rollback()
            except Exception:
                pass

    print(f"\nTotal processed: {results['total']}")
    print(f"Created new Users: {results['created']}")
    print(f"Skipped (already had user_id): {results['skipped_existing']}")
    print(f"Skipped (collision w/ suffix): {results['skipped_collision']}")
    print(f"Errors: {results['errors']}")
    print("\nBy Role Profile:")
    for rp, cnt in results["by_role_profile"].items():
        print(f"  Haritha: {rp}: {cnt}")
    if results["errors_detail"]:
        print(f"\nFirst 10 errors:")
        for d in results["errors_detail"][:10]:
            print(f"  {d}")
    if results["collision_detail"]:
        print(f"\nFirst 10 collisions (auto-renamed):")
        for d in results["collision_detail"][:10]:
            print(f"  {d}")

    after_with_user = frappe.db.sql(
        "SELECT COUNT(*) FROM tabEmployee WHERE status='Active' AND IFNULL(user_id,'') != ''"
    )[0][0]
    after_enabled_users = frappe.db.count("User", {"enabled": 1})
    print(f"\nAfter: with user_id = {after_with_user}")
    print(f"After: total enabled Users = {after_enabled_users}")
    print(f"Coverage: {after_with_user}/{total_active} = {round(100*after_with_user/total_active, 1)}%")
    return results