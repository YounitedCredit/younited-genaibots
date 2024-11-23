import os
import subprocess

def install_requirements():
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file == 'requirements.txt':
                file_path = os.path.join(root, file)
                subprocess.run(['pip', 'install', '-r', file_path], check=True)

if __name__ == '__main__':
    install_requirements()