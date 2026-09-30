import frappe

print("frappe.conf.server_script_enabled =", frappe.conf.get("server_script_enabled"))
print("frappe.conf keys with 'script':", [k for k in frappe.conf.keys() if 'script' in k.lower()])

# Also check Frappe's _flags that control Server Scripts
from frappe import _dict
print("frappe.flags.server_script_enabled =", getattr(frappe.flags, "server_script_enabled", "not set"))

# Check Server Script DocType
print("\nServer Script count:", frappe.db.count("Server Script"))

# Try invoking the flag check
try:
    from frappe.core.doctype.server_script.server_script import ServerScript
    print("Server Script class loaded")
except Exception as e:
    print(f"Import error: {e}")

# Check if Server Scripts are disabled in DB cache
ss_doc = frappe.get_all("Server Script", fields=["name", "disabled", "script_type", "reference_doctype", "doctype_event"])
print(f"\nServer Scripts in DB:")
for s in ss_doc:
    print(f"  - {s['name']} | disabled={s['disabled']} | {s['script_type']} | {s['reference_doctype']} | {s['doctype_event']}")