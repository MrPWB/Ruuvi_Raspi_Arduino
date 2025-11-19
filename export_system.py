# web_server_with_export.py - Erweiterte Version mit Export-Funktionen
from flask import Flask, render_template, jsonify, request, send_file, make_response
from database import RuuviDatabase
import json
import csv
import io
import zipfile
from datetime import datetime, timedelta
import pandas as pd
import os
import sys
import tempfile

app = Flask(__name__)
db = RuuviDatabase()

# Existing routes...
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/export')
def export_page():
    """Export configuration page"""
    return render_template('export.html')

# Export API Endpoints
@app.route('/api/export/csv')
def export_csv():
    """Export data as CSV"""
    try:
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        device_filter = request.args.get('device', 'all')
        fields = request.args.get('fields', 'all').split(',')
        
        # Build query
        data = get_filtered_data(start_date, end_date, device_filter)
        
        if not data:
            return jsonify({'error': 'No data found for the specified criteria'}), 404
        
        # Create CSV
        output = io.StringIO()
        
        # Define field mapping
        field_mapping = {
            'timestamp': 'Zeitstempel',
            'created_at': 'Erstellt_am',
            'address': 'MAC_Adresse', 
            'ruuvi_mac': 'RuuviTag_MAC',
            'temperature_c': 'Temperatur_°C',
            'humidity_percent': 'Luftfeuchtigkeit_%',
            'pressure_hpa': 'Luftdruck_hPa',
            'acc_g_x': 'Beschleunigung_X_g',
            'acc_g_y': 'Beschleunigung_Y_g', 
            'acc_g_z': 'Beschleunigung_Z_g',
            'battery_mv': 'Batterie_mV',
            'tx_power_dbm': 'TX_Power_dBm',
            'movement_counter': 'Bewegungszähler',
            'measurement_sequence': 'Messsequenz',
            'rssi_dbm': 'RSSI_dBm',
            'sample_count': 'Anzahl_Samples',
            'sample_period_seconds': 'Sample_Zeitraum_s'
        }
        
        # Filter fields if specified
        if fields != ['all']:
            available_fields = [f for f in field_mapping.keys() if f in fields]
        else:
            available_fields = list(field_mapping.keys())
        
        # Create CSV writer
        fieldnames = [field_mapping.get(f, f) for f in available_fields]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write data
        for row in data:
            csv_row = {}
            for field in available_fields:
                if field in row:
                    value = row[field]
                    # Format timestamps for Excel compatibility
                    if field in ['timestamp', 'created_at'] and value:
                        value = format_timestamp_for_export(value)
                    csv_row[field_mapping.get(field, field)] = value
            writer.writerow(csv_row)
        
        # Prepare response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=ruuvi_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/json')
def export_json():
    """Export data as JSON"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        device_filter = request.args.get('device', 'all')
        pretty = request.args.get('pretty', 'false').lower() == 'true'
        
        data = get_filtered_data(start_date, end_date, device_filter)
        
        if not data:
            return jsonify({'error': 'No data found'}), 404
        
        # Format timestamps
        for row in data:
            for field in ['timestamp', 'created_at']:
                if field in row and row[field]:
                    row[field] = format_timestamp_for_export(row[field])
        
        export_data = {
            'export_info': {
                'generated_at': datetime.now().isoformat(),
                'date_range': {
                    'start': start_date,
                    'end': end_date
                },
                'device_filter': device_filter,
                'total_records': len(data)
            },
            'data': data
        }
        
        if pretty:
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        else:
            json_str = json.dumps(export_data, ensure_ascii=False)
        
        response = make_response(json_str)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=ruuvi_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/excel')
def export_excel():
    """Export data as Excel with multiple sheets"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        device_filter = request.args.get('device', 'all')
        
        data = get_filtered_data(start_date, end_date, device_filter)
        
        if not data:
            return jsonify({'error': 'No data found'}), 404
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Format timestamps
            for col in ['timestamp', 'created_at']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            
            # All data sheet
            df.to_excel(writer, sheet_name='Alle_Daten', index=False)
            
            # Summary sheet per device
            if device_filter == 'all' and 'address' in df.columns:
                devices = df['address'].unique()
                
                summary_data = []
                for device in devices:
                    device_data = df[df['address'] == device]
                    ruuvi_mac = device_data['ruuvi_mac'].iloc[0] if 'ruuvi_mac' in device_data.columns else device
                    
                    summary = {
                        'Gerät': ruuvi_mac,
                        'MAC_Adresse': device,
                        'Anzahl_Messungen': len(device_data),
                        'Zeitraum_von': device_data['created_at'].min() if 'created_at' in device_data.columns else None,
                        'Zeitraum_bis': device_data['created_at'].max() if 'created_at' in device_data.columns else None,
                        'Ø_Temperatur': device_data['temperature_c'].mean() if 'temperature_c' in device_data.columns else None,
                        'Min_Temperatur': device_data['temperature_c'].min() if 'temperature_c' in device_data.columns else None,
                        'Max_Temperatur': device_data['temperature_c'].max() if 'temperature_c' in device_data.columns else None,
                        'Ø_Luftfeuchtigkeit': device_data['humidity_percent'].mean() if 'humidity_percent' in device_data.columns else None,
                        'Ø_Luftdruck': device_data['pressure_hpa'].mean() if 'pressure_hpa' in device_data.columns else None,
                        'Min_Batterie': device_data['battery_mv'].min() if 'battery_mv' in device_data.columns else None,
                        'Max_Batterie': device_data['battery_mv'].max() if 'battery_mv' in device_data.columns else None,
                    }
                    summary_data.append(summary)
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Zusammenfassung', index=False)
                
                # Individual device sheets (limit to first 5 devices)
                for i, device in enumerate(devices[:5]):
                    device_data = df[df['address'] == device]
                    ruuvi_mac = device_data['ruuvi_mac'].iloc[0] if 'ruuvi_mac' in device_data.columns else device
                    sheet_name = f'Gerät_{i+1}_{ruuvi_mac[:8]}'
                    device_data.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Send file
        filename = f'ruuvi_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/statistics')
