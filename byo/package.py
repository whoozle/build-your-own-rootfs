import byo
import logging
import os.path
import yaml
import json

logger = logging.getLogger(__name__)

from enum import IntEnum

class State(IntEnum):
	NOT_PRESENT	= 0
	DOWNLOADED	= 1
	UNPACKED	= 2
	BUILT		= 3
	INSTALLED	= 4

class PackageState(object):
	def __init__(self, package_state_dir):
		self.state_dir = package_state_dir
		self.__state_file = os.path.join(package_state_dir, 'state')
		self.__files_file = os.path.join(package_state_dir, 'files')
		self.__load()

	@property
	def state(self):
		return self.__state

	@state.setter
	def state(self, state):
		self.__state = state
		with open(self.__state_file, "w") as f:
			f.write(state.name)

	def __load(self):
		self.__state = State.NOT_PRESENT
		if not os.path.exists(self.__state_file):
			return
		try:
			with open(self.__state_file) as f:
				self.__state = State[f.read()]
		except:
			logger.exception("failed loading current state")

	def reset(self):
		self.__state = State.NOT_PRESENT
		if os.path.exists(self.__state_file):
			os.unlink(self.__state_file)
		if os.path.exists(self.__files_file):
			os.unlink(self.__files_file)

	@property
	def files(self):
		with open(self.__files_file) as f:
			return json.loads(f.read())


	@files.setter
	def files(self, files):
		with open(self.__files_file, "w") as f:
			f.write(json.dumps(files))


class Metadata(object):
	def __init__(self, data):
		self.data = data

	def __format(self, text):
		while True:
			next = text.format(*[], **self.data)
			if next == text:
				break
			text = next
		return next


	def __format_var(self, name):
		url = self.data.get(name, None)
		if url is not None:
			return self.__format(url)

	@property
	def depends(self):
		return self.data.get('Depends-On', [])

	@property
	def public_key(self):
		return self.data.get('Public-Key', None)

	@property
	def signature(self):
		return self.__format_var('Signature')

	@property
	def fetch_url(self):
		return self.__format_var('Fetch')

	@property
	def install_dir(self):
		return self.__format_var('InstallDirectory')

	@property
	def copy_to_root(self):
		return self.data.get('InstallIntoCommonRoot', True)

	@property
	def build(self):
		return map(self.__format, self.data.get('Build', []))

def read_metadata(name):
	root = os.path.join(byo.root, 'packages')
	with open(os.path.join(root, name + ".package")) as f:
		data = yaml.safe_load(f)
	logger.debug('read metadata %s %s', name, data)
	data = Metadata(data)
	return data

def get_package_queue(name):
	queue = [name]
	result = []
	visited = set()
	while queue:
		current = queue
		queue = []
		for name in current:
			logger.debug('processing %s...' %name)
			if name not in visited:
				visited.add(name)
				result.append(name)
				data = read_metadata(name)
				queue += data.depends
	return reversed(result)

def get_installed_packages(prefix):
	root = os.path.join(byo.root, 'build.' + prefix.strip('-'))
	logger.debug('enumerating installed packages in %s', root)
	r = []
	packages = os.path.join(root, 'packages')
	for package in os.listdir(packages):
		if (package.startswith('.')):
			continue
		state = PackageState(os.path.join(packages, package))
		if state.state != State.INSTALLED:
			logger.warning('skipping package %s, %s', package, state.state)
		r.append(package)
	return r
