#!/usr/bin/env python3
"""
RuuviTag Web-Server with Export Features
Flask-basierter Web-Server für die Visualisierung von RuuviTag-Sensordaten mit Export-Funktionen
"""

from flask import Flask, render_template, jsonify, request, send_file, make_response
from database import RuuviDatabase
import json
import csv
import io
import tempfile
from datetime import datetime
import os
import sys

app = Flask(__name__)

# Initialize database
db = RuuviDatabase()

@app.route('/')
def index():
    """Main dashboard page"""
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
            available_fields = [f for f in field_mapping.keys() if f in fields and f in data[0]]
        else:
            available_fields = [f for f in field_mapping.keys() if f in data[0]]
        
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
    """Export data as Excel (requires pandas and openpyxl)"""
    try:
        # Try to import pandas - if not available, return error with instructions
        try:
            import pandas as pd
        except ImportError:
            return jsonify({
                'error': 'Excel export requires pandas and openpyxl. Install with: pip3 install pandas openpyxl'
            }), 500
        
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
            
            # Summary sheet per device if multiple devices
            if device_filter == 'all' and 'address' in df.columns and df['address'].nunique() > 1:
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
                    }
                    
                    # Add statistical data if available
                    for col, name in [('temperature_c', 'Temperatur'), ('humidity_percent', 'Luftfeuchtigkeit'), ('pressure_hpa', 'Luftdruck')]:
                        if col in device_data.columns:
                            summary[f'Ø_{name}'] = device_data[col].mean()
                            summary[f'Min_{name}'] = device_data[col].min()
                            summary[f'Max_{name}'] = device_data[col].max()
                    
                    if 'battery_mv' in device_data.columns:
                        summary['Min_Batterie'] = device_data['battery_mv'].min()
                        summary['Max_Batterie'] = device_data['battery_mv'].max()
                    
                    summary_data.append(summary)
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Zusammenfassung', index=False)
        
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
        
        # Calculate basic statistics without pandas
        stats = {}
        
        # General statistics
        stats['general'] = {
            'total_records': len(data),
            'date_range': {
                'start': min([d['created_at'] for d in data]) if data else None,
                'end': max([d['created_at'] for d in data]) if data else None
            },
            'unique_devices': len(set([d['address'] for d in data if 'address' in d]))
        }
        
        # Temperature statistics
        temp_values = [d['temperature_c'] for d in data if 'temperature_c' in d and d['temperature_c'] is not None]
        if temp_values:
            stats['temperature'] = {
                'mean': sum(temp_values) / len(temp_values),
                'min': min(temp_values),
                'max': max(temp_values)
            }
        
        # Humidity statistics
        hum_values = [d['humidity_percent'] for d in data if 'humidity_percent' in d and d['humidity_percent'] is not None]
        if hum_values:
            stats['humidity'] = {
                'mean': sum(hum_values) / len(hum_values),
                'min': min(hum_values),
                'max': max(hum_values)
            }
        
        # Pressure statistics
        pres_values = [d['pressure_hpa'] for d in data if 'pressure_hpa' in d and d['pressure_hpa'] is not None]
        if pres_values:
            stats['pressure'] = {
                'mean': sum(pres_values) / len(pres_values),
                'min': min(pres_values),
                'max': max(pres_values)
            }
        
        # Per-device statistics
        devices = set([d['address'] for d in data if 'address' in d])
        if len(devices) > 1:
            stats['devices'] = {}
            for device in devices:
                device_data = [d for d in data if d.get('address') == device]
                device_stats = {
                    'record_count': len(device_data),
                    'ruuvi_mac': device_data[0].get('ruuvi_mac', device) if device_data else device
                }
                
                # Device temperature stats
                device_temps = [d['temperature_c'] for d in device_data if 'temperature_c' in d and d['temperature_c'] is not None]
                if device_temps:
                    device_stats['temperature'] = {
                        'mean': sum(device_temps) / len(device_temps),
                        'min': min(device_temps),
                        'max': max(device_temps)
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
            if 'T' in timestamp and 'Z' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp)
            elif ' ' in timestamp:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            else:
                return timestamp
        else:
            dt = timestamp
        
        # Return in German format
        return dt.strftime('%d.%m.%Y %H:%M:%S')
    except:
        return timestamp

