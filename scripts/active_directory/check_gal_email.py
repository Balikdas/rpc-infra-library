import win32com.client
import os

def check_active_gal_users(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        
        with open(file_path, 'r') as f:
            email_list = [line.strip() for line in f if line.strip()]

        print(f"{'Email Address':<35} | {'Status':<12} | {'Name'}")
        print("-" * 75)

        for email in email_list:
            recipient = namespace.CreateRecipient(email)
            
            # Check if the email exists in the GAL at all
            if recipient.Resolve():
                addr_entry = recipient.AddressEntry
                ex_user = addr_entry.GetExchangeUser()
                
                if ex_user:
                    # Check for Account Status
                    # MAPI property 'PR_ACCOUNT_DISABLED' (0x3905000B) often indicates disabled status
                    try:
                        is_disabled = addr_entry.PropertyAccessor.GetProperty("http://schemas.microsoft.com")
                    except:
                        is_disabled = False # Default to active if property can't be read

                    if is_disabled:
                        status = "Disabled"
                    else:
                        status = "Active"
                    
                    name = ex_user.Name
                else:
                    status = "External/No-Ex"
                    name = addr_entry.Name
            else:
                status = "Not Found"
                name = "N/A"

            # Filter: Only print or process not "Active" accounts
            if status != "Active":
                print(f"{email:<35} | {status:<12} | {name}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    check_active_gal_users("emails.txt")
