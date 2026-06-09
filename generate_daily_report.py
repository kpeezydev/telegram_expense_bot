import os
import pandas as pd
from datetime import datetime
import supabase_client
import drive_uploader

# Path to temporarily store the generated Excel file before upload
TEMP_DIR = os.path.join(os.path.dirname(__file__), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

def generate_and_upload_report_for_user(user_id: int, year: int, month: int):
    """Generates an Excel report for the given month and uploads to Google Drive."""
    print(f"Running report generation for user {user_id}...")
    
    month_name = datetime(year, month, 1).strftime('%B')

    # Fetch expenses for this month
    expenses = supabase_client.get_expenses_for_month(user_id, year, month)
    
    if not expenses:
        print(f"No expenses found for user {user_id} in {month_name} {year}. Skipping.")
        return

    # Convert to pandas DataFrame
    df = pd.DataFrame(expenses)
    
    # Reorder columns and rename for nicer output
    # Ensure 'date', 'description', 'amount' exist in the data
    columns_to_keep = ['date', 'description', 'amount']
    df = df[[col for col in columns_to_keep if col in df.columns]]
    df.columns = ['Date', 'Description', 'Amount ($)']
    
    # Add a total row
    total_amount = df['Amount ($)'].sum()
    total_row = pd.DataFrame([{'Date': 'Total', 'Description': '', 'Amount ($)': total_amount}])
    df = pd.concat([df, total_row], ignore_index=True)

    # Generate Excel file
    filename = f"Expenses_{user_id}_{month_name}_{year}.xlsx"
    filepath = os.path.join(TEMP_DIR, filename)
    
    # Export to Excel
    df.to_excel(filepath, index=False, engine='openpyxl')
    print(f"Generated report at {filepath}")

    # Upload to Google Drive
    file_id = drive_uploader.upload_file_to_drive(filepath, filename)
    if file_id:
        print(f"Successfully uploaded {filename} to Google Drive (ID: {file_id})")
        # Cleanup temp file
        os.remove(filepath)
    else:
        print(f"Failed to upload {filename} to Google Drive. File kept locally.")

def main():
    today = datetime.now()
    year = today.year
    month = today.month

    supabase = supabase_client.get_supabase()
    
    # Fetch distinct users from the current month
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month+1:02d}-01"

    print(f"Querying expenses from {start_date} to {end_date}")

    response = supabase.table("expenses") \
        .select("user_id") \
        .gte("date", start_date) \
        .lt("date", end_date) \
        .execute()
    
    users = set(item['user_id'] for item in response.data)
    print(f"Found {len(users)} users with expenses this month.")

    for user_id in users:
        try:
            generate_and_upload_report_for_user(user_id, year, month)
        except Exception as e:
            print(f"Failed to generate report for user {user_id}: {e}")

if __name__ == '__main__':
    main()
