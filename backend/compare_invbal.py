from flask import request, jsonify
import pandas as pd
import logging
print("[DEBUG] pd type:", type(pd))
print("[DEBUG] pd repr:", repr(pd))
print("[DEBUG] dir(pd):", dir(pd)[:10])
# print("[DEBUG] pandas location:", pd.__file__)
# print("[DEBUG] pandas version:", pd.__version__)
# print("[DEBUG] pandas dir:", dir(pd)[:10])

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inv_bal():
        conv_f = request.files.get('conv_file')
        eds_f  = request.files.get('eds_file')
        part_col = request.form.get('eds_part_col')
        value_col = request.form.get('value_col')
        display_col = request.form.get('display_col')  # Optional display column parameter

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

            # Validate display column if provided
            if display_col and (display_col not in conv_df.columns or display_col not in eds_df.columns):
                return jsonify(message=f"Display column '{display_col}' not found in both files."), 400

            # Extract and rename columns correctly
            conv_cols = [part_col, 'ECL_PN', value_col]
            eds_cols = ['ECL_PN', value_col]
            
            # Add display column if specified
            if display_col:
                conv_cols.append(display_col)
                eds_cols.append(display_col)
            
            # Build rename dictionaries
            conv_rename = {
                part_col: 'matched_val',          # <- this should become ESE.PN if selected
                'ECL_PN': 'conv_ecl',
                value_col: 'conv_val'
            }
            eds_rename = {
                'ECL_PN': 'eds_ecl',
                value_col: 'eds_val'
            }
            
            # Add display column renaming if specified
            if display_col:
                conv_rename[display_col] = 'conv_display'
                eds_rename[display_col] = 'eds_display'
            
            conv_df_renamed = conv_df[conv_cols].rename(columns=conv_rename)
            eds_df_renamed = eds_df[eds_cols].rename(columns=eds_rename)
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

            # Prepare output columns based on whether display column is included
            output_cols = ['eds_ecl', 'conv_ecl', 'matched_val', 'conv_val', 'eds_val', 'diff']
            if display_col and 'conv_display' in mismatches.columns and 'eds_display' in mismatches.columns:
                output_cols.extend(['conv_display', 'eds_display'])
            
            differences = mismatches[output_cols].to_dict(orient='records')
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
