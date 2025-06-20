from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

@app.route('/api/compare-inv-bal', methods=['POST'])
def compare_inv_bal():
    # 1) grab the uploaded files & dropdown value
    conv_f = request.files.get('conv_file')
    eds_f  = request.files.get('eds_file')
    part_col = request.form.get('eds_part_col')

    if not conv_f or not eds_f or not part_col:
        return jsonify(message="Missing one of: conv_file, eds_file or eds_part_col"), 400

    try:
        # 2) read CSVs directly from the uploaded file‐streams
        conv_df = pd.read_csv(conv_f, encoding='windows-1252', skiprows=8, dtype=str)
        eds_df  = pd.read_csv(eds_f,  encoding='windows-1252', skiprows=8,  dtype=str)

        diffs = []
        for _, eds_row in eds_df.iterrows():
            eds_part = eds_row.get('ECL_PN')
            if not eds_part:
                continue

            match = conv_df[conv_df[part_col] == eds_part]
            if match.empty:
                continue

            conv_row = match.iloc[0]
            # extract the extra fields
            conv_ecl       = conv_row.get('ECL_PN')
            matched_val    = conv_row.get(part_col)
            conv_val_str  = conv_row.get('OH-TOTAL')
            eds_val_str   = eds_row.get('OH-TOTAL')

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

        return jsonify(differences=diffs)

    except Exception as ex:
        return jsonify(message=str(ex)), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
