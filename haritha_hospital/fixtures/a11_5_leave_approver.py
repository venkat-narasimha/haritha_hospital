"""A.11.5 - Re-populate leave_approver from dept-head mapping
"""
import frappe


def run():
    # Dept → designation priority for head selection
    # First match (in this order) becomes the leave approver for the dept
    DEPT_HEAD_DESIGNATIONS = {
        # Nursing - HH: Nursing Superintendent > Incharge - Micu > Incharge > Nursing Supervisor
        "Nursing - HH": ["Nursing Superintendent", "Incharge - Micu", "Incharge", "Nursing Supervisor"],
        # Operations - HH: COO (per Decision 2) > GM > Sr Manager
        "Operations - HH": ["Chief Operating Officer", "General Manager", "Senior Manager"],
        # Business Development - HH: SVP > DGM > GM > AGM
        "Business Development - HH": ["Senior Vice President", "Deputy General Manager", "General Manager", "Assistant General Manager"],
        # Pharmacy - HH: Deputy Manager > Asst Manager > Manager
        "Pharmacy - HH": ["Deputy Manager", "Assistant Manager", "Manager"],
        # Human Resources - HH: Manager
        "Human Resources - HH": ["Manager"],
        # Finance & Accounts - HH: Manager > Sr Manager
        "Finance & Accounts - HH": ["Manager", "Senior Manager"],
        # Maintenance - HH: Manager > Supervisor
        "Maintenance - HH": ["Manager", "Supervisor"],
        # Lab Services - HH: Manager > Sr Technician
        "Lab Services - HH": ["Manager", "Senior Technician"],
        # Quality - HH: Manager > Asst Manager
        "Quality - HH": ["Manager", "Assistant Manager"],
        # IT - HH: Sr Manager > Manager > Sr Executive
        "IT - HH": ["Senior Manager", "Manager", "Senior Executive"],
        # Housekeeping - HH: Manager
        "Housekeeping - HH": ["Manager"],
        # Cath Lab - HH: Incharge
        "Cath Lab - HH": ["Incharge"],
        # Corporate Relations - HH: Manager > Sr Manager
        "Corporate Relations - HH": ["Manager", "Senior Manager"],
        # Credit Realization - HH: Manager
        "Credit Realization - HH": ["Manager"],
        # Billing - HH: AGM > Manager
        "Billing - HH": ["Assistant General Manager", "Manager"],
        # Bio Medical - HH: Asst Manager > Manager
        "Bio Medical - HH": ["Assistant Manager", "Manager"],
        # OP Operations - HH: Manager > Sr Manager
        "OP Operations - HH": ["Manager", "Senior Manager"],
        # IP Operations - HH: Manager
        "IP Operations - HH": ["Manager"],
        # Medical Services - HH: Clinical Assistant -> fallback
        "Medical Services - HH": ["Medical Superintendent", "Incharge"],
        # Administration - Medical - HH: Medical Superintendent
        "Administration - Medical - HH": ["Medical Superintendent"],
        # CSSD - HH: Manager
        "CSSD - HH": ["Manager"],
        # Operation Theatre - HH: Manager > Incharge
        "Operation Theatre - HH": ["Manager", "Incharge"],
        # Radiology - HH: Sr Technician > Manager
        "Radiology - HH": ["Senior Technician", "Technician", "Manager"],
        # Physiotherapy - HH: Sr Physiotherapist > Physiotherapist
        "Physiotherapy - HH": ["Senior Physiotherapist", "Physiotherapist"],
        # Respiratory Therapy - HH: Sr Respiratory Therapy
        "Respiratory Therapy - HH": ["Senior Respiratory Therapy"],
        # Dietetics - HH: Dietician
        "Dietetics - HH": ["Dietician"],
        # Dialysis - HH: Incharge
        "Dialysis - HH": ["Incharge", "Manager"],
        # Endoscopy - HH: Manager > Incharge
        "Endoscopy - HH": ["Manager", "Incharge"],
        # Cardiology - HH: Manager > Incharge
        "Cardiology - HH": ["Manager", "Incharge"],
        # Transport - HH: Senior Electrician (closest to lead) > Sr Manager
        "Transport - HH": ["Senior Manager", "Manager"],
        # Typing Pool - HH: Sr Manager
        "Typing Pool - HH": ["Senior Manager", "Manager"],
        # General Purchase - HH: Sr Manager
        "General Purchase - HH": ["Senior Manager", "Manager"],
        # Internal Audit - HH: Manager > Sr Manager
        "Internal Audit - HH": ["Manager", "Senior Manager"],
        # Legal - HH: Manager
        "Legal - HH": ["Manager", "Senior Manager"],
        # Medical Records - HH: Manager
        "Medical Records - HH": ["Manager", "Senior Manager"],
        # Nursing - OT - HH: Scrub Nurse area - tie to Nursing
        "Nursing - OT - HH": ["Incharge", "Nursing Supervisor"],
        # Skip placeholders
        # "Test ICU - HH": [],
        # "X - HH": [],
        # "Test ICU": [],
    }

    FALLBACK_APPROVER = "Administrator"  # Last resort

    print("=== A.11.5 Re-populate leave_approver ===")

    # BEFORE stats
    before = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_active,
            SUM(IF(IFNULL(leave_approver,'')!='', 1, 0)) AS with_approver,
            SUM(IF(leave_approver='Administrator', 1, 0)) AS approver_admin
        FROM tabEmployee WHERE status='Active'
    """)[0]
    print(f"Before: total_active={before[0]}, with_approver={before[1]}, approver_admin={before[2]}")

    results = {"updated": 0, "skipped_no_dept": 0, "skipped_no_approver": 0, "errors": 0,
               "by_dept": {}, "approver_assignments": {}}

    # Iterate over each unique department
    depts = frappe.db.sql("""
        SELECT DISTINCT department FROM tabEmployee
        WHERE status='Active' AND IFNULL(department,'') != ''
        ORDER BY department
    """, as_list=True)
    depts = [d[0] for d in depts]
    print(f"Departments to process: {len(depts)}")

    # Build dept → approver user mapping
    dept_to_approver = {}

    for dept in depts:
        # Skip placeholders
        if dept in ("Test ICU - HH", "Test ICU", "X - HH", "All Departments"):
            continue

        designation_candidates = DEPT_HEAD_DESIGNATIONS.get(dept, [])
        approver_user = None

        for des in designation_candidates:
            emp = frappe.get_all("Employee",
                filters={"status": "Active", "department": dept, "designation": des,
                        "user_id": ("!=", "")},
                fields=["name", "user_id"], limit=1)
            if emp:
                approver_user = emp[0]["user_id"]
                results["approver_assignments"][dept] = (des, emp[0]["name"], approver_user)
                break

        if not approver_user:
            approver_user = FALLBACK_APPROVER
            results["approver_assignments"][dept] = ("FALLBACK", None, FALLBACK_APPROVER)

        dept_to_approver[dept] = approver_user

    # Now update each employee's leave_approver
    employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "department", "leave_approver", "user_id"])

    for emp in employees:
        if not emp["department"]:
            results["skipped_no_dept"] += 1
            continue

        approver = dept_to_approver.get(emp["department"])
        if not approver:
            results["skipped_no_dept"] += 1
            continue

        # Don't set an employee as their own approver
        if approver == emp.get("user_id"):
            # Find next-best approver
            des_candidates = DEPT_HEAD_DESIGNATIONS.get(emp["department"], [])
            alt_user = None
            for des in des_candidates:
                alt = frappe.get_all("Employee",
                    filters={"status": "Active", "department": emp["department"],
                            "designation": des, "user_id": ("!=", emp.get("user_id") or "")},
                    fields=["user_id"], limit=1)
                if alt:
                    alt_user = alt[0]["user_id"]
                    break
            if alt_user:
                approver = alt_user
            else:
                approver = FALLBACK_APPROVER

        if not frappe.db.exists("User", approver):
            results["skipped_no_approver"] += 1
            continue

        try:
            doc = frappe.get_doc("Employee", emp["name"])
            doc.leave_approver = approver
            doc.save(ignore_permissions=True)
            results["updated"] += 1
            dept_key = emp["department"]
            results["by_dept"][dept_key] = results["by_dept"].get(dept_key, 0) + 1
        except Exception as e:
            results["errors"] += 1
            print(f"ERROR updating {emp['name']}: {str(e)[:200]}")
            try:
                frappe.db.rollback()
            except Exception:
                pass

    frappe.db.commit()
    print(f"\nResults:")
    print(f"  Updated: {results['updated']}")
    print(f"  Skipped (no dept): {results['skipped_no_dept']}")
    print(f"  Skipped (no approver User): {results['skipped_no_approver']}")
    print(f"  Errors: {results['errors']}")

    print(f"\nApprover assignments ({len(results['approver_assignments'])} depts):")
    for dept, (des, emp_name, user) in sorted(results['approver_assignments'].items()):
        print(f"  {dept} -> {user} ({des}, {emp_name or 'FALLBACK'})")

    # AFTER stats
    after = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_active,
            SUM(IF(IFNULL(leave_approver,'')!='', 1, 0)) AS with_approver,
            SUM(IF(leave_approver='Administrator', 1, 0)) AS approver_admin,
            SUM(IF(leave_approver != 'Administrator' AND IFNULL(leave_approver,'')!='', 1, 0)) AS approver_dept_heads
        FROM tabEmployee WHERE status='Active'
    """)[0]
    print(f"\nAfter: total_active={after[0]}, with_approver={after[1]}, approver_admin={after[2]}, approver_dept_heads={after[3]}")

    # Top approvers
    top_approvers = frappe.db.sql("""
        SELECT leave_approver, COUNT(*) AS cnt
        FROM tabEmployee WHERE status='Active' AND IFNULL(leave_approver,'')!=''
        GROUP BY leave_approver ORDER BY cnt DESC LIMIT 15
    """, as_dict=True)
    print(f"\nTop 15 leave_approvers:")
    for r in top_approvers:
        print(f"  {r['leave_approver']}: {r['cnt']}")


if __name__ == "__main__":
    run()