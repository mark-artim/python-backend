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
            
            # Fill NaN values in display columns to prevent undefined values in output
            if display_col:
                if display_col in conv_df.columns:
                    conv_df[display_col] = conv_df[display_col].fillna('')
                if display_col in eds_df.columns:
                    eds_df[display_col] = eds_df[display_col].fillna('')

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
            
            # Add display column renaming if specified and different from value column
            if display_col and display_col != value_col:
                conv_rename[display_col] = 'conv_display'
                eds_rename[display_col] = 'eds_display'
            elif display_col == value_col:
                # When display and value are the same column, use the value columns as display too
                logger.info(f"Display column '{display_col}' is same as value column, using conv_val/eds_val for display")
            
            # Debug: check if required columns exist before renaming
            missing_conv_cols = [col for col in conv_cols if col not in conv_df.columns]
            missing_eds_cols = [col for col in eds_cols if col not in eds_df.columns]
            
            if missing_conv_cols:
                logger.error(f"Missing columns in CONV file: {missing_conv_cols}")
                logger.error(f"Available CONV columns: {list(conv_df.columns)}")
                return jsonify({'error': f'Missing columns in CONV file: {missing_conv_cols}'}), 400
                
            if missing_eds_cols:
                logger.error(f"Missing columns in EDS file: {missing_eds_cols}")
                logger.error(f"Available EDS columns: {list(eds_df.columns)}")
                return jsonify({'error': f'Missing columns in EDS file: {missing_eds_cols}'}), 400
            
            conv_df_renamed = conv_df[conv_cols].rename(columns=conv_rename)
            eds_df_renamed = eds_df[eds_cols].rename(columns=eds_rename)
            
            # Debug: check if renamed columns exist
            logger.info(f"Renamed CONV columns: {list(conv_df_renamed.columns)}")
            logger.info(f"Renamed EDS columns: {list(eds_df_renamed.columns)}")
            # 🔍 DEBUG: Check column names after renaming
            # print("Merging EDS ECL_PN with CONV", part_col)

            # eds_sample = sorted(eds_df['ECL_PN'].dropna().astype(str).unique())[:20]
            # conv_sample = sorted(conv_df[part_col].dropna().astype(str).unique())[:20]

            # print("Sample sorted EDS['ECL_PN'] values:", eds_sample)
            # print(f"Sample sorted CONV['{part_col}'] values:", conv_sample)

            # Merge on part number from conv and eds
            merged = pd.merge(eds_df_renamed, conv_df_renamed, left_on='eds_ecl', right_on='matched_val', how='inner')
            
            # Debug: check what columns exist after merge
            logger.info(f"Merged dataframe columns: {list(merged.columns)}")
            logger.info(f"Looking for conv_val and eds_val columns...")
            
            if 'conv_val' not in merged.columns:
                logger.error("conv_val column missing from merged dataframe!")
                logger.error(f"Available columns: {list(merged.columns)}")
                return jsonify({'error': 'conv_val column missing after merge operation'}), 500
                
            if 'eds_val' not in merged.columns:
                logger.error("eds_val column missing from merged dataframe!")
                logger.error(f"Available columns: {list(merged.columns)}")
                return jsonify({'error': 'eds_val column missing after merge operation'}), 500

            def safe_float(val):
                """Convert value to float if numeric, return None if not convertible"""
                if pd.isna(val) or val is None or str(val).strip() == '':
                    return None
                try:
                    return float(str(val).strip())
                except (ValueError, TypeError):
                    return None

            def is_numeric_value(val):
                """Check if a value can be treated as numeric"""
                if pd.isna(val) or val is None or str(val).strip() == '':
                    return False
                try:
                    float(str(val).strip())
                    return True
                except (ValueError, TypeError):
                    return False

            # Convert to numeric where possible
            merged['conv_val_f'] = merged['conv_val'].apply(safe_float)
            merged['eds_val_f']  = merged['eds_val'].apply(safe_float)
            
            # Check if values are numeric or string
            merged['conv_is_numeric'] = merged['conv_val'].apply(is_numeric_value)
            merged['eds_is_numeric'] = merged['eds_val'].apply(is_numeric_value)
            
            # Calculate differences for different data types
            def calculate_difference(row):
                conv_val = row['conv_val']
                eds_val = row['eds_val']
                conv_numeric = row['conv_val_f']
                eds_numeric = row['eds_val_f']
                conv_is_num = row['conv_is_numeric']
                eds_is_num = row['eds_is_numeric']
                
                # Handle empty/null values
                if pd.isna(conv_val) or pd.isna(eds_val) or conv_val is None or eds_val is None:
                    return 1 if conv_val != eds_val else 0
                
                # Both are numeric - calculate numeric difference
                if conv_is_num and eds_is_num and conv_numeric is not None and eds_numeric is not None:
                    numeric_diff = conv_numeric - eds_numeric
                    logger.debug(f"Numeric comparison: {conv_val} ({conv_numeric}) - {eds_val} ({eds_numeric}) = {numeric_diff}")
                    return numeric_diff
                
                # Both are strings - compare as strings
                elif not conv_is_num and not eds_is_num:
                    conv_str = str(conv_val).strip()
                    eds_str = str(eds_val).strip()
                    string_diff = 0 if conv_str == eds_str else 1
                    logger.debug(f"String comparison: '{conv_str}' vs '{eds_str}' = {string_diff}")
                    return string_diff
                
                # Mixed types (numeric vs string) - always different
                else:
                    logger.debug(f"Mixed type comparison: {conv_val} (numeric: {conv_is_num}) vs {eds_val} (numeric: {eds_is_num}) = 1")
                    return 1
            
            merged['diff'] = merged.apply(calculate_difference, axis=1)
            
            # Find mismatches: numeric differences != 0, or string differences = 1
            mismatches = merged[merged['diff'] != 0]

            # Debug: check what columns exist in the mismatches dataframe
            logger.info(f"Mismatches dataframe columns: {list(mismatches.columns)}")
            
            # Prepare output columns based on what actually exists in the dataframe
            available_cols = list(mismatches.columns)
            output_cols = []
            
            # Add standard columns if they exist
            for col in ['eds_ecl', 'conv_ecl', 'matched_val', 'conv_val', 'eds_val', 'diff']:
                if col in available_cols:
                    output_cols.append(col)
                else:
                    logger.warning(f"Column '{col}' not found in mismatches dataframe")
            
            # Add display columns if they exist
            if display_col:
                if display_col == value_col:
                    # Display and value are the same - no separate display columns needed
                    logger.info("Display column same as value column - using conv_val/eds_val for display")
                else:
                    # Add separate display columns
                    for col in ['conv_display', 'eds_display']:
                        if col in available_cols:
                            output_cols.append(col)
                        else:
                            logger.warning(f"Display column '{col}' not found in mismatches dataframe")
            
            logger.info(f"Using output columns: {output_cols}")
            
            # Replace NaN values before converting to dict
            differences = mismatches[output_cols].to_dict(orient='records')
            # Clean up NaN values in the resulting dictionaries
            for record in differences:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
            
            # Also prepare all items (matched + mismatched) for the "Show Items" feature
            all_items = merged[output_cols].to_dict(orient='records')
            for record in all_items:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                # Add unique ID for data table
                record['id'] = f"{record.get('eds_ecl', '')}-{record.get('conv_ecl', '')}"
            
            matched_count = len(merged)
            shared_columns = list(set(conv_df.columns) & set(eds_df.columns))

            return jsonify(
                differences=differences, 
                all_items=all_items,
                matched_row_count=matched_count, 
                unmatched_count=len(differences),
                shared_columns=shared_columns
            )

        except Exception as ex:
            logger.exception("[compare_inv_bal] Unexpected error")
            if matched_count:
                logger.error(
                    f"[compare_inv_bal] {len(differences)} differences found out of {matched_count} matches"
                )
            return jsonify(message=str(ex)), 500
