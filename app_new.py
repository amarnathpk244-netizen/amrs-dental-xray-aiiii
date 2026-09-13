        st.download_button(
            label="📥 Download Report as Text (.txt)",
            data=st.session_state.last_report,
            file_name=report_filename,
            mime="text/plain",
            use_container_width=True,
        )
        
        formatted_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AMRs Dental Report - {safe_patient_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; color: #333; line-height: 1.6; max-width: 800px; margin: auto; }}
                .header {{ border-bottom: 3px solid #1e3d59; padding-bottom: 15px; margin-bottom: 25px; }}
                h2 {{ color: #1e3d59; margin: 0 0 5px 0; }}
                .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; background: #f4f6f8; padding: 15px; border-radius: 8px; margin-bottom: 25px; gap: 10px; }}
                .meta-item {{ font-size: 14px; }}
                pre {{ white-space: pre-wrap; font-family: Arial, sans-serif; font-size: 14px; background: #fff; border: 1px solid #e1e4e8; padding: 20px; border-radius: 8px; }}
                @media print {{ body {{ padding: 0; }} }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>AMRs Dental X-ray AI</h2>
                <p style="margin: 0; color: #666; font-size: 13px;">AI-Assisted Dental Radiographic Assessment Report</p>
            </div>
            <div class="meta-grid">
                <div class="meta-item"><b>Patient Name:</b> {safe_patient_name}</div>
                <div class="meta-item"><b>OP Number:</b> {op_number if 'op_number' in locals() else 'N/A'}</div>
                <div class="meta-item"><b>Examination Date:</b> {examination_date}</div>
                <div class="meta-item"><b>Radiograph Type:</b> {radiograph_type}</div>
            </div>
            <pre>{st.session_state.last_report}</pre>
        </body>
        </html>
        """
        b64 = base64.b64encode(formatted_html.encode()).decode()
        href = f'<a href="data:text/html;base64,{b64}" download="Dental_Report_{safe_patient_name}.html" target="_blank" style="display: block; text-align: center; background: #17b978; color: white; padding: 12px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 15px;">🌐 Open Printable Web Report / Save as PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

