from flask import request, jsonify
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inv_bal():
        conv_f = request.files.get('conv_file')
        eds_f = request.files.get('eds_file')
        part_col = request.form.get('eds_part_col')
        value_col = request.form.get('value_col')

        if not conv_f or not eds_f or not part_col or not value_col:
            return jsonify(message="Missing one of: conv_file, eds_file, eds_part_col or value_col"), 400

        try:
            conv_df = pd.read_csv(conv_f, encoding='windows-1252', skiprows=8, dtype=str)
            eds_df = pd.read_csv(eds_f, encoding='windows-1252', skiprows=8, dtype=str)

            conv_headers = conv_df.columns.str.strip().tolist()
            eds_headers = eds_df.columns.str.strip().tolist()
            shared_columns = sorted(list(set(conv_headers) & set(eds_headers)))

            # Validate necessary columns
            if part_col not in conv_headers:
                return jsonify(message=f"Part column '{part_col}' not found in CONV file."), 400
            if 'ECL_PN' not in eds_headers:
                return jsonify(message="ECL_PN must be present in the EDS file."), 400
            if value_col not in conv_headers or value_col not in eds_headers:
                return jsonify(message=f"Comparison column '{value_col}' not found in both files."), 400

            diffs = []
            match_count = 0

            for _, eds_row in eds_df.iterrows():
                eds_part = eds_row.get('ECL_PN')
                if not eds_part:
                    continue

                match = conv_df[conv_df[part_col] == eds_part]
                if match.empty:
                    continue

                conv_row = match.iloc[0]
                conv_val_str = conv_row.get(value_col)
                eds_val_str = eds_row.get(value_col)

                try:
                    c = float(conv_val_str)
                    e = float(eds_val_str)
                    match_count += 1
                    if c != e:
                        diffs.append({
                            'eds_ecl': eds_part,
                            'conv_ecl': conv_row.get('ECL_PN'),
                            'matched_val': conv_row.get(part_col),
                            'conv_total': c,
                            'eds_total': e,
                            'diff': c - e
                        })
                except (ValueError, TypeError):
                    continue

            return jsonify(
                differences=diffs,
                matched_row_count=match_count,
                unmatched_count=len(diffs),
                shared_columns=shared_columns
            )

        except Exception as ex:
            logger.exception("Error in compare_inv_bal")
            return jsonify(message=str(ex)), 500
