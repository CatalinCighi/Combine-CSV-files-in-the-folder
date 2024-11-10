import os
import json
import shutil
import re
from pathlib import Path
import pandas as pd
import fitz  # PyMuPDF


def get_folder_path():
    # Prompt the user to enter the path of the folder to be processed
    return input("Enter the path to the folder you want to process: ")


def load_json(json_path):
    # Load and return JSON data from the given path
    with open(json_path, "r") as file:
        print(f"Loading JSON data from {json_path}")
        return json.load(file)


def create_folder(path):
    # Create a folder at the given path if it does not already exist
    if not path.exists():
        print(f"Creating folder: {path}")
        path.mkdir(parents=True)


def categorize_files_by_type(base_path):
    # Categorize files by their extension and move them into corresponding folders
    print(f"Categorizing files in folder: {base_path}")
    file_inventory = {}
    for file in base_path.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            if ext not in file_inventory:
                file_inventory[ext] = []
            file_inventory[ext].append(file)

    # Create folders by type and move files
    for ext, files in file_inventory.items():
        type_folder = base_path / f"{ext[1:].upper()}_{len(files)}"
        create_folder(type_folder)
        for file in files:
            print(f"Moving file {file} to folder {type_folder}")
            shutil.move(str(file), str(type_folder))

    # Return the list of file extensions found
    print(f"File types found: {list(file_inventory.keys())}")
    return file_inventory.keys()


def associate_files_with_sources(base_path, file_types, json_data):
    # Associate files with banks based on filename or content matching
    for file_type in file_types:
        type_folder = (
            base_path
            / f"{file_type[1:].upper()}_{len(list((base_path / file_type[1:].upper()).iterdir()))}"
        )
        if not type_folder.exists():
            continue

        print(f"Associating files in folder: {type_folder}")
        for file in type_folder.iterdir():
            associated = False
            for bank, bank_data in json_data.items():
                bank_id = bank_data.get("Bank_ID", "")
                accounts = bank_data.get("Accounts", [])

                # Check filename for bank ID or any account ID
                if bank in file.name or re.search(bank_id, file.name):
                    print(f"File {file} matches bank {bank} by filename")
                    move_to_bank_folder(type_folder, file, bank)
                    associated = True
                    break

                # If not matched, check the accounts
                for account in accounts:
                    account_id = account.get("Account_ID", "")
                    if re.search(account_id, file.name):
                        print(
                            f"File {file} matches account {account['Account_Name']} of bank {bank} by filename"
                        )
                        move_to_bank_folder(type_folder, file, bank)
                        associated = True
                        break

                # If no match in filename, check the content
                if not associated:
                    if file.suffix.lower() == ".csv":
                        # Check CSV file contents for account ID
                        for account in accounts:
                            if check_csv_for_account_id(file, account["Account_ID"]):
                                print(
                                    f"File {file} matches account {account['Account_Name']} of bank {bank} by content (CSV)"
                                )
                                move_to_bank_folder(type_folder, file, bank)
                                associated = True
                                break
                    elif file.suffix.lower() == ".pdf":
                        # Check PDF file contents for account ID
                        for account in accounts:
                            if check_pdf_for_account_id(file, account["Account_ID"]):
                                print(
                                    f"File {file} matches account {account['Account_Name']} of bank {bank} by content (PDF)"
                                )
                                move_to_bank_folder(type_folder, file, bank)
                                associated = True
                                break
                if associated:
                    break

        # Update folder counts after categorizing
        update_subfolder_counts(type_folder)


def move_to_bank_folder(type_folder, file, bank):
    # Move the file to the subfolder for the specified bank, creating the folder if necessary
    bank_folder = type_folder / bank
    create_folder(bank_folder)
    print(f"Moving file {file} to bank folder {bank_folder}")
    shutil.move(str(file), str(bank_folder))


def check_csv_for_account_id(file, account_id):
    # Check if the account ID is present in the CSV file
    try:
        print(f"Checking CSV file {file} for account ID {account_id}")
        df = pd.read_csv(file)
        # Check if any row contains the account ID
        if df.apply(
            lambda row: row.astype(str).str.contains(account_id).any(), axis=1
        ).any():
            print(f"Account ID {account_id} found in CSV file {file}")
            return True
    except Exception as e:
        print(f"Error reading CSV file {file}: {e}")
    return False


def check_pdf_for_account_id(file, account_id):
    # Check if the account ID is present in the PDF file
    try:
        print(f"Checking PDF file {file} for account ID {account_id}")
        with fitz.open(file) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text()
                # Check if the account ID is in the extracted text
                if account_id in text:
                    print(
                        f"Account ID {account_id} found on page {page_number} of PDF file {file}"
                    )
                    return True
    except Exception as e:
        print(f"Error reading PDF file {file}: {e}")
    return False


def update_subfolder_counts(type_folder):
    # Update subfolder names to reflect the number of files they contain
    print(f"Updating subfolder counts in folder: {type_folder}")
    for subfolder in type_folder.iterdir():
        if subfolder.is_dir():
            count = len(list(subfolder.iterdir()))
            new_name = f"{subfolder.stem.split('_')[0]}_{count}"
            print(f"Renaming folder {subfolder} to {new_name}")
            subfolder.rename(type_folder / new_name)


def main():
    # Main function to handle user input and process the folder
    folder_path = Path(get_folder_path())
    json_path = Path("./bank.json")

    # Validate the provided paths
    if not folder_path.exists() or not json_path.exists():
        print("Invalid folder or JSON path.")
        return

    # Load bank data from the JSON file
    json_data = load_json(json_path)

    # Step 1: Categorize files by type
    file_types = categorize_files_by_type(folder_path)

    # Step 2: Associate files with sources based on JSON data
    associate_files_with_sources(folder_path, file_types, json_data)

    print("File categorization and association completed.")


if __name__ == "__main__":
    main()
