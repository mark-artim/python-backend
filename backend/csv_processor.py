from flask import request, jsonify
import pandas as pd
import logging
import io

logger = logging.getLogger(__name__)

def register_csv_routes(app):
    
    @app.route('/api/csv/preview', methods=['POST'])
    def preview_csv_file():
        """
        Upload CSV file and return preview with pagination support
        Allows user to navigate through entire file
        """
        try:
            file = request.files.get('file')
            skiprows = int(request.form.get('skiprows', 0))
            page = int(request.form.get('page', 1))
            rows_per_page = int(request.form.get('rowsPerPage', 20))
            
            if not file:
                return jsonify({"error": "No file provided"}), 400
            
            # First, get headers and total info
            file.seek(0)  # Reset file pointer
            total_lines = sum(1 for line in file)
            data_rows_count = total_lines - skiprows - 1  # -1 for header row
            total_pages = max(1, (data_rows_count + rows_per_page - 1) // rows_per_page)
            
            # Get headers from the first data row (after skiprows)
            file.seek(0)
            header_df = pd.read_csv(file, 
                                  encoding='windows-1252', 
                                  skiprows=skiprows, 
                                  nrows=1,
                                  dtype=str)
            headers = header_df.columns.tolist()
            
            # Calculate offset for pagination (after the header row)
            offset = (page - 1) * rows_per_page
            
            # Read specific chunk of data for pagination
            # Skip the header rows + offset rows, but don't include header in nrows count
            file.seek(0)
            df = pd.read_csv(file, 
                           encoding='windows-1252', 
                           skiprows=skiprows + 1 + offset,  # +1 to skip the header row
                           nrows=rows_per_page,
                           header=None,  # Don't treat first row as header
                           dtype=str)
            
            # Set the correct column names
            if len(df.columns) == len(headers):
                df.columns = headers
            
            # Fill NaN values for JSON serialization
            df = df.fillna('')
            
            preview_data = {
                "headers": headers,
                "sample_rows": df.to_dict('records'),
                "total_lines": total_lines,
                "data_rows_count": data_rows_count,
                "skiprows_used": skiprows,
                "current_page": page,
                "total_pages": total_pages,
                "rows_per_page": rows_per_page,
                "showing_rows": len(df)
            }
            
            logger.info(f"CSV preview generated: page {page}/{total_pages}, {len(df)} rows, {len(df.columns)} columns")
            return jsonify(preview_data)
            
        except Exception as e:
            logger.error(f"CSV preview error: {str(e)}")
            return jsonify({"error": f"Failed to preview file: {str(e)}"}), 500
    
    @app.route('/api/csv/process-preview', methods=['POST'])
    def process_preview():
        """
        Apply processing options and return preview of processed data
        Shows user what final result will look like
        """
        try:
            file = request.files.get('file')
            
            # Get form data for processing options
            skiprows = int(request.form.get('skiprows', 0))
            remove_commas = request.form.get('removeCommas') == 'true'
            remove_dollar_signs = request.form.get('removeDollarSigns') == 'true'
            uppercase_text = request.form.get('uppercaseText') == 'true'
            uppercase_column = request.form.get('uppercaseColumn')
            format_upc = request.form.get('formatUPC') == 'true'
            upc_column = request.form.get('upcColumn')
            
            # Handle multiple search/replace operations
            search_replace_operations = []
            try:
                import json
                search_replace_data = request.form.get('searchReplaceOperations', '[]')
                logger.info(f"Raw search/replace data: {search_replace_data}")
                search_replace_operations = json.loads(search_replace_data) if search_replace_data else []
                logger.info(f"Parsed search/replace operations: {search_replace_operations}")
            except Exception as e:
                logger.error(f"Error parsing search/replace operations: {e}")
                # Fallback to single operation for backward compatibility
                if request.form.get('searchReplace') == 'true':
                    search_replace_operations = [{
                        'column': request.form.get('searchColumn'),
                        'searchText': request.form.get('searchText', ''),
                        'replaceText': request.form.get('replaceText', '')
                    }]
            
            if not file:
                return jsonify({"error": "No file provided"}), 400
            
            # Read file with specified options (first 50 rows for preview)
            df = pd.read_csv(file, 
                           encoding='windows-1252', 
                           skiprows=skiprows,
                           nrows=50,
                           dtype=str)
            
            df = df.fillna('')
            
            # Apply processing options
            processed_df = apply_processing_options(
                df, remove_commas, remove_dollar_signs, uppercase_text, 
                uppercase_column, format_upc, upc_column, search_replace_operations
            )
            
            # Create processing summary
            summary = []
            if remove_commas:
                summary.append("✂️ Remove commas from all fields")
            if remove_dollar_signs:
                summary.append("💲 Remove dollar signs from all fields")
            if uppercase_text and uppercase_column:
                summary.append(f"🔤 Uppercase text in '{uppercase_column}' column")
            if format_upc and upc_column:
                summary.append(f"📊 Format '{upc_column}' as 11-digit UPC code")
            for operation in search_replace_operations:
                if operation.get('column') and operation.get('searchText'):
                    summary.append(f"🔄 Replace '{operation['searchText']}' → '{operation.get('replaceText', '')}' in '{operation['column']}'")
            
            preview_data = {
                "headers": processed_df.columns.tolist(),
                "sample_rows": processed_df.to_dict('records'),
                "row_count": len(processed_df),
                "processing_summary": summary if summary else ["No processing options selected"]
            }
            
            return jsonify(preview_data)
            
        except Exception as e:
            logger.error(f"Process preview error: {str(e)}")
            return jsonify({"error": f"Failed to process preview: {str(e)}"}), 500
    
    @app.route('/api/csv/download-processed', methods=['POST'])
    def download_processed():
        """
        Process full CSV file and return CSV content for download
        """
        try:
            file = request.files.get('file')
            output_filename = request.form.get('outputFilename', 'processed_file')
            
            # Get processing options
            skiprows = int(request.form.get('skiprows', 0))
            remove_commas = request.form.get('removeCommas') == 'true'
            remove_dollar_signs = request.form.get('removeDollarSigns') == 'true'
            uppercase_text = request.form.get('uppercaseText') == 'true'
            uppercase_column = request.form.get('uppercaseColumn')
            format_upc = request.form.get('formatUPC') == 'true'
            upc_column = request.form.get('upcColumn')
            
            # Handle multiple search/replace operations
            search_replace_operations = []
            try:
                import json
                search_replace_data = request.form.get('searchReplaceOperations', '[]')
                logger.info(f"Raw search/replace data: {search_replace_data}")
                search_replace_operations = json.loads(search_replace_data) if search_replace_data else []
                logger.info(f"Parsed search/replace operations: {search_replace_operations}")
            except Exception as e:
                logger.error(f"Error parsing search/replace operations: {e}")
                # Fallback to single operation for backward compatibility
                if request.form.get('searchReplace') == 'true':
                    search_replace_operations = [{
                        'column': request.form.get('searchColumn'),
                        'searchText': request.form.get('searchText', ''),
                        'replaceText': request.form.get('replaceText', '')
                    }]
            
            if not file:
                return jsonify({"error": "No file provided"}), 400
            
            logger.info(f"Processing full CSV file with {skiprows} skiprows")
            
            # Read full file
            df = pd.read_csv(file, 
                           encoding='windows-1252', 
                           skiprows=skiprows,
                           dtype=str)
            
            df = df.fillna('')
            original_row_count = len(df)
            
            # Apply processing options
            processed_df = apply_processing_options(
                df, remove_commas, remove_dollar_signs, uppercase_text, 
                uppercase_column, format_upc, upc_column, search_replace_operations
            )
            
            # Create CSV content
            csv_content = processed_df.to_csv(index=False, encoding='windows-1252')
            
            logger.info(f"CSV processing complete: {original_row_count} → {len(processed_df)} rows")
            
            # Return CSV content for download
            return jsonify({
                "csv_content": csv_content,
                "filename": f"{output_filename}.csv",
                "original_rows": original_row_count,
                "processed_rows": len(processed_df),
                "success": True
            })
            
        except Exception as e:
            logger.error(f"Download processed error: {str(e)}")
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500

def apply_processing_options(df, remove_commas, remove_dollar_signs, uppercase_text, 
                           uppercase_column, format_upc, upc_column, search_replace_operations):
    """Apply all processing options to dataframe"""
    processed_df = df.copy()
    
    # 1. Remove commas from all fields
    if remove_commas:
        for col in processed_df.columns:
            processed_df[col] = processed_df[col].astype(str).str.replace(',', '')
    
    # 2. Remove dollar signs from all fields  
    if remove_dollar_signs:
        for col in processed_df.columns:
            processed_df[col] = processed_df[col].astype(str).str.replace('$', '')
    
    # 3. Uppercase text in selected column
    if uppercase_text and uppercase_column and uppercase_column in processed_df.columns:
        processed_df[uppercase_column] = processed_df[uppercase_column].astype(str).str.upper()
    
    # 4. Format UPC code
    if format_upc and upc_column and upc_column in processed_df.columns:
        processed_df[upc_column] = processed_df[upc_column].apply(format_upc_code)
    
    # 5. Multiple Search and replace operations
    for operation in search_replace_operations:
        column = operation.get('column')
        search_text = operation.get('searchText', '')
        replace_text = operation.get('replaceText', '')
        
        if column and column in processed_df.columns and search_text:
            processed_df[column] = processed_df[column].astype(str).str.replace(
                search_text, replace_text, regex=False
            )
    
    return processed_df

def format_upc_code(value):
    """Format value as 11-digit UPC code"""
    if pd.isna(value) or value == '' or value == 'nan':
        return ''
    
    # Remove all non-numeric characters
    numeric_only = ''.join(filter(str.isdigit, str(value)))
    
    if len(numeric_only) == 0:
        return ''
    
    # If 12 digits, remove last character to make it 11
    if len(numeric_only) == 12:
        return numeric_only[:11]
    
    # If less than 11 digits, pad with leading zeros
    if len(numeric_only) < 11:
        return numeric_only.zfill(11)
    
    # If exactly 11 digits, return as is
    if len(numeric_only) == 11:
        return numeric_only
    
    # If more than 12 digits, take first 11
    return numeric_only[:11]