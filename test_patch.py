import sys

def apply_patch(filename, patch_text):
    search_block = patch_text.split("<<<<<<< SEARCH\n")[1].split("=======\n")[0]
    replace_block = patch_text.split("=======\n")[1].split(">>>>>>> REPLACE\n")[0]

    with open(filename, 'r') as f:
        content = f.read()

    if search_block in content:
        content = content.replace(search_block, replace_block)
        with open(filename, 'w') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find search block")

with open('patch_file', 'r') as f:
    apply_patch('backend_engine/main.py', f.read())

with open('patch_file2', 'r') as f:
    apply_patch('backend_engine/main.py', f.read())

with open('patch_file3', 'r') as f:
    apply_patch('backend_engine/main.py', f.read())
