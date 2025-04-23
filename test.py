import os

def count_files_with_ld_json(directory="html_dumps"):
    total_files = 0
    files_with_ld_json = 0

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        if os.path.isfile(filepath):
            total_files += 1
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "ld+json" in content:
                        files_with_ld_json += 1
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    print(f"Total files: {total_files}")
    print(f"Files containing 'ld+json': {files_with_ld_json}")

# Run the function
count_files_with_ld_json()
