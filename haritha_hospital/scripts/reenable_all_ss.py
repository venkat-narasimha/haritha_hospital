"""Re-enable Server Scripts after bulk provisioning."""
import frappe


def run():
    scripts = frappe.get_all("Server Script", fields=["name", "disabled"])
    print(f"Found {len(scripts)} Server Scripts")
    for s in scripts:
        ss = frappe.get_doc("Server Script", s["name"])
        before = ss.disabled
        ss.disabled = 0
        ss.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"  {s['name']}: {before} -> 0")
    # Verify
    print("\nFinal state:")
    final = frappe.get_all("Server Script", fields=["name", "disabled", "script_type", "reference_doctype", "doctype_event"])
    for s in final:
        print(f"  {s['name']}: disabled={s['disabled']} | {s['script_type']} | {s['reference_doctype']} | {s['doctype_event']}")


if __name__ == "__main__":
    run()