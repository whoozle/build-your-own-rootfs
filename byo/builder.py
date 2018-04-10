import logging
import byo.package
import urllib.request
import urllib.parse
import shutil
import shlex
import gpg
import os.path
import byo
from byo.process import Environment

logger = logging.getLogger(__name__)

class Builder(object):
	def __init__(self, prefix, target, options):
		self.prefix = prefix
		self.target = target
		self.options = options
		self.metadata = byo.package.read_metadata(target)
		self.gpg = gpg.Context()
		self.root = os.path.join(byo.root, 'build.' + prefix.strip('-'))
		self.archive = None
		self.work_dir = None
		self.env = Environment(self.root, target)
		self.__update_vars(self.metadata.data)

	def __update_vars(self, vars):
		vars['CrossCompilePrefix'] = self.prefix
		vars['Host'] = self.prefix.rstrip('-')

	def __fetch_cache(self, url, fname):
		downloads = self.env.create_dir('downloads')
		cached = os.path.join(downloads, fname)
		if os.path.exists(cached):
			return cached

		with urllib.request.urlopen(url) as response, open(cached, 'wb') as out_file:
			shutil.copyfileobj(response, out_file)

		logger.info('downloading finished')
		return cached

	def fetch(self):
		url = self.metadata.fetch_url
		if url is None:
			return
		parsed = urllib.parse.urlparse(url)
		fname = str(os.path.basename(parsed.path))
		logger.info('downloading url %s → %s', url, fname)
		self.archive = self.__fetch_cache(url, fname)

	def unpack(self):
		logger.info('unpacking...')
		self.work_dir = self.env.create_dir(self.target, 'work')
		self.env.exec(self.work_dir, 'tar', '--strip=1', '-xf', self.archive)

	def build(self):
		logger.info('building...')
		for cmd in self.metadata.build:
			cmd = shlex.split(cmd)
			self.env.exec(self.work_dir, *cmd)

	def install(self):
		logger.info('installing...')
	def package(self):
		logger.info('packaging...')
	def cleanup(self):
		logger.info('cleaning up...')


def _build(prefix, target, options):
	logger.info('building %s for %s...' %(target, prefix))
	builder = Builder(prefix, target, options)
	try:
		fname = builder.fetch()
		builder.unpack()
		builder.build()
		builder.install()
		builder.package()
	except:
		logger.exception('build failed')
		raise
	finally:
		builder.cleanup()

def build(prefix, target, options = {}):
	logger.info('building %s for %s...' %(target, prefix))
	for package in byo.package.get_package_queue(target):
		_build(prefix, package, options)