@app.route('/api/devices')
def get_devices():
    """API: Get list of all devices with their latest information"""
    try:
        devices = db.get_devices()
        return jsonify({
            'success': True,
            'data': devices,
            'count': len(devices)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/latest')
def get_latest():
    """API: Get latest readings from all devices"""
    try:
        limit = request.args.get('limit', 50, type=int)
        # Limit should be reasonable
        limit = min(max(1, limit), 1000)
        
        readings = db.get_latest_readings(limit)
        return jsonify({
            'success': True,
            'data': readings,
            'count': len(readings)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/device/<address>')
def get_device_data(address):
    """API: Get data for specific device"""
    try:
        hours = request.args.get('hours', 24, type=int)
        # Limit hours to reasonable range
        hours = min(max(1, hours), 8760)  # Max 1 year
        
        data = db.get_device_data(address, hours)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'device': address,
            'hours': hours
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/timerange')
def get_timerange_data():
    """API: Get data for time range from all devices"""
    try:
        hours = request.args.get('hours', 24, type=int)
        # Limit hours to reasonable range
        hours = min(max(1, hours), 8760)  # Max 1 year
        
        data = db.get_readings_by_timerange(hours)
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'hours': hours
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """API: Get general statistics about the database"""
    try:
        with db.get_cursor() as cursor:
            # Total readings
            cursor.execute("SELECT COUNT(*) as total FROM sensor_data")
            total_readings = cursor.fetchone()['total']
            
            # Date range
            cursor.execute("""
                SELECT 
                    MIN(created_at) as first_reading,
                    MAX(created_at) as last_reading
                FROM sensor_data
            """)
            date_range = cursor.fetchone()
            
            # Device count
            cursor.execute("SELECT COUNT(DISTINCT address) as device_count FROM sensor_data")
            device_count = cursor.fetchone()['device_count']
            
            # Readings in last 24h
            cursor.execute("""
                SELECT COUNT(*) as recent_readings 
                FROM sensor_data 
                WHERE created_at >= datetime('now', '-24 hours')
            """)
            recent_readings = cursor.fetchone()['recent_readings']
            
        return jsonify({
            'success': True,
            'data': {
                'total_readings': total_readings,
                'device_count': device_count,
                'recent_readings_24h': recent_readings,
                'first_reading': date_range['first_reading'],
                'last_reading': date_range['last_reading']
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    """API: Health check endpoint"""
    try:
        # Simple database connectivity test
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

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

def main():
    """Main function to run the web server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RuuviTag Web-Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port number (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--db", default="ruuvi_data.db", help="Path to SQLite database file")
    
    args = parser.parse_args()
    
    # Initialize database with custom path if provided
    global db
    if args.db != "ruuvi_data.db":
        db = RuuviDatabase(args.db)
    
    # Check if database file exists
    if not os.path.exists(args.db):
        print(f"Warning: Database file '{args.db}' does not exist.")
        print("Make sure the logger is running to create the database.")
    
    # Check if templates directory exists
    if not os.path.exists('templates'):
        print("Error: 'templates' directory not found!")
        print("Please create the 'templates' directory and place 'dashboard.html' in it.")
        sys.exit(1)
    
    if not os.path.exists('templates/dashboard.html'):
        print("Error: 'templates/dashboard.html' not found!")
        print("Please place the dashboard.html file in the 'templates' directory.")
        sys.exit(1)
    
    print(f"Starting RuuviTag Web-Server...")
    print(f"Database: {args.db}")
    print(f"URL: http://{args.host}:{args.port}")
    print(f"Dashboard: http://{args.host}:{args.port}/")
    print(f"API Health: http://{args.host}:{args.port}/api/health")
    print("Press Ctrl+C to stop the server")
    
    try:
        app.run(
            host=args.host, 
            port=args.port, 
            debug=args.debug,
            threaded=True  # Enable threading for concurrent requests
        )
    except KeyboardInterrupt:
        print("\nShutting down web server...")
    except Exception as e:
        print(f"Error starting web server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()