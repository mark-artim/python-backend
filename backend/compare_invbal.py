from flask import request, jsonify
import pandas as pd
from io import StringIO
import traceback
import logging

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inv_bal():
        # ✅ Log incoming request metadata
        logger.info("[compare_inv_bal] POST hit")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Form keys: {request.form.keys()}")
        logger.info(f"Files: {request.files.keys()}")

        conv_f = request.files.get('conv_file')
        eds_f  = request.files.get('eds_file')
        part_col = request.form.get('eds_part_col')

        # ✅ Log presence of expected inputs
        logger.info(f"[compare_inv_bal] conv_file: {bool(conv_f)}, eds_file: {bool(eds_f)}, part_col: {part_col}")

        if not conv_f or not eds_f or not part_col:
            logger.warning("[compare_inv_bal] Missing input")
            return jsonify(message="Missing one of: conv_file, eds_file or eds_part_col"), 400

        try:
            # ✅ Optional: validate file type
            if not conv_f.filename.endswith('.csv') or not eds_f.filename.endswith('.csv'):
                logger.warning("[compare_inv_bal] One or more files are not CSVs")
                return jsonify(message="Only .csv files are supported"), 400

            # ✅ Parse CSV files
            conv_df = pd.read_csv(conv_f, encoding='windows-1252', skiprows=8, dtype=str)
            eds_df  = pd.read_csv(eds_f, encoding='windows-1252', skiprows=8, dtype=str)

            diffs = []
            for _, eds_row in eds_df.iterrows():
                eds_part = eds_row.get('ECL_PN')
                if not eds_part:
                    continue

                match = conv_df[conv_df[part_col] == eds_part]
                if match.empty:
                    continue

                conv_row = match.iloc[0]
                conv_ecl     = conv_row.get('ECL_PN')
                matched_val  = conv_row.get(part_col)
                conv_val_str = conv_row.get('OH-TOTAL')
                eds_val_str  = eds_row.get('OH-TOTAL')

                try:
                    c = float(conv_val_str)
                    e = float(eds_val_str)
                except (ValueError, TypeError):
                    continue

                if c != e:
                    diffs.append({
                        'eds_ecl':     eds_part,
                        'conv_ecl':    conv_ecl,
                        'matched_val': matched_val,
                        'conv_total':  c,
                        'eds_total':   e,
                        'diff':        c - e
                    })

            logger.info(f"[compare_inv_bal] Returning {len(diffs)} differences")
            return jsonify(differences=diffs)

        except Exception as ex:
            logger.error("[compare_inv_bal] Exception occurred", exc_info=True)
            return jsonify(message="Internal server error", detail=str(ex)), 500
