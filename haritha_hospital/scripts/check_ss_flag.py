import frappe

def run():
    print("frappe.conf.server_script_enabled =", frappe.conf.get("server_script_enabled"))
    print("frappe.conf keys with 'script':", [k for k in frappe.conf.keys() if 'script' in k.lower()])
    print("\nServer Script count:", frappe.db.count("Server Script"))

    ss_doc = frappe.get_all("Server Script", fields=["name", "disabled", "script_type", "reference_doctype", "doctype_event"])
    print(f"\nServer Scripts in DB:")
    for s in ss_doc:
        print(f"  - {s['name']} | disabled={s['disabled']} | {s['script_type']} | {s['reference_doctype']} | {s['doctype_event']}")

if __name__ == "__main__":
    run()