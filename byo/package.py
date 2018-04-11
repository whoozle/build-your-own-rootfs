import byo
import logging
import os.path
import yaml

logger = logging.getLogger(__name__)

from enum import IntEnum

class State(IntEnum):
	NOT_PRESENT	= 0
	DOWNLOADED	= 1
	UNPACKED	= 2
	BUILT		= 3
	INSTALLED	= 4

class Metadata(object):
	def __init__(self, data):
		self.data = data

	def __format(self, url):
		return url.format(*[], **self.data)

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
	def build(self):
		return map(self.__format, self.data.get('Build', []))

def read_metadata(name):
	root = os.path.join(byo.root, 'packages')
	with open(os.path.join(root, name + ".package")) as f:
		data = yaml.load(f)
	logger.debug('read metadata %s', name)
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
