from flask import request, jsonify
import pandas as pd
from io import StringIO

import logging

logger = logging.getLogger(__name__)

def register_routes(app):
    logger.info("✅ Routes registered from compare_invbal.py")
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inventory():
    try:
        eds_part_col = request.form.get('eds_part_col')
        conv_file = request.files['conv_file']
        eds_file = request.files['eds_file']
        
        logger.info(f"compare-inv-bal called with eds_part_col={eds_part_col}")
        logger.info(f"Received files: conv_file={conv_file.filename}, eds_file={eds_file.filename}")

        # Read both CSVs, skipping header rows and setting encoding
        conv_df = pd.read_csv(conv_file.stream, encoding='windows-1252', skiprows=8, dtype=str)
        eds_df = pd.read_csv(eds_file.stream, encoding='windows-1252', skiprows=8, dtype=str)

        # Clean part numbers
        conv_df['ECL_PN'] = conv_df['ECL_PN'].astype(str).str.strip()
        eds_df[eds_part_col] = eds_df[eds_part_col].astype(str).str.strip()

        # Merge on ECL_PN
        merged = pd.merge(
            conv_df, eds_df,
            how='outer',
            left_on='ECL_PN',
            right_on=eds_part_col,
            suffixes=('_conv', '_eds')
        )

        # Convert OH-TOTAL columns safely
        merged['OH-TOTAL_conv'] = pd.to_numeric(merged.get('OH-TOTAL_conv'), errors='coerce')
        merged['OH-TOTAL_eds'] = pd.to_numeric(merged.get('OH-TOTAL_eds'), errors='coerce')

        # Fill NaNs with 0
        merged.fillna({'OH-TOTAL_conv': 0, 'OH-TOTAL_eds': 0}, inplace=True)

        # Calculate difference
        merged['Difference'] = merged['OH-TOTAL_conv'] - merged['OH-TOTAL_eds']

        # Keep rows where difference is not 0
        differences = merged[merged['Difference'] != 0]

        # Select only useful fields
        result = differences[[
            'ECL_PN', eds_part_col, 'OH-TOTAL_conv', 'OH-TOTAL_eds', 'Difference'
        ]].rename(columns={
            'ECL_PN': 'conv_ecl',
            eds_part_col: 'matched_val',
            'OH-TOTAL_conv': 'conv_total',
            'OH-TOTAL_eds': 'eds_total',
            'Difference': 'diff'
        })

        return jsonify(differences=result.to_dict(orient='records'))

    except Exception as e:
        logger.exception("Error in compare_inventory")
        return jsonify({'message': str(e)}), 500

