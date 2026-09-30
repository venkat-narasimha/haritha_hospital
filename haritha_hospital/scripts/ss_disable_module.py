"""Disable Provision User Server Script."""
import frappe


def run():
    SCRIPT_NAME = "Provision User on Employee Activate"
    if not frappe.db.exists("Server Script", SCRIPT_NAME):
        print(f"Server Script '{SCRIPT_NAME}' does not exist")
        return False

    ss = frappe.get_doc("Server Script", SCRIPT_NAME)
    before = ss.disabled
    ss.disabled = 1
    ss.save(ignore_permissions=True)
    frappe.db.commit()

    # Verify
    ss2 = frappe.get_doc("Server Script", SCRIPT_NAME)
    print(f"Server Script '{SCRIPT_NAME}': disabled {before} -> {ss2.disabled}")
    return ss2.disabled == 1


if __name__ == "__main__":
    run()