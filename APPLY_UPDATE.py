"""Apply source updates to an existing Windows project without replacing its data."""
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import sys
import zipfile

def apply_update(target, bundle=None):
    source=(bundle or Path(__file__).resolve().parent/'hivdr-system').resolve()
    target=Path(target).expanduser().resolve()
    if source==target:
        raise ValueError('Extract the update in a different folder from the existing project.')
    for relative in ('frontend/src/App.jsx','backend/app/main.py'):
        if not (target/relative).is_file():
            raise ValueError('Target is not the existing hivdr-system project: '+str(target))
    files=[]
    for file in source.rglob('*'):
        if not file.is_file(): continue
        relative=file.relative_to(source)
        if any(part in {'node_modules','dist','.venv','__pycache__','.pytest_cache','data','_update_backups'} for part in relative.parts): continue
        if file.suffix in {'.pyc','.sqlite3'} or file.name in {'local_login.txt','.env'}: continue
        files.append((file,relative))
    if not files:
        raise ValueError('Updated source files are missing. Place this script beside the extracted updated hivdr-system folder.')
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup=target/'_update_backups'/stamp
    backup.mkdir(parents=True)
    database=target/'backend/data/surveillance.sqlite3'
    if database.exists():
        with sqlite3.connect(database) as current, sqlite3.connect(backup/'surveillance.sqlite3') as snapshot:
            current.backup(snapshot)
    with zipfile.ZipFile(backup/'previous_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for _,relative in files:
            existing=target/relative
            if existing.is_file(): archive.write(existing,relative)
    for file,relative in files:
        destination=target/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(file,destination)
    return backup,len(files)

if __name__=='__main__':
    try:
        if len(sys.argv)!=2: raise ValueError('Usage: python APPLY_UPDATE.py "C:\\path\\to\\existing\\hivdr-system"')
        backup,count=apply_update(sys.argv[1])
        print('Updated',count,'source files.')
        print('Backup:',backup)
        print('Existing backend/data, credentials, .venv and node_modules were preserved.')
        print('Restart FastAPI, then run npm.cmd install and npm.cmd run dev inside frontend.')
    except Exception as error:
        print('Update could not finish:',error)
        sys.exit(1)
