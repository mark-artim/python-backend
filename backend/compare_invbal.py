from flask import request, jsonify
import pandas as pd
from io import StringIO

import logging

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/api/compare-inv-bal', methods=['POST'])
    def compare_inventory():
        try:
            eds_part_col = request.form.get('eds_part_col')
            conv_file = request.files['conv_file']
            eds_file = request.files['eds_file']
            
            logger.info(f"compare-inv-bal called with eds_part_col={eds_part_col}")
            logger.info(f"Received files: conv_file={conv_file.filename}, eds_file={eds_file.filename}")

            conv_df = pd.read_csv(conv_file.stream, skiprows=8)
            eds_df = pd.read_csv(eds_file.stream, skiprows=8)

            conv_df['ECL_PN'] = conv_df['ECL_PN'].astype(str).str.strip()
            eds_df['ECL_PN'] = eds_df[eds_part_col].astype(str).str.strip()

            merged = pd.merge(conv_df, eds_df, how='outer', left_on='ECL_PN', right_on=eds_part_col, suffixes=('_conv', '_eds'))
            merged['Difference'] = merged['OH-TOTAL_conv'].fillna(0) - merged['OH-TOTAL_eds'].fillna(0)

            differences = merged[merged['Difference'] != 0].to_dict(orient='records')

            return jsonify(differences=differences)

        except Exception as e:
            return jsonify({'message': str(e)}), 500
