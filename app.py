import streamlit as st
import streamlit.components.v1 as components
import re

# Set page config with blue accents and white bg
st.set_page_config(page_title="💸 Debt Settlement Calculator", page_icon="💸", layout="centered")

# Custom CSS for white background and blue accents
st.markdown("""
<style>
    /* Page background */
    .main {
        background-color: white;
        color: #0B3D91;
    }
    /* Button blue background */
    div.stButton > button {
        background-color: #0B3D91;
        color: white;
        border-radius: 6px;
        border: 1px solid #0B3D91;
    }
    div.stButton > button:hover {
        background-color: #09407d;
        border-color: #09407d;
    }
    textarea[disabled] {
    background-color: black !important;
    color: white !important;
    font-family: monospace !important;
}
</style>
""", unsafe_allow_html=True)

st.title("💸 Debt Settlement Calculator")

# Initialize session state defaults
if "step" not in st.session_state:
    st.session_state.step = "input"
if "combined_names" not in st.session_state:
    st.session_state.combined_names = {}
if "nets" not in st.session_state:
    st.session_state.nets = {}
if "merged_nets" not in st.session_state:
    st.session_state.merged_nets = {}
if "raw_input" not in st.session_state:
    st.session_state.raw_input = ""
if "selected_for_combine" not in st.session_state:
    st.session_state.selected_for_combine = {}

def parse_flexible_net_blocks(raw_text):
    lines = raw_text.strip().splitlines()
    name_net_map = {}
    current_name = None
    for line in lines:
        line = line.strip()
        if '@' in line:
            current_name = line.split('@')[0].strip()
        elif current_name and re.search(r'[-+]\d+(\.\d+)?', line):
            match = re.search(r'[-+]\d+(\.\d+)?', line)
            if match:
                net = float(match.group())
                name_net_map[current_name] = name_net_map.get(current_name, 0) + round(net)
                current_name = None
    return name_net_map

def merge_names(name_net_map, combined_names):
    merged = {}
    for name, amount in name_net_map.items():
        final_name = name
        for combined_name, originals in combined_names.items():
            if name in originals:
                final_name = combined_name
                break
        merged[final_name] = merged.get(final_name, 0) + amount
    return merged

# Step 1: Input data
if st.session_state.step == "input":
    raw_input = st.text_area("Paste your player data below:", height=250, value=st.session_state.raw_input)
    if st.button("Calculate Ledger"):
        if not raw_input.strip():
            st.warning("Please enter some data!")
        else:
            st.session_state.raw_input = raw_input
            st.session_state.nets = parse_flexible_net_blocks(raw_input)
            st.session_state.step = "duplicates"

# Step 2: Duplicate check & combine names
elif st.session_state.step == "duplicates":
    merged = merge_names(st.session_state.nets, st.session_state.combined_names)
    names = sorted([name for name, amt in merged.items() if amt != 0])

    st.subheader("Select names to combine:")

    # Initialize or update checkbox states if names changed
    if set(st.session_state.selected_for_combine.keys()) != set(names):
        st.session_state.selected_for_combine = {name: False for name in names}

    # Display checkboxes for all names
    for name in names:
        checked = st.checkbox(name, value=st.session_state.selected_for_combine[name])
        st.session_state.selected_for_combine[name] = checked

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Combine Selected Names"):
            selected_names = [n for n, checked in st.session_state.selected_for_combine.items() if checked]
            if len(selected_names) < 2:
                st.warning("Please select at least two names to combine")
            else:
                combined_name = selected_names[0]
                if combined_name in st.session_state.combined_names:
                    existing = set(st.session_state.combined_names[combined_name])
                    new_names = [n for n in selected_names if n not in existing]
                    st.session_state.combined_names[combined_name].extend(new_names)
                else:
                    st.session_state.combined_names[combined_name] = selected_names

                # Reset checkboxes (uncheck all)
                st.session_state.selected_for_combine = {name: False for name in names}

                # Show success message
                combined_str = " and ".join(selected_names)
                st.success(f"✅ Combined: {combined_str}")

                # Update merged nets immediately for UI consistency
                merged = merge_names(st.session_state.nets, st.session_state.combined_names)
                st.session_state.merged_nets = {k: v for k, v in merged.items() if v != 0}

    with col2:
        if st.button("Skip Combining"):
            st.session_state.merged_nets = {k: v for k, v in merged.items() if v != 0}
            st.session_state.step = "results"
            st.session_state.selected_for_combine = {}

# Step 3: Show results
elif st.session_state.step == "results":
    nets = st.session_state.merged_nets

    creditors = sorted([(n, v) for n, v in nets.items() if v > 0], key=lambda x: -x[1])
    debtors = sorted([(n, -v) for n, v in nets.items() if v < 0], key=lambda x: -x[1])

    transactions = []
    creditor_idx = 0
    debtor_idx = 0
    total_transferred = 0

    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor_name, debtor_amt = debtors[debtor_idx]
        creditor_name, creditor_amt = creditors[creditor_idx]

        pay_amt = min(debtor_amt, creditor_amt)
        transactions.append(f"{debtor_name} owes {creditor_name} ${int(pay_amt)}")
        total_transferred += pay_amt

        debtors[debtor_idx] = (debtor_name, debtor_amt - pay_amt)
        creditors[creditor_idx] = (creditor_name, creditor_amt - pay_amt)

        if debtors[debtor_idx][1] == 0:
            debtor_idx += 1
        if creditors[creditor_idx][1] == 0:
            creditor_idx += 1

    st.subheader("Settlement Results")

    # Format results into a single string with line breaks
    result_text = "\n".join(transactions)

    # Display result text area
    st.text_area("Results (copy below):", value=result_text, height=200, disabled=True)

    # Escape backticks so JS string won't break
    escaped_text = result_text.replace("`", "\\`")

    # Copy to clipboard button using Streamlit components
    components.html(f"""
    <button
        onclick="
            navigator.clipboard.writeText(`{escaped_text}`)
            .then(() => alert('Copied to clipboard!'));
        "
        style="
            background-color: #0B3D91;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            cursor: pointer;
            margin-top: 10px;
        "
    >
        📋 Copy to Clipboard
    </button>
    """, height=60)

    st.caption(f"Total transferred: ${int(total_transferred)}")

    if st.button("Start Over"):
        for key in ["step", "combined_names", "nets", "merged_nets", "raw_input", "selected_for_combine"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()