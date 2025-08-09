import pandas as pd
from db_utils import db_connection  # Using the connection pool
import logging
from datetime import datetime
import os
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_report(start_date, end_date, output_format='csv', output_dir='reports'):
    """
    Generate comprehensive attendance report with multiple output options
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        output_format (str): 'csv', 'excel', or 'both'
        output_dir (str): Directory to save reports
    """
    try:
        # Validate and parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start_dt > end_dt:
            raise ValueError("Start date cannot be after end date")
            
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Base filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"attendance_report_{start_date}_to_{end_date}_{timestamp}"
        
        with db_connection() as conn:
            # Main attendance data
            attendance_query = """
                SELECT 
                    s.student_id, 
                    s.name, 
                    s.department,
                    a.date, 
                    TIME_FORMAT(a.time, '%H:%i:%s') as time,
                    a.status,
                    a.notes
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.date BETWEEN %s AND %s
                ORDER BY a.date, s.department, s.student_id
            """
            df_attendance = pd.read_sql_query(attendance_query, conn, params=(start_date, end_date))
            
            # Summary statistics
            summary_query = """
                SELECT 
                    s.department,
                    COUNT(DISTINCT s.student_id) as total_students,
                    SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) as late_count
                FROM students s
                LEFT JOIN attendance a ON s.student_id = a.student_id 
                    AND a.date BETWEEN %s AND %s
                GROUP BY s.department
                ORDER BY s.department
            """
            df_summary = pd.read_sql_query(summary_query, conn, params=(start_date, end_date))
            
            # Calculate percentages
            df_summary['present_percentage'] = (df_summary['present_count'] / 
                                              (df_summary['present_count'] + 
                                               df_summary['absent_count'] + 
                                               df_summary['late_count'])) * 100
            
        if df_attendance.empty:
            print(" No attendance records found for the selected date range")
            return
        
        # Generate reports based on requested format
        if output_format in ('csv', 'both'):
            csv_path = os.path.join(output_dir, f"{base_filename}.csv")
            df_attendance.to_csv(csv_path, index=False)
            print(f" CSV report saved to {csv_path}")
            
        if output_format in ('excel', 'both'):
            excel_path = os.path.join(output_dir, f"{base_filename}.xlsx")
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_attendance.to_excel(writer, sheet_name='Attendance Details', index=False)
                df_summary.to_excel(writer, sheet_name='Summary Statistics', index=False)
                
                # Add some Excel formatting
                workbook = writer.book
                for sheetname in writer.sheets:
                    worksheet = writer.sheets[sheetname]
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(cell.value)
                            except:
                                pass
                        adjusted_width = (max_length + 2) * 1.2
                        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                
            print(f"Excel report saved to {excel_path}")
            
        logging.info(f"Generated report from {start_date} to {end_date}")
        
    except ValueError as e:
        print(f" Error: {e}")
        logging.error(f"Invalid date input: {e}")
    except Exception as e:
        print(f" Unexpected error: {e}")
        logging.error(f"Report generation failed: {e}")

def main():
    parser = argparse.ArgumentParser(description='Generate attendance reports')
    parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--format', choices=['csv', 'excel', 'both'], 
                       default='csv', help='Output format')
    parser.add_argument('--output', default='reports', 
                       help='Output directory path')
    
    args = parser.parse_args()
    
    print("\n=== Attendance Report Generator ===")
    print(f"Generating report from {args.start_date} to {args.end_date}")
    generate_report(args.start_date, args.end_date, args.format, args.output)

if __name__ == "__main__":
    main()