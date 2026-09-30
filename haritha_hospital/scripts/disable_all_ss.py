"""Disable ALL Server Scripts for safe bulk provisioning."""
import frappe


def run():
    scripts = frappe.get_all("Server Script", fields=["name", "disabled"])
    print(f"Found {len(scripts)} Server Scripts")
    for s in scripts:
        ss = frappe.get_doc("Server Script", s["name"])
        before = ss.disabled
        ss.disabled = 1
        ss.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  {s['name']}: {before} -> 1")
    # Verify
    print("\nVerification:")
    final = frappe.get_all("Server Script", fields=["name", "disabled"])
    for s in final:
        print(f"  {s['name']}: disabled={s['disabled']}")


if __name__ == "__main__":
    run()