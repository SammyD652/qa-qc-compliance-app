"""
streamlit_app.py
This is the entry point for the QA/QC equipment compliance checker web
application. It provides a simple user interface to upload an equipment
nameplate image and a technical submittal PDF, runs the comparison logic and
presents the results to the QA/QC engineer. Results can be downloaded as an
Excel file and a plain-English summary is shown on screen.

To run locally:

    pip install -r requirements.txt
    streamlit run app/streamlit_app.py

Make sure Tesseract OCR is installed on your system and accessible in the
PATH. See documentation for installation instructions.
"""
from __future__ import annotations

import streamlit as st
import tempfile

from app.ocr import ocr_image, ocr_pdf, words_to_text
from app.extraction import parse_nameplate_text, parse_submittal_text
from app.comparison import compare_equipment
from app.reporting import results_to_dataframe, write_results_to_excel, generate_plain_english_summary



import os
import sys

# Remove local 'altair' stub directory from sys.path to ensure pip-installed altair is used
this_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(this_dir, '..'))
altair_stub_path = os.path.join(project_root, 'altair')
if altair_stub_path in sys.path:
    sys.path.remove(altair_stub_path)

def main():
    st.set_page_config(page_title="QA/QC Equipment Compliance Checker", layout="wide")
    st.title("🔨 QA/QC Equipment Compliance Checker")
    st.markdown(
        """
        Upload an equipment nameplate (image or scanned PDF) and the corresponding
        technical submittal (PDF). The app will extract key parameters from
        both sources, compare them intelligently and report compliance.
        """
    )

    # File uploaders
    nameplate_file = st.file_uploader(
        "Equipment Nameplate (Image or PDF)", type=["png", "jpg", "jpeg", "pdf"], key="nameplate"
    )
    submittal_file = st.file_uploader(
        "Technical Submittal (PDF)", type=["pdf"], key="submittal"
    )
    run_button = st.button("Run Compliance Check")

    if run_button:
        if not nameplate_file or not submittal_file:
            st.error("Please upload both a nameplate and a submittal to proceed.")
            return
        try:
            # Perform OCR on nameplate
            with st.spinner("Reading nameplate..."):
                np_bytes = nameplate_file.read()
                if nameplate_file.type == "application/pdf":
                    np_words = ocr_pdf(np_bytes)
                else:
                    np_words = ocr_image(np_bytes)
                np_text = words_to_text(np_words)
                np_data = parse_nameplate_text(np_text)

            # Perform OCR on submittal
            with st.spinner("Reading submittal..."):
                sub_bytes = submittal_file.read()
                sub_words = ocr_pdf(sub_bytes)
                sub_text = words_to_text(sub_words)
                sub_data = parse_submittal_text(sub_text)

            # Compare
            with st.spinner("Comparing data..."):
                results = compare_equipment(np_data, sub_data)
                df = results_to_dataframe(results)

            # Display table
            st.subheader("Compliance Table")
            st.dataframe(df, use_container_width=True)

            # Provide Excel download
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                write_results_to_excel(df, tmp.name)
                tmp.seek(0)
                st.download_button(
                    label="Download Excel Report",
                    data=tmp.read(),
                    file_name="compliance_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            # Display plain-English summary
            st.subheader("Summary")
            summary = generate_plain_english_summary(results)
            st.text(summary)

        except ImportError as exc:
            st.error(f"Missing dependency: {exc}. Please install the required packages.")
        except Exception as exc:
            st.error(f"An unexpected error occurred: {exc}")


if __name__ == "__main__":
    main()
