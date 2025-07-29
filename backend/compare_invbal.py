from flask import request, jsonify
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inv_bal():
        conv_f = request.files.get('conv_file')
        eds_f  = request.files.get('eds_file')
        part_col = request.form.get('eds_part_col')
        value_col = request.form.get('value_col')

        if not conv_f or not eds_f or not part_col or not value_col:
            return jsonify(message="Missing one of: conv_file, eds_file, eds_part_col, value_col"), 400

        differences = []  # initialize for error handling
        matched_count = 0

        try:
            conv_df = pd.read_csv(conv_f, encoding='windows-1252', skiprows=8, dtype=str)
            eds_df  = pd.read_csv(eds_f, encoding='windows-1252', skiprows=8, dtype=str)

            if part_col not in conv_df.columns:
                return jsonify(message=f"Part column '{part_col}' not found in CONV file."), 400

            if value_col not in conv_df.columns or value_col not in eds_df.columns:
                return jsonify(message=f"Comparison column '{value_col}' not found in both files."), 400

            # Extract and rename columns correctly
            conv_df_renamed = conv_df[[part_col, 'ECL_PN', value_col]].rename(columns={
                part_col: 'matched_val',          # <- this should become ESE.PN if selected
                'ECL_PN': 'conv_ecl',
                value_col: 'conv_val'
            })
            eds_df_renamed = eds_df[['ECL_PN', value_col]].rename(columns={
                'ECL_PN': 'eds_ecl',
                value_col: 'eds_val'
            })
            # 🔍 DEBUG: Check column names after renaming
            # print("Merging EDS ECL_PN with CONV", part_col)

            # eds_sample = sorted(eds_df['ECL_PN'].dropna().astype(str).unique())[:20]
            # conv_sample = sorted(conv_df[part_col].dropna().astype(str).unique())[:20]

            # print("Sample sorted EDS['ECL_PN'] values:", eds_sample)
            # print(f"Sample sorted CONV['{part_col}'] values:", conv_sample)

            # Merge on part number from conv and eds
            merged = pd.merge(eds_df_renamed, conv_df_renamed, left_on='eds_ecl', right_on='matched_val', how='inner')

            def safe_float(val):
                try:
                    return float(val)
                except:
                    return None

            merged['conv_val_f'] = merged['conv_val'].apply(safe_float)
            merged['eds_val_f']  = merged['eds_val'].apply(safe_float)
            merged['diff'] = merged['conv_val_f'] - merged['eds_val_f']

            mismatches = merged[(merged['conv_val_f'].notnull()) & (merged['eds_val_f'].notnull()) & (merged['diff'] != 0)]

            differences = mismatches[['eds_ecl', 'conv_ecl', 'matched_val', 'conv_val', 'eds_val', 'diff']].to_dict(orient='records')
            matched_count = len(merged)

            shared_columns = list(set(conv_df.columns) & set(eds_df.columns))

            return jsonify(differences=differences, matched_row_count=matched_count, shared_columns=shared_columns)

        except Exception as ex:
            logger.exception("[compare_inv_bal] Unexpected error")
            if matched_count:
                logger.error(
                    f"[compare_inv_bal] {len(differences)} differences found out of {matched_count} matches"
                )
            return jsonify(message=str(ex)), 500