def export_statistics():
    """Generate statistical summary report"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        device_filter = request.args.get('device', 'all')
        
        data = get_filtered_data(start_date, end_date, device_filter)
        
        if not data:
            return jsonify({'error': 'No data found'}), 404
        
        df = pd.DataFrame(data)
        
        # Calculate statistics
        stats = {}
        
        # General statistics
        stats['general'] = {
            'total_records': len(df),
            'date_range': {
                'start': df['created_at'].min() if 'created_at' in df.columns else None,
                'end': df['created_at'].max() if 'created_at' in df.columns else None
            },
            'unique_devices': df['address'].nunique() if 'address' in df.columns else 0
        }
        
        # Temperature statistics
        if 'temperature_c' in df.columns:
            stats['temperature'] = {
                'mean': float(df['temperature_c'].mean()),
                'min': float(df['temperature_c'].min()),
                'max': float(df['temperature_c'].max()),
                'std': float(df['temperature_c'].std())
            }
        
        # Humidity statistics
        if 'humidity_percent' in df.columns:
            stats['humidity'] = {
                'mean': float(df['humidity_percent'].mean()),
                'min': float(df['humidity_percent'].min()),
                'max': float(df['humidity_percent'].max()),
                'std': float(df['humidity_percent'].std())
            }
        
        # Pressure statistics
        if 'pressure_hpa' in df.columns:
            stats['pressure'] = {
                'mean': float(df['pressure_hpa'].mean()),
                'min': float(df['pressure_hpa'].min()),
                'max': float(df['pressure_hpa'].max()),
                'std': float(df['pressure_hpa'].std())
            }
        
        # Per-device statistics
        if 'address' in df.columns:
            stats['devices'] = {}
            for device in df['address'].unique():
                device_data = df[df['address'] == device]
                device_stats = {
                    'record_count': len(device_data),
                    'ruuvi_mac': device_data['ruuvi_mac'].iloc[0] if 'ruuvi_mac' in device_data.columns else device
                }
                
                if 'temperature_c' in device_data.columns:
                    device_stats['temperature'] = {
                        'mean': float(device_data['temperature_c'].mean()),
                        'min': float(device_data['temperature_c'].min()),
                        'max': float(device_data['temperature_c'].max())
                    }
                
                stats['devices'][device] = device_stats
        
        return jsonify({
            'success': True,
            'generated_at': datetime.now().isoformat(),
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions
def get_filtered_data(start_date, end_date, device_filter):
    """Get filtered data based on parameters"""
    with db.get_cursor() as cursor:
        query = "SELECT * FROM sensor_data WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date + " 00:00:00")
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date + " 23:59:59")
        
        if device_filter and device_filter != 'all':
            query += " AND address = ?"
            params.append(device_filter)
        
        query += " ORDER BY created_at ASC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def format_timestamp_for_export(timestamp):
    """Format timestamp for better Excel/CSV compatibility"""
    if not timestamp:
        return timestamp
    
    try:
        # Handle different timestamp formats
        if isinstance(timestamp, str):
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        else:
            dt = timestamp
        
        # Return in German format
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except:
        return timestamp

# Add to existing routes from original web_server.py
@app.route('/api/devices')
def get_devices():
    try:
        devices = db.get_devices()
        return jsonify({
            'success': True,
            'data': devices,
            'count': len(devices)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/latest')
def get_latest():
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(max(1, limit), 1000)
        readings = db.get_latest_readings(limit)
        return jsonify({
            'success': True,
            'data': readings,
            'count': len(readings)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<address>')
def get_device_data(address):
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = min(max(1, hours), 8760)
        data = db.get_device_data(address, hours)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'device': address,
            'hours': hours
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/timerange')
def get_timerange_data():
    try:
        hours = request.args.get('hours', 24, type=int)
        hours = min(max(1, hours), 8760)
        data = db.get_readings_by_timerange(hours)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'hours': hours
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    try:
        with db.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="RuuviTag Web-Server with Export")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--db", default="ruuvi_data.db")
    
    args = parser.parse_args()
    
    # Initialize database
    if args.db != "ruuvi_data.db":
        db = RuuviDatabase(args.db)
    
    print(f"🚀 RuuviTag Web-Server with Export Features")
    print(f"📊 Dashboard: http://{args.host}:{args.port}/")
    print(f"📤 Export: http://{args.host}:{args.port}/export")
    
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)