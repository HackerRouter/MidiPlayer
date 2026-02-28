import zipfile
import re


def extract_duration_from_zip(zip_path):
    """Extract duration (seconds) from a datapack zip file.

    Reads speed from load.mcfunction and max note index from notes/ filenames.
    Each note tick = 80 score units; score increases by speed per game tick (20/sec).
    Formula: max_note * 80 / (speed * 20)
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            speed = None
            max_note = 0
            for name in zf.namelist():
                if name.endswith('load.mcfunction') and speed is None:
                    content = zf.read(name).decode('utf-8')
                    m = re.search(r'scoreboard players set speed \S+ (\d+)', content)
                    if m:
                        speed = int(m.group(1))
                elif '/notes/' in name and name.endswith('.mcfunction'):
                    fname = name.rsplit('/', 1)[-1].replace('.mcfunction', '')
                    if fname.isdigit():
                        max_note = max(max_note, int(fname))
            if speed and max_note > 0:
                return round(max_note * 80 / (speed * 20), 2)
    except Exception:
        pass
    return None
