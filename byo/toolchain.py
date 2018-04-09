import os

def find_in_dir(path):
	if not os.path.isdir(path) or not os.access(path, os.R_OK):
		return
	for f in os.listdir(path):
		if f.endswith('gcc'):
			yield (path, f[:-3])

def find_in_dirs(dirs):
	for dir in dirs:
		yield from find_in_dir(dir)

def find_in_path():
	yield from find_in_dirs(os.getenv('PATH').split(':'))
