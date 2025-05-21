import os

def update_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "{% extends 'main.html' %}" in content:
        content = content.replace("{% extends 'main.html' %}", "{% extends 'base/main.html' %}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")

def main():
    templates_dir = 'templates'
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                update_template(file_path)

if __name__ == '__main__':
    main() 