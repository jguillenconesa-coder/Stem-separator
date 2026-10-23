"""Preserve installed dependency notices in redistributable builds."""
from importlib.metadata import distributions
from pathlib import Path
import sys

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
index = []
for distribution in distributions():
    name = distribution.metadata['Name']
    index.append(f"{name}=={distribution.version}: {distribution.metadata.get('License', 'See package notices')}")
    for item in distribution.files or []:
        if any(word in item.name.lower() for word in ('license', 'copying', 'notice')):
            path = Path(distribution.locate_file(item))
            if path.is_file():
                target = output / name / str(item).replace('..', '_').replace(':', '_')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
(output / 'DEPENDENCIES.txt').write_text('\n'.join(index), encoding='utf-8')
