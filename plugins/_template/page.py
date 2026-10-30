"""Sample page: notes per top-up package — shows how to use sdk (data, shared IDs, history, the platform's shared data).
Copy the _template folder to plugins/<id>/ and replace this with your own business logic."""
import streamlit as st

from core import sdk

sdk.header(sdk.t("Package notes"), sdk.t("Sample plugin — how to save and read data through sdk"))

master = sdk.master()  # current master file of the selected game (None if not uploaded yet)
notes = sdk.load("notes")  # records of the selected game, most recently changed first

if sdk.can_edit():
    with st.form(sdk.key("add"), clear_on_submit=True):
        product_key = st.text_input(sdk.t("Product Key"), placeholder="web.item195", key=sdk.key("product_key"))
        text = st.text_area(sdk.t("Note"), key=sdk.key("text"))
        if st.form_submit_button(sdk.t("💾 Save note"), type="primary"):
            if not product_key.strip() or not text.strip():
                st.error(sdk.t("Product Key and text are required."))
            else:
                now = sdk.now()  # Vietnam time
                pk = sdk.product_key(product_key)  # shared ID, normalised like the master: web.item195
                sdk.save("notes", {
                    "id": f"{pk}-{now:%Y%m%d%H%M%S}",  # stable record key
                    "product_key": pk,
                    "note": text.strip(),
                    "date": f"{now:%Y-%m-%d}",
                })
                st.rerun()

if not notes:
    st.caption(sdk.t("No notes yet."))
else:
    st.dataframe([{
        sdk.t("Product Key"): n["product_key"],
        sdk.t("Package name (master)"): master.display_name(n["product_key"]) if master else "",
        sdk.t("Note"): n["note"],
        sdk.t("Edited by"): n["_updated_by"],
        sdk.t("At"): n["_updated_at"],
    } for n in notes], hide_index=True)
    picked = st.selectbox(sdk.t("Pick a note"), [n["_key"] for n in notes], key=sdk.key("picked"))
    with st.expander(sdk.t("Edit / delete history of this note")):
        for old in sdk.history("notes", picked):
            st.write(f"{old['changed_at']} · {old['changed_by']} · {old['action']}: {old['data'].get('note', '')}")
    if sdk.can_edit():
        c1, c2 = st.columns(2)
        if c1.button(sdk.t("🗑 Delete note"), key=sdk.key("delete")):
            sdk.delete("notes", picked)
            st.rerun()
        if c2.button(sdk.t("📌 Log to team history"), key=sdk.key("record")):
            aid = sdk.record(sdk.t("Summary of {n} notes", n=len(notes)), {"metrics": {"Notes": len(notes)}})
            st.success(sdk.t("Logged as #{aid} in Activity history.", aid=aid))
